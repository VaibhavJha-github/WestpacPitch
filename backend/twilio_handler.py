"""Twilio Voice + Media Streams handler.

Plug-and-play: once you have Twilio credentials, add them to .env and
uncomment the routes in main.py. The Mac Mini needs to be exposed via
Cloudflare Tunnel or ngrok.

Flow:
1. Twilio calls your /api/twilio/voice webhook
2. We return TwiML that opens a Media Stream WebSocket
3. Twilio streams live audio (mulaw 8kHz) to /api/twilio/stream
4. We run STT → Claude → TTS, and send audio back via the stream
"""
import base64
import json
import time
import asyncio
import audioop
from datetime import datetime
from uuid import uuid4

from fastapi import WebSocket
from starlette.responses import Response

import config
from config import ELEVENLABS_API_KEY
from stt import transcribe_audio, detected_language_to_code
from tts import synthesize_speech, get_voice_id
from llm import generate_response, generate_summary
from sentiment import analyze_sentiment
from tools import (
    get_customer_profile, get_customer_accounts, get_spending_summary,
    search_knowledge_pack, get_available_banker_slots, hold_slot,
    create_appointment, create_appointment_from_call, route_to_team,
    save_call_session, update_call_session, save_call_turn, update_analytics,
    send_sms,
)
from sentiment import aggregate_sentiment
from prompts import VOICE_AGENT_SYSTEM_PROMPT


def twiml_connect_stream(ws_url: str) -> str:
    """Return TwiML that answers the call and opens a Media Stream."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="{ws_url}">
      <Parameter name="customer_id" value="c0000001-0000-0000-0000-000000000001" />
    </Stream>
  </Connect>
</Response>"""


def voice_webhook_handler(host: str, scheme: str = "wss") -> Response:
    """Handle incoming Twilio voice call — return TwiML to start Media Stream."""
    ws_url = f"{scheme}://{host}/api/twilio/stream"
    twiml = twiml_connect_stream(ws_url)
    return Response(content=twiml, media_type="application/xml")


def mulaw_to_wav(mulaw_bytes: bytes) -> bytes:
    """Convert mulaw 8kHz mono to WAV 16kHz mono (for Whisper)."""
    import struct
    # Decode mulaw to PCM 16-bit
    pcm = audioop.ulaw2lin(mulaw_bytes, 2)
    # Resample 8kHz → 16kHz
    pcm_16k = audioop.ratecv(pcm, 2, 1, 8000, 16000, None)[0]

    # Wrap in WAV header
    data_size = len(pcm_16k)
    sample_rate = 16000
    channels = 1
    bits_per_sample = 16
    byte_rate = sample_rate * channels * bits_per_sample // 8
    block_align = channels * bits_per_sample // 8

    header = struct.pack(
        '<4sI4s4sIHHIIHH4sI',
        b'RIFF', 36 + data_size, b'WAVE',
        b'fmt ', 16, 1, channels, sample_rate, byte_rate, block_align, bits_per_sample,
        b'data', data_size,
    )
    return header + pcm_16k


def wav_to_mulaw(wav_bytes: bytes) -> bytes:
    """Convert WAV/PCM to mulaw 8kHz for Twilio playback."""
    import struct
    # Skip WAV header (44 bytes) if present
    if wav_bytes[:4] == b'RIFF':
        pcm = wav_bytes[44:]
        # Assume 16kHz from our TTS pipeline
        pcm_8k = audioop.ratecv(pcm, 2, 1, 16000, 8000, None)[0]
    else:
        pcm_8k = wav_bytes

    return audioop.lin2ulaw(pcm_8k, 2)


def mp3_to_mulaw(mp3_bytes: bytes) -> bytes:
    """Convert MP3 (from ElevenLabs) to mulaw 8kHz for Twilio.

    Requires ffmpeg installed on the system.
    """
    import subprocess
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
        f.write(mp3_bytes)
        mp3_path = f.name

    wav_path = mp3_path.replace('.mp3', '.wav')

    try:
        subprocess.run([
            'ffmpeg', '-y', '-i', mp3_path,
            '-ar', '8000', '-ac', '1', '-f', 'wav', wav_path
        ], capture_output=True, check=True)

        with open(wav_path, 'rb') as f:
            wav_data = f.read()

        # Skip WAV header, convert PCM to mulaw
        pcm = wav_data[44:]
        return audioop.lin2ulaw(pcm, 2)
    finally:
        os.unlink(mp3_path)
        if os.path.exists(wav_path):
            os.unlink(wav_path)


