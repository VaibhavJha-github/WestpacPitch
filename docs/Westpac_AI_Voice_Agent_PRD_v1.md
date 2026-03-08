WESTPAC AI VOICE AGENT DEMO PRD (V1)
Date: 2026-03-04
Owner: Vaibhav Jha
Status: Draft for execution

===============================================================================
1) EXECUTIVE SUMMARY
===============================================================================
Build a high-quality, low-latency web-based voice AI demo for Westpac executives.
The user speaks from a web app on a MacBook. The assistant transcribes speech,
replies naturally (multilingual), triages to the right support team, and can
book a real "Book a Banker" meeting (Google Calendar invite).

This PRD is optimized for:
- Demo reliability in front of executives
- Low operational cost
- Strong conversational quality
- Fast iteration before full production hardening

Locked architecture pivot:
- LLM on RunPod Serverless (NOT active worker)
- Quantized model for serverless latency/cost: Qwen2.5-14B-Instruct-AWQ
- STT via OpenAI API
- TTS via ElevenLabs Flash v2.5
- Web call only (no Twilio in this phase)
- Single concurrent caller

===============================================================================
2) GOALS, NON-GOALS, AND SUCCESS CRITERIA
===============================================================================
2.1 Goals
- Deliver a realistic first-contact customer service call experience.
- Demonstrate intelligent triage (correct team routing).
- Demonstrate "Book a Banker" booking for relevant intents.
- Demonstrate multilingual turn-level adaptation.
- Demonstrate sentiment + emotion-aware behavior.
- Provide structured handoff output to dashboard ingestion.

2.2 Non-Goals (V1)
- Production banking-core integration.
- Real identity verification enforcement.
- Multi-user concurrency.
- Full legal/compliance implementation for external customers.
- Telephony network support (Twilio reserved for future phase).

2.3 Success Criteria (Demo Acceptance)
Functional:
- Agent can hold a coherent 10-minute conversation.
- Agent can route to correct team bucket in at least 90% of scripted scenarios.
- Agent can create a Google Calendar invite when booking is accepted.
- Agent can switch language per turn and speak in detected/selected language.

Experience:
- Time to first AI audio (warm path): target <= 1.8s, stretch <= 2.2s.
- Typical short turn completion: target <= 4.0s.
- Agent speech tone sounds professional and natural.

Reliability:
- Warm-up flow works before demo start.
- Keepalive prevents mid-demo scale-to-zero during session window.
- Handoff JSON delivery has retry queue fallback.

===============================================================================
3) SCOPE
===============================================================================
3.1 In Scope (V1)
- Web app call UI (mic input, audio output, controls).
- Orchestration service (session state, routing, tools, prompting).
- STT integration with language detection.
- LLM integration (RunPod serverless endpoint).
- TTS integration with selectable voices and multilingual output.
- Team triage logic.
- Sentiment and emotion inference pipeline.
- Calendar booking tool integration.
- Dashboard payload publishing.

3.2 Out of Scope (V1)
- Agent to human live transfer telephony bridge.
- SMS sending.
- Customer-side identity docs or secure verification backends.
- CRM writeback or real ticketing integration.

===============================================================================
4) USERS AND USE CASES
===============================================================================
4.1 Primary User
- Demo operator (you), speaking as customer via web UI.

4.2 Secondary User
- Executive audience observing call quality, triage quality, and outputs.

4.3 Core Use Cases
- UC1: Customer asks general question; AI responds and triages if required.
- UC2: Customer asks home-loan-related request; AI offers Book a Banker.
- UC3: Customer expresses fraud/lost card/scam concern; AI routes to
       Security Specialist Team language (without awkward naming).
- UC4: Customer language changes mid-call; AI adapts output language.
- UC5: System emits structured post-call artifact for dashboard display.

===============================================================================
5) PRODUCT REQUIREMENTS (DETAILED)
===============================================================================
5.1 Call Lifecycle
- Start Call:
  - User clicks "Warm Up" then "Start Call".
  - System verifies endpoint, STT, TTS connectivity.
  - Agent greeting + recording disclosure + consent prompt.

