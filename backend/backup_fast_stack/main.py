"""Westpac AI Voice Agent — FastAPI Backend."""
import asyncio
import json
import time
import base64
import uuid
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import config
from db import get_supabase
from stt import transcribe_audio, detected_language_to_code
from tts import synthesize_speech, get_voice_id
from llm import generate_response, generate_summary, test_runpod_connection
from sentiment import analyze_sentiment, aggregate_sentiment
from tools import (
    get_customer_profile,
    get_customer_accounts,
    get_spending_summary,
    search_knowledge_pack,
    get_available_banker_slots,
    hold_slot,
    create_appointment,
    accept_appointment_slot,
    route_to_team,
    save_call_session,
    update_call_session,
    save_call_turn,
    update_analytics,
)

# Track warm state
_warm_state = {"model_ready": False, "stt_ready": False, "tts_ready": False, "db_ready": False}


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Westpac AI Voice Agent", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Health & Warmup
# ============================================================

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "warm": _warm_state,
        "model": config.CLAUDE_MODEL if config.ANTHROPIC_API_KEY else config.VLLM_MODEL,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/api/warmup")
async def warmup():
    results = {}

    # Test DB
    try:
        sb = get_supabase()
        sb.table("bankers").select("id").limit(1).execute()
        _warm_state["db_ready"] = True
        results["db"] = "ok"
    except Exception as e:
        results["db"] = str(e)

    # Test STT (just verify key exists)
    _warm_state["stt_ready"] = bool(config.OPENAI_API_KEY)
    results["stt"] = "ok" if _warm_state["stt_ready"] else "no key"

    # Test TTS (just verify key exists)
    _warm_state["tts_ready"] = bool(config.ELEVENLABS_API_KEY)
    results["tts"] = "ok" if _warm_state["tts_ready"] else "no key"

    # Test LLM (Claude → OpenAI → RunPod)
    try:
        resp = await generate_response(
            [{"role": "user", "content": "Say hello in one word."}],
            max_tokens=10,
        )
        _warm_state["model_ready"] = True
        results["llm"] = f"ok ({resp.get('provider', 'unknown')})"
        results["llm_latency_ms"] = resp["latency_ms"]
    except Exception as e:
        results["llm"] = str(e)

    return {"status": "warm" if all(_warm_state.values()) else "partial", "results": results}


# ============================================================
# REST API Endpoints
# ============================================================

@app.get("/api/appointments")
async def list_appointments():
    sb = get_supabase()
    res = sb.table("appointments").select(
        "*, call_sessions(ai_summary_short)"
    ).order("created_at", desc=True).execute()

    appointments = []
    for row in res.data:
        # Get transcript for this appointment
        transcript = []
        if row.get("session_id"):
            turns = sb.table("call_turns").select("*").eq(
                "session_id", row["session_id"]
            ).order("turn_index").execute()
            transcript = [
                {
                    "id": t["id"],
                    "sender": "Bot" if t["speaker"] == "bot" else "Customer",
                    "text": t["text"],
                    "timestamp": t.get("timestamp_label", ""),
                }
                for t in turns.data
            ]

        collected_data = row.get("collected_data_json", [])
        if isinstance(collected_data, str):
            collected_data = json.loads(collected_data)

        # Get slot time for the appointment
        slot_time = None
        slot_date = None
        for slot_key in ["confirmed_slot_id", "preferred_slot_id"]:
            sid = row.get(slot_key)
            if sid:
                slot_res = sb.table("banker_availability").select("starts_at, slot_label").eq("id", sid).execute()
                if slot_res.data:
                    slot_dt = slot_res.data[0]["starts_at"]
                    if slot_dt:
                        dt = datetime.fromisoformat(slot_dt.replace("Z", "+00:00"))
                        slot_time = dt.strftime("%H:%M")
                        slot_date = dt.strftime("%Y-%m-%d")
                    break

        appointments.append({
            "id": row["id"],
            "customerName": row.get("customer_name", ""),
            "customerInitials": row.get("customer_initials", ""),
            "companyName": row.get("company_name"),
            "time": slot_time or datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")).strftime("%H:%M"),
            "date": slot_date or datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")).strftime("%Y-%m-%d"),
            "type": row.get("appointment_type", ""),
            "locationType": row.get("location_type", "Phone"),
            "sentiment": row.get("sentiment", "Neutral"),
            "sentimentScore": float(row.get("sentiment_score", 50)),
            "sentimentNote": row.get("sentiment_note"),
            "intent": row.get("intent", ""),
            "aiNote": row.get("ai_note", ""),
            "status": row.get("status", "Upcoming"),
            "customerTenure": row.get("customer_tenure"),
            "age": row.get("age"),
            "location": row.get("location"),
            "profession": row.get("profession"),
            "totalBankingValue": row.get("total_banking_value"),
            "estimatedLoanSize": row.get("estimated_loan_size"),
            "currentLender": row.get("current_lender"),
            "reasonForLeaving": row.get("reason_for_leaving"),
            "selfDeclaredLVR": row.get("self_declared_lvr"),
            "collectedData": collected_data,
            "recommendedStrategy": {
                "title": row.get("recommended_strategy_title", ""),
                "description": row.get("recommended_strategy_description", ""),
            } if row.get("recommended_strategy_title") else None,
            "transcript": transcript,
        })

    return appointments


