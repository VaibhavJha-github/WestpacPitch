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
from db import get_supabase
from config import ELEVENLABS_API_KEY
from tts import synthesize_speech, get_voice_id
from session_flow import SessionFlow
from tools import (
    update_call_session,
)
from prompts import VOICE_AGENT_SYSTEM_PROMPT


TWILIO_DEFAULT_VOICE_ID = "snyKKuaGYk1VUEh42zbW"


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
    print("[voice_webhook_handler] CALLED")
    print(f"[voice_webhook_handler] host={host}, scheme={scheme}")
    ws_url = f"{scheme}://{host}/api/twilio/stream"
    print(f"[voice_webhook_handler] ws_url={ws_url}")
    twiml = twiml_connect_stream(ws_url)
    print(f"[voice_webhook_handler] returning TwiML")
    print(f"[voice_webhook_handler] TwiML content:\n{twiml}")
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
        print(f"[mp3_to_mulaw] Converting {mp3_path} to {wav_path}")
        result = subprocess.run([
            'ffmpeg', '-y', '-i', mp3_path,
            '-ar', '8000', '-ac', '1', '-f', 'wav', wav_path
        ], capture_output=True, check=False)
        
        if result.returncode != 0:
            print(f"[mp3_to_mulaw] ffmpeg error code: {result.returncode}")
            print(f"[mp3_to_mulaw] stderr: {result.stderr.decode()}")
            raise Exception(f"ffmpeg failed with code {result.returncode}: {result.stderr.decode()}")
        
        print(f"[mp3_to_mulaw] ffmpeg conversion successful")

        with open(wav_path, 'rb') as f:
            wav_data = f.read()

        # Skip WAV header, convert PCM to mulaw
        pcm = wav_data[44:]
        return audioop.lin2ulaw(pcm, 2)
    except FileNotFoundError as e:
        print(f"[mp3_to_mulaw] FileNotFoundError: {e}")
        raise
    finally:
        os.unlink(mp3_path)
        if os.path.exists(wav_path):
            os.unlink(wav_path)


