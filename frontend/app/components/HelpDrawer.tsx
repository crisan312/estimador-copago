"use client";
import { useState } from "react";
import { HelpCircle, X, ChevronDown, ChevronUp } from "lucide-react";

const FAQ = [
  {
    q: "¿Qué es el copago?",
    a: "Es la parte del costo de tu consulta que pagas tú. Si tu seguro cubre el 80%, tu copago es el 20% restante.",
  },
  {
    q: "¿Qué es el deducible?",
    a: "Es un monto anual que pagas de tu bolsillo antes de que el seguro empiece a cubrir. Por ejemplo, con un deducible de $500 anuales, los primeros $500 de gastos médicos los pagas tú.",
  },
  {
    q: "¿Qué es el coaseguro?",
    a: "Un porcentaje adicional que pagas después del deducible. Por ejemplo, 10% de coaseguro sobre el costo a cubrir.",
  },
  {
    q: "¿Por qué varía el copago entre hospitales?",
    a: "Los hospitales tienen tarifas distintas por la misma consulta. Tu seguro cubre un porcentaje fijo, así que a mayor tarifa del hospital, mayor tu copago.",
  },
  {
    q: "¿Es exacto el cálculo?",
    a: "Es una estimación confiable basada en tu póliza. El monto final puede variar ligeramente según la aseguradora y el médico específico. Siempre confirma antes de tu consulta.",
  },
  {
    q: "¿Qué pasa si mi póliza no está en el sistema?",
    a: "Usamos valores de referencia del mercado ecuatoriano para darte una estimación aproximada. El resultado es útil para comparar hospitales, pero confirma con tu aseguradora.",
  },
];

function Accordion({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-b border-gray-100 last:border-0">
      <button className="flex w-full items-center justify-between py-3 text-left text-sm font-medium text-gray-800" onClick={() => setOpen(!open)}>
        {q}
        {open ? <ChevronUp className="h-4 w-4 shrink-0 text-gray-400" /> : <ChevronDown className="h-4 w-4 shrink-0 text-gray-400" />}
      </button>
      {open && <p className="pb-3 text-sm text-gray-600 leading-relaxed">{a}</p>}
    </div>
  );
}

export default function HelpDrawer() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button onClick={() => setOpen(true)} className="fixed bottom-6 right-6 z-50 flex h-12 w-12 items-center justify-center rounded-full bg-brand-600 text-white shadow-lg hover:bg-brand-700 transition-colors">
        <HelpCircle className="h-6 w-6" />
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-black/20 backdrop-blur-sm" onClick={() => setOpen(false)} />
          <aside className="relative z-10 flex h-full w-full max-w-sm flex-col bg-white shadow-2xl">
            <header className="flex items-center justify-between border-b border-gray-100 px-5 py-4">
              <h2 className="font-semibold text-gray-900">Centro de ayuda</h2>
              <button onClick={() => setOpen(false)} className="text-gray-400 hover:text-gray-700">
                <X className="h-5 w-5" />
              </button>
            </header>

            <div className="flex-1 overflow-y-auto p-5 space-y-5">
              <section>
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-widest text-gray-400">Glosario</h3>
                <div className="space-y-0">
                  {FAQ.slice(0, 3).map((f) => <Accordion key={f.q} {...f} />)}
                </div>
              </section>
              <section>
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-widest text-gray-400">Preguntas frecuentes</h3>
                <div className="space-y-0">
                  {FAQ.slice(3).map((f) => <Accordion key={f.q} {...f} />)}
                </div>
              </section>

              <section className="rounded-xl bg-brand-50 p-4 text-sm text-brand-800">
                <strong>Atajos de teclado:</strong>
                <ul className="mt-2 space-y-1 text-xs">
                  <li><kbd className="rounded bg-white px-1 py-0.5 shadow-sm">N</kbd> — Nueva consulta</li>
                  <li><kbd className="rounded bg-white px-1 py-0.5 shadow-sm">/</kbd> — Buscar síntoma</li>
                  <li><kbd className="rounded bg-white px-1 py-0.5 shadow-sm">H</kbd> — Ayuda</li>
                </ul>
              </section>
            </div>
          </aside>
        </div>
      )}
    </>
  );
}
