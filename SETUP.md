# Westpac AI Voice Agent Setup Guide

This repository currently contains a working end-to-end demo for:

- Browser-based live AI voice conversations from the dashboard
- Twilio phone-call intake with booking creation
- Supabase-backed appointments, transcripts, summaries, analytics, and client views
- Banker acceptance flow with Twilio SMS confirmation and cross-sell messaging

This guide reflects the current codebase as it exists now.

---

## What The System Currently Does

### Core flows

- Dashboard live call page opens a browser WebSocket to the backend and runs a full AI voice session.
- Twilio voice webhook answers a phone call, opens a Twilio Media Stream, transcribes speech, generates responses, and can create an appointment.
- Completed calls are summarized and written into Supabase as:
  - call sessions
  - call turns
  - appointments
  - client-facing banker briefing data
- A banker can accept an appointment from the dashboard and trigger SMS confirmation.

### Current backend capabilities

- STT: Groq Whisper primary, OpenAI Whisper fallback
- Live LLM responses: Groq primary, OpenAI fallback
- Post-call summaries: Claude primary, Groq/OpenAI fallback
- Browser live-call TTS: streamed PCM audio
- Twilio call TTS: ElevenLabs voice output transcoded for Twilio telephony
- Shared conversation engine: both dashboard live sessions and Twilio calls now use the same backend session flow for turn handling, booking logic, and post-call summarization

### Current frontend capabilities

- Appointment list, detail view, calendar, clients, analytics, and live call page
- Backend-backed appointment fetching and polling
- Appointment accept / decline actions
- Cached appointment detail loading to reduce UI flicker

---

## Current Architecture

### High-level services

1. Dashboard frontend
   - React + TypeScript + Vite
   - Runs locally on port 5173 by default

2. FastAPI backend
   - Runs locally on port 8000
   - Exposes REST endpoints and WebSocket endpoints

3. Supabase
   - Stores demo customers, banker slots, appointments, call sessions, call turns, analytics

4. Twilio
   - Voice webhook for incoming calls
   - Media Streams for real-time audio
   - SMS for booking confirmation

5. Model providers
   - Groq for fast STT and live LLM responses
   - OpenAI fallback for STT / LLM and OpenAI TTS when needed
   - Anthropic Claude for post-call summaries
   - ElevenLabs for selected voices and Twilio-specific voice output

### Request / audio flow

#### Dashboard live call

- Frontend page: `/live`
- Frontend captures mic audio with browser VAD
- Frontend sends completed utterances to `ws://localhost:8000/api/live/session`
- Backend shared session engine processes the turn
- Backend streams audio back to the browser

#### Twilio phone call

- Twilio sends `POST /api/twilio/voice`
- Backend returns TwiML instructing Twilio to open `/api/twilio/stream`
- Twilio streams 8kHz mulaw audio over WebSocket
- Backend performs server-side VAD, hands utterances into the shared session engine, then sends audio back to Twilio in mulaw chunks

#### Optional OpenAI Realtime path

- `ws://localhost:8000/api/realtime/session`
- Separate experimental / alternate voice path using OpenAI Realtime API

---

## Repository Layout

```text
backend/                 FastAPI app, Twilio flow, session engine, STT/LLM/TTS
dashboard/               React dashboard
docs/                    PRDs and reference docs
supabase_schema_and_seed.sql
SETUP.md
RUNPOD_SETUP.md
```

Important backend files:

- `backend/main.py`: FastAPI app, REST routes, dashboard live-session route, Twilio routes
- `backend/session_flow.py`: shared conversation / booking / summarization engine
- `backend/twilio_handler.py`: Twilio-specific media transport and telephony playback
- `backend/stt.py`: Groq/OpenAI transcription
- `backend/llm.py`: live LLM and post-call summaries
- `backend/tts.py`: OpenAI / ElevenLabs TTS
- `backend/tools.py`: appointment creation, slot handling, SMS helpers, analytics updates
- `backend/config.py`: environment variable loading from `.env` and `.env.local`

Important frontend files:

- `dashboard/src/pages/Live.tsx`: browser live-call UI
- `dashboard/src/lib/api.ts`: frontend API client
- `dashboard/src/lib/supabase.ts`: frontend backend/Supabase config

---

## Prerequisites

Install these before setup:

- Python 3.11+
- Node.js 18+
- npm 9+
- Git
- ffmpeg
- ngrok

### Windows install notes