@app.get("/api/appointments/{appointment_id}")
async def get_appointment(appointment_id: str):
    appointments = await list_appointments()
    apt = next((a for a in appointments if a["id"] == appointment_id), None)
    if not apt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return apt


class AcceptSlotRequest(BaseModel):
    slot_id: str


@app.post("/api/appointments/{appointment_id}/accept")
async def accept_slot(appointment_id: str, req: AcceptSlotRequest):
    result = accept_appointment_slot(appointment_id, req.slot_id)
    return result


@app.get("/api/clients")
async def list_clients():
    sb = get_supabase()
    # Use the view
    try:
        res = sb.table("v_client_rollup").select("*").execute()
        clients = []
        for row in res.data:
            clients.append({
                "id": f"client-{row['customer_id']}",
                "customerId": row["customer_id"],
                "name": row.get("name", ""),
                "initials": row.get("initials", ""),
                "companyName": row.get("company_name"),
                "location": row.get("location"),
                "profession": row.get("profession"),
                "tenure": row.get("tenure"),
                "totalBankingValue": row.get("total_banking_value"),
                "totalAppointments": row.get("total_appointments", 0),
                "lastContactDate": row.get("last_contact_date", ""),
                "averageSentiment": float(row.get("average_sentiment", 50) or 50),
            })
        return clients
    except Exception:
        # Fallback: derive from appointments
        res = sb.table("customer_profiles").select("*").execute()
        return [
            {
                "id": f"client-{r['id']}",
                "customerId": r["id"],
                "name": r["full_name"],
                "initials": r["initials"],
                "companyName": r.get("company_name"),
                "location": r.get("location"),
                "profession": r.get("profession"),
                "tenure": r.get("tenure_label"),
                "totalBankingValue": r.get("banking_value_label"),
                "totalAppointments": 0,
                "lastContactDate": r.get("created_at", ""),
                "averageSentiment": 50,
            }
            for r in res.data
        ]


