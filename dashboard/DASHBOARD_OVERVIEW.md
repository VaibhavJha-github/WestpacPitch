# Westpac AI Callbot — Lender Dashboard Overview

## What Is This Dashboard?

The **Lender Dashboard** is the banker-facing companion to **Book a Banker** — Westpac's AI-powered appointment booking system. While Book a Banker handles the customer-facing interaction (voice callbot that qualifies leads and schedules appointments), this dashboard provides lenders with everything they need to prepare for those appointments.

### The Book a Banker + Lender Dashboard Relationship

```
┌────────────────────────────────────────────────────────────────────────────┐
│                           BOOK A BANKER ECOSYSTEM                          │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│   CUSTOMER-FACING                          BANKER-FACING                   │
│   ┌─────────────────────┐                  ┌─────────────────────┐         │
│   │   Book a Banker     │                  │   Lender Dashboard  │         │
│   │   (AI Callbot)      │ ──── feeds ────► │   (This App)        │         │
│   └─────────────────────┘                  └─────────────────────┘         │
│                                                                            │
│   • Answers customer calls                 • Displays appointment queue    │
│   • Verifies identity                      • Shows customer context        │
│   • Understands intent                     • Provides call transcripts     │
│   • Collects loan details                  • Surfaces AI insights          │
│   • Books appointments                     • Recommends strategy           │
│   • Captures conversation                  • Tracks client history         │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

**Book a Banker** creates the appointment. **Lender Dashboard** ensures the banker is prepared.

---

## Why This Dashboard Exists

When a customer calls Book a Banker, the AI callbot:
1. Verifies their identity
2. Understands their banking needs (refinance, first home, investment, etc.)
3. Collects relevant details (loan amount, property, income, timeline)
4. Books an appointment with the right specialist

Without this dashboard, lenders would walk into meetings cold — no context, no preparation, potentially asking the customer to repeat everything they just told the callbot.

**This dashboard solves that problem** by giving lenders:
- Full visibility into what the customer discussed with the callbot
- AI-generated insights and recommended approach
- Customer profile and banking history
- Sentiment analysis to gauge the customer's mindset

---

## System Architecture

The AI Callbot ecosystem includes multiple dashboards serving different audiences:

| Dashboard | Audience | Purpose |
|-----------|----------|---------|
| **Lender Dashboard** *(this app)* | Bankers / Home Loan Specialists | Pre-meeting preparation with customer context |
| **Analytics Dashboard** | Engineers / Support / Operations | Real-time callbot monitoring and performance metrics |
| **Customer Service Dashboard** *(planned)* | Contact Centre Agents | Live call support, escalation handling, customer lookup |

---

## Lender Dashboard — What's Inside

### Purpose
Prepare lenders for customer appointments booked via Book a Banker by providing pre-meeting context: customer profile, call transcript, sentiment analysis, collected information, and AI-generated strategy recommendations.

### Core Workflow

```
Customer calls Book a Banker → AI Callbot handles conversation → Books appointment → 
Lender opens dashboard → Reviews briefing → Attends meeting prepared
```

### How Data Flows from Book a Banker to the Dashboard

```
Book a Banker Collects:        Lender Dashboard Displays:
├─ Identity verification   →   Customer profile (name, tenure, profession)
├─ Customer intent         →   Intent classification + AI notes
├─ Loan details            →   Collected Information section
├─ Conversation tone       →   Sentiment score + analysis
└─ Appointment booking     →   Calendar + appointment cards
```

### Dashboard Sections

| Section | Description |
|---------|-------------|
| **My Appointments** | Upcoming appointments grouped by date, with quick-select transcript preview panel |
| **Calendar** | Monthly calendar view of all scheduled appointments with click-to-view details |
| **Clients** | Searchable list of all customers the lender has interacted with, linking to profile history |
| **Appointment Detail** | Full pre-meeting briefing with transcript, sentiment, collected data, and AI strategy |
| **Client Profile** | Aggregated view of a customer's complete interaction history across all appointments |

### Key Features

| Feature | What It Does | How It Helps the Banker |
|---------|--------------|-------------------------|
| **Transcript Review** | Full call transcript with bot/customer message distinction | Understand exactly what was discussed, reference specific points |
| **Sentiment Analysis** | Score (0-100%) + label (Positive/Neutral/Anxious/Frustrated) | Adjust approach — reassure anxious customers, address frustrated ones |
| **Collected Information** | Structured data extracted from conversation (loan amount, property, deposit, etc.) | Skip repetitive questions, jump straight to solutions |
| **AI Strategy** | Suggested approach based on customer situation and intent | Objection handling tips, competitor counter-strategies |
| **Customer Context** | Tenure, profession, banking value, location from customer database | Personalize the conversation, recognize loyalty |

### Book a Banker → Dashboard Data Mapping

| Book a Banker Collects | Displayed As |
|------------------------|--------------|
| Name, DOB (verification) | Customer profile header |
| Stated intent | Intent badge + AI notes |
| Loan amount, property, deposit, etc. | Collected Information list |
| Conversation tone | Sentiment score + note |
| Preferred appointment time/type | Appointment card with date, time, location type |
| Competitor mentions | Noted in AI strategy |

### Value Proposition for Bankers

> **"Walk into every meeting already knowing what the customer needs."**

| Without Dashboard | With Dashboard |
|-------------------|----------------|
| "What can I help you with today?" | "I see you're looking at refinancing your $650k loan — let's talk about how we can beat that CBA offer." |
| Cold-start conversations | Personalized from the first moment |
| Customer repeats everything | Banker references specifics |
| Generic pitch | Tailored strategy based on AI analysis |
| Miss competitor threats | Proactive counter-offers |
| Unaware of customer mood | Approach adjusted to sentiment |

---

## Analytics Dashboard

### Purpose
Provide engineers, support staff, and operations teams with real-time visibility into Book a Banker's performance, system health, and customer interaction patterns.

### Sections

| Section | Description |
|---------|-------------|
| **Live Operations** | Active calls, queue depth, average wait time, bot capacity |
| **Today's Performance** | Key metrics (total calls, appointments booked, avg duration, conversion rate, escalation rate) + hourly call volume chart |
| **Insights** | Recent completed calls table, sentiment distribution, top customer intents |
| **System** | Uptime, latency, error rate, model version |

### Key Metrics

| Metric | Description |
|--------|-------------|
| **Active Calls** | Number of calls currently being handled by Book a Banker |
| **Queue Depth** | Customers waiting to connect to Book a Banker |
| **Avg Wait Time** | Average time customers wait before Book a Banker answers |
| **Conversion Rate** | Percentage of calls that result in a booked appointment |
| **Escalation Rate** | Percentage of calls requiring human agent handoff |
| **Sentiment Distribution** | Breakdown of customer sentiment across all calls |
| **Top Intents** | Most common customer intents (Refinance, First Home, Business Loan, etc.) |

### Use Cases

- **Engineers**: Monitor system health, identify latency issues, track model performance
- **Support**: Review recent calls, identify escalated conversations, spot patterns
- **Operations**: Track daily volumes, measure conversion performance, capacity planning

---

## Customer Service Dashboard *(Planned)*

### Purpose
Enable contact centre agents to handle escalated calls, provide live support during Book a Banker interactions, and access customer history for quick resolution.

### Potential Features

| Feature | Description |
|---------|-------------|
| **Live Call Takeover** | Agent can join or take over an active Book a Banker conversation when escalation is triggered |
| **Escalation Queue** | Real-time list of calls flagged for human intervention |
| **Customer Lookup** | Quick search by name, phone, or account number to pull up interaction history |
| **Call History** | View past Book a Banker transcripts and outcomes for a specific customer |
| **Canned Responses** | Pre-approved responses for common scenarios to assist agents |
| **Sentiment Alerts** | Notifications when calls show frustrated or negative sentiment |

### Use Cases

- **Escalation Handling**: Customer requests to speak to a human or Book a Banker detects frustration
- **Complex Enquiries**: Issues beyond Book a Banker's capability (disputes, complaints, exceptions)
- **Callback Support**: Agent follows up on incomplete calls or dropped connections

---

## Summary: How It All Fits Together

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                                                                               │
│    Customer Journey with Book a Banker + Lender Dashboard                     │
│                                                                               │
│    ┌─────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────┐   │
│    │Customer │───►│ Book a Banker   │───►│ Lender Dashboard│───►│ Meeting │   │
│    │ Calls   │    │ (AI Callbot)    │    │ (Banker Prep)   │    │ Success │   │
│    └─────────┘    └─────────────────┘    └─────────────────┘    └─────────┘   │
│                                                                               │
│    "I want to      AI qualifies,          Banker reviews        Personalized  │
│    refinance"      collects details,      context, strategy,    conversation  │
│                    books appointment      sentiment, transcript  from start   │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## Technical Notes

- All dashboards share the same design system (Westpac brand colors, consistent typography)
- Analytics dashboard is accessible via a link on the Lender Dashboard sidebar
- This prototype uses mock data to simulate real Book a Banker interactions
- Built with React + TypeScript + Vite for fast development and hot reloading
