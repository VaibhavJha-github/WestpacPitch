"""STT — Groq Whisper (fast, ~200ms) → OpenAI Whisper (fallback)."""
import io
import re
import time
from config import OPENAI_API_KEY, GROQ_API_KEY

# Lazy clients
_openai_client = None
_groq_client = None


def _get_openai():
    global _openai_client
    if not _openai_client:
        from openai import OpenAI
        _openai_client = OpenAI(api_key=OPENAI_API_KEY)
    return _openai_client


def _get_groq():
    global _groq_client
    if not _groq_client:
        from groq import Groq
        _groq_client = Groq(api_key=GROQ_API_KEY)
    return _groq_client


HALLUCINATION_PHRASES = {
    "bye", "bye bye", "bye-bye", "byebye", "goodbye", "bye.",
    "thank you for watching", "thanks for watching",
    "subscribe", "like and subscribe",
    "thank you", "thanks", "you", "the end",
    "...", "", " ", "hmm", "um", "uh", "ah",
    "silence", "music", "applause", "laughter",
    "the customer may speak", "for more information",
    "please see the complete disclaimer",
    "hello", "hello.",
    "apa khabar", "obrigado", "gracias", "merci", "danke",
    "namaste", "salaam", "shalom", "ciao", "hola",
    "arigato", "arigatou", "xie xie", "xiexie",
    "salam", "bonjour", "guten tag",
    "assalamualaikum", "ni hao",
    "subtitles by the amara.org community",
    "subtitles by the amara org community",
    "amara.org", "amara org",
    "please subscribe", "like subscribe",
    "thank you for listening",
    "transcribed by", "translated by",
    "copyright", "all rights reserved",
}

HALLUCINATION_PATTERNS = [
    r'https?://\S+',
    r'www\.\S+',
    r'visit\s+\S+\.com',
    r'disclaimer',
    r'subscribe',
    r'for more information',
    r'please see the',
    r'[\U0001F300-\U0001F9FF]',
    r'👏|😄|🎵|🎶|♪',
    r'amara\.?org',
    r'subtitles?\s+by',
    r'transcribed?\s+by',
    r'translated?\s+by',
]


def is_hallucination(text: str) -> bool:
    lower = text.lower().strip('.,!? ')
    if lower in HALLUCINATION_PHRASES:
        return True
    if len(lower) <= 3:
        return True
    for pattern in HALLUCINATION_PATTERNS:
        if re.search(pattern, lower):
            return True
    words = lower.split()
    if len(words) >= 3 and len(set(words)) == 1:
        return True
    letters_only = re.sub(r'[^a-zA-Z\u0900-\u097F\u4e00-\u9fff\u0370-\u03ff]', '', text)
    if len(letters_only) < 3:
        return True
    return False


def transcribe_audio(audio_bytes: bytes, filename: str = "audio.webm") -> dict:
    """Transcribe audio. Tries Groq first (~200ms), falls back to OpenAI (~1.5s)."""
    # Try Groq first (much faster)
    if GROQ_API_KEY:
        try:
            return _transcribe_groq(audio_bytes, filename)
        except Exception as e:
            print(f"[STT] Groq failed: {e}, falling back to OpenAI")

    return _transcribe_openai(audio_bytes, filename)


def _transcribe_groq(audio_bytes: bytes, filename: str) -> dict:
    start = time.time()
    client = _get_groq()

    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = filename

    response = client.audio.transcriptions.create(
        model="whisper-large-v3",
        file=audio_file,
        response_format="verbose_json",
        language="en",
    )

    latency_ms = int((time.time() - start) * 1000)
    text = response.text.strip()

    if is_hallucination(text):
        text = ""

    return {
        "text": text,
        "language": getattr(response, "language", "english"),
        "latency_ms": latency_ms,
    }


def _transcribe_openai(audio_bytes: bytes, filename: str) -> dict:
    start = time.time()
    client = _get_openai()

    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = filename

    response = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        response_format="verbose_json",
        language="en",
    )

    latency_ms = int((time.time() - start) * 1000)
    text = response.text.strip()

    if is_hallucination(text):
        text = ""

    return {
        "text": text,
        "language": getattr(response, "language", "english"),
        "latency_ms": latency_ms,
    }


LANGUAGE_CODE_MAP = {
    "english": "en",
    "hindi": "hi",
    "urdu": "hi",
    "mandarin": "zh",
    "chinese": "zh",
    "cantonese": "zh-HK",
    "greek": "el",
}


def detected_language_to_code(language: str) -> str:
    return LANGUAGE_CODE_MAP.get(language.lower(), "en")
