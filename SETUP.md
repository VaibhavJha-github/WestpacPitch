# Westpac AI Voice Agent — Full Setup Guide

This guide gets you from a fresh clone to a fully working demo:
- AI answers phone calls via Twilio
- Handles 2 demo scenarios (Budget Planning + Book a Banker)
- Saves transcripts, summaries, and bookings to Supabase
- Dashboard shows everything live (appointments, transcripts, calendar)
- Banker accepts booking → customer gets SMS confirmation + cross-sell

---

## Prerequisites

You need these installed on your Mac Mini (or whatever machine runs the backend):

- **Python 3.11+** — `python3 --version`
- **Node.js 18+** — `node --version`
- **npm** — `npm --version`
- **ffmpeg** — needed for audio conversion (Twilio uses mulaw format)
- **git** — `git --version`

### Install ffmpeg if you don't have it:
```bash
brew install ffmpeg
```

### Verify Python:
```bash
python3 --version
# Should be 3.11 or higher
```

---

## Step 1: Clone the Repo

```bash
cd ~/Documents
git clone https://github.com/VaibhavJha-github/WestpacPitch.git
cd WestpacPitch
```

---

## Step 2: Set Up the Backend

### 2a. Create a Python virtual environment
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
```

You should see `(venv)` in your terminal prompt now.

### 2b. Install Python dependencies
```bash
pip install -r requirements.txt
```

This installs FastAPI, Twilio, OpenAI, Groq, Anthropic, Supabase, etc.

### 2c. Create your `.env` file

```bash
cp .env.example .env
```

Now open `backend/.env` in any text editor and fill in your real keys:

```bash
nano .env
# or
open -a TextEdit .env
```

Fill in ALL of these (you already have most of them):

```
# Supabase (already set up)
SUPABASE_URL=https://hpqldmexivtoaphymwva.supabase.co
SUPABASE_ANON_KEY=<your-anon-key>
SUPABASE_SERVICE_KEY=<your-service-key>

# Groq
GROQ_API_KEY=<your-groq-key>

# Anthropic
ANTHROPIC_API_KEY=<your-anthropic-key>
CLAUDE_MODEL=claude-sonnet-4-6

# OpenAI
OPENAI_API_KEY=<your-openai-key>

# ElevenLabs
ELEVENLABS_API_KEY=<your-elevenlabs-key>
USE_ELEVENLABS=1
DEFAULT_VOICE_ID=EXAVITQu4vr4xnSDxMaL

# Voice IDs
VOICE_ID_INDIAN_EN=EXAVITQu4vr4xnSDxMaL
VOICE_ID_AUSTRALIAN_EN=IKne3meq5aSn9XLyUdCD

# Twilio (fill these in Step 5)
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=
CUSTOMER_PHONE_NUMBER=
```

### 2d. Test the backend starts

```bash
python main.py
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

Open a browser and go to: `http://localhost:8000/api/health`

You should see JSON with `"status": "ok"`. If yes, the backend works. Press Ctrl+C to stop it for now.

---

## Step 3: Set Up the Database (Supabase)

**If you already ran the schema before, skip this step.**

If starting fresh:

1. Go to https://supabase.com/dashboard
2. Open your project (hpqldmexivtoaphymwva)
3. Go to **SQL Editor**
4. Copy the entire contents of `supabase_schema_and_seed.sql` from the repo root
5. Paste it in the SQL editor
6. Click **Run**
7. It should complete without errors

This creates all tables, views, indexes, seed data (3 customers, 1 banker, transactions, etc.)

### Verify:
Go to **Table Editor** in Supabase and check:
- `customer_profiles` — should have 3 rows
- `bankers` — should have 1 row (Mia Sullivan)
- `customer_transactions` — should have 58 rows
- `banker_availability` — should have 10 rows

---

## Step 4: Set Up the Dashboard

### 4a. Install dependencies
```bash
cd ../dashboard_src/dashboard
npm install
```

### 4b. Create the dashboard `.env`

```bash
cat > .env << 'EOF'
VITE_SUPABASE_URL=https://hpqldmexivtoaphymwva.supabase.co
VITE_SUPABASE_ANON_KEY=<your-supabase-anon-key>
VITE_BACKEND_URL=http://localhost:8000
EOF
```

Replace `<your-supabase-anon-key>` with your actual anon key.

### 4c. Test the dashboard locally

```bash
npm run dev
```

Open `http://localhost:5173` in your browser. You should see the Westpac dashboard with existing appointments from the seed data.

