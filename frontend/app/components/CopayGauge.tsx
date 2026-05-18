"use client";

export default function CopayGauge({ coveragePct }: { coveragePct: number }) {
  const pct = Math.max(0, Math.min(100, coveragePct));
  const patientPct = 100 - pct;

  return (
    <div className="space-y-1.5">
      <div className="flex h-4 w-full overflow-hidden rounded-full bg-gray-100">
        <div
          className="h-full rounded-l-full bg-green-400 transition-all duration-700"
          style={{ width: `${pct}%` }}
          title={`Seguro: ${pct}%`}
        />
        <div
          className="h-full rounded-r-full bg-amber-400 transition-all duration-700"
          style={{ width: `${patientPct}%` }}
          title={`Tu parte: ${patientPct}%`}
        />
      </div>
      <div className="flex justify-between text-xs text-gray-500">
        <span className="flex items-center gap-1"><span className="inline-block h-2 w-2 rounded-full bg-green-400" /> Seguro cubre {pct.toFixed(0)}%</span>
        <span className="flex items-center gap-1">Tu parte {patientPct.toFixed(0)}% <span className="inline-block h-2 w-2 rounded-full bg-amber-400" /></span>
      </div>
    </div>
  );
}
