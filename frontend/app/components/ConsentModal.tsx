"use client";
import { useState } from "react";
import { Shield, ExternalLink, X } from "lucide-react";

interface Props {
  onAccept: () => void;
  onDecline: () => void;
}

export default function ConsentModal({ onAccept, onDecline }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [accepting, setAccepting] = useState(false);

  const handleAccept = async () => {
    setAccepting(true);
    await onAccept();
    setAccepting(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="relative w-full max-w-lg rounded-2xl bg-white shadow-2xl">
        {/* Header */}
        <div className="flex items-center gap-3 border-b border-gray-100 px-6 py-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
            <Shield className="h-5 w-5" />
          </div>
          <div>
            <h2 className="font-semibold text-gray-900">Aviso de privacidad y consentimiento</h2>
            <p className="text-xs text-gray-500">Ley Orgánica de Protección de Datos Personales — Ecuador</p>
          </div>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-4 text-sm text-gray-700 max-h-80 overflow-y-auto">
          <p>
            Para estimar tu copago médico, necesitamos procesar información sobre tu <strong>estado de salud</strong>{" "}
            y tu <strong>póliza de seguro</strong>. Estos son <strong>datos sensibles</strong> según la{" "}
            <abbr title="Ley Orgánica de Protección de Datos Personales">LOPDP</abbr> de Ecuador (Art. 26).
          </p>

          <div className="rounded-xl bg-gray-50 p-4 space-y-2 text-xs">
            <p className="font-semibold text-gray-800">¿Qué datos tratamos?</p>
            <ul className="space-y-1 list-disc list-inside text-gray-600">
              <li>Síntomas que describes (datos de salud)</li>
              <li>Número de póliza de seguro médico</li>
              <li>Historial de la conversación</li>
            </ul>
            <p className="font-semibold text-gray-800 pt-1">¿Para qué los usamos?</p>
            <ul className="space-y-1 list-disc list-inside text-gray-600">
              <li>Identificar la especialidad médica recomendada</li>
              <li>Calcular tu copago exacto</li>
              <li>Mostrarte hospitales ordenados por menor costo para ti</li>
            </ul>
          </div>

          {expanded && (
            <div className="rounded-xl border border-gray-100 p-4 space-y-2 text-xs text-gray-600">
              <p><strong>Responsable del tratamiento:</strong> CopayAI — hackIAthon Viamatica</p>
              <p><strong>Base legal:</strong> Tu consentimiento explícito (LOPDP Art. 7)</p>
              <p><strong>Retención:</strong> 90 días desde la creación. Puedes solicitar eliminación en cualquier momento.</p>
              <p><strong>Cifrado:</strong> Todos tus datos sensibles se cifran en reposo con AES-128-CBC.</p>
              <p><strong>Tus derechos ARCO:</strong> Puedes Acceder, Rectificar, Cancelar u Oponerte al tratamiento desde "Mis datos" en cualquier momento.</p>
              <p><strong>Transferencias:</strong> No compartimos tus datos con terceros ni realizamos transferencias internacionales.</p>
              <p><strong>DPO:</strong> privacidad@copayai.ec</p>
            </div>
          )}

          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs text-brand-600 hover:underline"
          >
            {expanded ? "Ver menos" : "Ver aviso completo de privacidad"}
          </button>
        </div>

        {/* Footer */}
        <div className="border-t border-gray-100 px-6 py-4 space-y-3">
          <p className="text-xs text-gray-500 text-center">
            Al aceptar, confirmas que eres mayor de edad y consientes el tratamiento de tus datos de salud
            conforme a la LOPDP. Puedes retirar tu consentimiento en cualquier momento.
          </p>
          <div className="flex gap-3">
            <button
              onClick={onDecline}
              className="flex-1 rounded-xl border border-gray-200 py-2.5 text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors"
            >
              No acepto
            </button>
            <button
              onClick={handleAccept}
              disabled={accepting}
              className="flex-1 rounded-xl bg-brand-600 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 transition-colors disabled:opacity-60"
            >
              {accepting ? "Registrando..." : "Acepto — Continuar"}
            </button>
          </div>
          <div className="flex justify-center gap-4 text-[10px] text-gray-400">
            <a href="/privacidad" target="_blank" className="flex items-center gap-1 hover:text-brand-600">
              <ExternalLink className="h-3 w-3" /> Aviso de privacidad
            </a>
            <a href="/mis-datos" className="flex items-center gap-1 hover:text-brand-600">
              Mis datos
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