---

## Step 5: Set Up Twilio

### 5a. Create a Twilio account
1. Go to https://www.twilio.com/try-twilio
2. Sign up (free trial gives you $15 credit — enough for demos)
3. Verify your phone number

### 5b. Get a Twilio phone number
1. In Twilio Console → **Phone Numbers** → **Buy a Number**
2. Search for an Australian number (+61) or US number (+1)
3. Buy it (costs ~$1/month)
4. Note the number (e.g., `+61412345678`)

### 5c. Get your credentials
1. Go to Twilio Console dashboard
2. Copy your **Account SID** (starts with `AC`)
3. Copy your **Auth Token**

### 5d. Update your backend `.env`

```bash
cd ../../backend
nano .env
```

Add these lines:
```
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_PHONE_NUMBER=+61412345678
CUSTOMER_PHONE_NUMBER=+614xxxxxxxx
```

`CUSTOMER_PHONE_NUMBER` = your personal phone number (the one you'll call FROM during the demo, and where SMS confirmations will be sent).

**Important for Twilio trial accounts:** You can only send SMS to verified numbers. Go to Twilio Console → **Phone Numbers** → **Verified Caller IDs** and add your personal number.

---

## Step 6: Expose Your Mac Mini to the Internet

Twilio needs to reach your backend over the internet. You have two options:

### Option A: ngrok (easiest, free)

```bash
# Install ngrok
brew install ngrok

# Sign up at https://ngrok.com and get your auth token
ngrok config add-authtoken <your-ngrok-token>

# Start the tunnel
ngrok http 8000
```

ngrok will show you a URL like:
```
Forwarding: https://abc123.ngrok-free.app -> http://localhost:8000
```

Copy that `https://xxx.ngrok-free.app` URL. This is your **PUBLIC_URL**.

**Note:** Free ngrok URLs change every time you restart. For a stable URL, upgrade to ngrok paid ($8/month) or use Cloudflare Tunnel.

### Option B: Cloudflare Tunnel (free, stable URL)

```bash
# Install cloudflared
brew install cloudflare/cloudflare/cloudflared

# Login (opens browser)
cloudflared tunnel login

# Create a tunnel
cloudflared tunnel create westpac-demo

# Run the tunnel
cloudflared tunnel --url http://localhost:8000
```

This gives you a stable `https://xxx.trycloudflare.com` URL.

---

## Step 7: Connect Twilio to Your Backend

1. Go to Twilio Console → **Phone Numbers** → **Active Numbers**
2. Click your number
3. Under **Voice Configuration**:
   - **A call comes in**: Webhook
   - **URL**: `https://<YOUR_PUBLIC_URL>/api/twilio/voice`
   - **HTTP Method**: POST
4. Click **Save**

That's it. When someone calls your Twilio number, Twilio will hit your backend, which starts the AI conversation.

---

## Step 8: Run Everything

You need 3 terminals open:

### Terminal 1: Backend
```bash
cd ~/Documents/WestpacPitch/backend
source venv/bin/activate
python main.py
```

### Terminal 2: Tunnel
```bash
ngrok http 8000
# Copy the https URL and set it in Twilio (Step 7)
```

### Terminal 3: Dashboard (for local testing)
```bash
cd ~/Documents/WestpacPitch/dashboard_src/dashboard
npm run dev
```

---

## Step 9: Test End-to-End

### Test 1: Call your Twilio number
1. From your personal phone, call the Twilio number
2. You should hear: "G'day Rohan, thanks for calling Westpac! I'm Alex..."
3. Say: "Hey, I'm looking to save up for a car, about 25 grand"
4. The AI should walk you through your expenses (coffee, Uber Eats, etc.)
5. Hang up when done

### Test 2: Check the dashboard
1. Open `http://localhost:5173` (or your Vercel URL)
2. You should see the new appointment appear with status **"Pending"**
3. Click into it — you'll see the full transcript and AI summary

### Test 3: Accept the booking
1. On the appointment detail page, click **"Accept Booking"**
2. You should get a green banner: "Confirmation SMS sent..."
3. Check your phone — you should receive:
   - **SMS 1** (immediately): Booking confirmation with time/location
   - **SMS 2** (10 seconds later): Home insurance cross-sell

### Test 4: Home loan scenario
1. Call again
2. Say: "I'm looking to get a home loan"
3. Answer the AI's questions (location, budget, deposit, fixed/variable)
4. When it asks about booking, say "Friday" or any day
5. Pick a time slot, say in-person or online
6. Hang up and check the dashboard

---

## Step 10: Deploy Dashboard to Your Domain

### Option A: Vercel (recommended)

1. Push to GitHub (already done)
2. Go to https://vercel.com
3. Click **New Project** → Import your GitHub repo
4. Set the **Root Directory** to: `dashboard_src/dashboard`
5. Set **Framework Preset**: Vite
6. Add **Environment Variables**:
   ```
   VITE_SUPABASE_URL = https://hpqldmexivtoaphymwva.supabase.co
   VITE_SUPABASE_ANON_KEY = <your-anon-key>
   VITE_BACKEND_URL = https://<your-ngrok-or-cloudflare-url>
   ```
7. Click **Deploy**
8. Once deployed, go to **Settings** → **Domains**
9. Add your custom domain
10. Update your domain's DNS (Vercel will tell you what to set)

**Important:** Every time your ngrok URL changes, you need to update `VITE_BACKEND_URL` in Vercel and redeploy. That's why Cloudflare Tunnel with a stable URL is better for production.

### Option B: Use a stable backend URL

If you set up Cloudflare Tunnel with a custom subdomain (e.g., `api.yourdomain.com`), your Vercel env var stays the same forever:
```
VITE_BACKEND_URL = https://api.yourdomain.com
```

---

## Architecture Summary

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Customer    │────>│   Twilio     │────>│  Mac Mini        │
│  (Phone)     │<────│  (Voice+SMS) │<────│  (FastAPI:8000)  │
└─────────────┘     └──────────────┘     │                   │
                                          │  Groq (STT+LLM)  │
                                          │  OpenAI (TTS)     │
                                          │  Claude (Summary) │
                                          └────────┬──────────┘
                                                   │
                                          ┌────────▼──────────┐
                                          │   Supabase        │
                                          │  (Database)       │
                                          └────────┬──────────┘
                                                   │
                                          ┌────────▼──────────┐
                                          │   Vercel          │
                                          │  (Dashboard)      │
                                          │  yourdomain.com   │
                                          └───────────────────┘
```

### What happens during a call:
1. Customer calls Twilio number
2. Twilio hits `/api/twilio/voice` → returns TwiML to open Media Stream
3. Twilio streams audio to `/api/twilio/stream` WebSocket
4. Backend: audio → Groq Whisper (STT) → Groq LLM → OpenAI TTS → back to Twilio
5. Each turn saved to `call_turns` table
6. If booking requested → `appointments` table (status: Pending)
7. Call ends → Claude generates summary → `call_sessions` updated
8. Dashboard auto-refreshes and shows the new appointment

### What happens when banker accepts:
1. Banker clicks "Accept" on dashboard
2. Dashboard calls `POST /api/appointments/{id}/accept`
3. Backend updates appointment status to "Upcoming"
4. Backend sends confirmation SMS via Twilio
5. 10 seconds later, sends cross-sell SMS
6. Dashboard shows green "Confirmed" badge

---

## Troubleshooting

### "Connection refused" when calling Twilio number
- Make sure `python main.py` is running
- Make sure ngrok/cloudflare tunnel is running
- Make sure the Twilio webhook URL matches your tunnel URL

### No audio / AI doesn't respond
- Check terminal for errors
- Make sure `ffmpeg` is installed: `ffmpeg -version`
- Make sure your API keys are correct in `.env`
- Test the warmup: `curl -X POST http://localhost:8000/api/warmup`

### SMS not received
- Check Twilio trial: only verified numbers receive SMS
- Check `CUSTOMER_PHONE_NUMBER` in `.env` (must include country code like +61)
- Check Twilio Console → **Messaging** → **Logs** for errors

### Dashboard shows no data
- Make sure `VITE_BACKEND_URL` points to the right backend
- Check browser console for errors
- Make sure Supabase schema is seeded

### Dashboard works locally but not on Vercel
- Update `VITE_BACKEND_URL` in Vercel to your public tunnel URL (not localhost)
- Redeploy after changing env vars

---

## Cost Estimates (for demo)

| Service | Cost |
|---------|------|
| Twilio number | ~$1/month |
| Twilio voice | ~$0.02/min |
| Twilio SMS | ~$0.05/msg |
| Groq API | Free tier (generous) |
| OpenAI TTS | ~$0.015/1K chars |
| Claude (summaries) | ~$0.003/summary |
| Supabase | Free tier |
| Vercel | Free tier |
| ngrok | Free (or $8/mo for stable URL) |

A typical demo call costs less than $0.10.
