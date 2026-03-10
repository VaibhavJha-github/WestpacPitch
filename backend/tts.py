"""TTS integration — OpenAI TTS (fast) with ElevenLabs fallback."""
import time
import httpx
from openai import AsyncOpenAI
from config import OPENAI_API_KEY, ELEVENLABS_API_KEY, VOICE_MAP, DEFAULT_VOICE_ID
from typing import AsyncGenerator

_openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# OpenAI TTS voice mapping (these are the available voices)
# alloy, echo, fable, onyx, nova, shimmer
OPENAI_VOICE_MAP = {
    "en": "nova",
    "en-IN": "nova",
    "en-AU": "onyx",
    "hi": "nova",
    "zh": "nova",
    "zh-HK": "nova",
    "el": "nova",
}


def get_voice_id(language_code: str, override_voice: str | None = None) -> str:
    """Get ElevenLabs voice ID (for fallback)."""
    if override_voice:
        return override_voice
    return VOICE_MAP.get(language_code, DEFAULT_VOICE_ID)


async def synthesize_speech(
    text: str,
    voice_override: str | None = None,
    language_code: str = "en",
) -> bytes:
    """Generate TTS audio. Uses OpenAI TTS for speed."""
    if voice_override and ELEVENLABS_API_KEY:
        return await _elevenlabs_tts(text, voice_override, language_code)

    try:
        return await _openai_tts(text, language_code)
    except Exception as e:
        print(f"[TTS] OpenAI failed: {e}, trying ElevenLabs")
        return await _elevenlabs_tts(text, voice_override, language_code)


async def _openai_tts(text: str, language_code: str) -> bytes:
    """OpenAI TTS — fast, ~500ms."""
    voice = OPENAI_VOICE_MAP.get(language_code, "nova")

    response = await _openai_client.audio.speech.create(
        model="tts-1",  # tts-1 is faster than tts-1-hd
        voice=voice,
        input=text,
        response_format="mp3",
        speed=1.0,
    )

    return response.content


async def stream_speech(
    text: str,
    language_code: str = "en",
    chunk_size: int = 4096,
    voice_id: str | None = None,
) -> AsyncGenerator[bytes, None]:
    """Stream TTS as raw PCM16 24kHz chunks. ElevenLabs with selected voice, OpenAI fallback."""
    import os
    if os.getenv("USE_ELEVENLABS") and ELEVENLABS_API_KEY:
        try:
            print(f"[TTS] Using ElevenLabs voice={voice_id or 'default'}", flush=True)
            async for chunk in _stream_elevenlabs(text, language_code, chunk_size, voice_id=voice_id):
                yield chunk
            return
        except Exception as e:
            print(f"[TTS] ElevenLabs failed: {e}, falling back to OpenAI", flush=True)

    print(f"[TTS] Using OpenAI TTS", flush=True)
    async for chunk in _stream_openai(text, language_code, chunk_size):
        yield chunk


async def _stream_openai(
    text: str,
    language_code: str = "en",
    chunk_size: int = 4096,
) -> AsyncGenerator[bytes, None]:
    """Stream OpenAI TTS as raw PCM16 24kHz."""
    voice = OPENAI_VOICE_MAP.get(language_code, "nova")
    url = "https://api.openai.com/v1/audio/speech"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "tts-1",
        "voice": voice,
        "input": text,
        "response_format": "pcm",
        "speed": 1.0,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        async with client.stream("POST", url, json=payload, headers=headers) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes(chunk_size=chunk_size):
                yield chunk


# ElevenLabs voice mapping — Australian accent for Westpac
ELEVENLABS_VOICE_MAP = {
    "en": "IKne3meq5aSn9XLyUdCD",        # Charlie - Deep, Confident, Australian
}


async def _stream_elevenlabs(
    text: str,
    language_code: str = "en",
    chunk_size: int = 4096,
    voice_id: str | None = None,
) -> AsyncGenerator[bytes, None]:
    """Stream ElevenLabs TTS as raw PCM16 24kHz."""
    vid = voice_id or ELEVENLABS_VOICE_MAP.get(language_code, "IKne3meq5aSn9XLyUdCD")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{vid}/stream?output_format=pcm_24000"

    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True,
        },
    }

    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        async with client.stream("POST", url, json=payload, headers=headers) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes(chunk_size=chunk_size):
                yield chunk


async def _elevenlabs_tts(
    text: str,
    voice_override: str | None = None,
    language_code: str = "en",
) -> bytes:
    """ElevenLabs fallback."""
    vid = get_voice_id(language_code, voice_override)
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{vid}/stream"

    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True,
        },
    }

    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }

    chunks = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        async with client.stream("POST", url, json=payload, headers=headers) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes(chunk_size=4096):
                chunks.append(chunk)

    return b"".join(chunks)