- Mid Call:
  - Continuous turn-taking with speech barge behavior (future-ready).
  - User speaks, STT streams transcript.
  - LLM returns streamed tokens.
  - TTS streams response audio.
  - Sentiment/emotion updates each turn.

- End Call:
  - Agent recap.
  - If triage path selected, state transfer destination.
  - If booking path selected, confirm calendar booking details.
  - Publish handoff payload to dashboard endpoint.

5.2 Greeting and Opening Script Behavior
- Required opening behavior:
  - Agent introduces itself as Westpac AI customer assistant.
  - States call may be recorded for quality/training (demo mode).
  - Requests customer name + DOB verbally for flow realism.
  - For demo, verification is simulated (no hard backend check).

5.3 Language Handling
- STT auto-detect language every turn.
- If confidence below threshold (e.g., <0.75), ask in English:
  "I heard [language]. Would you like to continue in English or [language]?"
- Output language defaults to detected or user-confirmed language.
- TTS voice can be switched by UI at runtime (per-turn).

5.4 Team Triage Logic
Team buckets:
- Cards & Payments
- Transactions & Accounts
- Home Loans / Mortgages
- Personal Loans
- Security Specialist Team
- Disputes / Chargebacks
- Digital Banking / App Support
- Financial Hardship

Routing behaviors:
- If user explicitly asks for human escalation -> route to best matching team.
- If risk-sensitive (fraud/scam/lost stolen) -> prioritize Security Specialist Team.
- If request is outside policy scope -> explain limitation + route.

5.5 Book a Banker Logic
- Offer booking when intent is home-loan/mortgage aligned.
- Ask for preferred time window and confirm Australia/Brisbane timezone.
- Meeting duration fixed at 30 minutes.
- Create Google Calendar event and invite:
  - vaibhav130304@gmail.com
- Event title:
  - "Westpac Book a Banker - Follow-up"
- Agent confirms booking in-call.

5.6 Sentiment + Emotion
- Sentiment model: VADER over cleaned transcript chunks.
- Emotion classifier: transformer-based labeler (calm/anxious/frustrated/angry/
  confused).
- Use trend-aware rules, not single-turn only.
- Add emotion and risk flags to handoff payload.

5.7 Dashboard Handoff Artifact
- Generate structured JSON at call end (and periodic snapshots optional).
- On publish failure, push to retry queue.
- Manual deletion policy retained by operator.

===============================================================================
6) NON-FUNCTIONAL REQUIREMENTS
===============================================================================
6.1 Performance Targets
- Warm TTFA: <= 1.8s typical.
- Turn completion (short response): <= 4.0s typical.
- LLM token generation target (serverless warm): ~40-120 tok/s expected,
  hardware dependent.

6.2 Availability and Reliability
- Pre-demo warm-up required.
- Keepalive ping every 2-3 minutes during 30-minute demo window.
- Health endpoint required before call starts.

6.3 Cost
- Optimize for low recurring cost with serverless scale-to-zero.
- Avoid active workers by design.
- Quantized model to reduce inference and startup cost.

6.4 Security (Demo)
- Secrets in env variables only.
- No hardcoded API keys.
- TLS over all external APIs.
- Tailscale/private access for backend admin endpoints.

===============================================================================
7) MODEL AND INFRA DECISION RECORD
===============================================================================
7.1 Why Qwen2.5-14B-Instruct-AWQ
- Better serverless fit than 24B class for latency/cost.
- Strong multilingual behavior.
- Good instruction-following and tool-call handling with prompt engineering.
- Quantization quality drop acceptable for demo.

7.2 Why Not 24B for Default
- Higher cold/warm resource demand.
- Potentially slower and costlier under serverless constraints.
- More risk for live executive demo reliability if endpoint variability appears.

7.3 RunPod Strategy
- Serverless endpoint only.
- min workers = 0.
- Use warm-up button + keepalive to avoid start lag during demo.
- Prefer cached model path over network volume unless custom assets mandate it.

===============================================================================
8) HIGH-LEVEL ARCHITECTURE
===============================================================================
8.1 Components
- Frontend (Web app on MacBook)
  - Mic capture, speaker playback, controls, transcript and debug panels.