@app.get("/api/analytics")
async def get_analytics():
    sb = get_supabase()
    today = datetime.utcnow().strftime("%Y-%m-%d")
    res = sb.table("analytics_snapshots").select("*").eq("snapshot_date", today).execute()

    if res.data:
        snap = res.data[0]
    else:
        # Return defaults
        snap = {
            "total_calls": 0,
            "completed_appointments": 0,
            "avg_call_duration_secs": 0,
            "avg_ttfa_ms": 0,
            "escalation_count": 0,
            "conversion_rate": 0,
            "sentiment_positive_pct": 0,
            "sentiment_neutral_pct": 0,
            "sentiment_anxious_pct": 0,
            "sentiment_frustrated_pct": 0,
            "top_intents_json": [],
            "model_version": config.VLLM_MODEL,
        }

    top_intents = snap.get("top_intents_json", [])
    if isinstance(top_intents, str):
        top_intents = json.loads(top_intents)

    return {
        "warm": _warm_state,
        "today": {
            "totalCalls": snap.get("total_calls", 0),
            "completedAppointments": snap.get("completed_appointments", 0),
            "avgCallDuration": f"{snap.get('avg_call_duration_secs', 0) // 60}m {snap.get('avg_call_duration_secs', 0) % 60}s",
            "avgTTFA": f"{snap.get('avg_ttfa_ms', 0)}ms",
            "escalationCount": snap.get("escalation_count", 0),
            "conversionRate": float(snap.get("conversion_rate", 0)),
        },
        "sentiment": {
            "positive": float(snap.get("sentiment_positive_pct", 0)),
            "neutral": float(snap.get("sentiment_neutral_pct", 0)),
            "anxious": float(snap.get("sentiment_anxious_pct", 0)),
            "frustrated": float(snap.get("sentiment_frustrated_pct", 0)),
        },
        "topIntents": top_intents,
        "modelVersion": snap.get("model_version", config.VLLM_MODEL),
    }


@app.get("/api/banker-slots")
async def get_banker_slots(date: str | None = None):
    slots = get_available_banker_slots(date)
    return slots


# ============================================================
# WebSocket Live Session
# ============================================================