#### Python

- Install from Python.org or use `winget install Python.Python.3.11`

#### Node.js

- Install from Node.js LTS or use `winget install OpenJS.NodeJS.LTS`

#### ffmpeg

One option:

```powershell
winget install Gyan.FFmpeg
```

If you install manually, make sure the ffmpeg binary is on your system PATH.

#### ngrok

One option:

```powershell
winget install Ngrok.Ngrok
```

Then authenticate it once:

```powershell
ngrok config add-authtoken <YOUR_NGROK_AUTHTOKEN>
```

### macOS install notes

Using Homebrew is the simplest path:

#### Homebrew

If you do not already have Homebrew:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### Python

```bash
brew install python@3.11
```

#### Node.js

```bash
brew install node@20
```

#### ffmpeg

```bash
brew install ffmpeg
```

#### ngrok

```bash
brew install ngrok/ngrok/ngrok
```

Then authenticate it once:

```bash
ngrok config add-authtoken <YOUR_NGROK_AUTHTOKEN>
```

### Quick verification

Windows:

```powershell
python --version
node --version
npm --version
ffmpeg -version
ngrok version
```

macOS:

```bash
python3 --version
node --version
npm --version
ffmpeg -version
ngrok version
```

---

## Backend Setup

From the repo root:

Windows:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

macOS:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Python dependencies currently required

These are installed from `backend/requirements.txt`:

- fastapi
- uvicorn[standard]
- websockets
- python-dotenv
- supabase
- openai
- httpx
- vaderSentiment
- pydantic
- numpy
- anthropic
- groq
- twilio

### Backend environment files

The backend loads variables in this order:

1. `backend/.env`
2. `backend/.env.local` with override enabled

Recommended approach:

Windows:

```powershell
copy .env.example .env
copy .env.example .env.local
```

macOS:

```bash
cp .env.example .env
cp .env.example .env.local
```

Then put machine-specific and demo-specific overrides in `.env.local`.

### Required backend environment variables

Minimum recommended set for the current architecture:

```env
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_KEY=

GROQ_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
CLAUDE_MODEL=claude-sonnet-4-6-20250514

ELEVENLABS_API_KEY=
USE_ELEVENLABS=1

VOICE_ID_INDIAN_EN=omLr0bN17lYIC1JWLSYV
VOICE_ID_AUSTRALIAN_EN=snyKKuaGYk1VUEh42zbW
DEFAULT_VOICE_ID=omLr0bN17lYIC1JWLSYV

TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=
CUSTOMER_PHONE_NUMBER=

RUNPOD_API_KEY=
RUNPOD_ENDPOINT_ID=
VLLM_BASE_URL=
VLLM_MODEL=Qwen/Qwen2.5-14B-Instruct-AWQ
```

### Start the backend

Windows:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python main.py
```

macOS:

```bash
cd backend
source .venv/bin/activate
python3 main.py
```

Backend default URL:

- `http://localhost:8000`

Useful checks:

- `GET /api/health`
- `POST /api/warmup`

---

## Database Setup

If you are starting from an empty Supabase project:

1. Create a Supabase project.
2. Open the SQL editor.
3. Run the contents of `supabase_schema_and_seed.sql`.

This seeds demo customers, appointments, banker availability, transactions, and related tables/views used by the dashboard and voice flows.

At minimum, verify these tables exist and contain data:

- `customer_profiles`
- `customer_accounts`
- `customer_transactions`
- `banker_availability`
- `appointments`
- `call_sessions`
- `call_turns`
- `analytics_snapshots`

---

## Dashboard Setup

From the repo root:

Windows:

```powershell
cd dashboard
npm install
```

macOS:

```bash
cd dashboard
npm install
```

There is no checked-in dashboard env file. Create one:

Windows:

```powershell
@"
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
VITE_BACKEND_URL=http://localhost:8000
"@ | Set-Content .env.local
```

macOS:

```bash
cat > .env.local <<'EOF'
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
VITE_BACKEND_URL=http://localhost:8000
EOF
```

### Frontend scripts

Available scripts from `dashboard/package.json`:

- `npm run dev`
- `npm run build`
- `npm run lint`
- `npm run preview`

### Start the dashboard

Windows:

```powershell
cd dashboard
npm run dev
```

macOS:

```bash
cd dashboard
npm run dev
```

Dashboard default URL:

- `http://localhost:5173`

---

## Twilio Setup

