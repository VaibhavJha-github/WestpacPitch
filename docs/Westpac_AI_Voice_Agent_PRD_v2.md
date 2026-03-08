# Westpac AI Voice Agent PRD v2

Date: March 7, 2026
Owner: Vaibhav Jha
Status: Approved architecture, implementation-ready
Audience: hackathon build team, technical reviewers, executive stakeholders

## 1. Executive Summary

This product is a live, voice-based Westpac first-contact AI assistant that books bankers, triages sensitive issues, prepares bankers before meetings, and feeds a dynamic lender dashboard with the full context of the interaction.

The experience is split into two surfaces:

1. A customer-facing live voice session reached from a web dashboard route.
2. A banker-facing lender dashboard that shows appointments, transcripts, sentiment, extracted facts, recommended strategy, customer context, and appointment scheduling outcomes.

The system is designed to be demo-safe, latency-conscious, and commercially believable. It does not attempt full autonomous banking. Instead, it focuses on the highest-value low-risk workflow: intake, qualification, booking, handoff, banker preparation, and guided support.

The architecture is:

1. `Vercel` hosts the frontend dashboard.
2. `RunPod Serverless Load Balancer` hosts the live orchestration backend.
3. `Qwen2.5-14B-Instruct-AWQ` runs in `vLLM` on `A40` or `A6000 48GB`.
4. `OpenAI` provides speech-to-text.
5. `ElevenLabs` provides low-latency multilingual text-to-speech.
6. `Supabase` stores dynamic dashboard data, synthetic customer records, transactions, banker availability, call sessions, and appointments.
7. A local Westpac knowledge pack grounds the model on products, rates, and policy snippets used in the demo.

This version replaces the earlier Google Calendar plan with a more pitch-friendly internal banker scheduling workflow that fits the lender dashboard more naturally.

## 2. Why This Product Exists

Current customer-service flows often fail in three ways:

1. Customers repeat themselves across intake, transfer, and appointment stages.
2. Human bankers enter meetings cold and waste time rediscovering context.
3. Simple intake and triage consume expensive human capacity.

This product addresses those failures by:

1. Capturing customer intent once.
2. Structuring that information immediately into banker-ready context.
3. Routing or booking intelligently.
4. Showing operational analytics and banker preparation value on the dashboard.

The business case is not "replace all humans." The business case is:

1. reduce low-value repetitive intake work,
2. increase appointment conversion,
3. reduce wrong transfers,
4. shorten time-to-context for bankers,
5. expand multilingual first-contact coverage,
6. limit hallucination risk by keeping the AI inside a bounded workflow.

## 3. Product Positioning

### 3.1 Product Statement

Book a Banker AI is a first-contact voice assistant that qualifies intent, gathers context, books or triages appropriately, and briefs the next human with a structured summary.

### 3.2 What It Is Not

It is not:

1. a general-purpose autonomous banker,
2. a transaction-executing agent,
3. a final production compliance system,
4. a fully open-ended financial advice engine.

### 3.3 Primary Pitch Narrative

The AI handles the early interaction, reduces friction, and makes the banker more effective rather than less necessary.

## 4. Product Goals

### 4.1 Primary Goals

1. Deliver a realistic live voice interaction with strong turn quality and low perceived latency.
2. Demonstrate safe and useful first-contact handling.
3. Show correct routing to the right team or correct banker-booking behavior.
4. Populate the existing lender dashboard dynamically instead of using mock data.
5. Use synthetic customer accounts and transactions to create believable customer context and spending insights.
6. Demonstrate multilingual switching and banker-facing summaries.

### 4.2 Secondary Goals

1. Show executives how the product can outperform a static chat interface.
2. Demonstrate why AI risk can be managed with scoped workflows and grounded knowledge.
3. Create an architecture that can be deployed from one container image for the backend and one static frontend deployment.

## 5. Non-Goals

1. Real core-banking integration.
2. Real money movement or account changes.
3. Real customer verification or identity proofing.
4. Full telephony integration in v1.
5. Multi-caller concurrency.
6. Broad customer-service coverage outside supported flows.

## 6. Current Dashboard Context

The provided dashboard is already a strong banker-facing prototype. The current source lives in [dashboard_src/dashboard](/Users/vaibhavjha/Documents/WestpacChatbot/dashboard_src/dashboard).

