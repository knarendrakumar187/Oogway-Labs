"""
Script to download and verify 18 curated landmark episodes of Lenny's Podcast
from the ChatPRD/lennys-podcast-transcripts public archive.
"""
import os
import urllib.request
import json
import re

EPISODES = [
    ("elena-verna", "Elena Verna - 10 Growth Tactics That Never Work & B2B PLG"),
    ("brian-balfour", "Brian Balfour - Four Growth Fits & Retention Loops"),
    ("casey-winters", "Casey Winters - Scaling Growth, SEO & Retention"),
    ("shreyas-doshi", "Shreyas Doshi - High-Agency PMing, Strategy & LNO Framework"),
    ("sean-ellis", "Sean Ellis - North Star Metrics & Growth Sprints"),
    ("annie-duke", "Annie Duke - Thinking in Bets & Decision Frameworks"),
    ("hila-qu", "Hila Qu - PLG Retention, Activation Metrics & Onboarding"),
    ("fareed-mosavat", "Fareed Mosavat - Product Experimentation at Slack & Instacart"),
    ("madhavan-ramanujam", "Madhavan Ramanujam - Monetization & Pricing Before Product"),
    ("dan-hockenmaier", "Dan Hockenmaier - Marketplace Liquidity & Network Effects"),
    ("kevin-weil", "Kevin Weil - Product Leadership at Twitter, Instagram, OpenAI"),
    ("bob-moesta", "Bob Moesta - Jobs to be Done Theory & Progress Forces"),
    ("april-dunford", "April Dunford - Product Positioning & Differentiated Value"),
    ("marily-nika", "Marily Nika - AI Product Management & AI Features"),
    ("gibson-biddle", "Gibson Biddle - Netflix Product Strategy & DHM Model"),
    ("geoffrey-moore", "Geoffrey Moore - Crossing the Chasm & Tech Adoption"),
    ("marty-cagan", "Marty Cagan - Empowered Product Teams & Product Operating Model"),
    ("brian-chesky", "Brian Chesky - Founder-Led Product & Airbnb Playbook"),
]

BASE_URL = "https://raw.githubusercontent.com/ChatPRD/lennys-podcast-transcripts/main/episodes"

def fetch_and_save_transcripts(output_dir="data/transcripts"):
    os.makedirs(output_dir, exist_ok=True)
    downloaded = 0
    
    print(f"Downloading {len(EPISODES)} curated episodes into {output_dir}...")
    for slug, label in EPISODES:
        out_file = os.path.join(output_dir, f"{slug}.md")
        if os.path.exists(out_file) and os.path.getsize(out_file) > 1000:
            print(f"  [cached] {slug} ({os.path.getsize(out_file)} bytes)")
            downloaded += 1
            continue
            
        url = f"{BASE_URL}/{slug}/transcript.md"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                content = resp.read().decode("utf-8")
                with open(out_file, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"  [downloaded] {slug} ({len(content)} chars)")
                downloaded += 1
        except Exception as e:
            print(f"  [FAILED] {slug} ({url}): {e}")

    print(f"\nCompleted: {downloaded}/{len(EPISODES)} episodes ready in {output_dir}")
    return downloaded

if __name__ == "__main__":
    fetch_and_save_transcripts()
