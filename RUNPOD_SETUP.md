# RunPod Serverless vLLM Setup

No custom Docker image needed. RunPod has an official vLLM worker.

## Steps

### 1. Go to RunPod Serverless
- Log in at https://www.runpod.io/console/serverless
- Click **New Endpoint**

### 2. Select the vLLM Worker
- Under "Quick Deploy", find **vLLM** (or search for it)
- Or use the worker image: `runpod/worker-vllm:stable-cuda12.1.0`

### 3. Configure the Endpoint

**GPU Selection:**
- Select **A40 48GB** or **A6000 48GB**
- Either works for Qwen2.5-14B-AWQ (needs ~10GB VRAM, plenty of headroom)

**Worker Configuration:**
- Active Workers: `0` (scales to zero when idle)
- Max Workers: `1` (single demo caller)
- Idle Timeout: `5 minutes` (keeps warm after last request)
- Execution Timeout: `300 seconds`

**Environment Variables:**
```
MODEL_NAME=Qwen/Qwen2.5-14B-Instruct-AWQ
MAX_MODEL_LEN=8192
GPU_MEMORY_UTILIZATION=0.90
DTYPE=half
QUANTIZATION=awq
DISABLE_LOG_STATS=true
```

**Advanced (optional but recommended):**
```
TOKENIZER_MODE=auto
MAX_NUM_SEQS=1
```

### 4. Create the Endpoint
- Click **Create**
- Wait for it to build (first time takes a few minutes)
- Note the **Endpoint ID** (looks like `abc123def456`)

### 5. Update Your Backend .env

Add this line to `/Users/vaibhavjha/Documents/WestpacChatbot/backend/.env`:
```
RUNPOD_ENDPOINT_ID=<your-endpoint-id-here>
```

The backend will automatically construct the URL:
`https://api.runpod.ai/v2/<endpoint-id>/openai/v1`

### 6. Test It

Restart the backend:
```bash
cd /Users/vaibhavjha/Documents/WestpacChatbot/backend
source venv/bin/activate
python main.py
```

Then warmup:
```bash
curl -X POST http://localhost:8000/api/warmup
```

Or use the **Warm Up** button on the Live page at http://localhost:5173/live

First warmup will be slow (30-60s) as the model loads. Subsequent calls will be fast (~300-900ms).

### 7. Test Directly (Optional)

You can test the RunPod endpoint directly:
```bash
curl https://api.runpod.ai/v2/<endpoint-id>/openai/v1/chat/completions \
  -H "Authorization: Bearer <YOUR_RUNPOD_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-14B-Instruct-AWQ",
    "messages": [{"role": "user", "content": "Say hello"}],
    "max_tokens": 20
  }'
```

## Cost Estimate

- A40: ~$0.39/hr active, $0 idle (with scale-to-zero)
- A6000: ~$0.39/hr active, $0 idle
- For a 1-hour demo session: ~$0.40-0.80
- FlashBoot (if available): reduces cold start to ~10-15s

## Troubleshooting

**Cold start too slow?**
- Set Active Workers to `1` before the demo (costs money while idle but instant response)
- Or hit Warm Up 2 minutes before demo

**Out of memory?**
- Shouldn't happen with AWQ on 48GB, but try setting `GPU_MEMORY_UTILIZATION=0.85`

**Model download slow on first deploy?**
- First deploy downloads ~8GB model. Subsequent starts use cached model.
- Enable FlashBoot for faster cold starts if available.
