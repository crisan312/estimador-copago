"use client";
import { useSearchParams } from "next/navigation";
import ChatInterface from "../components/ChatInterface";

export default function ChatClient() {
  const params = useSearchParams();
  const q = params.get("q") ?? undefined;
  const demo = params.get("demo") === "1";

  return (
    <main className="flex-1 overflow-hidden">
      <ChatInterface initialQuery={q} isDemo={demo} />
    </main>
  );
}