async def handle_twilio_stream(ws: WebSocket):
    """Handle Twilio Media Stream WebSocket connection.

    Twilio sends JSON messages with audio chunks (base64 mulaw).
    We accumulate audio, run VAD, then process through our pipeline.
    """
    await ws.accept()

    stream_sid = None
    call_sid = None
    customer_id = "c0000001-0000-0000-0000-000000000001"
    session_id = str(uuid4())

    # Audio buffer for incoming mulaw
    audio_buffer = bytearray()
    silence_frames = 0
    speech_started = False
    SILENCE_THRESHOLD = 50  # mulaw energy threshold
    SILENCE_FRAMES_NEEDED = 40  # ~2 seconds at 50 packets/sec
    MIN_AUDIO_SIZE = 4000  # minimum audio to process

    # Conversation state
    messages = []
    turn_index = 0
    all_turns = []
    voice_override = None
    booking_created = False  # Track if a booking was made during the call

    # Create session
    save_call_session({
        "id": session_id,
        "customer_id": customer_id,
        "session_status": "active",
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

    async def process_audio(audio_mulaw: bytes):
        """Process accumulated audio through STT → LLM → TTS pipeline."""
        nonlocal turn_index, messages, all_turns

        # Convert mulaw to WAV for Whisper
        wav_bytes = mulaw_to_wav(audio_mulaw)

        # STT
        stt_result = transcribe_audio(wav_bytes)
        customer_text = stt_result["text"].strip()
        if not customer_text:
            return

        detected_lang = detected_language_to_code(stt_result["language"])
        print(f"[TWILIO] Customer: {customer_text} (lang={detected_lang})")

        turn_index += 1
        save_call_turn({
            "session_id": session_id,
            "speaker": "customer",
            "text": customer_text,
            "timestamp_label": datetime.utcnow().strftime("%H:%M"),
            "language_code": detected_lang,
            "turn_index": turn_index,
            "stt_latency_ms": stt_result["latency_ms"],
        })
        all_turns.append({"speaker": "customer", "text": customer_text})
        messages.append({"role": "user", "content": customer_text})

        # Build context
        extra_context = context
        for kw in ["rate", "loan", "product", "home loan", "fixed", "variable", "first home", "fraud", "scam", "lost card"]:
            if kw in customer_text.lower():
                knowledge = search_knowledge_pack(kw)
                if knowledge:
                    extra_context += "\n\nRelevant Knowledge:\n" + "\n---\n".join(
                        f"{k['title']}: {k['content'][:500]}" for k in knowledge
                    )
                break

        for kw in ["spend", "saving", "budget", "afford", "money", "car", "goal"]:
            if kw in customer_text.lower():
                spending = get_spending_summary(customer_id)
                if spending:
                    extra_context += "\n\nSpending Summary:\n" + "\n".join(
                        f"- {s['category']}: ${s['total_amount']} ({s['transaction_count']} txns)"
                        for s in spending
                    )
                break

        # LLM
        llm_result = await generate_response(messages, context=extra_context)
        bot_text = llm_result["text"]

        # Handle tool calls (same as main.py)
        if llm_result.get("tool_call"):
            tc = llm_result["tool_call"]
            tool_name = tc.get("tool", "")
            tool_args = tc.get("args", {})

            if tool_name == "get_available_banker_slots":
                tool_result = get_available_banker_slots(tool_args.get("date"))
                if tool_result:
                    slots_text = "\n".join(f"- {s['slot_label']} ({s['status']})" for s in tool_result[:5])
                    messages.append({"role": "assistant", "content": bot_text or "Let me check available slots."})
                    messages.append({"role": "user", "content": f"[Tool result - available slots:\n{slots_text}]\nNow offer the customer 2 suitable slots."})
                    followup = await generate_response(messages, context=extra_context)
                    bot_text = followup["text"]

            elif tool_name == "search_knowledge_pack":
                tool_result = search_knowledge_pack(tool_args.get("query", ""))
                if tool_result:
                    knowledge_text = "\n---\n".join(f"{k['title']}: {k['content'][:400]}" for k in tool_result)
                    messages.append({"role": "assistant", "content": bot_text or "Let me look that up."})
                    messages.append({"role": "user", "content": f"[Knowledge result:\n{knowledge_text}]\nAnswer using this."})
                    followup = await generate_response(messages, context=extra_context)
                    bot_text = followup["text"]

            elif tool_name == "get_spending_summary":
                tool_result = get_spending_summary(tool_args.get("customer_id", customer_id))
                if tool_result:
                    spending_text = "\n".join(f"- {s['category']}: ${s['total_amount']}" for s in tool_result)
                    messages.append({"role": "assistant", "content": bot_text or "Let me review your spending."})
                    messages.append({"role": "user", "content": f"[Spending data:\n{spending_text}]\nProvide helpful insights."})
                    followup = await generate_response(messages, context=extra_context)
                    bot_text = followup["text"]

            elif tool_name == "create_appointment_offer":
                nonlocal booking_created
                apt = create_appointment_from_call(
                    session_id=session_id,
                    customer_id=customer_id,
                    intent=tool_args.get("intent", "Home Loan Enquiry"),
                    location_type=tool_args.get("location_type", "Phone"),
                    ai_note=tool_args.get("ai_note", ""),
                    collected_data=tool_args.get("collected_data"),
                    primary_slot_id=tool_args.get("primary_slot_id"),
                    fallback_slot_id=tool_args.get("fallback_slot_id"),
                )
                booking_created = True
                if not bot_text:
                    bot_text = "I've noted your booking. Rob will confirm shortly and you'll get a text with the details."

            elif tool_name == "send_followup_sms":
                sms_body = tool_args.get("message", "")
                if sms_body and config.CUSTOMER_PHONE_NUMBER:
                    send_sms(config.CUSTOMER_PHONE_NUMBER, sms_body)

            elif tool_name == "route_to_team":
                team = route_to_team(tool_args.get("intent", ""), tool_args.get("emotion"))
                update_call_session(session_id, {"routed_team": team})

        if not bot_text:
            bot_text = "I understand. How can I help you further?"

        messages.append({"role": "assistant", "content": bot_text})
        print(f"[TWILIO] Bot: {bot_text}")

        # TTS
        try:
            tts_audio = await synthesize_speech(bot_text, voice_override, detected_lang)
            mulaw_audio = mp3_to_mulaw(tts_audio)

            # Send audio back to Twilio in chunks
            chunk_size = 320  # 20ms of 8kHz mulaw
            for i in range(0, len(mulaw_audio), chunk_size):
                chunk = mulaw_audio[i:i + chunk_size]
                payload = base64.b64encode(chunk).decode()
                await ws.send_json({
                    "event": "media",
                    "streamSid": stream_sid,
                    "media": {"payload": payload}
                })
                await asyncio.sleep(0.02)  # 20ms pacing

        except Exception as e:
            print(f"[TWILIO TTS ERROR] {e}")

        turn_index += 1
        save_call_turn({
            "session_id": session_id,
            "speaker": "bot",
            "text": bot_text,
            "timestamp_label": datetime.utcnow().strftime("%H:%M"),
            "language_code": detected_lang,
            "turn_index": turn_index,
            "llm_latency_ms": llm_result["latency_ms"],
        })
        all_turns.append({"speaker": "bot", "text": bot_text})

    try:
        async for message in ws.iter_text():
            data = json.loads(message)
            event = data.get("event")

            if event == "connected":
                print(f"[TWILIO] Stream connected")

            elif event == "start":
                stream_sid = data["start"]["streamSid"]
                call_sid = data["start"].get("callSid")
                # Check for custom parameters
                params = data["start"].get("customParameters", {})
                if params.get("customer_id"):
                    customer_id = params["customer_id"]
                print(f"[TWILIO] Stream started: {stream_sid}, call: {call_sid}")

                # AI greets first
                customer_name = profile["full_name"].split()[0] if profile else "mate"
                greeting = f"G'day {customer_name}, thanks for calling Westpac! I'm Alex, your AI assistant. Just letting you know this call is being recorded for quality purposes. How can I help you today?"
                messages.append({"role": "assistant", "content": greeting})
                all_turns.append({"speaker": "bot", "text": greeting})
                turn_index += 1
                save_call_turn({
                    "session_id": session_id,
                    "speaker": "bot",
                    "text": greeting,
                    "timestamp_label": datetime.utcnow().strftime("%H:%M"),
                    "language_code": "en",
                    "turn_index": turn_index,
                })

                # TTS greeting
                try:
                    tts_audio = await synthesize_speech(greeting, voice_override, "en")
                    mulaw_audio = mp3_to_mulaw(tts_audio)
                    chunk_size = 320
                    for i in range(0, len(mulaw_audio), chunk_size):
                        chunk = mulaw_audio[i:i + chunk_size]
                        payload_b64 = base64.b64encode(chunk).decode()
                        await ws.send_json({
                            "event": "media",
                            "streamSid": stream_sid,
                            "media": {"payload": payload_b64}
                        })
                        await asyncio.sleep(0.02)
                except Exception as e:
                    print(f"[TWILIO] Greeting TTS error: {e}")

            elif event == "media":
                # Incoming audio chunk (base64 mulaw)
                payload = data["media"]["payload"]
                chunk = base64.b64decode(payload)
                audio_buffer.extend(chunk)

                # Simple energy-based VAD
                energy = sum(abs(b - 128) for b in chunk) / len(chunk) if chunk else 0

                if energy > SILENCE_THRESHOLD:
                    speech_started = True
                    silence_frames = 0
                elif speech_started:
                    silence_frames += 1
                    if silence_frames >= SILENCE_FRAMES_NEEDED and len(audio_buffer) > MIN_AUDIO_SIZE:
                        # End of utterance
                        audio_data = bytes(audio_buffer)
                        audio_buffer.clear()
                        speech_started = False
                        silence_frames = 0

                        # Process in background so we don't block the stream
                        asyncio.create_task(process_audio(audio_data))

            elif event == "stop":
                print(f"[TWILIO] Stream stopped")
                break

    except Exception as e:
        print(f"[TWILIO] Error: {e}")

    # Post-call: sentiment + summary + update DB
    if all_turns:
        try:
            print(f"[TWILIO POST-CALL] Processing {len(all_turns)} turns...")

            # Sentiment
            customer_texts = [t["text"] for t in all_turns if t["speaker"] == "customer"]
            agg = aggregate_sentiment(
                [{"speaker": "customer", "text": t} for t in customer_texts]
            )

            # Summary
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
                "booking_state": "pending_banker" if booking_created else "none",
            })

            # Update appointment with summary data if booking was created
            if booking_created:
                sb = get_supabase()
                apts = sb.table("appointments").select("id").eq("session_id", session_id).execute()
                if apts.data:
                    sb.table("appointments").update({
                        "sentiment": agg["label"],
                        "sentiment_score": agg["score"],
                        "sentiment_note": agg["emotion"],
                        "ai_note": summary.get("long_summary", ""),
                        "recommended_strategy_title": summary.get("recommended_strategy_title", ""),
                        "recommended_strategy_description": summary.get("recommended_strategy_description", ""),
                    }).eq("id", apts.data[0]["id"]).execute()

            # Update analytics
            try:
                update_analytics({
                    "total_calls": 1,  # Will be incremented properly in production
                    "completed_appointments": 1 if booking_created else 0,
                })
            except Exception:
                pass

            print(f"[TWILIO POST-CALL] Done. Sentiment: {agg['label']}, Intent: {summary.get('primary_intent')}")

        except Exception as e:
            print(f"[TWILIO] Post-call error: {e}")
            import traceback; traceback.print_exc()
