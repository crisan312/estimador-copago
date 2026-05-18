import { Metadata } from "next";
import TopBar from "../components/TopBar";
import { BookOpen, DollarSign, Hospital, HelpCircle } from "lucide-react";

export const metadata: Metadata = { title: "CopayAI — Ayuda" };

const GLOSSARY = [
  { term: "Copago",     def: "La parte de la consulta que pagas tú. Si el seguro cubre el 80%, tu copago es el 20% restante." },
  { term: "Deducible",  def: "Monto anual que pagas antes de que el seguro empiece a cubrir. Ej: $500 de deducible = tú pagas los primeros $500 del año." },
  { term: "Coaseguro",  def: "Porcentaje adicional que pagas sobre el costo después del deducible. Varía por plan y tipo de atención." },
  { term: "Red médica", def: "Lista de hospitales y clínicas con convenio con tu aseguradora. Atenderte en la red suele ser más barato." },
  { term: "Tope anual", def: "El máximo que tu seguro paga en un año. Una vez alcanzado, pagas el 100% de los gastos restantes." },
  { term: "Urgencias",  def: "Atención para condiciones que necesitan atención en pocas horas pero no son riesgo inmediato de vida." },
  { term: "Emergencia", def: "Atención inmediata por riesgo vital: dolor de pecho intenso, dificultad respiratoria, pérdida de conciencia, etc." },
];

export default function HelpPage() {
  return (
    <div className="min-h-screen flex flex-col">
      <TopBar />
      <main className="mx-auto w-full max-w-3xl px-4 py-10 space-y-10">
        <header>
          <h1 className="text-3xl font-bold text-gray-900">Centro de ayuda</h1>
          <p className="mt-2 text-gray-500">Todo lo que necesitas saber para usar CopayAI y entender tu seguro médico.</p>
        </header>

        {/* Glosario */}
        <section>
          <div className="flex items-center gap-2 mb-4">
            <BookOpen className="h-5 w-5 text-brand-600" />
            <h2 className="text-lg font-semibold text-gray-900">Glosario de seguros médicos</h2>
          </div>
          <div className="divide-y divide-gray-100 rounded-2xl border border-gray-100 bg-white overflow-hidden">
            {GLOSSARY.map((g) => (
              <div key={g.term} className="flex gap-4 px-5 py-4">
                <span className="min-w-[110px] font-semibold text-gray-800 text-sm">{g.term}</span>
                <span className="text-sm text-gray-600 leading-relaxed">{g.def}</span>
              </div>
            ))}
          </div>
        </section>

        {/* Atajos */}
        <section className="card bg-brand-50 border-brand-100">
          <div className="flex items-center gap-2 mb-3">
            <HelpCircle className="h-5 w-5 text-brand-600" />
            <h2 className="text-lg font-semibold text-gray-900">Atajos de teclado</h2>
          </div>
          <ul className="space-y-2 text-sm text-gray-700">
            <li><kbd className="rounded border bg-white px-2 py-0.5 shadow-sm text-xs">N</kbd> — Nueva consulta</li>
            <li><kbd className="rounded border bg-white px-2 py-0.5 shadow-sm text-xs">/</kbd> — Buscar síntoma en la barra principal</li>
            <li><kbd className="rounded border bg-white px-2 py-0.5 shadow-sm text-xs">H</kbd> — Abrir esta ayuda</li>
            <li><kbd className="rounded border bg-white px-2 py-0.5 shadow-sm text-xs">Enter</kbd> — Enviar mensaje en el chat</li>
          </ul>
        </section>

        {/* Hospitales */}
        <section>
          <div className="flex items-center gap-2 mb-4">
            <Hospital className="h-5 w-5 text-brand-600" />
            <h2 className="text-lg font-semibold text-gray-900">Red de hospitales en Ecuador</h2>
          </div>
          <p className="text-sm text-gray-600 mb-3">
            CopayAI tiene datos de más de 25 hospitales y clínicas en las principales ciudades. Los precios son de referencia — confirma disponibilidad directamente con el centro médico.
          </p>
          <div className="flex flex-wrap gap-2">
            {["Guayaquil","Quito","Cuenca","Manta","Ambato","Portoviejo","Loja","Riobamba"].map((c) => (
              <span key={c} className="badge-blue">{c}</span>
            ))}
          </div>
        </section>

        <p className="text-center text-xs text-gray-400">
          CopayAI · hackIAthon Viamatica 2026 · Los estimados son referenciales — confirma con tu aseguradora.
        </p>
      </main>
    </div>
  );
}
