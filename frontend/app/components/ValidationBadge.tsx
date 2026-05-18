"use client";
import { CheckCircle2, AlertTriangle } from "lucide-react";

export default function ValidationBadge({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100);
  const isHigh = confidence >= 0.75;

  return (
    <div className={`flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium ${isHigh ? "bg-green-50 text-green-700" : "bg-amber-50 text-amber-700"}`}>
      {isHigh
        ? <CheckCircle2 className="h-3.5 w-3.5" />
        : <AlertTriangle className="h-3.5 w-3.5" />
      }
      {isHigh
        ? `Cálculo verificado · Confianza ${pct}%`
        : `Estimado aproximado · Confianza ${pct}% — Confirma con tu aseguradora`
      }
    </div>
  );
}
