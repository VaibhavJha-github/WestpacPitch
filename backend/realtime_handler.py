"""OpenAI Realtime API handler — single WebSocket for STT + LLM + TTS."""
import json
import base64
import asyncio
import time
from datetime import datetime
from uuid import uuid4

import websockets

from config import OPENAI_API_KEY
from prompts import VOICE_AGENT_SYSTEM_PROMPT
from tools import (
    get_customer_profile, get_customer_accounts, get_spending_summary,
    search_knowledge_pack, get_available_banker_slots, hold_slot,
    create_appointment, route_to_team, save_call_session,
    update_call_session, save_call_turn,
)
from sentiment import aggregate_sentiment
from llm import generate_summary

REALTIME_URL = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2025-06-03"

TOOLS = [
    {
        "type": "function",
        "name": "get_spending_summary",
        "description": "Get the customer's categorized spending breakdown from their transaction history",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "The customer ID"}
            },
            "required": ["customer_id"]
        }
    },
    {
        "type": "function",
        "name": "search_knowledge_pack",
        "description": "Search Westpac product/rate/policy information",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"}
            },
            "required": ["query"]
        }
    },
    {
        "type": "function",
        "name": "get_available_banker_slots",
        "description": "Check available appointment slots with Mia Sullivan, Home Loan Specialist",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Date to check (optional, YYYY-MM-DD)"}
            },
            "required": []
        }
    },
    {
        "type": "function",
        "name": "route_to_team",
        "description": "Route the customer to a specialist team (fraud, hardship, etc.)",
        "parameters": {
            "type": "object",
            "properties": {
                "intent": {"type": "string", "description": "The customer's intent/issue"},
                "emotion": {"type": "string", "description": "The customer's emotional state"}
            },
            "required": ["intent"]
        }
    },
]