- Orchestrator API (Backend)
  - Session state, STT/TTS/LLM routing, booking tool, sentiment/emotion.
- STT Provider
  - OpenAI gpt-4o-mini-transcribe.
- LLM Provider
  - RunPod Serverless endpoint hosting Qwen2.5-14B-Instruct-AWQ.
- TTS Provider
  - ElevenLabs Flash v2.5.
- Tool Integration
  - Google Calendar API.
- Observability + Artifact
  - Structured JSON handoff to dashboard webhook.

8.2 Sequence (Per Turn)
1) User audio chunk -> frontend websocket -> backend.
2) Backend forwards/streams to STT.
3) STT partial transcript arrives.
4) End-of-turn detected.
5) Backend sends compact context + latest user turn to LLM.
6) LLM streams tokens.
7) Backend sends text chunks to TTS.
8) TTS streams audio to frontend.
9) Backend updates sentiment/emotion and logs turn metadata.

===============================================================================
9) LATENCY ENGINEERING PLAN
===============================================================================
9.1 Pipeline Budget (Warm)
- STT detection + partial: 250-600ms
- LLM TTFT: 300-900ms
- TTS first audio: 100-250ms
- Network overhead: 100-300ms
Estimated TTFA: 0.9-1.8s
Estimated full short turn: 2.0-4.0s

9.2 Perceived Latency Masking
- If no LLM token by 450-700ms:
  - play short acknowledgement phrase:
    "Good question, let me check that for you."
- Start TTS as soon as first meaningful chunk arrives.
- Keep generated responses concise unless user asks for detail.

9.3 Context Control
- Sliding context window target: 8k-16k active tokens.
- Every 3-4 turns, summarize prior context and compress memory.
- Keep explicit factual memory list (customer intent, constraints, next action).

===============================================================================
10) PROMPT AND POLICY SPEC
===============================================================================
10.1 System Prompt Core Directives
- You are Westpac first-contact AI assistant (demo scope).
- Be calm, concise, clear, and professional.
- Ask one focused follow-up question when needed.
- Never fabricate policy, fees, balances, or outcomes.
- Never request PIN/CVV/password/OTP.
- Escalate to correct specialist team when outside scope or high risk.
- Offer Book a Banker when mortgage/home-loan intent is present.

10.2 Response Style Rules
- 1-3 sentence default responses.
- Natural fillers allowed when waiting/tooling latency occurs.
- Avoid overly robotic repetitive phrases.

10.3 Escalation Text Rules
- Use phrase: "Security Specialist Team" for fraud/scam/lost card risk.
- Never say "scam team" or casual internal language.
- If user requests human: route and confirm transfer path clearly.

===============================================================================
11) SENTIMENT + EMOTION DESIGN
===============================================================================
11.1 Inputs
- Turn transcript + running call context.

11.2 Outputs
- Sentiment score: negative/neutral/positive + compound.
- Emotion labels with confidence.
- Escalation recommendation flag.

11.3 Suggested Rules
- If anger/frustration high for >=2 turns and unresolved intent:
  - prefer human escalation.
- If anxiety + fraud-like terms appear:
  - route to Security Specialist Team.

===============================================================================
12) BOOKING TOOL SPEC (GOOGLE CALENDAR)
===============================================================================
12.1 Trigger
- Home loan/mortgage-related intent and user says yes to booking.

12.2 Inputs Collected in Conversation
- Preferred day/time window.
- Confirmation of timezone (Brisbane).

12.3 Event Creation Defaults
- Title: Westpac Book a Banker - Follow-up
- Duration: 30 minutes
- Attendee: vaibhav130304@gmail.com
- Timezone: Australia/Brisbane
- Description includes:
  - short issue summary
  - triage team
  - sentiment/emotion summary (if desired)

12.4 Failure Handling
- If Calendar API fails:
  - apologize, mention temporary issue, and offer callback/escalation path.

===============================================================================
13) DATA CONTRACTS
===============================================================================
13.1 Session Start Request
- session_id
- selected_voice
- selected_language_mode (auto/manual)
- consent_response

13.2 Turn Event
- timestamp
- raw_transcript
- detected_language
- language_confidence
- llm_reply_text
- tts_voice_used
- latency_metrics

