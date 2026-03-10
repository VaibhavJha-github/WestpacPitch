# Westpac Demo Runbook

This is the current fastest path to run the demo end to end.

## Demo Outcome

The current demo supports this flow:

1. Customer speaks to the AI either from the browser Live page or by calling the Twilio number.
2. The AI captures the conversation, books an appointment, and stores transcript and summary data.
3. The banker sees the appointment in the dashboard.
4. The banker opens the appointment, reviews transcript, intent, summary, sentiment, and collected information.
5. The banker accepts the appointment.
6. The customer receives Twilio SMS confirmation.

---

## Current Demo Architecture

### Browser live-call path

- UI: `dashboard/src/pages/Live.tsx`
- Frontend sends completed utterances to `WS /api/live/session`
- Backend shared session engine processes turns and updates data in Supabase

### Twilio phone-call path

- Twilio webhook: `POST /api/twilio/voice`
- Twilio media stream: `WS /api/twilio/stream`
- Backend performs telephony VAD and uses the same shared session engine as the browser flow

### Shared logic

- Shared conversation engine: `backend/session_flow.py`
- Booking + slot logic: `backend/tools.py`
- Post-call summary and appointment enrichment: `backend/session_flow.py`

---

## Required Services For Demo Day

You need these running:

1. Supabase project with seeded schema/data
2. FastAPI backend on port 8000
3. Dashboard on port 5173
4. ngrok tunnel exposing backend to Twilio
5. Twilio number configured with the correct voice webhook URL

---

## Environment Files

### Backend env loading order

The backend currently loads:

1. `backend/.env`
2. `backend/.env.local`

If the same variable exists in both files, `.env.local` wins.

### Minimum backend keys for the current demo

- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `SUPABASE_ANON_KEY`
- `GROQ_API_KEY`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `ELEVENLABS_API_KEY`
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_PHONE_NUMBER`
- `CUSTOMER_PHONE_NUMBER`

### Dashboard env

Create `dashboard/.env.local` with:

- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`
- `VITE_BACKEND_URL`

---

## One-Time Setup

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Dashboard

```powershell
cd dashboard
npm install
```

### Dependencies that must exist on the machine

- Python 3.11+
- Node.js 18+
- ffmpeg on PATH
- ngrok installed and authenticated

---

## Demo Day Start Order

Use separate terminals.

### Terminal A: Backend

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python main.py
```

Health check:

- `http://localhost:8000/api/health`

### Terminal B: Public tunnel for Twilio

```powershell
ngrok http 8000
```

Copy the HTTPS URL and confirm Twilio points to:

- `https://<public-url>/api/twilio/voice`

### Terminal C: Dashboard

```powershell
cd dashboard
npm run dev
```

Dashboard URL:

- `http://localhost:5173`

---

## Pre-Demo Smoke Test

Do this before the real walkthrough.

### Browser smoke test

1. Open the dashboard.
2. Go to the Live page.
3. Click Warm Up.
4. Start a short browser mic call.
5. Say a simple sentence.
6. Confirm transcript appears and the bot responds.

### Booking smoke test

1. Complete a short booking conversation.
2. Confirm a new appointment appears in the dashboard.
3. Open the appointment detail page.
4. Confirm these fields are populated:
   - transcript
   - AI summary
   - intent
   - sentiment
   - collected information

### Acceptance smoke test

1. Click Accept Booking.
2. Confirm the SMS status banner reflects sent, skipped, or error.

---

## Twilio Full Demo Test

1. Make sure backend, dashboard, and ngrok are already running.
2. Confirm Twilio still points to the current ngrok URL.
3. Call the Twilio number from your phone.
4. Complete a booking conversation.
5. Check the dashboard for the created appointment.
6. Open the appointment detail page.
7. Accept the booking.
8. Confirm SMS is received on the demo phone.

---

## What To Show In The Demo

### Recommended demo narrative

1. Start on the dashboard and explain the banker workflow.
2. Open the Live page and show that the backend is warmed up.
3. Run either:
   - a browser call first for quality and speed
   - or a Twilio phone call first for realism
4. Show the new appointment appearing in the dashboard.
5. Open the appointment detail page and highlight:
   - transcript
   - AI summary
   - detected intent
   - sentiment
   - collected facts
   - recommended strategy
6. Accept the appointment.
7. Show SMS confirmation.

### Suggested talking points

- The same backend conversation engine is used across both browser live calls and Twilio calls.
- The system converts unstructured conversation into structured banker-ready context.
- The dashboard is not just a transcript view; it produces a banker briefing and downstream actions.

---

## Known Differences Between Browser And Twilio Demo Paths

- Browser live calls have better audio quality than Twilio phone calls.
- Twilio calls are limited by telephony audio and Twilio media-stream timing.
- The Twilio path uses the same session engine, but a different transport and audio encoding chain.

For executive demos, if reliability matters more than phone realism, use the browser live path first and Twilio second.

---

## Common Demo Failures And Quick Checks

### Twilio call does not connect

Check:

- backend is running
- ngrok is running
- Twilio webhook URL is correct and includes `/api/twilio/voice`
- Twilio account / number is active

### Twilio call connects but audio fails

Check:

- ffmpeg is installed and on PATH
- backend was restarted after PATH changes
- no backend hot reload happened mid-call

### Appointment does not appear in dashboard

Check:

- backend is writing to the intended Supabase project
- appointment fetch is pointing to the active backend URL
- warmup and DB connection are healthy

### SMS not received

Check:

- Twilio credentials are valid
- `CUSTOMER_PHONE_NUMBER` uses full country code
- Twilio trial destination number is verified

### Live session dies during testing

Check:

- backend files were not edited during the call
- auto-reload did not restart Uvicorn during the session

---

## Recommendation For Presentation Reliability

For the cleanest live demo:

1. Start and verify the browser live flow first.
2. Use Twilio as the second-stage realism demo.
3. Avoid editing backend files once the demo environment is running.
4. Keep ngrok open and do not restart it unless you are ready to update the Twilio webhook URL.
