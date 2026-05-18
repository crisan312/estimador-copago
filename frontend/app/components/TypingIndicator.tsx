"use client";
import { Bot } from "lucide-react";

export default function TypingIndicator({ agent }: { agent?: string }) {
  return (
    <div className="flex items-end gap-2 self-start">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-100 text-brand-600">
        <Bot className="h-4 w-4" />
      </div>
      <div className="sse-bubble-agent flex items-center gap-3">
        <span className="flex gap-1">
          <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:0ms]" />
          <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:150ms]" />
          <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:300ms]" />
        </span>
        {agent && <span className="text-xs text-gray-400">{agent}</span>}
      </div>
    </div>
  );
}
