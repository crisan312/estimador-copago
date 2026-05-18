"use client";
import { Stethoscope, AlertTriangle, Clock } from "lucide-react";
import { SpecialtyData } from "../types";

const urgencyConfig = {
  EMERGENCIA: { cls: "badge-red",   icon: AlertTriangle, label: "Emergencia" },
  URGENTE:    { cls: "badge-amber",  icon: Clock,         label: "Urgente" },
  NORMAL:     { cls: "badge-blue",   icon: Stethoscope,   label: "Normal" },
  PREVENTIVO: { cls: "badge-gray",   icon: Stethoscope,   label: "Preventivo" },
};

export default function SpecialtyBadge({ data }: { data: SpecialtyData }) {
  const cfg = urgencyConfig[data.urgencia] ?? urgencyConfig.NORMAL;
  const Icon = cfg.icon;

  return (
    <div className="card flex items-start gap-3 bg-blue-50 border-blue-100">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-brand-100 text-brand-600">
        <Stethoscope className="h-5 w-5" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-semibold text-gray-900">{data.especialidad_primaria}</span>
          <span className={cfg.cls}>
            <Icon className="mr-1 h-3 w-3" />
            {cfg.label}
          </span>
        </div>
        {data.especialidad_alternativa && (
          <p className="mt-0.5 text-xs text-gray-500">Alternativa: {data.especialidad_alternativa}</p>
        )}
        {data.razon && <p className="mt-1 text-sm text-gray-600">{data.razon}</p>}
        <p className="mt-1 text-xs text-gray-400">{data.tiempo_espera_recomendado}</p>
      </div>
    </div>
  );
}
