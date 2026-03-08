"""LLM — Groq (fastest) → GPT-4o-mini (fallback) | Claude (post-call summary)."""
import time
import json
import httpx
from config import (
    ANTHROPIC_API_KEY, CLAUDE_MODEL,
    GROQ_API_KEY, OPENAI_API_KEY,
    VLLM_BASE_URL, VLLM_MODEL, RUNPOD_API_KEY,
)
from prompts import VOICE_AGENT_SYSTEM_PROMPT, SUMMARY_PROMPT

# Groq model for live conversation
GROQ_MODEL = "llama-3.3-70b-versatile"


async def generate_response(
    messages: list[dict],
    context: str = "",
    temperature: float = 0.7,
    max_tokens: int = 150,
) -> dict:
    """Live call response. Groq → GPT-4o-mini → RunPod fallback."""
    start = time.time()

    system_message = VOICE_AGENT_SYSTEM_PROMPT.replace("{context}", context or "No additional context.")
    full_messages = [{"role": "system", "content": system_message}] + messages

    # Groq first (fastest — ~200ms)
    if GROQ_API_KEY:
        try:
            return await _call_groq(full_messages, temperature, max_tokens, start)
        except Exception as e:
            print(f"[LLM] Groq failed: {e}, falling back")

    # GPT-4o-mini fallback
    if OPENAI_API_KEY:
        try:
            return await _call_openai(full_messages, temperature, max_tokens, start)
        except Exception as e:
            print(f"[LLM] OpenAI failed: {e}")

    # RunPod last resort
    if VLLM_BASE_URL:
        return await _call_runpod_vllm(full_messages, temperature, max_tokens, start)

    raise RuntimeError("No LLM provider configured")


async def generate_summary(transcript: list[dict]) -> dict:
    """Post-call summary. Claude for quality."""
    transcript_text = "\n".join(
        f"{'Customer' if t['speaker'] == 'customer' else 'Bot'}: {t['text']}"
        for t in transcript
    )

    prompt = SUMMARY_PROMPT.replace("{transcript}", transcript_text)
    start = time.time()
    system_message = "You are an AI analyst for Westpac Bank."
    msgs = [{"role": "system", "content": system_message}, {"role": "user", "content": prompt}]

    if ANTHROPIC_API_KEY:
        try:
            result = await _call_claude(msgs, system_message, 0.3, 600, start)
            return _parse_summary(result["text"])
        except Exception as e:
            print(f"[SUMMARY] Claude failed: {e}")

    # Fallback to Groq for summary too
    if GROQ_API_KEY:
        try:
            result = await _call_groq(msgs, 0.3, 600, start)
            return _parse_summary(result["text"])
        except Exception as e:
            print(f"[SUMMARY] Groq failed: {e}")

    result = await _call_openai(msgs, 0.3, 600, start)
    return _parse_summary(result["text"])


def _parse_summary(text: str) -> dict:
    try:
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return json.loads(text.strip())
    except (json.JSONDecodeError, IndexError):
        return {
            "short_summary": text[:200],
            "long_summary": text,
            "primary_intent": "Unknown",
            "routed_team": "Home Loans / Mortgages",
            "recommended_strategy_title": "Review Required",
            "recommended_strategy_description": "Manual review needed.",
            "collected_data": [],
            "sentiment_label": "Neutral",
            "sentiment_note": "",
        }


async def _call_groq(
    messages: list[dict], temperature: float, max_tokens: int, start: float
) -> dict:
    """Groq — insanely fast inference (~200ms)."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    text = data["choices"][0]["message"]["content"]
    latency_ms = int((time.time() - start) * 1000)
    return _parse_response(text, latency_ms, provider="groq")


async def _call_openai(
    messages: list[dict], temperature: float, max_tokens: int, start: float
) -> dict:
    """GPT-4o-mini fallback."""
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)

    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    text = resp.choices[0].message.content
    latency_ms = int((time.time() - start) * 1000)
    return _parse_response(text, latency_ms, provider="gpt-4o-mini")


async def _call_claude(
    full_messages: list[dict], system_message: str,
    temperature: float, max_tokens: int, start: float
) -> dict:
    """Claude — quality for summaries."""
    claude_messages = []
    for msg in full_messages:
        if msg["role"] == "system":
            continue
        claude_messages.append({"role": msg["role"], "content": msg["content"]})

    if not claude_messages or claude_messages[0]["role"] != "user":
        claude_messages.insert(0, {"role": "user", "content": "Hello"})

    merged = []
    for msg in claude_messages:
        if merged and merged[-1]["role"] == msg["role"]:
            merged[-1]["content"] += "\n" + msg["content"]
        else:
            merged.append(msg.copy())

    url = "https://api.anthropic.com/v1/messages"
    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system_message,
        "messages": merged,
    }
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    text = data["content"][0]["text"]
    latency_ms = int((time.time() - start) * 1000)
    return _parse_response(text, latency_ms, provider="claude")


async def _call_runpod_vllm(
    messages: list[dict], temperature: float, max_tokens: int, start: float
) -> dict:
    """RunPod vLLM — last resort."""
    url = f"{VLLM_BASE_URL}/chat/completions"
    payload = {
        "model": VLLM_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {RUNPOD_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    text = data["choices"][0]["message"]["content"]
    latency_ms = int((time.time() - start) * 1000)
    return _parse_response(text, latency_ms, provider="runpod-vllm")


def _parse_response(text: str, latency_ms: int, provider: str = "unknown") -> dict:
    tool_call = None

    if '{"tool"' in text:
        try:
            start_idx = text.index('{"tool"')
            brace_count = 0
            end_idx = start_idx
            for i in range(start_idx, len(text)):
                if text[i] == '{':
                    brace_count += 1
                elif text[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i + 1
                        break

            json_str = text[start_idx:end_idx]
            tool_call = json.loads(json_str)
            text = (text[:start_idx] + text[end_idx:]).strip()
        except (ValueError, json.JSONDecodeError):
            pass

    return {
        "text": text,
        "tool_call": tool_call,
        "latency_ms": latency_ms,
        "provider": provider,
    }


async def test_runpod_connection() -> dict:
    if not VLLM_BASE_URL:
        return {"status": "not_configured"}
    try:
        start = time.time()
        result = await _call_runpod_vllm(
            [{"role": "system", "content": "You are helpful."}, {"role": "user", "content": "Say ready."}],
            0.1, 5, start,
        )
        return {"status": "ok", "latency_ms": result["latency_ms"]}
    except Exception as e:
        return {"status": "error", "message": str(e)}
