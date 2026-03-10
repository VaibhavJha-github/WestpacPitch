# Westpac AI Voice Agent Demo Status And Plan

Last updated: March 10, 2026

## Current Status

The current repository is in a demo-capable state.

### Working now

- Backend REST API is operational
- Dashboard is operational
- Browser live-call page is operational
- Twilio call flow is operational enough to answer calls and create appointments
- Appointment acceptance flow is operational
- Twilio SMS integration is operational when credentials and verified numbers are configured correctly
- Shared conversation engine is now used across browser live calls and Twilio calls

### Recently completed architectural changes

- Extracted shared conversation / booking / summary logic into `backend/session_flow.py`
- Wired dashboard live sessions to the shared session flow
- Wired Twilio sessions to the shared session flow
- Hardened summary normalization and appointment enrichment
- Added transcript-derived fallbacks for intent, location type, and collected information
- Updated documentation for setup and architecture

---

## What The Demo Currently Proves

The system currently demonstrates:

1. AI-led customer conversation
2. Structured extraction from free-form voice conversation
3. Automatic appointment creation
4. Banker-facing transcript, summary, intent, sentiment, and collected facts
5. Banker acceptance workflow
6. Triggered SMS follow-up

This is the current end-to-end story the demo supports.

---

## Remaining Risks

### Medium risk

- Twilio voice quality and continuity are still more fragile than the browser live path because of telephony audio constraints and the current Twilio TTS transport chain.

### Low-to-medium risk

- ngrok URL churn can break Twilio if the webhook is not updated after a restart.

### Low risk

- Browser live-call flow is the strongest path for a controlled demo.

---

## Recommended Demo Strategy

### Best presentation sequence

1. Show dashboard context first
2. Run a browser live-call demo to show the conversation loop cleanly
3. Show the appointment being created
4. Show banker review and acceptance
5. Show SMS confirmation
6. If needed, run a Twilio phone-call demo as the realism extension

This sequence reduces risk while still showing the full value proposition.

---

## Short-Term Plan

### Demo-stability priorities

1. Keep the browser live-call path as the primary demo route
2. Use Twilio only after confirming tunnel + webhook + ffmpeg + credentials are stable
3. Avoid backend hot reload during any live call test

### Optional engineering follow-up

1. Improve Twilio TTS transport so it is closer to the browser streaming path
2. Add a more explicit demo-preflight checklist endpoint or status surface
3. Optionally add stable public hosting for backend and/or dashboard

---

## Demo Readiness Checklist

### Must be true before the demo

- Backend starts cleanly
- `/api/health` responds
- `/api/warmup` responds successfully
- Dashboard loads and shows appointments
- Browser live session works
- Twilio webhook points to the active tunnel URL
- Twilio test call works
- Appointment accept flow works
- SMS works to the demo phone number

### Nice to have

- One successful full dry run recorded shortly before the presentation
- A fallback browser-only demo path prepared in case Twilio degrades

---

## Bottom Line

The current system is ready for guided demo use.

The browser live-call path is the strongest route.
The Twilio path is viable, but should still be treated as the more operationally sensitive part of the demo.