The app currently contains:

1. `My Appointments`
2. `Calendar`
3. `Clients`
4. `Appointment Detail`
5. `Analytics`

The app currently uses static mock data from [mockData.ts](/Users/vaibhavjha/Documents/WestpacChatbot/dashboard_src/dashboard/src/data/mockData.ts) and [clientsData.ts](/Users/vaibhavjha/Documents/WestpacChatbot/dashboard_src/dashboard/src/data/clientsData.ts).

This PRD assumes we will preserve those page concepts and replace the static layer with live API-backed data from Supabase and the RunPod backend.

## 7. Core User Journeys

### 7.1 Journey A: Book a Banker

1. Customer starts a live voice session.
2. AI greets, requests name and DOB for demo realism, and starts qualification.
3. AI detects home-loan-relevant intent.
4. AI asks a few structured questions.
5. AI checks banker availability for the next Friday.
6. AI offers two primary slots.
7. Customer selects one slot.
8. AI asks for one fallback slot.
9. AI confirms that a banker will review and accept the booking.
10. Dashboard receives the appointment, transcript, summary, extracted facts, and recommended banker strategy.
11. Banker sees the appointment, reviews the briefing, and accepts one slot.
12. Accepted slot appears on the banker calendar.

### 7.2 Journey B: Sensitive Routing

1. Customer reports a fraud-like or lost-card issue.
2. AI identifies the request as sensitive and outside demo scope.
3. AI states that the issue is best handled by the `Security Specialist Team`.
4. AI ends the call with a clean transfer-style message.
5. Dashboard records the triage, risk reason, and call summary.

### 7.3 Journey C: Spending Insight Demo

1. Customer asks for help planning toward a financial goal like buying a car.
2. AI reviews synthetic transaction data for that customer.
3. AI identifies spend categories and recurring patterns.
4. AI offers factual spending observations and practical suggestions.
5. AI remains serious about financial conclusions even if the customer is playful.
6. Dashboard shows the insights and relevant summary for later banker follow-up.

## 8. Demo Persona Design

### 8.1 Primary Customer Persona

One primary synthetic customer will be used across the demo so that the dashboard feels cohesive and historically rich.

Recommended persona:

1. Name: `Rohan Mehta`
2. Age: `31`
3. Location: `Brisbane, QLD`
4. Profession: `Product Designer`
5. Tenure: `4 years with Westpac`
6. Goal themes:
   - considering a car purchase by year-end,
   - exploring first-home options,
   - somewhat anxious about spending discipline,
   - occasionally playful in tone.

### 8.2 Banker Persona

Use real Westpac-style role naming based on current public Westpac language such as `Home Loan Specialist`, `Westpac lender`, and `mobile lender`.

Recommended banker persona:

1. Display name: `Mia Sullivan`
2. Role: `Home Loan Specialist`
3. Region: `Brisbane City`
4. Appointment modes:
   - phone,
   - video chat,
   - in-branch,
   - meet up

This aligns with Westpac’s public positioning of home-loan appointments by phone, video chat, in branch, or meeting a mobile lender.

## 9. Success Criteria

### 9.1 Functional

1. The AI can hold a coherent 10-minute conversation.
2. The AI can route to the correct specialist bucket in scripted scenarios.
3. The AI can offer available banker slots and record selected primary and fallback preferences.
4. The banker can accept a slot from the dashboard and see the appointment reflected in calendar views.
5. The live session can feed transcript, summary, sentiment, extracted data, and strategy into the dashboard.
6. The AI can detect user language per turn and switch reply voice/language.

### 9.2 Experience

1. Warm time-to-first-audio should usually be within 1.0 to 1.8 seconds.
2. Typical short turn completion should usually be within 2.0 to 4.0 seconds.
3. The voice should sound natural enough to present credibly to executives.
4. The dashboard should feel live, not mock or manually stitched together.

### 9.3 Business

1. Show that customer repetition can be reduced.
2. Show that banker prep time can be reduced.
3. Show that routing quality can be explained.
4. Show that AI risk can be limited by scope rather than ignored.

## 10. Scope

### 10.1 In Scope

