"""Westpac AI Voice Agent — FastAPI Backend."""
import asyncio
import json
import time
import base64
import uuid
import importlib.util
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import config
from db import get_supabase
from stt import transcribe_audio, detected_language_to_code
from tts import synthesize_speech, stream_speech, get_voice_id
from llm import generate_response, generate_summary, test_runpod_connection
from sentiment import analyze_sentiment, aggregate_sentiment
from session_flow import SessionFlow
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
    send_booking_confirmation_sms,
    send_crosssell_sms_delayed,
    send_sms,
    create_appointment_from_call,
)

# Track warm state
_warm_state = {"model_ready": False, "stt_ready": False, "tts_ready": False, "db_ready": False}


def _safe_float(value, default: float = 0.0) -> float:
    """Coerce DB values to float while handling NULL/invalid values safely."""
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _extract_session_summary(call_session_ref) -> str:
    """Read ai_summary_short from Supabase nested relation payload."""
    if not call_session_ref:
        return ""
    if isinstance(call_session_ref, dict):
        return call_session_ref.get("ai_summary_short", "") or ""
    if isinstance(call_session_ref, list) and call_session_ref:
        first = call_session_ref[0] if isinstance(call_session_ref[0], dict) else {}
        return first.get("ai_summary_short", "") or ""
    return ""


def _clean_ai_summary(ai_note: str, fallback_summary: str) -> str:
    """Normalize summary text for dashboard rendering.

    Some rows can contain a raw JSON blob instead of plain text.
    """
    raw = (ai_note or "").strip()
    if not raw:
        return (fallback_summary or "").strip()

    # Try direct JSON parsing first.
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return (parsed.get("short_summary") or parsed.get("long_summary") or fallback_summary or raw).strip()
    except Exception:
        pass

    # Handle cases where JSON content is embedded in text.
    if "short_summary" in raw and "{" in raw and "}" in raw:
        try:
            start = raw.index("{")
            end = raw.rindex("}") + 1
            parsed = json.loads(raw[start:end])
            if isinstance(parsed, dict):
                return (parsed.get("short_summary") or parsed.get("long_summary") or fallback_summary or raw).strip()
        except Exception:
            pass

    cleaned = raw
    lower = cleaned.lower()
    for marker in [
        "he has been booked",
        "she has been booked",
        "they have been booked",
        "appointment booked",
        "video call with",
        "phone call with",
    ]:
        idx = lower.find(marker)
        if idx > 0:
            cleaned = cleaned[:idx].rstrip(" ,.-") + "."
            break

    cleaned = cleaned.replace('{ "short_summary": "', "").replace('" }', "").strip()
    return cleaned


def _normalize_seed_display_date(row: dict, display_date: str) -> str:
    """Push old seeded demo appointments into the future so live calls stand out."""
    if row.get("session_id"):
        return display_date
    try:
        parsed = datetime.fromisoformat(display_date)
    except Exception:
        return display_date
    today = datetime.now(timezone.utc).date()
    if parsed.date() >= today:
        return display_date

    # Deterministic per appointment id so ordering is stable across refreshes.
    appt_id = str(row.get("id", ""))
    offset = (sum(ord(ch) for ch in appt_id) % 21)
    future_date = today + timedelta(days=120 + offset)
    return future_date.isoformat()


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
# Root & Health
# ============================================================

@app.get("/")
async def root():
    return {
        "service": "Westpac AI Voice Agent Backend",
        "status": "running",
        "endpoints": {
            "health": "/api/health",
            "warmup": "/api/warmup (POST)",
            "appointments": "/api/appointments",
            "dashboard": "http://localhost:5173"
        }
    }