async def handle_realtime_session(client_ws):
    """Bridge between browser WebSocket and OpenAI Realtime API."""
    await client_ws.accept()

    session_id = str(uuid4())
    customer_id = "c0000001-0000-0000-0000-000000000001"
    all_turns = []
    voice = "nova"

    # Save session
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

    system_prompt = VOICE_AGENT_SYSTEM_PROMPT.replace("{context}", context or "No additional context.")

    await client_ws.send_json({
        "type": "session_started",
        "session_id": session_id,
        "customer_id": customer_id,
    })

    openai_ws = None

    try:
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "realtime=v1",
        }

        openai_ws = await websockets.connect(REALTIME_URL, additional_headers=headers)
        print(f"[REALTIME] Connected to OpenAI Realtime API")

        # Configure session
        session_config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": system_prompt,
                "voice": voice,
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "gpt-4o-mini-transcribe",
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 800,
                },
                "tools": TOOLS,
                "tool_choice": "auto",
                "temperature": 0.7,
                "max_response_output_tokens": 200,
            }
        }

        await openai_ws.send(json.dumps(session_config))
        print(f"[REALTIME] Session configured with {len(system_prompt)} char system prompt")

        # Current response tracking
        current_bot_text = ""

        async def relay_from_openai():
            """Relay OpenAI events to browser client."""
            nonlocal current_bot_text

            async for message in openai_ws:
                event = json.loads(message)
                event_type = event.get("type", "")

                # Debug: log all event types
                if event_type not in ("response.audio.delta", "input_audio_buffer.speech_started", "input_audio_buffer.speech_stopped"):
                    print(f"[REALTIME EVENT] {event_type}")

                if event_type == "session.created":
                    print(f"[REALTIME] Session created: {event.get('session', {}).get('id', 'unknown')}")

                elif event_type == "session.updated":
                    print(f"[REALTIME] Session updated OK")

                elif event_type == "response.audio.delta":
                    delta = event.get("delta", "")
                    if delta:
                        await client_ws.send_json({
                            "type": "audio_delta",
                            "delta": delta,
                        })

                elif event_type == "response.audio_transcript.delta":
                    current_bot_text += event.get("delta", "")

                elif event_type == "response.audio_transcript.done":
                    bot_text = event.get("transcript", current_bot_text)
                    if bot_text:
                        print(f"[REALTIME] Bot: {bot_text[:80]}")
                        all_turns.append({"speaker": "bot", "text": bot_text})
                        await client_ws.send_json({
                            "type": "response_text",
                            "text": bot_text,
                        })
                    current_bot_text = ""

                elif event_type == "conversation.item.input_audio_transcription.completed":
                    user_text = event.get("transcript", "").strip()
                    if user_text:
                        print(f"[REALTIME] Customer: {user_text}")
                        all_turns.append({"speaker": "customer", "text": user_text})
                        await client_ws.send_json({
                            "type": "transcript",
                            "speaker": "customer",
                            "text": user_text,
                        })

                elif event_type == "conversation.item.input_audio_transcription.failed":
                    print(f"[REALTIME] Transcription failed: {event.get('error', {})}")

                elif event_type == "response.function_call_arguments.done":
                    call_id = event.get("call_id", "")
                    fn_name = event.get("name", "")
                    args_str = event.get("arguments", "{}")

                    print(f"[REALTIME] Tool call: {fn_name}({args_str[:100]})")

                    try:
                        args = json.loads(args_str)
                    except json.JSONDecodeError:
                        args = {}

                    result = await execute_tool(fn_name, args, customer_id)
                    result_str = json.dumps(result) if isinstance(result, (dict, list)) else str(result)

                    print(f"[REALTIME] Tool result: {result_str[:100]}")

                    await openai_ws.send(json.dumps({
                        "type": "conversation.item.create",
                        "item": {
                            "type": "function_call_output",
                            "call_id": call_id,
                            "output": result_str,
                        }
                    }))

                    await openai_ws.send(json.dumps({
                        "type": "response.create"
                    }))

                elif event_type == "response.done":
                    await client_ws.send_json({"type": "response_done"})

                elif event_type == "input_audio_buffer.speech_started":
                    await client_ws.send_json({"type": "speech_started"})

                elif event_type == "input_audio_buffer.speech_stopped":
                    await client_ws.send_json({"type": "speech_stopped"})

                elif event_type == "error":
                    err = event.get("error", {})
                    print(f"[REALTIME ERROR] {err}")
                    await client_ws.send_json({
                        "type": "error",
                        "message": str(err.get("message", "Unknown error")),
                    })

        async def relay_from_client():
            """Relay browser audio to OpenAI."""
            nonlocal voice
            while True:
                data = await client_ws.receive_json()
                msg_type = data.get("type")

                if msg_type == "audio":
                    audio_b64 = data.get("audio", "")
                    if audio_b64 and openai_ws:
                        await openai_ws.send(json.dumps({
                            "type": "input_audio_buffer.append",
                            "audio": audio_b64,
                        }))

                elif msg_type == "set_voice":
                    voice = data.get("voice_id", "nova")

                elif msg_type == "end_call":
                    break

        await asyncio.gather(
            relay_from_openai(),
            relay_from_client(),
        )

    except Exception as e:
        print(f"[REALTIME] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if openai_ws:
            await openai_ws.close()

        # Post-call processing
        try:
            if all_turns:
                print(f"[POST-CALL] Processing {len(all_turns)} turns...")

                for i, turn in enumerate(all_turns):
                    save_call_turn({
                        "session_id": session_id,
                        "speaker": turn["speaker"],
                        "text": turn["text"],
                        "timestamp_label": datetime.utcnow().strftime("%H:%M"),
                        "language_code": "en",
                        "turn_index": i + 1,
                    })

                customer_texts = [t["text"] for t in all_turns if t["speaker"] == "customer"]
                agg = aggregate_sentiment(
                    [{"speaker": "customer", "text": t} for t in customer_texts]
                )

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

                print(f"[POST-CALL] Done. Sentiment: {agg['label']}")

                try:
                    await client_ws.send_json({
                        "type": "session_ended",
                        "session_id": session_id,
                        "summary": summary,
                        "sentiment": agg,
                    })
                except Exception:
                    pass
        except Exception as e:
            print(f"[POST-CALL ERROR] {e}")


async def execute_tool(fn_name: str, args: dict, customer_id: str):
    """Execute a tool call and return the result."""
    if fn_name == "get_spending_summary":
        cid = args.get("customer_id", customer_id)
        result = get_spending_summary(cid)
        if result:
            return [{"category": s["category"], "total": s["total_amount"], "count": s["transaction_count"]} for s in result]
        return "No spending data found."

    elif fn_name == "search_knowledge_pack":
        query = args.get("query", "")
        result = search_knowledge_pack(query)
        if result:
            return [{"title": k["title"], "content": k["content"][:500]} for k in result]
        return "No results found."

    elif fn_name == "get_available_banker_slots":
        date = args.get("date")
        result = get_available_banker_slots(date)
        if result:
            return [{"slot_label": s["slot_label"], "status": s["status"]} for s in result[:5]]
        return "No available slots."

    elif fn_name == "route_to_team":
        intent = args.get("intent", "")
        emotion = args.get("emotion")
        team = route_to_team(intent, emotion)
        return f"Routed to: {team}"

    return "Unknown tool."