@app.websocket("/api/live/session")
async def live_session(ws: WebSocket):
    await ws.accept()

    session_id = str(uuid.uuid4())
    customer_id = "c0000001-0000-0000-0000-000000000001"  # Default demo customer
    turn_index = 0
    messages = []
    all_turns = []
    voice_override = None
    language_mode = "auto"
    detected_lang = "en"

    # Create session in DB
    save_call_session({
        "id": session_id,
        "customer_id": customer_id,
        "session_status": "active",
    })

    await ws.send_json({
        "type": "session_started",
        "session_id": session_id,
        "customer_id": customer_id,
    })

    # Load customer context
    profile = get_customer_profile(customer_id)
    accounts = get_customer_accounts(customer_id)
    context_parts = []
    if profile:
        context_parts.append(f"Customer: {profile['full_name']}, Age: {profile.get('age')}, Location: {profile.get('location')}, Profession: {profile.get('profession')}, Tenure: {profile.get('tenure_label')}")
    if accounts:
        acct_summary = ", ".join(f"{a['nickname']}: ${a['balance']}" for a in accounts)
        context_parts.append(f"Accounts: {acct_summary}")

    context = "\n".join(context_parts)

    try:
        while True:
            data = await ws.receive_json()
            msg_type = data.get("type")

            if msg_type == "audio":
                # Decode base64 audio
                audio_b64 = data.get("audio", "")
                audio_bytes = base64.b64decode(audio_b64)

                # Skip tiny audio clips (likely noise)
                if len(audio_bytes) < 1000:
                    continue

                # STT
                stt_start = time.time()
                stt_result = transcribe_audio(audio_bytes)
                stt_latency = stt_result["latency_ms"]

                customer_text = stt_result["text"].strip()
                if not customer_text:
                    continue

                raw_lang = detected_language_to_code(stt_result["language"])
                # Only switch language if utterance is long enough (short = likely name/number)
                word_count = len(customer_text.split())
                if word_count >= 4:
                    detected_lang = raw_lang
                # else keep previous detected_lang (defaults to "en")

                turn_index += 1
                all_turns.append({"speaker": "customer", "text": customer_text, "lang": detected_lang, "stt_ms": stt_latency})

                # Send transcript update (no sentiment during call — done post-call)
                await ws.send_json({
                    "type": "transcript",
                    "speaker": "customer",
                    "text": customer_text,
                    "language": detected_lang,
                    "stt_latency_ms": stt_latency,
                    "turn_index": turn_index,
                })

                # Build context for LLM
                messages.append({"role": "user", "content": customer_text})

                # Additional context for tool calls
                extra_context = context
                # Check if we need knowledge
                for kw in ["rate", "loan", "product", "home loan", "fixed", "variable", "first home", "fraud", "scam", "lost card"]:
                    if kw in customer_text.lower():
                        knowledge = search_knowledge_pack(kw)
                        if knowledge:
                            extra_context += "\n\nRelevant Knowledge:\n" + "\n---\n".join(
                                f"{k['title']}: {k['content'][:500]}" for k in knowledge
                            )
                        break

                # Check if spending-related
                for kw in ["spend", "saving", "budget", "afford", "money", "car", "goal", "coffee", "eating out"]:
                    if kw in customer_text.lower():
                        spending = get_spending_summary(customer_id)
                        if spending:
                            extra_context += "\n\nSpending Summary:\n" + "\n".join(
                                f"- {s['category']}: ${s['total_amount']} ({s['transaction_count']} txns, avg ${s['avg_amount']})"
                                for s in spending
                            )
                        break

                # LLM response
                llm_result = await generate_response(messages, context=extra_context)
                llm_latency = llm_result["latency_ms"]

                bot_text = llm_result["text"]

                # Handle tool calls
                if llm_result.get("tool_call"):
                    tc = llm_result["tool_call"]
                    tool_name = tc.get("tool", "")
                    tool_args = tc.get("args", {})
                    tool_result = None

                    if tool_name == "get_available_banker_slots":
                        tool_result = get_available_banker_slots(tool_args.get("date"))
                        if tool_result:
                            slots_text = "\n".join(f"- {s['slot_label']} ({s['status']})" for s in tool_result[:5])
                            messages.append({"role": "assistant", "content": bot_text or "Let me check available slots."})
                            messages.append({"role": "user", "content": f"[Tool result - available slots:\n{slots_text}]\nNow offer the customer 2 suitable slots from this list."})
                            followup = await generate_response(messages, context=extra_context)
                            bot_text = followup["text"]
                            llm_latency += followup["latency_ms"]

                    elif tool_name == "search_knowledge_pack":
                        tool_result = search_knowledge_pack(tool_args.get("query", ""))
                        if tool_result:
                            knowledge_text = "\n---\n".join(f"{k['title']}: {k['content'][:400]}" for k in tool_result)
                            messages.append({"role": "assistant", "content": bot_text or "Let me look that up."})
                            messages.append({"role": "user", "content": f"[Knowledge result:\n{knowledge_text}]\nAnswer the customer's question using this information."})
                            followup = await generate_response(messages, context=extra_context)
                            bot_text = followup["text"]
                            llm_latency += followup["latency_ms"]

                    elif tool_name == "route_to_team":
                        team = route_to_team(tool_args.get("intent", ""), tool_args.get("emotion"))
                        update_call_session(session_id, {"routed_team": team})

                    elif tool_name == "get_spending_summary":
                        tool_result = get_spending_summary(tool_args.get("customer_id", customer_id))
                        if tool_result:
                            spending_text = "\n".join(f"- {s['category']}: ${s['total_amount']} ({s['transaction_count']} txns)" for s in tool_result)
                            messages.append({"role": "assistant", "content": bot_text or "Let me review your spending."})
                            messages.append({"role": "user", "content": f"[Spending data:\n{spending_text}]\nProvide helpful spending insights to the customer."})
                            followup = await generate_response(messages, context=extra_context)
                            bot_text = followup["text"]
                            llm_latency += followup["latency_ms"]

                if not bot_text:
                    bot_text = "I understand. How can I help you further?"

                messages.append({"role": "assistant", "content": bot_text})

                # TTS
                tts_start = time.time()
                voice_lang = detected_lang if language_mode == "auto" else "en-IN"
                try:
                    audio_bytes_out = await synthesize_speech(bot_text, voice_override, voice_lang)
                    tts_latency = int((time.time() - tts_start) * 1000)
                    audio_b64_out = base64.b64encode(audio_bytes_out).decode()
                except Exception as e:
                    print(f"[TTS ERROR] {e}")
                    tts_latency = 0
                    audio_b64_out = ""

                turn_index += 1
                all_turns.append({"speaker": "bot", "text": bot_text, "lang": voice_lang, "llm_ms": llm_latency, "tts_ms": tts_latency})

                await ws.send_json({
                    "type": "response",
                    "text": bot_text,
                    "audio": audio_b64_out,
                    "language": voice_lang,
                    "llm_latency_ms": llm_latency,
                    "tts_latency_ms": tts_latency,
                    "stt_latency_ms": stt_latency,
                    "turn_index": turn_index,
                })

            elif msg_type == "set_voice":
                voice_override = data.get("voice_id")
                await ws.send_json({"type": "voice_updated", "voice_id": voice_override})

            elif msg_type == "set_language_mode":
                language_mode = data.get("mode", "auto")
                await ws.send_json({"type": "language_mode_updated", "mode": language_mode})

            elif msg_type == "end_call":
                break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await ws.send_json({"type": "error", "message": str(e)})
    finally:
        # Post-call: save turns, run sentiment, generate summary
        try:
            if all_turns:
                print(f"[POST-CALL] Processing {len(all_turns)} turns...")

                # Save all turns to DB now
                for i, turn in enumerate(all_turns):
                    save_call_turn({
                        "session_id": session_id,
                        "speaker": turn["speaker"],
                        "text": turn["text"],
                        "timestamp_label": datetime.utcnow().strftime("%H:%M"),
                        "language_code": turn.get("lang", "en"),
                        "turn_index": i + 1,
                        "stt_latency_ms": turn.get("stt_ms"),
                        "llm_latency_ms": turn.get("llm_ms"),
                        "tts_latency_ms": turn.get("tts_ms"),
                    })

                # Run sentiment on customer turns
                customer_texts = [t["text"] for t in all_turns if t["speaker"] == "customer"]
                agg = aggregate_sentiment(
                    [{"speaker": "customer", "text": t} for t in customer_texts]
                )

                # Generate summary with Claude (quality matters here, not speed)
                summary = await generate_summary(all_turns)

                update_call_session(session_id, {
                    "session_status": "completed",
                    "ended_at": datetime.utcnow().isoformat(),
                    "sentiment_label": agg["label"],
                    "sentiment_score": agg["score"],
                    "emotion_summary": agg["emotion"],
                    "primary_intent": summary.get("primary_intent", ""),
                    "routed_team": summary.get("routed_team", ""),
                    "ai_summary_short": summary.get("short_summary", ""),
                    "ai_summary_long": summary.get("long_summary", ""),
                    "recommended_strategy_title": summary.get("recommended_strategy_title", ""),
                    "recommended_strategy_description": summary.get("recommended_strategy_description", ""),
                })

                print(f"[POST-CALL] Done. Sentiment: {agg['label']}, Intent: {summary.get('primary_intent')}")

                try:
                    await ws.send_json({
                        "type": "session_ended",
                        "session_id": session_id,
                        "summary": summary,
                        "sentiment": agg,
                    })
                except Exception:
                    pass  # WS might be closed already
        except Exception as e:
            print(f"[POST-CALL ERROR] {e}")


# ============================================================
# Twilio Voice Routes (uncomment when Twilio is configured)
# ============================================================

from starlette.requests import Request
from twilio_handler import voice_webhook_handler, handle_twilio_stream


@app.post("/api/twilio/voice")
async def twilio_voice(request: Request):
    """Twilio calls this when someone dials your number."""
    host = request.headers.get("host", "localhost")
    scheme = "wss" if request.url.scheme == "https" else "ws"
    return voice_webhook_handler(host, scheme)


@app.websocket("/api/twilio/stream")
async def twilio_stream(ws: WebSocket):
    """Twilio Media Streams WebSocket — real-time audio."""
    await handle_twilio_stream(ws)


# ============================================================
# Run
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
