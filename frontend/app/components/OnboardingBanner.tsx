"use client";
import { useState, useEffect } from "react";
import { X, Info } from "lucide-react";

export default function OnboardingBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!localStorage.getItem("copay_onboarded")) setVisible(true);
  }, []);

  const dismiss = () => {
    localStorage.setItem("copay_onboarded", "1");
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <div className="border-l-4 border-brand-500 bg-brand-50 px-4 py-3 text-sm text-brand-800 flex items-start gap-3">
      <Info className="mt-0.5 h-4 w-4 shrink-0 text-brand-600" />
      <span>
        <strong>Bienvenido a CopayAI.</strong> Describe tu síntoma en tus propias palabras y te
        diremos cuánto pagarás por tu consulta con tu seguro médico. Es gratis y tarda menos de 2 minutos.
      </span>
      <button onClick={dismiss} className="ml-auto shrink-0 text-brand-400 hover:text-brand-700">
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}