1. Live voice session route in the dashboard.
2. Warm-up action for the backend.
3. Language switching and voice switching.
4. Dynamic transcript rendering.
5. Dynamic appointment generation.
6. Dynamic analytics.
7. Dynamic client and appointment detail pages.
8. Synthetic customer financial data.
9. Booking flow with banker availability and banker acceptance.
10. Sentiment and emotion signals.
11. Westpac knowledge-pack retrieval from local text or markdown files.

### 10.2 Out of Scope

1. Twilio or phone-number calling.
2. Real banking actions.
3. Real SMS sending.
4. Google Calendar integration for v1.
5. Full compliance and legal handling for public deployment.

## 11. Architecture

### 11.1 Deployment Split

#### Frontend

Hosted on `Vercel`.

Responsibilities:

1. render dashboard pages,
2. render live control page,
3. capture browser audio,
4. play AI audio stream,
5. call backend APIs,
6. subscribe to live updates.

#### Backend

Hosted on `RunPod Serverless Load Balancer`.

Responsibilities:

1. websocket/session orchestration,
2. model inference,
3. STT integration,
4. TTS integration,
5. retrieval over Westpac knowledge pack,
6. transaction insight generation,
7. sentiment and emotion enrichment,
8. slot lookup and booking creation,
9. persistence to Supabase.

#### Database

Hosted on `Supabase`.

Responsibilities:

1. persist customers,
2. persist accounts and transactions,
3. persist bankers and availability,
4. persist call sessions and turns,
5. persist appointments,
6. persist dashboard analytics aggregates,
7. persist knowledge references and system settings.

### 11.2 Model Runtime

1. Model: `Qwen2.5-14B-Instruct-AWQ`
2. Inference server: `vLLM`
3. GPU target: `A40` or `A6000`, `48GB`
4. Quantization: `AWQ`
5. Endpoint mode: `RunPod Serverless Load Balancer`

### 11.3 Why A40 or A6000

RunPod’s current pricing makes `A6000/A40 48GB` a better demo choice than `4090 PRO 24GB` for this workload because the extra VRAM headroom comes at a small incremental cost and reduces deployment tightness.

This matters because the backend is not just serving the LLM. It is also:

1. streaming orchestration,
2. retrieval,
3. enrichment,
4. tool invocation,
5. generating structured outputs for the dashboard.

### 11.4 Why Quantization

Quantization is the correct choice for this demo:

1. lower cold-start burden,
2. lower serverless cost,
3. better single-worker throughput,
4. enough retained quality for an intake-and-booking workflow.

### 11.5 Why Load Balancer Instead of Queue Endpoint

The product needs:

1. interactive websocket behavior,
2. streaming responses,
3. lower-latency request handling,
4. direct real-time API behavior.

That is what RunPod load-balancing endpoints are for.

## 12. High-Level System Flow

1. User opens dashboard on Vercel.
2. User clicks `Warm Up`.
3. Frontend calls backend warm-up endpoint.
4. Backend verifies:
   - model ready,
   - STT configured,
   - TTS configured,
   - database reachable.
5. User clicks `Start Call`.
6. Browser streams mic audio to backend.
7. Backend sends audio to STT.
8. STT returns transcript and language metadata.
9. Backend retrieves customer profile, transactions, and relevant Westpac knowledge as needed.
10. Backend sends compact context to the LLM.
11. LLM returns streamed text.
12. Backend sends streamed text to TTS.
13. TTS returns streamed audio to browser.
14. Backend continuously writes turn data and structured summaries to Supabase.
15. Dashboard pages read live data from Supabase-backed APIs.
16. Banker accepts appointment slot from dashboard.
17. Calendar and appointment state update accordingly.

## 13. Feature Set

### 13.1 Live Call Control Room

New route: `/live`

Purpose:

1. operator starts and controls the voice session,
2. operator warms the backend,
3. operator changes voice and language preferences,
4. operator views transcript and timing live,
5. operator demonstrates model responsiveness and switching behavior.

Required UI elements:

1. `Warm Up` button
2. `Start Call` button
3. `End Call` button
4. status chip:
   - offline,
   - warming,
   - ready,
   - in call,
   - degraded,
   - error
5. live transcript stream
6. live sentiment/emotion strip
7. voice selector:
   - Indian English default,
   - Australian English,
   - Hindi,
   - Mandarin,
   - Cantonese,
   - Greek
