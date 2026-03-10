import { useState, useRef, useEffect } from "react";
import { Mic, Phone, PhoneOff, Zap, Volume2 } from "lucide-react";
import { BACKEND_URL } from "../lib/supabase";
import { warmupBackend } from "../lib/api";

type Status =
  | "offline"
  | "warming"
  | "ready"
  | "in_call"
  | "degraded"
  | "error";

interface TranscriptEntry {
  speaker: "customer" | "bot";
  text: string;
}

const VOICE_OPTIONS = [
  { id: "IKne3meq5aSn9XLyUdCD", label: "Charlie (Male, Australian)" },
  { id: "snyKKuaGYk1VUEh42zbW", label: "Oliver (Male, Australian Pro)" },
  { id: "omLr0bN17lYIC1JWLSYV", label: "Bunty (Male, Indian)" },
  { id: "JBFqnCBsd6RMkjVDRZzb", label: "George (Male, British)" },
  { id: "pFZP5JQG7iQjIQuC4Bku", label: "Lily (Female, British)" },
  { id: "EXAVITQu4vr4xnSDxMaL", label: "Sarah (Female, American)" },
  { id: "nPczCjzI2devNBz1zQrb", label: "Brian (Male, Deep)" },
  { id: "Xb7hH8MSUJpSbSDYk0k2", label: "Alice (Female, British)" },
];

const STATUS_COLORS: Record<Status, string> = {
  offline: "bg-slate-400",
  warming: "bg-amber-400 animate-pulse",
  ready: "bg-green-500",
  in_call: "bg-green-500 animate-pulse",
  degraded: "bg-amber-500",
  error: "bg-red-500",
};

const STATUS_LABELS: Record<Status, string> = {
  offline: "Offline",
  warming: "Warming Up...",
  ready: "Ready",
  in_call: "In Call",
  degraded: "Degraded",
  error: "Error",
};

// VAD settings
const SPEECH_THRESHOLD = 0.025;
const SILENCE_DURATION_MS = 1800;
const MIN_SPEECH_MS = 500;

