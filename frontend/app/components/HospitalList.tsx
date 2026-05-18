"use client";
import { MapPin, Phone, Clock, Star } from "lucide-react";
import { Hospital } from "../types";

function RatingStars({ rating }: { rating: number }) {
  return (
    <span className="flex items-center gap-0.5 text-xs text-amber-500">
      <Star className="h-3 w-3 fill-current" />
      {rating.toFixed(1)}
    </span>
  );
}

export default function HospitalList({ hospitals }: { hospitals: Hospital[] }) {
  if (!hospitals.length) return null;

  return (
    <div className="card space-y-3">
      <h3 className="text-sm font-semibold text-gray-700">
        Hospitales ordenados por menor copago para ti
      </h3>

      <ul className="space-y-2">
        {hospitals.map((h, idx) => (
          <li
            key={h.id}
            className={`rounded-xl border p-3 transition-colors ${
              idx === 0 ? "border-brand-200 bg-brand-50" : "border-gray-100 bg-white hover:bg-gray-50"
            }`}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  {idx === 0 && <span className="badge-blue text-[10px]">Mejor opción</span>}
                  <span className="text-sm font-semibold text-gray-900 truncate">{h.nombre}</span>
                  {h.en_red_autorizada && (
                    <span className="badge-green text-[10px]">En tu red</span>
                  )}
                </div>

                <div className="mt-1 flex flex-wrap items-center gap-3 text-xs text-gray-500">
                  <span className="flex items-center gap-1">
                    <MapPin className="h-3 w-3" />{h.direccion}
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />{h.tiempo_espera_promedio_min} min espera
                  </span>
                  {h.telefono && (
                    <a href={`tel:${h.telefono}`} className="flex items-center gap-1 text-brand-600 hover:underline">
                      <Phone className="h-3 w-3" />{h.telefono}
                    </a>
                  )}
                  <RatingStars rating={h.rating_atencion} />
                </div>
              </div>

              <div className="shrink-0 text-right">
                <p className="text-lg font-bold text-brand-700">${h.copago_estimado_usd?.toFixed(2)}</p>
                <p className="text-[10px] text-gray-400">tu copago</p>
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
