"use client";
import { TokenBudget } from "../types";

export default function TokenUsageBar({ budget }: { budget: TokenBudget }) {
  const pct = Math.min(budget.usage_pct, 100);
  const color = pct >= 80 ? "bg-red-400" : pct >= 60 ? "bg-amber-400" : "bg-brand-400";

  return (
    <div className="flex items-center gap-2 text-xs text-gray-400">
      <div className="h-1 w-24 rounded-full bg-gray-100">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span>{budget.used.toLocaleString()} / {budget.budget.toLocaleString()} tokens</span>
      {budget.alert && <span className="badge-amber">Presupuesto alto</span>}
    </div>
  );
}