async def handle_twilio_stream(ws: WebSocket):
    """Handle Twilio Media Stream WebSocket connection.

    Twilio sends JSON messages with audio chunks (base64 mulaw).
    We accumulate audio, run VAD, then process through our pipeline.
    """
    print("[Twilio Stream] WebSocket connection attempt")
    try:
        await ws.accept()
        print("[Twilio Stream] WebSocket accepted successfully")
    except Exception as e:
        print(f"[Twilio Stream] ERROR accepting WebSocket: {e}")
        return

    stream_sid = None
    call_sid = None
    flow = SessionFlow()

    # Audio buffer for incoming mulaw
    audio_buffer = bytearray()
    speech_started = False
    speech_start_time = None
    silence_start_time = None
    listening_enabled = False
    response_in_flight = False
    resume_listening_at = 0.0
    media_packets = 0

    voice_override = TWILIO_DEFAULT_VOICE_ID
    started = None

    async def process_audio(audio_mulaw: bytes):
        """Process accumulated audio through the shared session flow."""
        nonlocal listening_enabled, response_in_flight, resume_listening_at

        if not started:
            return
        if response_in_flight:
            print("[TWILIO] Skipping utterance because a response is already in flight")
            return

        response_in_flight = True

        try:
            wav_bytes = mulaw_to_wav(audio_mulaw)
            turn_result = await flow.process_audio(wav_bytes, filename="audio.wav")
            if not turn_result:
                return

            print(f"[TWILIO] Customer: {turn_result['customer_text']}")
            print(f"[TWILIO] Bot: {turn_result['bot_text']}")

            listening_enabled = False
            audio_buffer.clear()

            tts_audio = await synthesize_speech(turn_result["bot_text"], voice_override, turn_result["language"])
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
        finally:
            audio_buffer.clear()
            listening_enabled = True
            resume_listening_at = time.time() + 0.35
            response_in_flight = False

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
                    flow.customer_id = params["customer_id"]
                print(f"[TWILIO] Stream started: {stream_sid}, call: {call_sid}")
                print("[Twilio Stream] Creating shared session...")

                try:
                    started = await flow.start()
                    print(f"[Twilio Stream] Session created: {started['session_id']}")
                except Exception as e:
                    print(f"[Twilio Stream] ERROR creating session: {e}")
                    await ws.close()
                    return

                greeting = started["greeting"]

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
                    listening_enabled = True
                    audio_buffer.clear()
                    speech_started = False
                    speech_start_time = None
                    silence_start_time = None
                    resume_listening_at = time.time() + 0.35
                    media_packets = 0
                    print("[TWILIO] Greeting playback finished; inbound speech detection enabled")
                except Exception as e:
                    print(f"[TWILIO] Greeting TTS error: {e}")

            elif event == "media":
                media_packets += 1
                media = data.get("media", {})
                track = media.get("track", "unknown")
                now = time.time()

                if not listening_enabled:
                    if media_packets % 50 == 0:
                        print(f"[TWILIO MEDIA] Ignoring media until greeting finishes; packets={media_packets}, track={track}")
                    continue

                if response_in_flight or now < resume_listening_at:
                    if speech_started:
                        speech_started = False
                        speech_start_time = None
                        silence_start_time = None
                        audio_buffer.clear()
                    continue

                if track not in ("inbound", "inbound_track", "unknown"):
                    if media_packets % 50 == 0:
                        print(f"[TWILIO MEDIA] Ignoring non-inbound track={track}; packets={media_packets}")
                    continue

                # Incoming audio chunk (base64 mulaw)
                payload = media["payload"]
                chunk = base64.b64decode(payload)
                pcm_chunk = audioop.ulaw2lin(chunk, 2)
                rms = (audioop.rms(pcm_chunk, 2) / 32768.0) if pcm_chunk else 0.0

                if media_packets % 50 == 0:
                    print(
                        f"[TWILIO MEDIA] packets={media_packets} track={track} rms={rms:.4f} "
                        f"speech_started={speech_started} buffer={len(audio_buffer)}"
                    )

                speech_threshold = 0.025  # Same as Live dashboard

                if rms > speech_threshold:
                    if not speech_started:
                        audio_buffer.clear()
                        speech_started = True
                        speech_start_time = now
                        print(f"[TWILIO VAD] Speech started; rms={rms:.4f}")
                    audio_buffer.extend(chunk)
                    silence_start_time = None
                elif speech_started:
                    audio_buffer.extend(chunk)
                    if silence_start_time is None:
                        silence_start_time = now
                        print(f"[TWILIO VAD] Silence started; rms={rms:.4f}")
                    elif (now - silence_start_time) > 1.8:
                        duration = (now - speech_start_time) if speech_start_time else 0.0
                        if duration > 0.5 and len(audio_buffer) > 4000:
                            audio_data = bytes(audio_buffer)
                            print(
                                f"[TWILIO VAD] Utterance complete; duration={duration:.2f}s, "
                                f"bytes={len(audio_data)}"
                            )
                            asyncio.create_task(process_audio(audio_data))
                        else:
                            print(
                                f"[TWILIO VAD] Discarded short utterance; duration={duration:.2f}s, "
                                f"bytes={len(audio_buffer)}"
                            )

                        audio_buffer.clear()
                        speech_started = False
                        speech_start_time = None
                        silence_start_time = None

            elif event == "stop":
                print(f"[TWILIO] Stream stopped")
                break

    except RuntimeError as e:
        if "WebSocket is not connected" in str(e):
            print("[TWILIO] WebSocket closed during reload/shutdown")
        else:
            print(f"[TWILIO WS EXCEPTION] RuntimeError: {e}")
            import traceback
            traceback.print_exc()
    except Exception as e:
        print(f"[TWILIO WS EXCEPTION] Error in stream handler: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

    try:
        finalized = await flow.finalize()
        if finalized:
            update_call_session(finalized["session_id"], {
                "booking_state": "pending_banker" if finalized["booking_created"] else "none",
            })
    except Exception as e:
        print(f"[TWILIO] Post-call error: {e}")
        import traceback; traceback.print_exc()
