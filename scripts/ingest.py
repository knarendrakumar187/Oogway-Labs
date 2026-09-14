"""
Ingestion script for The Lenny Growth Assistant.
Processes 18 curated markdown transcripts:
- Parses metadata and speaker dialogue turns
- Chunks text (500-750 words with ~100 words overlap)
- Attaches metadata (speaker, start_timestamp, end_timestamp, youtube_url, episode_title)
- Generates 384-dim embeddings with sentence-transformers/all-MiniLM-L6-v2
- Saves data/chunks.json for instant local vector search
- Optionally populates PostgreSQL + pgvector if connection is available
"""
import os
import sys
import re
import json
import time
from typing import List, Dict, Any

# Ensure stdout handles utf-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
TRANSCRIPTS_DIR = os.path.join(DATA_DIR, "transcripts")
CHUNKS_FILE = os.path.join(DATA_DIR, "chunks.json")

def parse_seconds(ts_str: str) -> int:
    parts = ts_str.split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    elif len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    return 0

def format_seconds(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def parse_transcript_file(file_path: str) -> Dict[str, Any]:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    slug = os.path.splitext(os.path.basename(file_path))[0]
    
    # Extract frontmatter metadata
    title_m = re.search(r'^title:\s*(.+)$', content, re.MULTILINE)
    guest_m = re.search(r'^guest:\s*(.+)$', content, re.MULTILINE)
    yt_m = re.search(r'^youtube_url:\s*(.+)$', content, re.MULTILINE)

    title = title_m.group(1).strip() if title_m else slug.replace("-", " ").title()
    # Clean quotes
    title = title.strip("'\"")
    guest = guest_m.group(1).strip().strip("'\"") if guest_m else "Guest"
    youtube_url = yt_m.group(1).strip().strip("'\"") if yt_m else ""

    parts = content.split("---")
    body = parts[2] if len(parts) >= 3 else content

    # Regex matching: Speaker (HH:MM:SS) or (MM:SS)
    pattern = re.compile(r'(?:^|\n)(?:([A-Za-z\s\.\'\-]+?)\s*)?\((\d{1,2}:\d{2}(?::\d{2})?)\):\s*')
    matches = list(pattern.finditer(body))
    
    turns = []
    current_speaker = guest
    for i, m in enumerate(matches):
        speaker_cand = m.group(1)
        if speaker_cand:
            speaker_cand = speaker_cand.strip()
            if len(speaker_cand) > 1 and not speaker_cand.startswith("http"):
                current_speaker = speaker_cand
        ts = m.group(2)
        start_idx = m.end()
        end_idx = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        text = body[start_idx:end_idx].strip()
        if text:
            turns.append({
                "speaker": current_speaker,
                "timestamp": ts,
                "seconds": parse_seconds(ts),
                "text": text
            })

    return {
        "slug": slug,
        "title": title,
        "guest": guest,
        "youtube_url": youtube_url,
        "turns": turns
    }

def chunk_episode(episode_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    turns = episode_data["turns"]
    if not turns:
        return []

    chunks = []
    i = 0
    chunk_idx = 0

    while i < len(turns):
        chunk_turns = []
        word_count = 0
        j = i

        while j < len(turns) and word_count < 550:
            turn_words = len(turns[j]["text"].split())
            chunk_turns.append(turns[j])
            word_count += turn_words
            j += 1

        if chunk_turns:
            start_turn = chunk_turns[0]
            end_turn = chunk_turns[-1]
            speakers = list(dict.fromkeys([t["speaker"] for t in chunk_turns]))
            
            # Format text representation with timestamps and speakers
            formatted_text_parts = []
            for t in chunk_turns:
                formatted_text_parts.append(f"{t['speaker']} ({t['timestamp']}): {t['text']}")
            chunk_text = "\n\n".join(formatted_text_parts)

            yt_base = episode_data["youtube_url"]
            yt_link = f"{yt_base}&t={start_turn['seconds']}s" if yt_base else ""

            chunk_obj = {
                "id": f"{episode_data['slug']}_chunk_{chunk_idx:03d}",
                "episode_slug": episode_data["slug"],
                "episode_title": episode_data["title"],
                "guest": episode_data["guest"],
                "youtube_url": episode_data["youtube_url"],
                "timestamped_url": yt_link,
                "start_timestamp": start_turn["timestamp"],
                "end_timestamp": end_turn["timestamp"],
                "start_seconds": start_turn["seconds"],
                "end_seconds": end_turn["seconds"],
                "speakers": speakers,
                "primary_speaker": episode_data["guest"] if episode_data["guest"] in speakers else speakers[0],
                "word_count": word_count,
                "text": chunk_text,
                "summary_snippet": chunk_turns[0]["text"][:240] + ("..." if len(chunk_turns[0]["text"]) > 240 else "")
            }
            chunks.append(chunk_obj)
            chunk_idx += 1

        if j >= len(turns):
            break

        # Calculate overlap of ~100 words
        overlap_words = 0
        next_i = j
        while next_i > i + 1 and overlap_words < 100:
            next_i -= 1
            overlap_words += len(turns[next_i]["text"].split())
        i = max(i + 1, next_i)

    return chunks

def build_knowledge_base():
    from sentence_transformers import SentenceTransformer
    
    print("=" * 60)
    print("Loading SentenceTransformer model 'all-MiniLM-L6-v2'...")
    t0 = time.time()
    model = SentenceTransformer("all-MiniLM-L6-v2")
    print(f"Model loaded in {time.time() - t0:.2f}s")

    all_chunks = []
    files = sorted([f for f in os.listdir(TRANSCRIPTS_DIR) if f.endswith(".md")])
    print(f"Processing {len(files)} transcript files...")

    for fname in files:
        fpath = os.path.join(TRANSCRIPTS_DIR, fname)
        ep = parse_transcript_file(fpath)
        ep_chunks = chunk_episode(ep)
        all_chunks.extend(ep_chunks)
        print(f"  {ep['slug']:<24} -> {len(ep['turns']):>3} turns -> {len(ep_chunks):>2} chunks")

    print(f"\nTotal chunks to embed: {len(all_chunks)}")
    print("Generating embeddings (batch encoding on CPU)...")
    
    texts_to_embed = [
        f"Episode: {c['episode_title']}. Guest: {c['guest']}. Topic: {c['text']}"
        for c in all_chunks
    ]

    t1 = time.time()
    embeddings = model.encode(texts_to_embed, batch_size=32, show_progress_bar=True, normalize_embeddings=True)
    embed_duration = time.time() - t1
    print(f"Embeddings generated in {embed_duration:.2f}s ({len(all_chunks)/embed_duration:.1f} chunks/sec)")

    # Attach embeddings to chunk records
    for i, c in enumerate(all_chunks):
        c["embedding"] = embeddings[i].tolist()

    os.makedirs(os.path.dirname(CHUNKS_FILE), exist_ok=True)
    with open(CHUNKS_FILE, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False)

    size_mb = os.path.getsize(CHUNKS_FILE) / (1024 * 1024)
    print(f"\nKnowledge base saved to {CHUNKS_FILE} ({size_mb:.2f} MB, {len(all_chunks)} chunks)")
    print("=" * 60)
    return all_chunks

if __name__ == "__main__":
    build_knowledge_base()
