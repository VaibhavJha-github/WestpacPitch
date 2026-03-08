"""OpenAI Whisper STT integration — optimised for speed."""
import io
import re
import time
from openai import OpenAI
from config import OPENAI_API_KEY

_client = OpenAI(api_key=OPENAI_API_KEY)

# Whisper hallucinations on silence/noise
HALLUCINATION_PHRASES = {
    "bye", "bye bye", "bye-bye", "byebye", "goodbye", "bye.",
    "thank you for watching", "thanks for watching",
    "subscribe", "like and subscribe",
    "thank you", "thanks", "you", "the end",
    "...", "", " ", "hmm", "um", "uh",
    "silence", "music", "applause", "laughter",
    "the customer may speak", "for more information",
    "please see the complete disclaimer",
    "hello", "hello.",
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
]


def is_hallucination(text: str) -> bool:
    lower = text.lower().strip('.,!? ')
    if lower in HALLUCINATION_PHRASES:
        return True
    if len(lower) <= 2:
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
    """Transcribe audio using Whisper."""
    start = time.time()

    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = filename

    response = _client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        response_format="verbose_json",
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