### What Twilio is currently used for

- Incoming voice calls
- Real-time Twilio Media Streams
- SMS confirmation after banker acceptance

### Twilio prerequisites

1. Create a Twilio account.
2. Buy or provision a phone number.
3. If using a trial account, verify the phone numbers you will call from / send SMS to.

### Required Twilio backend config

Set these in `backend/.env.local`:

```env
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+61...
CUSTOMER_PHONE_NUMBER=+61...
```

### Expose the backend with ngrok

Start your backend first, then in another terminal:

```powershell
ngrok http 8000
```

Copy the public HTTPS URL from ngrok, for example:

- `https://your-tunnel.ngrok-free.app`

### Configure the Twilio voice webhook

In the Twilio Console for your number:

- Voice webhook URL: `https://YOUR-NGROK-URL/api/twilio/voice`
- Method: `POST`

Important:

- Use the full `/api/twilio/voice` path.
- If ngrok changes, update the Twilio webhook.

### Twilio voice behavior in the current build

- Twilio phone calls use the same shared session engine as the dashboard live session.
- The current default Twilio voice is Oliver via ElevenLabs.
- Twilio call playback still goes through telephony transcoding to 8kHz mulaw, so call audio quality and timing will differ from the browser live-call page.

---

## Current Backend Routes

### REST routes

- `GET /`
- `GET /api/health`
- `POST /api/warmup`
- `GET /api/appointments`
- `GET /api/appointments/{appointment_id}`
- `POST /api/appointments/{appointment_id}/accept`
- `POST /api/appointments/{appointment_id}/decline`
- `GET /api/clients`
- `GET /api/analytics`
- `GET /api/banker-slots`

### WebSocket routes

- `WS /api/live/session`
- `WS /api/realtime/session`
- `WS /api/twilio/stream`

### Twilio webhook route

- `POST /api/twilio/voice`

---

## Recommended Local Run Order

Open separate terminals.

### Terminal 1: backend

Windows:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python main.py
```

macOS:

```bash
cd backend
source .venv/bin/activate
python3 main.py
```

### Terminal 2: dashboard

Windows:

```powershell
cd dashboard
npm run dev
```

macOS:

```bash
cd dashboard
npm run dev
```

### Terminal 3: ngrok

Windows or macOS:

```powershell
ngrok http 8000
```

---

## Smoke Test Checklist

### Backend

1. Open `http://localhost:8000/api/health`
2. Confirm the backend responds
3. Call `POST /api/warmup` and confirm DB/STT/TTS/LLM readiness

### Dashboard

1. Open `http://localhost:5173`
2. Verify appointments load
3. Open `/live`
4. Click warmup and then start a browser live call

### Twilio

1. Make sure ngrok is running
2. Confirm Twilio number points to `/api/twilio/voice`
3. Call the Twilio number
4. Confirm the call can create an appointment
5. Accept the appointment from the dashboard and confirm SMS behavior

---

## Common Troubleshooting

### ffmpeg not found

Symptom:

- Twilio greeting or Twilio TTS playback fails

Fix:

- Install ffmpeg
- Ensure it is on PATH
- Fully restart the terminal or VS Code after updating PATH

### Twilio webhook hit but no call audio

Check:

- ngrok is still running
- webhook URL includes `/api/twilio/voice`
- backend is reachable from ngrok

### Twilio trial account cannot call or SMS properly

Check:

- your caller ID / target number is verified in Twilio
- your Twilio number is active

### Dashboard loads but shows stale or incomplete data

Check:

- backend is pointing to the intended Supabase project
- `SUPABASE_SERVICE_KEY` is valid
- seed SQL has been run

### Auto-reload interrupts a live call

If backend files change while a live WebSocket or Twilio call is active, Uvicorn reload can terminate the session. Avoid editing backend files during a call test.

---

## Current Limitations / Notes

- Twilio phone-call audio quality will not exactly match the browser live-call experience because Twilio uses narrowband telephony audio.
- The optional RunPod config is still supported in config, but it is not the primary live-call response path in the current code.
- The dashboard live call page and Twilio transport share the same session engine, but they still differ in how audio is captured and played back.

---

## Quick Start Summary

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
copy .env.example .env.local
python main.py
```

```powershell
cd dashboard
npm install
@"
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
VITE_BACKEND_URL=http://localhost:8000
"@ | Set-Content .env.local
npm run dev
```

```powershell
ngrok http 8000
```
