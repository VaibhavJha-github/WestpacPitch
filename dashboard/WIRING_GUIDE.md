# Dashboard Wiring Guide

This file documents the current frontend wiring, data sources, and backend integration points.

It replaces the earlier mock-data-only description.

---

## Current Data Sources

### Backend API

Primary source for runtime data:

- appointments
- appointment detail
- client list
- analytics
- banker slot lookup
- live-session WebSocket events

Frontend API client lives in `dashboard/src/lib/api.ts`.

### Supabase client

The frontend still creates a Supabase client in `dashboard/src/lib/supabase.ts`, but the main appointment and analytics workflows are currently backend-driven.

### Mock data

`dashboard/src/data/mockData.ts` still exists for typing and fallback use in some UI flows, but the live app behavior is intended to come from backend data.

---

## Routing

Current routes in the dashboard:

- `/appointment`
- `/appointment/:id`
- `/calendar`
- `/clients`
- `/clients/:id`
- `/analytics`
- `/live`

---

## Page Wiring Summary

### Dashboard page

- Fetches appointments from the backend
- Displays list + transcript preview

### Appointment detail page

- Fetches a specific appointment by ID
- Uses local cache to avoid detail-page flicker
- Reads transcript, AI summary, collected information, and strategy from the backend-shaped appointment payload

### Clients page

- Fetches clients from backend

### Analytics page

- Fetches analytics summary from backend

### Live page

- Calls `POST /api/warmup`
- Opens `WS /api/live/session`
- Captures audio locally in the browser
- Uses browser-side VAD
- Sends completed utterances to backend
- Receives streamed bot audio and transcript updates back from backend

---

## Key Backend Contracts Used By The Frontend

### Appointment shape

The frontend expects each appointment to include fields like:

- `id`
- `customerName`
- `time`
- `date`
- `type`
- `locationType`
- `sentiment`
- `sentimentScore`
- `intent`
- `aiNote`
- `collectedData`
- `recommendedStrategy`
- `transcript`

The backend currently normalizes these in `backend/main.py`.

### Live session messages

The frontend Live page expects messages such as:

- `session_started`
- `thinking`
- `transcript`
- `response_text`
- `audio_delta`
- `response_done`
- `session_ended`
- `error`

---

## Current Backend Session Architecture Relevant To The Frontend

The core conversation logic now lives in `backend/session_flow.py`.

That shared session engine is used by:

- the dashboard live call WebSocket flow
- the Twilio voice-call flow

This means intent extraction, booking creation, collected-data enrichment, summary generation, and appointment updates are intentionally centralized.

---

## Known Practical Notes

- Browser live audio quality is better than Twilio call quality because the browser path is not constrained by 8kHz telephony audio.
- Twilio and dashboard calls share conversation logic, but not identical audio transport.
- If backend files change during a live call, development reload can terminate the WebSocket session.

---

## When Updating The Dashboard

If you change appointment rendering or live-call UX, verify all of these still match the backend payloads:

- location type casing
- intent display
- `collectedData` shape as `{ label, value }[]`
- `recommendedStrategy` presence / absence
- transcript sender mapping

If you change backend appointment shaping, update `dashboard/src/lib/api.ts`, `dashboard/src/pages/AppointmentDetail.tsx`, and any components relying on the appointment type definition in `dashboard/src/data/mockData.ts`.