8. language mode:
   - auto,
   - manual override
9. backend latency metrics:
   - STT,
   - LLM TTFT,
   - TTS first audio,
   - end-to-end

### 13.2 Banker-Facing Dashboard Dynamicization

The existing lender dashboard should remain the polished banker-facing story.

Dynamic changes:

1. `My Appointments` becomes live data instead of mock data.
2. `Calendar` uses actual appointment records and banker slot states.
3. `Clients` reads synthetic customer profile records from Supabase.
4. `Appointment Detail` reads transcripts, extracted facts, strategy, and sentiment from stored call data.
5. `Analytics` reads live operational metrics and call outcomes.

### 13.3 Synthetic Banking Data Layer

For the demo customer we will generate:

1. current accounts,
2. savings accounts,
3. credit card,
4. personal loan or no personal loan depending on persona,
5. recurring bills,
6. recurring subscriptions,
7. coffee and food-delivery transactions,
8. fake due dates,
9. fake repayment reminders,
10. fake balance history.

This lets the AI answer questions like:

1. spending patterns,
2. affordability tradeoffs,
3. simple goal planning,
4. account complexity,
5. product fit or banker-routing reasons.

### 13.4 Bankers and Availability

The system will store hardcoded Friday availability for next week.

Required states:

1. available
2. offered
3. primary-selected-by-customer
4. fallback-selected-by-customer
5. accepted-by-banker
6. declined-by-banker
7. booked

### 13.5 Appointment Workflow

Customer-facing flow:

1. AI checks availability.
2. AI offers two suitable slots.
3. Customer selects preferred slot.
4. AI asks for fallback slot.
5. AI confirms that the banker will review and respond.

Banker-facing flow:

1. Banker sees appointment card with primary and fallback options.
2. Banker accepts one option.
3. Calendar updates with confirmed booking.
4. Appointment detail page reflects final slot and call summary.

### 13.6 Analytics

The analytics page should stop being static and show:

1. active session state,
2. warm status,
3. number of completed demo calls,
4. total booked appointments,
5. average call duration,
6. average TTFA,
7. escalation count,
8. top intents,
9. sentiment distribution,
10. model version.

## 14. Supported Customer Scenarios

### 14.1 Scenario One: Home Loan Refinancing and Banker Booking

Goal:

1. show realistic first-contact intake,
2. collect useful data,
3. offer banker slots,
4. populate the dashboard with banker-ready context.

### 14.2 Scenario Two: Lost Card or Fraud Concern

Goal:

1. show safe boundary behavior,
2. show correct escalation language,
3. show banker or security handoff packet.

### 14.3 Scenario Three: Car Goal and Spending Insight

Goal:

1. show value beyond static FAQ,
2. use synthetic transactions,
3. generate practical recommendations,
4. demonstrate that the AI can be helpful without being dangerous.

## 15. Conversational Behavior Spec

### 15.1 Opening

The AI should:

1. introduce itself as Westpac’s AI customer assistant,
2. mention recording in demo language,
3. ask for name and DOB,
4. simulate verification,
5. move directly into intent capture.

### 15.2 Tone

1. calm,
2. concise,
3. professional,
4. natural,
5. not robotic,
6. not over-enthusiastic.

### 15.3 Humor Policy

Humor is allowed only when:

1. the customer is clearly playful,
2. the topic is low-risk,
3. the core financial content remains serious and factual.

Humor is disallowed for:

1. fraud,
2. hardship,
3. disputes,
4. sensitive card or account issues,
5. any risk-heavy scenario.

### 15.4 Language Behavior

1. detect language every turn,
2. if confidence is low, confirm in English first,
3. reply in the confirmed or detected language,
4. keep voice selection per reply,
5. allow manual override from the live UI.

### 15.5 Filler and Perceived Latency

If there is backend delay, the AI may use short professional acknowledgements such as:

1. `Let me check that for you.`
2. `One moment while I look into that.`
3. `Good question, I’ll pull that up now.`

These should be triggered by orchestration rules, not relied on purely through prompting.

## 16. Intent Routing

Routing buckets:

1. `Home Loans / Mortgages`
2. `Cards & Payments`
3. `Transactions & Accounts`
4. `Digital Banking Support`
5. `Security Specialist Team`
6. `Personal Loans`
7. `Financial Hardship`
8. `Disputes / Chargebacks`

