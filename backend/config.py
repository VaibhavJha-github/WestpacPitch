import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

# Load .env first, then allow .env.local to override for machine-specific/demo values.
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR / ".env.local", override=True)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6-20250514")
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
RUNPOD_ENDPOINT_ID = os.getenv("RUNPOD_ENDPOINT_ID", "")
# RunPod Serverless vLLM OpenAI-compatible endpoint
# Format: https://api.runpod.ai/v2/{endpoint_id}/openai/v1
VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "")
if not VLLM_BASE_URL and RUNPOD_ENDPOINT_ID:
    VLLM_BASE_URL = f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}/openai/v1"
VLLM_MODEL = os.getenv("VLLM_MODEL", "Qwen/Qwen2.5-14B-Instruct-AWQ")
DEFAULT_VOICE_ID = os.getenv("DEFAULT_VOICE_ID", "omLr0bN17lYIC1JWLSYV")

# Twilio
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")  # Your Twilio number e.g. +61...
CUSTOMER_PHONE_NUMBER = os.getenv("CUSTOMER_PHONE_NUMBER", "")  # Demo customer's real phone for SMS

VOICE_MAP = {
    "en-IN": os.getenv("VOICE_ID_INDIAN_EN", "omLr0bN17lYIC1JWLSYV"),
    "en-AU": os.getenv("VOICE_ID_AUSTRALIAN_EN", "snyKKuaGYk1VUEh42zbW"),
    "hi": os.getenv("VOICE_ID_HINDI", "6MoEUz34rbRrmmyxgRm4"),
    "el": os.getenv("VOICE_ID_GREEK", "CsiIKWiAQRGMe7qh9P9q"),
    "zh": os.getenv("VOICE_ID_MANDARIN", "DowyQ68vDpgFYdWVGjc3"),
    "zh-HK": os.getenv("VOICE_ID_CANTONESE", "R5E9sH7cGUEbuu7YE7K7"),
}