@app.get("/favicon.ico")
async def favicon():
    return {"message": "No favicon"}


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "warm": _warm_state,
        "model": config.CLAUDE_MODEL if config.ANTHROPIC_API_KEY else config.VLLM_MODEL,
        "timestamp": datetime.now(timezone.utc).isoformat(),
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

    # Test STT readiness and provider path visibility
    groq_module_present = importlib.util.find_spec("groq") is not None
    has_groq_key = bool(config.GROQ_API_KEY)
    has_openai_key = bool(config.OPENAI_API_KEY)
    _warm_state["stt_ready"] = has_openai_key or (has_groq_key and groq_module_present)
    if has_groq_key and groq_module_present:
        results["stt"] = "ok (groq primary, openai fallback)"
    elif has_groq_key and not groq_module_present and has_openai_key:
        results["stt"] = "ok (openai fallback only; groq package missing in runtime env)"
    elif has_openai_key:
        results["stt"] = "ok (openai only)"
    else:
        results["stt"] = "no key"

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
            try:
                collected_data = json.loads(collected_data)
            except Exception:
                collected_data = []

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

        summary_short = _extract_session_summary(row.get("call_sessions"))
        ai_note = _clean_ai_summary(row.get("ai_note", ""), summary_short)
        sentiment_label = row.get("sentiment") or row.get("sentiment_label") or "Neutral"
        sentiment_score = _safe_float(row.get("sentiment_score"), 50.0)
        if sentiment_score <= 0:
            sentiment_score = {
                "Positive": 85.0,
                "Neutral": 55.0,
                "Anxious": 35.0,
                "Frustrated": 20.0,
            }.get(sentiment_label, 50.0)

        display_time = slot_time or datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")).strftime("%H:%M")
        display_date = slot_date or datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")).strftime("%Y-%m-%d")
        display_date = _normalize_seed_display_date(row, display_date)

        appointments.append({
            "id": row["id"],
            "customerName": row.get("customer_name", ""),
            "customerInitials": row.get("customer_initials", ""),
            "companyName": row.get("company_name"),
            "time": display_time,
            "date": display_date,
            "type": row.get("appointment_type", ""),
            "locationType": "Video chat" if row.get("location_type", "Phone") == "Video Chat" else row.get("location_type", "Phone"),
            "sentiment": sentiment_label,
            "sentimentScore": sentiment_score,
            "sentimentNote": row.get("sentiment_note") or row.get("emotion_summary"),
            "intent": row.get("intent", ""),
            "aiNote": ai_note,
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
            "collectedData": collected_data if isinstance(collected_data, list) else [],
            "recommendedStrategy": {
                "title": row.get("recommended_strategy_title", ""),
                "description": row.get("recommended_strategy_description", ""),
            } if row.get("recommended_strategy_title") else None,
            "preferredSlotId": row.get("preferred_slot_id"),
            "fallbackSlotId": row.get("fallback_slot_id"),
            "confirmedSlotId": row.get("confirmed_slot_id"),
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

    # Send confirmation SMS + cross-sell
    sms_result = send_booking_confirmation_sms(appointment_id)
    result["sms"] = sms_result

    # Send cross-sell SMS after 10 second delay (background)
    if sms_result.get("crosssell_body") and sms_result.get("to"):
        asyncio.create_task(
            send_crosssell_sms_delayed(sms_result["to"], sms_result["crosssell_body"], delay_seconds=10)
        )

    return result


class DeclineRequest(BaseModel):
    reason: str = ""


@app.post("/api/appointments/{appointment_id}/decline")
async def decline_appointment(appointment_id: str, req: DeclineRequest):
    sb = get_supabase()
    # Release both slots
    apt = sb.table("appointments").select("preferred_slot_id, fallback_slot_id").eq("id", appointment_id).execute()
    if apt.data:
        for key in ["preferred_slot_id", "fallback_slot_id"]:
            slot_id = apt.data[0].get(key)
            if slot_id:
                sb.table("banker_availability").update({"status": "available"}).eq("id", slot_id).execute()

    sb.table("appointments").update({"status": "Cancelled"}).eq("id", appointment_id).execute()
    return {"status": "declined"}


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
                "averageSentiment": _safe_float(row.get("average_sentiment"), 50.0),
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
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
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
            "conversionRate": _safe_float(snap.get("conversion_rate"), 0.0),
        },
        "sentiment": {
            "positive": _safe_float(snap.get("sentiment_positive_pct"), 0.0),
            "neutral": _safe_float(snap.get("sentiment_neutral_pct"), 0.0),
            "anxious": _safe_float(snap.get("sentiment_anxious_pct"), 0.0),
            "frustrated": _safe_float(snap.get("sentiment_frustrated_pct"), 0.0),
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

    flow = SessionFlow()
    voice_override = None
    language_mode = "auto"

    started = await flow.start()

    await ws.send_json({
        "type": "session_started",
        "session_id": started["session_id"],
        "customer_id": started["customer_id"],
    })

    tts_task = None

    async def do_tts_stream(text, lang, vid=None):
        """TTS streaming."""
        try:
            async for chunk in stream_speech(text, language_code=lang, voice_id=vid):
                chunk_b64 = base64.b64encode(chunk).decode()
                await ws.send_json({"type": "audio_delta", "delta": chunk_b64})
        except asyncio.CancelledError:
            print("[TTS] Interrupted by user")
            return
        except Exception as e:
            print(f"[TTS STREAM ERROR] {e}")
            return
        await ws.send_json({"type": "response_done"})

    async def cancel_tts():
        nonlocal tts_task
        tts_task = None  # No-op now, TTS runs inline

    try:
        greeting = started["greeting"]
        await ws.send_json({"type": "response_text", "text": greeting})
        await do_tts_stream(greeting, "en", voice_override)

        while True:
            data = await ws.receive_json()
            msg_type = data.get("type")

            if msg_type == "interrupt":
                await cancel_tts()
                continue

            if msg_type == "audio":
              try:
                # Cancel any ongoing TTS first
                await cancel_tts()

                # Decode base64 audio
                audio_b64 = data.get("audio", "")
                audio_bytes = base64.b64decode(audio_b64)

                # Skip tiny audio clips (likely noise) — need at least ~500ms of audio
                if len(audio_bytes) < 20000:
                    continue

                # STT
                stt_start = time.time()
                audio_fmt = data.get("format", "webm")
                turn_result = await flow.process_audio(audio_bytes, filename=f"audio.{audio_fmt}")
                if not turn_result:
                    continue

                await ws.send_json({
                    "type": "thinking",
                })

                await ws.send_json({
                    "type": "transcript",
                    "speaker": "customer",
                    "text": turn_result["customer_text"],
                    "language": turn_result["language"],
                    "stt_latency_ms": turn_result["stt_latency_ms"],
                    "turn_index": turn_result["turn_index"] - 1,
                })

                await ws.send_json({
                    "type": "response_text",
                    "text": turn_result["bot_text"],
                    "llm_latency_ms": turn_result["llm_latency_ms"],
                    "stt_latency_ms": turn_result["stt_latency_ms"],
                    "turn_index": turn_result["turn_index"],
                })

                # Stream TTS inline (more reliable than background task)
                await do_tts_stream(turn_result["bot_text"], turn_result["language"], voice_override)

              except Exception as e:
                print(f"[TURN ERROR] {e}", flush=True)
                import traceback; traceback.print_exc()
                try:
                    await ws.send_json({"type": "error", "message": "Sorry, hit a snag. Try again."})
                    await ws.send_json({"type": "response_done"})
                except Exception:
                    pass

            elif msg_type == "set_voice":
                voice_override = data.get("voice_id")
                await ws.send_json({"type": "voice_updated", "voice_id": voice_override})

            elif msg_type == "set_language_mode":
                language_mode = data.get("mode", "auto")
                await ws.send_json({"type": "language_mode_updated", "mode": language_mode})

            elif msg_type == "end_call":
                await cancel_tts()
                break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await ws.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        try:
            finalized = await flow.finalize()
            if finalized:
                try:
                    await ws.send_json({
                        "type": "session_ended",
                        "session_id": finalized["session_id"],
                        "summary": finalized["summary"],
                        "sentiment": finalized["sentiment"],
                    })
                except Exception:
                    pass
        except Exception as e:
            print(f"[POST-CALL ERROR] {e}")


# ============================================================
# OpenAI Realtime API (full pipeline — STT + LLM + TTS)
# ============================================================

from realtime_handler import handle_realtime_session


@app.websocket("/api/realtime/session")
async def realtime_session(ws: WebSocket):
    """OpenAI Realtime API — single pipeline for voice."""
    await handle_realtime_session(ws)


# ============================================================
# Twilio Voice Routes
# ============================================================

from starlette.requests import Request
from twilio_handler import voice_webhook_handler, handle_twilio_stream


@app.post("/api/twilio/voice")
async def twilio_voice(request: Request):
    """Twilio calls this when someone dials your number."""
    host = request.headers.get("host", "localhost")
    scheme = "wss" if request.url.scheme == "https" else "ws"
    ws_url = f"{scheme}://{host}/api/twilio/stream"
    print(f"[Twilio Voice] Incoming POST to /api/twilio/voice")
    print(f"[Twilio Voice] Host header: {host}")
    print(f"[Twilio Voice] Scheme: {scheme}")
    print(f"[Twilio Voice] WebSocket URL: {ws_url}")
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