Routing rules:

1. Fraud, scam, suspicious access, lost or stolen card trends toward `Security Specialist Team`.
2. Home purchase, refinance, borrowing power, fixed-rate expiry, lender comparison, deposit, or pre-approval trends toward `Home Loans / Mortgages`.
3. Explicit human request routes to the closest matching specialist team.
4. Unsupported but low-risk questions can be answered from the knowledge pack first.

## 17. Knowledge and Retrieval

### 17.1 Knowledge Source

Do not use live web search in v1.

Use a local knowledge pack composed of:

1. Westpac rates snapshots,
2. product summaries,
3. Book a Banker information,
4. approved FAQ snippets,
5. known routing guidance.

### 17.2 Retrieval Approach

1. store documents as markdown or text files,
2. chunk them,
3. embed them,
4. retrieve top matches for grounded responses,
5. include references in structured logs even if not shown to customer.

## 18. Sentiment and Emotion

### 18.1 Goal

The dashboard should help the banker understand customer mood and urgency, not just raw text.

### 18.2 Implementation

1. `VADER` for fast polarity.
2. lightweight emotion classifier for:
   - calm,
   - anxious,
   - frustrated,
   - angry,
   - confused
3. trend logic across turns, not one-turn classification only.

### 18.3 Dashboard Usage

1. show sentiment badge on appointment cards,
2. show score and note in appointment detail,
3. use trend for banker preparation strategy.

## 19. Synthetic Financial Insight Engine

This is a key differentiator in the pitch because it shows useful customer-facing value.

### 19.1 Supported Insight Types

1. category spend totals,
2. monthly spend averages,
3. recurring merchant patterns,
4. simple goal-gap analysis,
5. discretionary-spend flags,
6. bill clustering and due-date awareness.

### 19.2 Guardrails

1. insights must be derived from synthetic stored transactions,
2. the agent must not claim certainty beyond the available fake data,
3. tone can be lightly playful only if user is playful,
4. recommendations must remain practical and non-judgmental.

### 19.3 Example Output Style

Good:

1. `You spent about $2,000 on cafe purchases over the past year. If reducing that spend feels realistic, that could help your savings goal.`

Bad:

1. insulting the customer,
2. giving hard financial advice,
3. making lifestyle judgments,
4. fabricating repayment outcomes.

## 20. Data Model

### 20.1 Core Tables

#### `customer_profiles`

Fields:

1. id
2. full_name
3. initials
4. date_of_birth
5. age
6. location
7. profession
8. tenure_label
9. company_name
10. banking_value_label
11. profile_summary
12. created_at
13. updated_at

#### `customer_accounts`

Fields:

1. id
2. customer_id
3. account_type
4. nickname
5. balance
6. currency
7. status
8. due_date
9. metadata_json

#### `customer_transactions`

Fields:

1. id
2. customer_id
3. account_id
4. posted_at
5. merchant
6. description
7. category
8. amount
9. direction
10. is_recurring

#### `bankers`

Fields:

1. id
2. display_name
3. role_title
4. region
5. location_type_support_json
6. bio
7. active

#### `banker_availability`

Fields:

1. id
2. banker_id
3. starts_at
4. ends_at
5. timezone
6. status
7. slot_label

#### `call_sessions`

Fields:

1. id
2. customer_id
3. session_status
4. started_at
5. ended_at
6. detected_languages_json
7. primary_intent
8. routed_team
9. sentiment_label
10. sentiment_score
11. emotion_summary
12. ai_summary_short
13. ai_summary_long
14. recommended_strategy_title
15. recommended_strategy_description
16. booking_state
17. created_at

#### `call_turns`

Fields:

1. id
2. session_id
3. speaker
4. text
5. timestamp_label
6. language_code
7. turn_index
8. stt_latency_ms
9. llm_latency_ms
10. tts_latency_ms

#### `appointments`

Fields:

1. id
2. customer_id
3. session_id
4. banker_id
5. appointment_type
6. location_type
7. intent
8. ai_note
9. sentiment
10. sentiment_score
11. status
12. preferred_slot_id
13. fallback_slot_id
14. confirmed_slot_id
15. created_at

#### `knowledge_documents`

