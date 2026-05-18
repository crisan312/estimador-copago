import { SSEEvent } from "../types";

const BASE = process.env.NEXT_PUBLIC_API_URL || "";

let _sessionId: string | null = null;

function getSessionId(): string {
  if (typeof window === "undefined") return "";
  if (!_sessionId) {
    _sessionId = sessionStorage.getItem("copay_session") || crypto.randomUUID();
    sessionStorage.setItem("copay_session", _sessionId);
  }
  return _sessionId;
}

export async function* streamChat(
  message: string,
  conversationId: string | null
): AsyncGenerator<SSEEvent> {
  const resp = await fetch(`${BASE}/api/v1/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Session-Id": getSessionId(),
    },
    body: JSON.stringify({ message, conversation_id: conversationId }),
  });

  if (resp.status === 403) throw new Error("CONSENT_REQUIRED");
  if (!resp.ok) throw new Error(`Chat error: ${resp.status}`);

  const reader = resp.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n\n");
    buffer = lines.pop() ?? "";
    for (const chunk of lines) {
      const line = chunk.trim();
      if (!line.startsWith("data:")) continue;
      const json = line.slice(5).trim();
      try {
        yield JSON.parse(json) as SSEEvent;
      } catch {}
    }
  }
}

export async function* streamDemo(): AsyncGenerator<SSEEvent> {
  const resp = await fetch(`${BASE}/api/v1/demo`, {
    headers: { "X-Session-Id": getSessionId() },
  });
  if (!resp.ok) throw new Error(`Demo error: ${resp.status}`);
  const reader = resp.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n\n");
    buffer = lines.pop() ?? "";
    for (const chunk of lines) {
      const line = chunk.trim();
      if (!line.startsWith("data:")) continue;
      try { yield JSON.parse(line.slice(5).trim()) as SSEEvent; } catch {}
    }
  }
}

export async function getHospitals(city?: string, specialty?: string) {
  const params = new URLSearchParams();
  if (city) params.set("city", city);
  if (specialty) params.set("specialty", specialty);
  const resp = await fetch(`${BASE}/api/v1/hospitals?${params}`);
  return resp.json();
}

export async function getSummary(conversationId: string) {
  const resp = await fetch(`${BASE}/api/v1/conversation/${conversationId}/summary`);
  return resp.json();
}