13.3 Handoff Payload (to Dashboard)
- session_id
- start_time/end_time
- transcript_summary_short
- transcript_summary_detailed
- detected_languages
- primary_intent
- routed_team
- routing_confidence
- sentiment_timeline
- emotion_timeline
- risk_flags
- booking_status
- booking_event_id
- recommended_human_approach

===============================================================================
14) FRONTEND SPEC (WEB CALL + EXEC PANEL)
===============================================================================
14.1 Core Controls
- Warm Up GPU/Endpoint button
- Start Call / End Call button
- Voice selector (AU English default)
- Language mode selector (auto/manual)
- Live latency indicator

14.2 Panels
- Live transcript (user and AI turns)
- Triage decision + confidence
- Sentiment/emotion timeline
- Tool events (booking created / escalation path)
- Backend health status

14.3 UX Notes
- Keep visual design professional and minimal.
- Add clear status chips: WARMING, READY, IN CALL, ERROR.

===============================================================================
15) BACKEND IMPLEMENTATION PLAN
===============================================================================
Recommended stack:
- FastAPI (Python) backend
- WebSocket for streaming call session
- Async task queue for webhook retries

Services/modules:
- session_manager.py
- stt_client.py
- llm_client.py
- tts_client.py
- sentiment_engine.py
- routing_engine.py
- booking_tool.py
- handoff_publisher.py
- health_router.py

===============================================================================
16) DEPLOYMENT PLAN
===============================================================================
16.1 Environments
- local-dev (MacBook)
- demo-prod (cloud backend + RunPod endpoint)

16.2 RunPod Endpoint Config (Target)
- Serverless enabled
- min workers = 0
- max workers = 1
- idle timeout handled via keepalive for demo window
- model: Qwen2.5-14B-Instruct-AWQ
- quantization: AWQ 4-bit

16.3 Warm-up Strategy
- Warm-up button sends:
  - endpoint health check
  - short dummy completion request
- UI blocks Start Call until READY = true.

===============================================================================
17) TEST PLAN
===============================================================================
17.1 Unit Tests
- Intent routing rules
- Language confidence fallback
- Sentiment/emotion pipeline output shape
- Booking request validation

17.2 Integration Tests
- STT -> LLM -> TTS full turn
- Booking success and failure modes
- Handoff webhook publish + retry
- Warm-up and keepalive behavior

17.3 Demo Scenario Tests (Must Pass)
- Scenario A: Home loan inquiry -> booking success.
- Scenario B: Lost/stolen card concern -> Security Specialist Team route.
- Scenario C: English -> Hindi -> English turn switching.
- Scenario D: User asks human escalation explicitly -> correct team route.

===============================================================================
18) RISKS AND MITIGATIONS
===============================================================================
Risk: Serverless cold start delay.
Mitigation: warm-up button + pre-demo run + keepalive.

Risk: Language misdetection.
Mitigation: confidence threshold and English confirmation fallback.

Risk: Incorrect triage.
Mitigation: explicit routing rules + keyword guardrails + confidence score.

Risk: Calendar API token failure.
Mitigation: token refresh checks before demo + fallback verbal path.

Risk: API provider latency spike.
Mitigation: acknowledgement fillers + concise response policy.

===============================================================================
19) EXECUTIVE DEMO RUNBOOK
===============================================================================
T-30 minutes:
- Start backend service.
- Press Warm Up.
- Validate all health checks green.
- Run one dry call (2 turns).

T-10 minutes:
- Confirm voice/language defaults.
- Confirm Google Calendar token valid.
- Confirm dashboard webhook reachable.

During demo:
- Run 2 scripted scenarios + 1 spontaneous scenario.
- Keep answers concise and high confidence.
- Use triage confidence panel to explain decisions.

===============================================================================
20) WHAT I STILL NEED FROM YOU (WITH EXACT STEPS)
===============================================================================
20.1 Dashboard Webhook URL and Contract
What I need:
- Webhook URL for handoff JSON POST.
- Required headers/auth method.
- Required/optional payload fields.

How to get/provide:
1) Ask your friend for endpoint URL and sample payload format.
2) Ask whether auth is Bearer token or API key header.
3) Share one working curl example with request body.
4) Confirm success response code/body (e.g., 200 + {ok:true}).

