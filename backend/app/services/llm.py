import json
import time
import logging
import urllib.request
import urllib.error
from typing import List, Dict, Any, Tuple, Optional
from backend.app.config import settings

logger = logging.getLogger(__name__)

class ProviderError(Exception):
    def __init__(self, code: str, message: str, troubleshooting: Optional[str] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.troubleshooting = troubleshooting or "Check your provider settings and configuration in .env."

SYSTEM_PROMPT = """You are the Lenny Growth Assistant, an expert AI advisor for product managers and growth leaders, grounded strictly and exclusively in the provided transcripts from Lenny's Podcast.

CRITICAL INSTRUCTIONS:
1. Grounding: Answer ONLY based on the facts, frameworks, and insights in the provided transcript context. Never fabricate facts, speakers, or episodes.
2. Attribution: Explicitly mention which guest (e.g. Elena Verna, Brian Balfour, Casey Winters) made the point and include their timestamp.
3. Structure: Provide a clear, actionable summary with bullet points, key takeaways, and exact quotes where relevant.
4. Refusal: If the provided context does not contain relevant insights to answer the question, do not guess or hallucinate. Clearly say: "I couldn't find any discussion covering this topic in the indexed episodes of Lenny's Podcast."
"""

def get_installed_ollama_models(base_url: str) -> list:
    try:
        req = urllib.request.Request(f"{base_url}/api/tags")
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [m.get("name", "") for m in data.get("models", [])]
    except Exception:
        return []

def resolve_ollama_model(base_url: str, requested_model: Optional[str] = None) -> str:
    target_model = requested_model or settings.OLLAMA_MODEL
    installed = get_installed_ollama_models(base_url)
    if installed:
        if target_model not in installed:
            matching = [m for m in installed if target_model.split(":")[0] in m]
            if matching:
                return matching[0]
            return installed[0]
    return target_model

def call_ollama(prompt: str, system_prompt: str, model: Optional[str] = None) -> str:
    base_url = settings.OLLAMA_BASE_URL.rstrip("/")
    target_model = resolve_ollama_model(base_url, model)

    url = f"{base_url}/api/chat"

    payload = {
        "model": target_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "stream": False,
        "options": {
            "temperature": 0.2
        }
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=settings.OLLAMA_TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("message", {}).get("content", "")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            logger.warning("Ollama model '%s' not found on local instance: %s", target_model, e)
            raise ProviderError(
                code="OLLAMA_MODEL_NOT_FOUND",
                message=f"Model '{target_model}' is not yet downloaded in local Ollama.",
                troubleshooting=(
                    f"1. Open your terminal or PowerShell and run: `ollama pull {target_model}`\n"
                    f"2. Or switch to 'Local Extractive' in the sidebar for instant zero-dependency offline synthesis.\n"
                    f"3. Or switch to 'Groq LPU' for sub-second cloud inference."
                )
            )
        else:
            raise ProviderError(
                code="OLLAMA_HTTP_ERROR",
                message=f"Ollama returned HTTP {e.code}: {e.reason}",
                troubleshooting="Check Ollama logs or restart the Ollama application."
            )
    except urllib.error.URLError as e:
        logger.warning("Ollama connection failed at %s: %s", url, e)
        raise ProviderError(
            code="OLLAMA_NOT_REACHABLE",
            message=f"Ollama service is not reachable at {base_url}. {e}",
            troubleshooting=(
                f"1. Make sure Ollama is installed and running (`ollama serve` or open Ollama Desktop).\n"
                f"2. Pull the model: `ollama run {target_model}`\n"
                f"3. Or switch to 'Groq LPU' or 'Local Extractive' in the sidebar."
            )
        )
    except Exception as e:
        logger.error("Ollama unexpected error: %s", e)
        raise ProviderError(
            code="OLLAMA_ERROR",
            message=f"Error executing Ollama model inference: {e}",
            troubleshooting=f"Check Ollama console logs or try running `ollama run {target_model}` directly."
        )

def call_openai(prompt: str, system_prompt: str, model: Optional[str] = None) -> str:
    api_key = settings.OPENAI_API_KEY
    if not api_key or api_key.startswith("sk-placeholder") or api_key == "":
        raise ProviderError(
            code="OPENAI_KEY_MISSING",
            message="OpenAI API key is missing or not configured.",
            troubleshooting="Set OPENAI_API_KEY=sk-... in your .env file or switch LLM_PROVIDER=mock or ollama."
        )

    target_model = model or settings.OPENAI_MODEL
    url = "https://api.openai.com/v1/chat/completions"

    payload = {
        "model": target_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        logger.error("OpenAI HTTP %d: %s", e.code, err_body)
        raise ProviderError(
            code=f"OPENAI_HTTP_{e.code}",
            message=f"OpenAI API returned error code {e.code}: {e.reason}",
            troubleshooting="Verify that your OPENAI_API_KEY is valid and has active credits."
        )
    except Exception as e:
        raise ProviderError(code="OPENAI_ERROR", message=f"OpenAI request failed: {e}")

def call_anthropic(prompt: str, system_prompt: str, model: Optional[str] = None) -> str:
    api_key = settings.ANTHROPIC_API_KEY
    if not api_key or api_key == "":
        raise ProviderError(
            code="ANTHROPIC_KEY_MISSING",
            message="Anthropic API key is missing or not configured.",
            troubleshooting="Set ANTHROPIC_API_KEY=sk-ant-... in your .env file or switch LLM_PROVIDER=mock or ollama."
        )

    target_model = model or settings.ANTHROPIC_MODEL
    url = "https://api.anthropic.com/v1/messages"

    payload = {
        "model": target_model,
        "system": system_prompt,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1500,
        "temperature": 0.2
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["content"][0]["text"]
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        logger.error("Anthropic HTTP %d: %s", e.code, err_body)
        raise ProviderError(
            code=f"ANTHROPIC_HTTP_{e.code}",
            message=f"Anthropic API returned error code {e.code}: {e.reason}",
            troubleshooting="Verify that your ANTHROPIC_API_KEY is valid and has active balance."
        )
    except Exception as e:
        raise ProviderError(code="ANTHROPIC_ERROR", message=f"Anthropic request failed: {e}")

def call_groq(prompt: str, system_prompt: str, model: Optional[str] = None) -> str:
    """Call Groq's OpenAI-compatible inference API (https://api.groq.com/openai/v1)."""
    api_key = settings.GROQ_API_KEY
    if not api_key or api_key == "":
        raise ProviderError(
            code="GROQ_KEY_MISSING",
            message="Groq API key is missing or not configured.",
            troubleshooting="Set GROQ_API_KEY=gsk_... in your .env file. Get a free key at https://console.groq.com/"
        )

    target_model = model or settings.GROQ_MODEL
    url = "https://api.groq.com/openai/v1/chat/completions"

    payload = {
        "model": target_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 1500
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
    )

    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt == 0:
                logger.warning("Groq rate limit (429) hit, retrying in 2 seconds...")
                time.sleep(2.0)
                continue
            err_body = e.read().decode("utf-8", errors="ignore")
            logger.error("Groq HTTP %d: %s", e.code, err_body)
            raise ProviderError(
                code=f"GROQ_HTTP_{e.code}",
                message=f"Groq API returned error {e.code}: {e.reason}",
                troubleshooting="Groq free tier rate limit reached. Wait a few seconds or switch provider in the sidebar."
            )
        except Exception as e:
            raise ProviderError(code="GROQ_ERROR", message=f"Groq request failed: {e}")

def call_mock_synthesis(prompt: str, retrieved_chunks: List[Dict[str, Any]], is_grounded: bool) -> str:
    """
    Extractive synthesis provider for zero-dependency offline demo evaluation.
    Produces highly coherent, grounded answers directly from the retrieved transcript segments.
    """
    if not is_grounded or not retrieved_chunks:
        return (
            "I searched through the indexed episodes of Lenny's Podcast, but could not find a relevant "
            "discussion answering this specific question. To maintain strict grounding and avoid hallucinations, "
            "I do not fabricate answers outside the podcast corpus."
        )

    primary_chunk = retrieved_chunks[0]
    guest = primary_chunk.get("guest", "the guest")
    title = primary_chunk.get("episode_title", "the episode")
    start_ts = primary_chunk.get("start_timestamp", "00:00:00")
    end_ts = primary_chunk.get("end_timestamp", "00:00:00")
    
    # Extract dialogue insights
    text = primary_chunk.get("text", "")
    lines = [line.strip() for line in text.split("\n\n") if line.strip()]
    quotes = [l for l in lines if not l.lower().startswith("lenny")]
    chosen_quotes = quotes[:3] if quotes else lines[:2]

    insights = []
    for q in chosen_quotes:
        parts = q.split("):", 1)
        if len(parts) == 2:
            spk_ts = parts[0] + ")"
            quote_content = parts[1].strip()
            # Truncate if long
            if len(quote_content) > 300:
                quote_content = quote_content[:297] + "..."
            insights.append(f"- **{spk_ts}**: \"{quote_content}\"")
        else:
            insights.append(f"- {q[:250]}")

    other_sources = []
    for c in retrieved_chunks[1:]:
        other_sources.append(f"*{c['guest']}* in episode *{c['episode_title']}* ({c['start_timestamp']})")

    secondary_str = f"\n\n**Additional perspective:**\n- Also addressed by " + "; ".join(other_sources) if other_sources else ""

    response = (
        f"Based on **{guest}** in ***{title}*** ({start_ts} – {end_ts}):\n\n"
        f"Here are the core takeaways from the conversation:\n\n"
        + "\n\n".join(insights) +
        secondary_str +
        f"\n\n**Key Takeaway for PMs:** Focus on sustainable, loop-driven principles rather than one-off hacks. Ground your roadmap in verified user mechanics and clear metrics."
    )
    return response

def generate_llm_response(
    query: str,
    retrieved_chunks: List[Dict[str, Any]],
    is_grounded: bool,
    provider: Optional[str] = None
) -> Tuple[str, str]:
    """
    Routes to the configured or requested provider.
    Returns: Tuple[response_text, provider_name]
    """
    active_provider = (provider or settings.LLM_PROVIDER).lower()

    if not is_grounded or not retrieved_chunks:
        refusal = (
            "I searched through the indexed episodes of Lenny's Podcast, but could not find a relevant "
            "discussion answering this question. To maintain strict grounding and avoid hallucinations, "
            "I only provide answers directly supported by the podcast transcripts."
        )
        return refusal, active_provider

    # Build grounded context
    context_blocks = []
    for i, chunk in enumerate(retrieved_chunks):
        block = (
            f"--- SOURCE {i+1} ---\n"
            f"Episode: {chunk.get('episode_title')}\n"
            f"Guest: {chunk.get('guest')}\n"
            f"Timestamp Range: {chunk.get('start_timestamp')} to {chunk.get('end_timestamp')}\n"
            f"Excerpts:\n{chunk.get('text')}\n"
        )
        context_blocks.append(block)

    full_context = "\n".join(context_blocks)
    user_prompt = (
        f"USER QUESTION:\n{query}\n\n"
        f"PODCAST TRANSCRIPT CONTEXT:\n{full_context}\n\n"
        f"Please provide a grounded, actionable answer citing the specific guests, episodes, and timestamps."
    )

    if active_provider == "mock":
        text = call_mock_synthesis(query, retrieved_chunks, is_grounded)
        return text, "mock"

    elif active_provider == "ollama":
        base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        active_model = resolve_ollama_model(base_url)
        text = call_ollama(user_prompt, SYSTEM_PROMPT, active_model)
        return text, f"ollama ({active_model})"

    elif active_provider == "openai":
        text = call_openai(user_prompt, SYSTEM_PROMPT)
        return text, f"openai ({settings.OPENAI_MODEL})"

    elif active_provider == "anthropic":
        text = call_anthropic(user_prompt, SYSTEM_PROMPT)
        return text, f"anthropic ({settings.ANTHROPIC_MODEL})"

    elif active_provider == "groq":
        text = call_groq(user_prompt, SYSTEM_PROMPT)
        return text, f"groq ({settings.GROQ_MODEL})"

    else:
        # Fallback to mock with notice
        logger.warning("Unrecognized provider '%s'. Defaulting to mock.", active_provider)
        text = call_mock_synthesis(query, retrieved_chunks, is_grounded)
        return text, f"mock (fallback from {active_provider})"

def get_available_providers() -> Dict[str, bool]:
    """Check availability of each provider."""
    # Check Ollama
    ollama_ok = False
    try:
        req = urllib.request.Request(f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags")
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            if resp.status == 200:
                ollama_ok = True
    except Exception:
        ollama_ok = False

    openai_ok = bool(settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("sk-placeholder") and len(settings.OPENAI_API_KEY) > 10)
    anthropic_ok = bool(settings.ANTHROPIC_API_KEY and len(settings.ANTHROPIC_API_KEY) > 10)
    groq_ok = bool(settings.GROQ_API_KEY and settings.GROQ_API_KEY.startswith("gsk_") and len(settings.GROQ_API_KEY) > 10)

    return {
        "ollama": ollama_ok,
        "openai": openai_ok,
        "anthropic": anthropic_ok,
        "groq": groq_ok,
        "mock": True  # Always available
    }
