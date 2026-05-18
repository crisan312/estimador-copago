"use client";
import { useState, useRef, useEffect, useCallback } from "react";
import { Send, RefreshCw } from "lucide-react";
import { ChatMessage, CopayData, Hospital, SpecialtyData, TokenBudget, SSEEvent } from "../types";
import { streamChat, streamDemo } from "../lib/api";
import ChatBubble from "./ChatBubble";
import TypingIndicator from "./TypingIndicator";
import CopayCard from "./CopayCard";
import HospitalList from "./HospitalList";
import SpecialtyBadge from "./SpecialtyBadge";
import TokenUsageBar from "./TokenUsageBar";

interface Props {
  initialQuery?: string;
  isDemo?: boolean;
}

export default function ChatInterface({ initialQuery, isDemo }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState<string | null>(null);
  const [copayData, setCopayData] = useState<CopayData | null>(null);
  const [hospitals, setHospitals] = useState<Hospital[]>([]);
  const [specialty, setSpecialty] = useState<SpecialtyData | null>(null);
  const [tokenBudget, setTokenBudget] = useState<TokenBudget | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [completed, setCompleted] = useState(false);

  const bottomRef = useRef<HTMLDivElement>(null);
  const initialized = useRef(false);

  const addMessage = useCallback((role: ChatMessage["role"], content: string) => {
    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), role, content, timestamp: new Date() },
    ]);
  }, []);

  const processEvents = useCallback(async (gen: AsyncGenerator<SSEEvent>) => {
    setIsStreaming(true);
    try {
      for await (const event of gen) {
        if (event.type === "message" && event.content) {
          setThinking(null);
          addMessage(event.role as ChatMessage["role"] ?? "assistant", event.content);
        } else if (event.type === "thinking") {
          setThinking(event.agent as string ?? null);
        } else if (event.type === "copay") {
          setCopayData(event as unknown as CopayData);
        } else if (event.type === "hospitals") {
          const h = (event as { hospitales?: Hospital[] }).hospitales ?? [];
          setHospitals(h);
        } else if (event.type === "specialty") {
          setSpecialty(event as unknown as SpecialtyData);
        } else if (event.type === "token_budget") {
          setTokenBudget(event as unknown as TokenBudget);
        } else if (event.type === "state" && event.conversation_id) {
          setConversationId(event.conversation_id as string);
        } else if (event.type === "completed") {
          setCompleted(true);
        } else if (event.type === "error") {
          setThinking(null);
          addMessage("assistant", `⚠️ ${event.message ?? "Error inesperado"}`);
        }
      }
    } finally {
      setThinking(null);
      setIsStreaming(false);
    }
  }, [addMessage]);

  // Auto-start
  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;
    if (isDemo) {
      processEvents(streamDemo());
    } else if (initialQuery) {
      addMessage("user", initialQuery);
      processEvents(streamChat(initialQuery, null));
    } else {
      // Trigger greeting
      processEvents(streamChat("", null));
    }
  }, [initialQuery, isDemo, processEvents, addMessage]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, thinking, copayData]);

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || isStreaming) return;
    setInput("");
    addMessage("user", text);
    await processEvents(streamChat(text, conversationId));
  };

  const reset = () => {
    setMessages([]);
    setCopayData(null);
    setHospitals([]);
    setSpecialty(null);
    setTokenBudget(null);
    setConversationId(null);
    setCompleted(false);
    initialized.current = false;
    processEvents(streamChat("", null));
  };

  return (
    <div className="flex h-full flex-col">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.map((m) => <ChatBubble key={m.id} message={m} />)}
        {thinking && <TypingIndicator agent={thinking} />}

        {/* Embedded result cards */}
        {specialty && <SpecialtyBadge data={specialty} />}
        {copayData && <CopayCard data={copayData} />}
        {hospitals.length > 0 && <HospitalList hospitals={hospitals} />}

        <div ref={bottomRef} />
      </div>

      {/* Footer */}
      <div className="border-t border-gray-100 bg-white px-4 py-3 space-y-2">
        {tokenBudget && <TokenUsageBar budget={tokenBudget} />}

        <div className="flex gap-2">
          <input
            type="text"
            placeholder={completed ? "¿Alguna otra pregunta?" : "Escribe tu respuesta..."}
            className="flex-1 rounded-xl border border-gray-200 bg-gray-50 px-4 py-2.5 text-sm outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100 transition-all"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") sendMessage(); }}
            disabled={isStreaming}
          />
          <button onClick={sendMessage} disabled={isStreaming || !input.trim()} className="btn-primary">
            <Send className="h-4 w-4" />
          </button>
          <button onClick={reset} title="Nueva consulta" className="btn-secondary px-3">
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>

        <p className="text-center text-[10px] text-gray-400">
          Los estimados son referenciales — confirma con tu aseguradora.
        </p>
      </div>
    </div>
  );
}
