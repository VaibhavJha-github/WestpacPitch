# Dashboard Wiring Guide — Component & Button Reference

> **Purpose**: This document catalogues every component, page, button, and interactive element in the Lender Dashboard. It describes what each element currently does (or doesn't do) and what it **should** do when fully wired up. Feed this to an agent to hook everything together.

---

## Tech Stack

- **React 19** + **TypeScript** + **Vite 7**
- **Tailwind CSS v4** (via `@tailwindcss/vite` plugin, imported as `@import "tailwindcss"` in `App.css`)
- **react-router-dom v7** (BrowserRouter, Routes, NavLink, useNavigate, useParams, useSearchParams)
- **lucide-react** for icons
- **No state management library** — all state is local (`useState`, `useMemo`)
- **No API layer** — all data comes from `src/data/mockData.ts` and `src/data/clientsData.ts`

---

## Routing Structure (`App.tsx`)

| Route | Component | Description |
|-------|-----------|-------------|
| `/appointment` | `Dashboard` | Main appointments list (default route, `*` redirects here) |
| `/calendar` | `CalendarView` | Monthly calendar view |
| `/appointment/:id` | `AppointmentDetail` | Full appointment briefing page |
| `/clients` | `Clients` | Client list/table |
| `/clients/:id` | `ClientProfile` | Individual client profile |
| `/analytics` | `Analytics` | Callbot analytics dashboard |

All routes render inside `<Layout>` which provides the top nav bar.

---

## Data Layer

### `src/data/mockData.ts`

**Types exported:**
- `Sentiment` — `'Positive' | 'Neutral' | 'Anxious' | 'Frustrated'`
- `Message` — `{ id, sender: 'Bot'|'Customer', text, timestamp }`
- `LocationType` — `'In-branch' | 'Mobile lender visit' | 'Video chat' | 'Phone'`
- `CollectedData` — `{ label, value? }`
- `Appointment` — Full appointment object (see fields below)

**Key `Appointment` fields:**
- `id`, `customerName`, `customerInitials`, `companyName?`
- `time`, `date` (ISO string like `'2026-01-15'`), `type` (e.g. "Refinance Discussion")
- `locationType`, `sentiment`, `sentimentScore` (0–100), `sentimentNote?`
- `intent`, `aiNote`, `status` (`'Upcoming' | 'Completed' | 'Cancelled'`)
- `customerTenure?`, `age?`, `location?`, `profession?`, `totalBankingValue?`
- `estimatedLoanSize?`, `currentLender?`, `reasonForLeaving?`, `selfDeclaredLVR?`
- `collectedData?` — array of `{ label, value }`
- `recommendedStrategy?` — `{ title, description }`
- `transcript` — array of `Message`

**Data exported:** `appointments: Appointment[]` — hardcoded array of 4 mock appointments.

### `src/data/clientsData.ts`

**Types exported:**
- `Client` — aggregated client profile built from appointments

**Functions exported:**
- `getClientsFromAppointments()` — groups appointments by `customerName`, computes `averageSentiment`, `totalAppointments`, `lastContactDate`. Returns sorted by most recent contact.
- `getClientById(clientId)` — finds a client by their `client-{appointmentId}` ID.

**⚠️ Wiring note:** Client IDs are generated as `client-${apt.id}` from the *first* appointment for that customer. This means if a customer has appointments `id: '1'` and `id: '5'`, their client ID is `client-1`.

---

## Components

### 1. `Layout.tsx` — Top Navigation Shell

**Location:** `src/components/Layout.tsx`
**Props:** `{ children: React.ReactNode }`

**What it renders:**
- Top nav bar with Westpac logo (`/westpac.svg`), nav links, user greeting
- Scrollable content area that auto-scrolls to top on route change

**Nav links (all wired and working):**
| Link | Route | Active? |
|------|-------|---------|
| My Appointments | `/appointment` | ✅ Works |
| Calendar | `/calendar` | ✅ Works |
| Clients | `/clients` | ✅ Works |

**🔴 NOT WIRED — Things to connect:**
- **User avatar/name** ("Welcome, James" + "JM" avatar) — hardcoded. Should come from an auth/user context if user system is added.
- **No link to Analytics** from the nav bar — Analytics is only reachable via a small link at the bottom of the Dashboard page. Consider adding it to the nav or keeping it intentionally hidden from lenders.
- **Westpac logo** (`/westpac.svg`) — has `onError` handler to hide if missing. Verify the SVG exists in `/public/`.

---

### 2. `AppointmentCard.tsx` — Appointment List Item

**Location:** `src/components/AppointmentCard.tsx`
**Props:** `{ appointment: Appointment, isSelected?: boolean, onClick?: () => void, isNext?: boolean }`

**What it renders:**
- Date/time, location type icon, appointment type, customer name
- AI Sentiment badge (score + label)
- Detected Intent badge
- "Next Up" badge (red, shown when `isNext=true`)
- "View Details" button → navigates to `/appointment/${id}`
- "Join Meeting" button (only shown when `isNext=true` AND appointment date is today)

**🔴 NOT WIRED — Things to connect:**
- **"Join Meeting" button** — renders but has no `onClick` handler. Should launch a video meeting (external link, WebRTC, etc.) or navigate to a meeting URL.
- **Card click** (`onClick` prop) — currently used by `Dashboard.tsx` to select the card and show the transcript preview. The click toggles selection but doesn't navigate. **Only when the card is selected**, clicking the customer name (`h3`) navigates to the detail page. This two-step interaction may be confusing.
- **Sentiment colors** — only handles `'Positive'` (green), `'Anxious'` (yellow), default (slate). Missing explicit handling for `'Neutral'` and `'Frustrated'`.

---

### 3. `TranscriptPanel.tsx` — Transcript Preview / Full Transcript

**Location:** `src/components/TranscriptPanel.tsx`
**Props:** `{ appointment: Appointment | null, previewMode?: boolean, hideButton?: boolean }`

**What it renders:**
- Empty state with "Select an appointment to view details" when no appointment selected
- Message count header
- Chat-style transcript (Bot messages right-aligned in red, Customer messages left-aligned in grey)
- In `previewMode`: shows first 4 messages + "X more messages..." + "View Full Details" button
- "View Full Details" button → navigates to `/appointment/${id}`

**🔴 NOT WIRED — Things to connect:**
- **`hideButton` prop** — accepted but only used to conditionally hide the footer button. Currently only used when explicitly passed; works correctly.
- **No search/filter** within the transcript — might be useful for long conversations.
- **No copy-to-clipboard** for transcript messages.

---

## Pages

### 4. `Dashboard.tsx` — My Appointments (Main Page)

**Location:** `src/pages/Dashboard.tsx`
**Route:** `/appointment`

**Layout:** Two-column grid (2/3 appointment list, 1/3 transcript preview)

**State:**
- `selectedAppointmentId` — defaults to `appointments[0].id`

**What it renders:**
- Header: "Scheduled Appointments" + count
- Left column: Appointment cards grouped by date (Today/Tomorrow/date)
  - Uses `AppointmentCard` for each
  - First appointment gets `isNext=true`
  - Clicking a card sets it as selected (shows transcript in right panel)
- Right column: Sticky `TranscriptPanel` in preview mode for the selected appointment
- Footer: "View Callbot Analytics" link → navigates to `/analytics`

**🔴 NOT WIRED — Things to connect:**
- **No filtering/sorting** of appointments (by date, sentiment, intent, status, etc.)
- **No pagination** — renders all appointments. Fine for 4 mock items, but needs pagination or virtual scrolling for production.
- **No status filtering** — all appointments show regardless of `status` (Upcoming/Completed/Cancelled). Should probably only show Upcoming by default.
- **Date grouping** uses `formatDateHeader` which calculates Today/Tomorrow relative to `new Date()`. Mock dates are hardcoded to Jan 2026 — they won't show as "Today" unless the current date matches.

---

### 5. `CalendarView.tsx` — Calendar Page

**Location:** `src/pages/CalendarView.tsx`
**Route:** `/calendar`

**State:**
- `searchParams` — uses URL search params to track `appointmentId` for the modal

**What it renders:**
- Header with month navigation (chevrons) + "New Appointment" button
- 7-column calendar grid for January 2026 (hardcoded: 31 days, offset of 4 = starts on Thursday)
- Day cells show appointment pills (time + customer name), clickable to open modal
- Modal shows: date/time/location, customer card (initials, name, tenure, company, est. value), location/profession/banking value, intent + AI note
- Modal footer: "View Full Details" button → navigates to `/appointment/${id}`

**🔴 NOT WIRED — Things to connect:**
- **Month navigation** (ChevronLeft/ChevronRight buttons) — rendered but have no `onClick` logic. Should cycle through months and update the calendar grid.
- **"New Appointment" button** — rendered but has no `onClick` handler. Should open a form/modal to create a new appointment.
- **Calendar is hardcoded to January 2026** — `daysInMonth = 31`, `startDayOffset = 4`. Needs dynamic month/year calculation.
- **Today highlight** uses `new Date().getDate()` which won't match January unless we're actually in January.
- **No drag-and-drop** or appointment rescheduling from the calendar.

---

### 6. `AppointmentDetail.tsx` — Full Appointment Briefing

**Location:** `src/pages/AppointmentDetail.tsx`
**Route:** `/appointment/:id`

**Layout:** Two-column (5/7 split)

**What it renders:**
- **Header**: Back button (← `navigate(-1)`), appointment type, date/time/location, Reschedule button, Launch Meeting button (video chat only)
- **Left column (col-span-5):**
  - Customer card: initials, name, tenure badge, company, estimated loan size, location, profession, banking value, current lender
  - Intent card: intent text + reason for leaving
  - Collected Information: list of label/value pairs from `collectedData`
  - Recommended Strategy: title + description in a callout box
- **Right column (col-span-7):**
  - Call Transcript with sentiment badge (color bar)
  - AI Summary section (sparkles icon + `aiNote` + `sentimentNote`)
  - Full scrollable transcript (all messages)

**🔴 NOT WIRED — Things to connect:**
- **"Reschedule" button** — rendered but no `onClick`. Should open a date/time picker or rescheduling flow.
- **"Launch Meeting" button** (only for Video chat appointments) — rendered but no `onClick`. Should open a video meeting link.
- **Back button** — uses `navigate(-1)` which works but could be unexpected if user navigated directly to this URL.
- **No customer name link** to the client profile page. The customer name is displayed but not clickable. Should link to `/clients/client-${appointment.id}` (but note: client IDs are derived from appointments, so this only works if the customer's *first* appointment matches this ID).
- **No "Mark as Complete"** or status update functionality.
- **No notes/comments** section for the banker to add their own notes.
- **No print/export** option for the briefing.

---

### 7. `Clients.tsx` — Client List

**Location:** `src/pages/Clients.tsx`
**Route:** `/clients`

**State:**
- `searchQuery` — text input for filtering

**What it renders:**
- Header: "Clients" + count + search input
- Table with columns: Client (avatar + name + company), Details (profession + location), Last Contact (date), Appointments (count), Sentiment (% badge)
- Entire row is clickable → navigates to `/clients/${client.id}`

**Search filters on:** name, companyName, profession, location (case-insensitive substring match)

**🔴 NOT WIRED — Things to connect:**
- **No column sorting** — table headers are static. Should allow sorting by name, date, sentiment, appointment count.
- **No pagination** — renders all clients.
- **Sentiment color thresholds:** ≥80% green, ≥60% amber, <60% red. These are consistent with `ClientProfile.tsx`.

---

### 8. `ClientProfile.tsx` — Individual Client Profile

**Location:** `src/pages/ClientProfile.tsx`
**Route:** `/clients/:id`

**What it renders:**
- **Back button** → navigates to `/clients`
- **Left column (col-span-5):**
  - Customer card: initials, name, tenure, company, location, profession, banking value
  - Average Sentiment card with color bar
  - Collected Information: de-duplicated `collectedData` across all their appointments
- **Right column (col-span-7):**
  - Interaction History: list of all appointments for this client
  - Each appointment shows: type, date, time, location type, status badge (Completed=green, Upcoming=blue), intent, AI note
  - Each appointment row is clickable → navigates to `/appointment/${apt.id}`

**🔴 NOT WIRED — Things to connect:**
- **No edit functionality** for client details.
- **No contact actions** (call, email, message buttons).
- **Status badges** use `apt.status` but all mock data is `'Upcoming'` — verify rendering for `'Completed'` and `'Cancelled'`.
- **Collected data de-duplication** filters by label only (first occurrence wins). If the same label has different values across appointments, only the first is shown.

---

### 9. `Analytics.tsx` — Callbot Analytics Dashboard

**Location:** `src/pages/Analytics.tsx`
**Route:** `/analytics`

**All data is hardcoded inline** (not from `mockData.ts`). No shared state with the rest of the app.

**What it renders:**
- **Back button** → navigates to `/` (which redirects to `/appointment`)
- **Live Operations:** System status bar (online indicator, active calls, queue, wait time, bot capacity), Active Calls list
- **Today's Performance:** Stats card (total calls, appointments, avg duration, conversion %, escalation %), hourly call volume bar chart (CSS-based, animated)
- **Insights:** Recent Completed Calls table (customer, duration, sentiment, intent, outcome), Sentiment Distribution bars, Top Intents list
- **System:** Uptime, latency, error rate, escalation rate, model version

**🔴 NOT WIRED — Things to connect:**
- **All data is hardcoded** — `liveMetrics`, `todayStats`, `versionStats`, `sentimentBreakdown`, `topIntents`, `hourlyVolume`, `activeCalls`, `recentCalls` are all inline objects/arrays. Should be fetched from an API or shared data source.
- **No real-time updates** — "Live Operations" section is static. Should poll or use WebSocket for live data.
- **No date range selector** — "Today's Performance" is fixed. Should allow date range filtering.
- **No click-through** on recent calls table rows — they're not interactive. Could link to a call detail view.
- **No export/download** for analytics data.
- **Bar chart** is pure CSS (div widths) — works but is not interactive (no tooltips, no hover values).

---

## Shared Patterns & Conventions

### Colors
- **Westpac Red:** `#DA1710` (primary brand, buttons, active nav, accents)
- **Hover Red:** `red-800` (button hover states)
- **Sentiment colors:**
  - Positive → green (`text-green-600/700`, `bg-green-500`)
  - Neutral → slate (`text-slate-600`, `bg-slate-400`)
  - Anxious → amber/yellow (`text-amber-600`, `text-yellow-700`, `bg-amber-500`)
  - Frustrated → red (`text-red-600`, `bg-red-500`)

### Animations
- `page-transition` class on route content (`App.css`) — subtle fade-up on page enter
- `animate-bar-rise` class on Analytics bar chart bars — scale-up from bottom with staggered delay

### Navigation Patterns
- `useNavigate()` for programmatic navigation
- `NavLink` with active class styling (red underline + text) in Layout
- Back buttons use either `navigate(-1)` (AppointmentDetail) or `navigate('/specific-route')` (ClientProfile, Analytics)

---

## Summary: What Needs Wiring

| Priority | Item | Location | Action Needed |
|----------|------|----------|---------------|
| 🔴 High | Join Meeting button | `AppointmentCard.tsx:96-98` | Add onClick — launch video meeting |
| 🔴 High | Launch Meeting button | `AppointmentDetail.tsx:61-63` | Add onClick — launch video meeting |
| 🔴 High | Reschedule button | `AppointmentDetail.tsx:57-59` | Add onClick — open reschedule flow |
| 🔴 High | New Appointment button | `CalendarView.tsx:49-51` | Add onClick — open creation flow |
| 🔴 High | Calendar month navigation | `CalendarView.tsx:45-48` | Add onClick + dynamic month/year |
| 🟡 Medium | Calendar hardcoded month | `CalendarView.tsx:26-30` | Make dynamic (daysInMonth, startDayOffset) |
| 🟡 Medium | All Analytics data | `Analytics.tsx:7-79` | Replace with API calls or shared data |
| 🟡 Medium | Appointment filtering/sorting | `Dashboard.tsx` | Add status filter, date sort, search |
| 🟡 Medium | Client table sorting | `Clients.tsx` | Add column sort headers |
| 🟡 Medium | Customer name → client profile link | `AppointmentDetail.tsx` | Make customer name clickable |
| 🟢 Low | User context | `Layout.tsx:67` | Replace hardcoded "Welcome, James" |
| 🟢 Low | Banker notes section | `AppointmentDetail.tsx` | Add editable notes area |
| 🟢 Low | Client contact actions | `ClientProfile.tsx` | Add call/email/message buttons |
| 🟢 Low | Transcript search | `TranscriptPanel.tsx` | Add search within messages |
| 🟢 Low | Analytics real-time | `Analytics.tsx` | Add polling/WebSocket for live data |
| 🟢 Low | Print/export briefing | `AppointmentDetail.tsx` | Add print/PDF export button |