Fields:

1. id
2. slug
3. title
4. content
5. source_label
6. updated_at

### 20.2 Derived Views

We should create Supabase views for:

1. lender dashboard appointment cards,
2. client history rollup,
3. analytics daily summary,
4. appointment detail join,
5. transaction category aggregates.

## 21. API Design

### 21.1 Frontend to Backend

#### `POST /api/warmup`

Purpose:

1. warm the model,
2. test credentials,
3. confirm readiness.

#### `GET /api/health`

Purpose:

1. expose service health,
2. show model ready state,
3. show provider connectivity state.

#### `WS /api/live/session`

Purpose:

1. stream audio in,
2. stream transcript and text out,
3. stream audio out,
4. push live metrics and structured events.

#### `GET /api/appointments`

Purpose:

1. return live banker appointments.

#### `GET /api/appointments/:id`

Purpose:

1. return full detail view data.

#### `POST /api/appointments/:id/accept`

Purpose:

1. banker accepts selected slot.

#### `GET /api/clients`

Purpose:

1. return client rollups.

#### `GET /api/analytics`

Purpose:

1. return current operations and daily metrics.

### 21.2 Internal Tools Exposed to the LLM

1. `get_customer_profile(customer_id)`
2. `get_customer_accounts(customer_id)`
3. `get_customer_transactions(customer_id, range)`
4. `get_spending_summary(customer_id)`
5. `search_knowledge_pack(query)`
6. `get_available_banker_slots(intent, date_range)`
7. `hold_customer_slot(session_id, slot_id, slot_type)`
8. `create_appointment_offer(session_id, primary_slot_id, fallback_slot_id)`
9. `create_call_summary(session_id)`
10. `route_to_team(intent, emotion, risk_flags)`

## 22. Dashboard Integration Plan

### 22.1 Existing Pages To Keep

Keep and rewire:

1. appointments page,
2. calendar page,
3. clients page,
4. appointment detail page,
5. analytics page.

### 22.2 New Page To Add

Add:

1. `/live` operator page for call demo control.

### 22.3 Data Contract Mapping

Current dashboard fields already align well with what the AI should generate:

1. `customerName`
2. `customerInitials`
3. `time`
4. `date`
5. `type`
6. `locationType`
7. `sentiment`
8. `sentimentScore`
9. `sentimentNote`
10. `intent`
11. `aiNote`
12. `collectedData`
13. `recommendedStrategy`
14. `transcript`

This means the frontend redesign burden is moderate. The real work is data plumbing.

## 23. Latency Plan

### 23.1 Estimated Budget

Warm path expected:

1. browser upload and segmentation: `50-150ms`
2. STT partial and end-of-turn: `250-600ms`
3. retrieval and tool prep: `50-150ms`
4. LLM TTFT: `300-900ms`
5. TTS first audio: `100-250ms`
6. network overhead: `100-300ms`

Expected TTFA:

1. typical: `0.9-1.8s`
2. acceptable demo spike: `2.2s`

### 23.2 Latency Controls

1. warm-up request before demo,
2. keepalive during demo window,
3. short default replies,
4. streamed TTS,
5. orchestration filler phrases if TTFT drifts too high,
6. compact context with rolling summaries.

## 24. Risk Management

### 24.1 Hallucination Control

We reduce risk by limiting the agent to:

1. intake,
2. qualification,
3. grounded product explanation,
4. booking,
5. structured summarization,
6. routing.

We do not let it:

1. move money,
2. change real account state,
3. promise policy exceptions,
4. quote fabricated rates or balances.

### 24.2 Demo Risk

1. provider latency spikes,
2. voice API failures,
3. model cold-start delay,
4. missing dashboard data sync.

Mitigations:

1. warm-up,
2. single-caller design,
3. persisted appointment and call rows in Supabase,
4. explicit health checks,
5. fallback acknowledgement phrases.

### 24.3 Secret Handling

Secrets already exist but must not be committed to git. They belong only in local `.env` files, Vercel environment variables, and RunPod worker environment variables.

## 25. Implementation Phases

### Phase 1: Backend Foundation

1. FastAPI app
2. health endpoint
3. warm-up endpoint
4. Supabase connection
5. environment loading

### Phase 2: Database and Synthetic Data