const Live = () => {
  const [status, setStatus] = useState<Status>("offline");
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [selectedVoice, setSelectedVoice] = useState("IKne3meq5aSn9XLyUdCD");
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isAiSpeaking, setIsAiSpeaking] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [warmupResult, setWarmupResult] = useState<any>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const transcriptEndRef = useRef<HTMLDivElement>(null);
  const cleanupRef = useRef<(() => void) | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const nextPlayTimeRef = useRef(0);
  const gainRef = useRef<GainNode | null>(null);

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcript]);

  const handleWarmup = async () => {
    setStatus("warming");
    try {
      const result = await warmupBackend();
      setWarmupResult(result);
      setStatus(result.status === "warm" ? "ready" : "degraded");
    } catch {
      setStatus("error");
    }
  };

  const handleEndCall = () => {
    if (cleanupRef.current) {
      cleanupRef.current();
      cleanupRef.current = null;
    }
    if (wsRef.current) {
      try {
        wsRef.current.send(JSON.stringify({ type: "end_call" }));
      } catch {}
      wsRef.current.close();
      wsRef.current = null;
    }
    setStatus("ready");
    setIsSpeaking(false);
    setIsAiSpeaking(false);
  };

  const handleStartCall = async () => {
    setTranscript([]);
    setStatus("in_call");

    let alive = true;

    // Audio context for TTS playback (PCM16 24kHz)
    const playbackCtx = new AudioContext({ sampleRate: 24000 });
    audioContextRef.current = playbackCtx;
    nextPlayTimeRef.current = 0;

    // GainNode for instant audio cutoff on interruption
    const gain = playbackCtx.createGain();
    gain.connect(playbackCtx.destination);
    gainRef.current = gain;

    let aiSpeakingLocal = false;
    let micEnabled = false; // Don't process mic until greeting finishes

    // --- WebSocket to backend (Groq pipeline) ---
    const wsUrl = BACKEND_URL.replace("http", "ws") + "/api/live/session";
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      ws.send(JSON.stringify({ type: "set_voice", voice_id: selectedVoice }));
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === "session_started") {
        setSessionId(data.session_id);
      } else if (data.type === "thinking") {
        setIsThinking(true);
      } else if (data.type === "transcript") {
        setTranscript((prev) => [
          ...prev,
          { speaker: "customer", text: data.text },
        ]);
      } else if (data.type === "response_text") {
        setIsThinking(false);
        setTranscript((prev) => [...prev, { speaker: "bot", text: data.text }]);
      } else if (data.type === "audio_delta") {
        setIsAiSpeaking(true);
        aiSpeakingLocal = true;
        const pcmBytes = base64ToArrayBuffer(data.delta);
        playPcm16(playbackCtx, pcmBytes);
      } else if (data.type === "response_done") {
        setIsAiSpeaking(false);
        aiSpeakingLocal = false;
        // Enable mic after first response (greeting) finishes
        if (!micEnabled) micEnabled = true;
      } else if (data.type === "session_ended") {
        setStatus("ready");
      } else if (data.type === "error") {
        console.error("Backend error:", data.message);
      }
    };

    ws.onerror = () => setStatus("error");
    ws.onclose = () => {
      if (alive) setStatus("ready");
    };

    // --- Capture mic with AudioWorklet + client-side VAD ---
    let stream: MediaStream | null = null;
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 24000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
    } catch {
      setStatus("error");
      return;
    }

    const micCtx = new AudioContext({ sampleRate: 24000 });
    const source = micCtx.createMediaStreamSource(stream);

    // AudioWorklet for PCM capture + VAD
    const workletCode = `
      class PCMProcessor extends AudioWorkletProcessor {
        constructor() {
          super();
          this._speaking = false;
          this._silenceStart = 0;
          this._speechStart = 0;
          this._chunks = [];
        }

        process(inputs) {
          const input = inputs[0];
          if (input.length === 0) return true;

          const float32 = input[0];
          const int16 = new Int16Array(float32.length);

          // Convert + calculate RMS
          let sum = 0;
          for (let i = 0; i < float32.length; i++) {
            const s = Math.max(-1, Math.min(1, float32[i]));
            int16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
            sum += s * s;
          }
          const rms = Math.sqrt(sum / float32.length);

          const now = currentTime * 1000; // ms

          if (rms > ${SPEECH_THRESHOLD}) {
            if (!this._speaking) {
              this._speaking = true;
              this._speechStart = now;
              this._speechFrames = 0;
              this._notifiedStart = false;
              this._chunks = [];
            }
            this._speechFrames++;
            this._silenceStart = 0;
            this._chunks.push(int16.buffer);
            // Only notify after ~400ms of sustained speech (~38 frames at 128 samples/24kHz)
            if (!this._notifiedStart && this._speechFrames > 38) {
              this._notifiedStart = true;
              this.port.postMessage({ type: 'vad', state: 'started' });
            }
          } else if (this._speaking) {
            this._chunks.push(int16.buffer);
            if (this._silenceStart === 0) {
              this._silenceStart = now;
            } else if (now - this._silenceStart > ${SILENCE_DURATION_MS}) {
              // Speech ended
              const speechDuration = now - this._speechStart;
              if (speechDuration > ${MIN_SPEECH_MS}) {
                // Send buffered audio
                this.port.postMessage({
                  type: 'audio_complete',
                  chunks: this._chunks,
                });
              }
              this._speaking = false;
              this._silenceStart = 0;
              this._speechFrames = 0;
              this._notifiedStart = false;
              this._chunks = [];
              this.port.postMessage({ type: 'vad', state: 'stopped' });
            }
          }

          return true;
        }
      }
      registerProcessor('pcm-vad-processor', PCMProcessor);
    `;

    const blob = new Blob([workletCode], { type: "application/javascript" });
    const workletUrl = URL.createObjectURL(blob);

    await micCtx.audioWorklet.addModule(workletUrl);
    const workletNode = new AudioWorkletNode(micCtx, "pcm-vad-processor");
    source.connect(workletNode);
    workletNode.connect(micCtx.destination);

    workletNode.port.onmessage = (e) => {
      if (!alive || ws.readyState !== WebSocket.OPEN || !micEnabled) return;

      if (e.data.type === "vad") {
        if (e.data.state === "started") {
          setIsSpeaking(true);

          if (aiSpeakingLocal) {
            // Interrupt: kill audio + notify backend
            setIsAiSpeaking(false);
            aiSpeakingLocal = false;

            if (gainRef.current) {
              gainRef.current.disconnect();
              const newGain = playbackCtx.createGain();
              newGain.connect(playbackCtx.destination);
              gainRef.current = newGain;
            }
            nextPlayTimeRef.current = 0;

            ws.send(JSON.stringify({ type: "interrupt" }));
          }
        } else {
          setIsSpeaking(false);
        }
      } else if (e.data.type === "audio_complete") {
        // Combine PCM chunks into WAV and send
        const chunks = e.data.chunks as ArrayBuffer[];
        const totalLen = chunks.reduce(
          (sum: number, c: ArrayBuffer) => sum + c.byteLength,
          0,
        );
        const combined = new Int16Array(totalLen / 2);
        let offset = 0;
        for (const chunk of chunks) {
          const view = new Int16Array(chunk);
          combined.set(view, offset);
          offset += view.length;
        }

        const wavBytes = pcmToWav(combined, 24000);
        const b64 = arrayBufferToBase64(wavBytes);
        ws.send(JSON.stringify({ type: "audio", audio: b64, format: "wav" }));
      }
    };

    // --- Cleanup ---
    cleanupRef.current = () => {
      alive = false;
      workletNode.disconnect();
      source.disconnect();
      micCtx.close().catch(() => {});
      playbackCtx.close().catch(() => {});
      if (stream) stream.getTracks().forEach((t) => t.stop());
      URL.revokeObjectURL(workletUrl);
    };
  };

  // --- PCM16 playback (same as before) ---
  const playPcm16 = (ctx: AudioContext, pcmBytes: ArrayBuffer) => {
    const int16 = new Int16Array(pcmBytes);
    const float32 = new Float32Array(int16.length);
    for (let i = 0; i < int16.length; i++) {
      float32[i] = int16[i] / 0x7fff;
    }

    const buffer = ctx.createBuffer(1, float32.length, 24000);
    buffer.getChannelData(0).set(float32);

    const src = ctx.createBufferSource();
    src.buffer = buffer;
    // Connect through gain node so we can instantly silence on interruption
    src.connect(gainRef.current || ctx.destination);

    const now = ctx.currentTime;
    const startTime = Math.max(now, nextPlayTimeRef.current);
    src.start(startTime);
    nextPlayTimeRef.current = startTime + buffer.duration;
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Live Call Control
          </h1>
          <p className="text-slate-500 mt-1">
            Voice session operator dashboard
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div
            className={`w-2.5 h-2.5 rounded-full ${STATUS_COLORS[status]}`}
          />
          <span className="text-sm font-medium text-slate-700">
            {STATUS_LABELS[status]}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-6">
        <div className="col-span-4 space-y-4">
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-3">
            <h3 className="font-semibold text-slate-800 text-sm">
              Session Controls
            </h3>
            <div className="space-y-2">
              <button
                onClick={handleWarmup}
                disabled={status === "warming" || status === "in_call"}
                className="w-full py-2.5 bg-amber-50 text-amber-700 border border-amber-200 text-sm font-medium rounded-lg hover:bg-amber-100 transition disabled:opacity-50 flex items-center justify-center gap-2"
              >
                <Zap size={16} /> Warm Up
              </button>
              {status !== "in_call" ? (
                <button
                  onClick={handleStartCall}
                  disabled={status !== "ready"}
                  className="w-full py-2.5 bg-[#DA1710] text-white text-sm font-medium rounded-lg hover:bg-red-800 transition disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  <Phone size={16} /> Start Call
                </button>
              ) : (
                <button
                  onClick={handleEndCall}
                  className="w-full py-2.5 bg-slate-800 text-white text-sm font-medium rounded-lg hover:bg-slate-900 transition flex items-center justify-center gap-2"
                >
                  <PhoneOff size={16} /> End Call
                </button>
              )}
            </div>

            {status === "in_call" && (
              <div
                className={`w-full py-3 text-sm font-medium rounded-lg flex items-center justify-center gap-2 ${
                  isThinking
                    ? "bg-amber-50 text-amber-700 border border-amber-200"
                    : isAiSpeaking
                      ? "bg-blue-50 text-blue-700 border border-blue-200"
                      : isSpeaking
                        ? "bg-red-50 text-red-700 border border-red-200"
                        : "bg-green-50 text-green-700 border border-green-200"
                }`}
              >
                <Mic
                  size={18}
                  className={isSpeaking || isThinking ? "animate-pulse" : ""}
                />
                {isThinking
                  ? "Processing..."
                  : isAiSpeaking
                    ? "AI speaking..."
                    : isSpeaking
                      ? "Listening..."
                      : "Ready - just speak"}
              </div>
            )}
          </div>

          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-3">
            <h3 className="font-semibold text-slate-800 text-sm flex items-center gap-2">
              <Volume2 size={14} /> Voice
            </h3>
            <select
              value={selectedVoice}
              onChange={(e) => setSelectedVoice(e.target.value)}
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm"
            >
              {VOICE_OPTIONS.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.label}
                </option>
              ))}
            </select>
          </div>

          {warmupResult && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
              <h3 className="font-semibold text-slate-800 text-sm mb-2">
                Warmup Status
              </h3>
              <div className="space-y-1 text-xs">
                {Object.entries(warmupResult.results || {}).map(([k, v]) => (
                  <div key={k} className="flex justify-between">
                    <span className="text-slate-500 uppercase">{k}</span>
                    <span
                      className={`font-medium ${String(v).startsWith("ok") ? "text-green-600" : "text-red-600"}`}
                    >
                      {String(v)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="col-span-8">
          <div
            className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col"
            style={{ height: "calc(100vh - 200px)" }}
          >
            <div className="px-5 py-3 border-b border-slate-100 flex justify-between items-center bg-slate-50">
              <div>
                <h3 className="font-bold text-slate-800">Live Transcript</h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  {transcript.length} messages
                  {sessionId && (
                    <span className="ml-2 text-slate-400">
                      Session: {sessionId.slice(0, 8)}...
                    </span>
                  )}
                </p>
              </div>
              <div className="text-xs text-emerald-600 font-medium">
                Groq + OpenAI TTS
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-5 space-y-3">
              {transcript.length === 0 && (
                <div className="flex items-center justify-center h-full text-slate-400">
                  <div className="text-center">
                    <Mic size={48} className="mx-auto mb-4 opacity-20" />
                    <p>Start a call to begin — just speak naturally</p>
                    <p className="text-xs mt-2">
                      Groq STT (~200ms) + Groq LLM (~200ms) + Streaming TTS
                    </p>
                  </div>
                </div>
              )}
              {transcript.map((entry, i) => (
                <div
                  key={i}
                  className={`flex flex-col ${entry.speaker === "bot" ? "items-end" : "items-start"}`}
                >
                  <div
                    className={`max-w-[80%] p-3 rounded-xl text-sm ${
                      entry.speaker === "customer"
                        ? "bg-slate-100 text-slate-800 rounded-tl-none"
                        : "bg-red-50 text-slate-800 rounded-br-sm border border-red-100"
                    }`}
                  >
                    <p>{entry.text}</p>
                  </div>
                  <span className="text-[10px] text-slate-400 mt-1 px-1">
                    {entry.speaker === "customer" ? "Customer" : "AI"}
                  </span>
                </div>
              ))}
              <div ref={transcriptEndRef} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// --- Helpers ---
function base64ToArrayBuffer(b64: string): ArrayBuffer {
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes.buffer;
}

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  const chunkSize = 8192;
  for (let i = 0; i < bytes.length; i += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunkSize));
  }
  return btoa(binary);
}

function pcmToWav(pcmData: Int16Array, sampleRate: number): ArrayBuffer {
  const dataLength = pcmData.length * 2;
  const buffer = new ArrayBuffer(44 + dataLength);
  const view = new DataView(buffer);

  // RIFF header
  writeString(view, 0, "RIFF");
  view.setUint32(4, 36 + dataLength, true);
  writeString(view, 8, "WAVE");

  // fmt chunk
  writeString(view, 12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);

  // data chunk
  writeString(view, 36, "data");
  view.setUint32(40, dataLength, true);

  // PCM samples
  const pcmView = new Int16Array(buffer, 44);
  pcmView.set(pcmData);

  return buffer;
}

function writeString(view: DataView, offset: number, str: string) {
  for (let i = 0; i < str.length; i++) {
    view.setUint8(offset + i, str.charCodeAt(i));
  }
}

export default Live;
