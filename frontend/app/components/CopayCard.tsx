"use client";
import { CopayData } from "../types";
import CopayGauge from "./CopayGauge";
import ValidationBadge from "./ValidationBadge";
import { DollarSign } from "lucide-react";

export default function CopayCard({ data }: { data: CopayData }) {
  const fmt = (n: number) => `$${n.toFixed(2)}`;

  return (
    <div className="card border-brand-100 space-y-4">
      <div className="flex items-center gap-2 text-sm font-semibold text-gray-700">
        <DollarSign className="h-4 w-4 text-brand-600" />
        Desglose de tu copago
      </div>

      <CopayGauge coveragePct={data.cobertura_pct} />

      <div className="divide-y divide-gray-50 rounded-xl bg-gray-50 text-sm">
        <div className="flex justify-between px-4 py-2.5 text-gray-600">
          <span>Costo total de la consulta</span>
          <span className="font-medium">{fmt(data.costo_consulta_usd)}</span>
        </div>
        {data.deducible_aplicado > 0 && (
          <div className="flex justify-between px-4 py-2.5 text-gray-600">
            <span>Deducible aplicado</span>
            <span className="font-medium text-amber-600">− {fmt(data.deducible_aplicado)}</span>
          </div>
        )}
        <div className="flex justify-between px-4 py-2.5 text-gray-600">
          <span>Tu seguro cubre ({data.cobertura_pct.toFixed(0)}%)</span>
          <span className="font-medium text-green-600">− {fmt(data.seguro_cubre_usd)}</span>
        </div>
        <div className="flex justify-between px-4 py-2.5 font-semibold text-gray-900 bg-white rounded-b-xl">
          <span>Tu copago estimado</span>
          <span className="text-lg text-brand-700">{fmt(data.copago_estimado_usd)}</span>
        </div>
      </div>

      <ValidationBadge confidence={data.confianza} />

      {data.advertencias?.length > 0 && (
        <ul className="space-y-1 text-xs text-amber-700">
          {data.advertencias.map((w, i) => <li key={i}>⚠️ {w}</li>)}
        </ul>
      )}

      {data.tope_alcanzado && (
        <p className="badge-red text-xs">Tope de cobertura anual alcanzado — pagas el 100% restante.</p>
      )}
    </div>
  );
}