20.2 RunPod Endpoint Access Details
What I need:
- Endpoint ID/URL
- API key/token
- Selected GPU tier and region preference

How to get it (RunPod console):
1) Log in to RunPod.
2) Go to Serverless -> Endpoints -> Create Endpoint.
3) Select template/runtime for vLLM-compatible inference.
4) Set model to Qwen2.5-14B-Instruct-AWQ.
5) Save endpoint and copy endpoint URL/ID.
6) Create API key under account settings and copy token.
7) Share endpoint URL + token securely (.env entry, not chat plain text).

20.3 OpenAI STT API Key
What I need:
- OPENAI_API_KEY

How to get it:
1) Visit platform.openai.com and sign in.
2) Go to API Keys.
3) Create new secret key.
4) Copy once and store in your password manager.
5) Add to .env as OPENAI_API_KEY=...

20.4 ElevenLabs API Key + Voice IDs
What I need:
- ELEVENLABS_API_KEY
- Voice IDs for:
  - AU English default
  - Hindi
  - Mandarin
  - Greek

How to get it:
1) Log in to ElevenLabs.
2) Open profile/settings -> API keys -> create key.
3) Go to Voices library.
4) Pick desired voices and note each voice_id.
5) Test short sample for each voice quality.
6) Share selected voice_id mapping.

20.5 Google Calendar OAuth Credentials
What I need:
- GOOGLE_CLIENT_ID
- GOOGLE_CLIENT_SECRET
- Authorized redirect URI
- Token generated for your Gmail account

How to set up (Google Cloud):
1) Go to console.cloud.google.com.
2) Create/select a project.
3) Enable Google Calendar API.
4) Configure OAuth consent screen (External/Internal as needed).
5) Create OAuth client credentials (Web application).
6) Add redirect URI used by backend (e.g., http://localhost:8000/auth/callback).
7) Download client JSON.
8) Run local auth flow once to generate refresh token.
9) Store credentials and token in secure env/config.

20.6 Tailscale Networking Details
What I need:
- Confirmation MacBook and backend host are in same Tailscale tailnet.
- Backend reachable private URL.

How to set up:
1) Install Tailscale on each machine.
2) Log into same Tailscale account/tailnet.
3) Confirm both devices appear as connected.
4) Note backend machine tailnet IP or DNS name.
5) Test from MacBook: curl backend /health URL over tailnet.

20.7 Demo Voice Script Approvals
What I need:
- Final opening script sentence.
- Final escalation phrases per team.
- Final booking confirmation phrasing.

How to provide:
1) I will give draft copy variants.
2) You choose preferred style (formal/neutral/friendly).
3) We lock wording for demo consistency.

20.8 Demo Scenario Script List
What I need:
- 3 exact scenarios you will perform live.

How to provide:
1) Write one sentence goal for each scenario.
2) Include one expected AI success behavior per scenario.
3) Include one fail-safe line if tool/API fails.

20.9 Budget/Runtime Guardrails
What I need:
- Max spend target for demo day.
- Allowed warm-up duration before session.

How to provide:
1) Choose budget ceiling (e.g., <= $20 total).
2) Choose pre-warm lead time (e.g., 15 min).
3) Choose keepalive window (already chosen: 30 min).

===============================================================================
21) OPEN ITEMS (TO RESOLVE IN PRD V2)
===============================================================================
- Dashboard payload final schema and endpoint auth.
- Exact RunPod region after latency checks.
- Final selected voice IDs and multilingual tone profile.
- Final prompt wording with Westpac team naming validation.
- Optional Phase 2 phone-call path (currently out of scope).

===============================================================================
22) RECOMMENDED NEXT ACTIONS (IMMEDIATE)
===============================================================================
1) Confirm dashboard webhook contract from your friend.
2) Create/collect all API credentials listed above.
3) Stand up backend skeleton and /warmup + /health first.
4) Integrate STT -> LLM -> TTS streaming path.
5) Add triage + booking + sentiment pipeline.
6) Run full demo rehearsal with the 3 scripted scenarios.

END OF DOCUMENT