1. schema creation SQL
2. seed banker persona
3. seed customer persona
4. seed accounts and transactions
5. seed Friday availability
6. seed initial knowledge documents

### Phase 3: Live Voice Loop

1. websocket session
2. STT integration
3. vLLM integration
4. TTS integration
5. live event streaming

### Phase 4: Booking and Routing

1. banker slot lookup
2. booking offer creation
3. appointment creation
4. routing handoff states

### Phase 5: Dashboard Wiring

1. replace mock data reads
2. add live page
3. add real analytics
4. add banker accept action
5. add dynamic calendar

### Phase 6: Demo Hardening

1. script rehearsal
2. latency tuning
3. prompt tuning
4. safety wording refinement
5. UI polish

## 26. Demo Script Recommendations

### Script 1: Refinance and Book a Banker

Customer asks about refinancing because fixed rate is ending and wants to compare options. AI collects details, checks Friday availability, offers two slots, captures primary and fallback, and creates a lender-ready appointment.

### Script 2: Lost Card and Transfer

Customer reports a missing card and suspicious behavior. AI refuses to over-handle it, uses the `Security Specialist Team` wording, explains that the issue needs a specialist, and ends the call cleanly.

### Script 3: Car Goal and Spending Insight

Customer says they want to buy a car by the end of the year but feel broke. AI reviews synthetic transactions, surfaces spending patterns, gives practical guidance, and suggests whether a banker conversation could help.

## 27. Detailed Setup Steps

### 27.1 Supabase SQL Path

You selected manual SQL execution. The implementation will therefore produce one SQL file that can be pasted into the Supabase SQL editor.

Steps:

1. Open Supabase project dashboard.
2. Go to `SQL Editor`.
3. Create a new query.
4. Paste the full schema and seed SQL I generate.
5. Run it once.
6. Confirm the tables and seeded rows exist under `Table Editor`.

### 27.2 RunPod Setup

Steps:

1. Log into RunPod.
2. Go to `Serverless`.
3. Create a `Load Balancer` endpoint, not a queue endpoint.
4. Choose `A40` or `A6000`.
5. Configure the container image we will build.
6. Set environment variables for backend secrets.
7. Enable `FlashBoot` if available.
8. Prefer cached model loading for Qwen.
9. Set a small idle timeout appropriate for the demo.

### 27.3 Vercel Setup

Steps:

1. Push the dashboard repo to GitHub.
2. Import the repo into Vercel.
3. Add environment variables for the frontend:
   - public Supabase URL
   - public Supabase anon key
   - public backend API URL
4. Attach your chosen custom domain after functionality is stable.

### 27.4 ElevenLabs Setup

Steps:

1. Keep the selected voice IDs in backend config.
2. Map the default voice to Indian English for the opening gag.
3. Allow frontend voice override to Australian English or language-specific voices.

### 27.5 Knowledge Pack Setup

Steps:

1. collect current Westpac product and rate snippets,
2. write them into markdown files,
3. include source labels and last-updated dates,
4. ingest them into the knowledge table or local document loader.

## 28. Remaining Inputs Needed From You

Most core infrastructure choices are now locked. Remaining items are content and deployment-level rather than architectural.

### Required Later

1. final custom domain for Vercel, if any,
2. final RunPod region after latency testing,
3. the exact Westpac pricing and product snippets you want grounded in the knowledge pack,
4. confirmation on whether Cantonese stays in the demo language list,
5. final demo opening wording,
6. final banker acceptance copy on the dashboard,
7. secret rotation before public or shared deployment.

## 29. Final Recommendation

Build the product as a live intake-and-booking system, not as a general customer-service replacement.

The strongest executive story is:

1. the AI handles repetitive first contact,
2. the AI creates banker-ready context,
3. the AI reduces customer repetition,
4. the AI gives multilingual coverage and intelligent triage,
5. the dashboard proves operational value and banker productivity.

That is a stronger case than trying to sell unrestricted autonomous banking in one leap.

## 30. Research Notes

This PRD uses current Westpac public wording around `Book a Banker`, `home loan specialists`, `Westpac lender`, and appointment modes including phone, video chat, in branch, and meeting a mobile lender.

It also uses current RunPod serverless and pricing guidance for load-balanced endpoints and A40/A6000 worker economics.
