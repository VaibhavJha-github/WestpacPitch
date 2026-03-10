# Westpac Dashboard

This is the React + TypeScript + Vite frontend for the Westpac AI Voice Agent demo.

## What It Currently Does

- Lists appointments from the backend
- Shows appointment detail pages with transcript, summary, intent, sentiment, and collected information
- Shows calendar, clients, and analytics pages
- Starts a browser-based live AI voice session from the Live page
- Accepts or declines appointments from the banker workflow

## Stack

- React 19
- TypeScript
- Vite 7
- Tailwind CSS 4
- react-router-dom 7
- Supabase JS client

## Scripts

```bash
npm run dev
npm run build
npm run lint
npm run preview
```

## Environment Variables

Create `dashboard/.env.local`:

```env
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
VITE_BACKEND_URL=http://localhost:8000
```

## Run Locally

```bash
cd dashboard
npm install
npm run dev
```

Default local URL:

- `http://localhost:5173`

## Frontend To Backend Integration

The frontend currently talks to these backend routes:

- `GET /api/appointments`
- `GET /api/appointments/{id}`
- `POST /api/appointments/{id}/accept`
- `POST /api/appointments/{id}/decline`
- `GET /api/clients`
- `GET /api/analytics`
- `GET /api/banker-slots`
- `POST /api/warmup`
- `GET /api/health`
- `WS /api/live/session`

## Key Pages

- `/appointment`: main appointments page
- `/appointment/:id`: appointment briefing page
- `/calendar`: calendar view
- `/clients`: client list
- `/clients/:id`: client profile
- `/analytics`: analytics page
- `/live`: browser live-call page

## Notes

- Appointment and client data now primarily come from the backend, not static mock data.
- The Live page performs client-side VAD in the browser and sends completed utterances to the backend.
- The dashboard and Twilio phone-call flow now share the same backend session engine for conversation logic and post-call enrichment.
