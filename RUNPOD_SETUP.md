# RunPod Setup Notes

RunPod is optional in the current repository.

## Current status

- The codebase still supports RunPod-related environment variables in `backend/config.py`.
- The current primary live response path is Groq first, then OpenAI fallback.
- RunPod is not the main active provider in the current live turn-processing path.

That means you do not need RunPod to run the current demo locally.

Use RunPod only if you want to prepare an alternate hosted OpenAI-compatible endpoint for future experimentation or to reintroduce a custom vLLM path.

---

## Environment Variables

These are the RunPod-related variables currently recognized by the backend:

```env
RUNPOD_API_KEY=
RUNPOD_ENDPOINT_ID=
VLLM_BASE_URL=
VLLM_MODEL=Qwen/Qwen2.5-14B-Instruct-AWQ
```

If `VLLM_BASE_URL` is not set but `RUNPOD_ENDPOINT_ID` is set, the backend constructs:

```text
https://api.runpod.ai/v2/<RUNPOD_ENDPOINT_ID>/openai/v1
```

---

## Suggested RunPod Configuration

If you still want a compatible endpoint ready:

### Model

- `Qwen/Qwen2.5-14B-Instruct-AWQ`

### Worker shape

- A40 48GB or A6000 48GB
- max workers: 1
- active workers: 0 for cost savings, 1 if you want reduced cold starts

### Typical environment values

```env
MODEL_NAME=Qwen/Qwen2.5-14B-Instruct-AWQ
MAX_MODEL_LEN=8192
GPU_MEMORY_UTILIZATION=0.90
DTYPE=half
QUANTIZATION=awq
DISABLE_LOG_STATS=true
TOKENIZER_MODE=auto
MAX_NUM_SEQS=1
```

---

## How To Test It Independently

If you provision a RunPod OpenAI-compatible endpoint, test it directly with a simple chat completion request before wiring anything else around it.

Example shape:

```bash
curl https://api.runpod.ai/v2/<endpoint-id>/openai/v1/chat/completions \
  -H "Authorization: Bearer <RUNPOD_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-14B-Instruct-AWQ",
    "messages": [{"role": "user", "content": "Say hello in one word."}],
    "max_tokens": 20
  }'
```

---

## Recommendation

For the current demo architecture, prioritize:

1. Groq credentials
2. OpenAI credentials
3. Anthropic credentials
4. ElevenLabs credentials
5. Twilio credentials

Treat RunPod as optional infrastructure, not a required part of the current setup.
