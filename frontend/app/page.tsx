import Link from "next/link";
import { MessageSquare, MapPin, BarChart2, Clock, Shield, Zap } from "lucide-react";
import TopBar from "./components/TopBar";
import SearchBar from "./components/SearchBar";
import OnboardingBanner from "./components/OnboardingBanner";

const QUICK_ACTIONS = [
  { icon: MessageSquare, label: "Nueva consulta", href: "/chat", desc: "Describe tu síntoma" },
  { icon: MapPin,        label: "Red de hospitales", href: "/chat?tab=hospitals", desc: "Ver hospitales cerca" },
  { icon: BarChart2,     label: "Demo en vivo", href: "/chat?demo=1", desc: "Ver cómo funciona" },
];

const FEATURES = [
  { icon: Shield, title: "Cálculo verificado", desc: "Validamos cobertura, deducible y topes de tu póliza" },
  { icon: Zap,    title: "Respuesta en 30 s",  desc: "6 agentes IA trabajando en paralelo por ti" },
  { icon: MapPin, title: "25+ hospitales",      desc: "Red de hospitales y clínicas en Ecuador con precios reales" },
  { icon: Clock,  title: "Sin sorpresas",       desc: "Sabes exactamente cuánto pagarás antes de ir" },
];

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col">
      <TopBar />
      <OnboardingBanner />

      {/* Hero */}
      <main className="flex flex-1 flex-col items-center justify-center px-4 py-20 text-center">
        <span className="mb-4 badge-blue text-xs uppercase tracking-widest">hackIAthon · Reto 3</span>
        <h1 className="mb-3 text-4xl font-bold tracking-tight text-gray-900 sm:text-5xl">
          ¿Cuánto pagaré por mi<br className="hidden sm:block" /> consulta médica?
        </h1>
        <p className="mb-10 max-w-xl text-lg text-gray-500">
          Describe tu síntoma y te decimos en segundos cuánto cubre tu seguro y cuánto pagas tú — antes de salir de casa.
        </p>

        <SearchBar />

        <div className="mt-8 flex flex-wrap justify-center gap-3">
          {QUICK_ACTIONS.map((a) => (
            <Link key={a.href} href={a.href} className="btn-secondary">
              <a.icon className="h-4 w-4" />
              {a.label}
            </Link>
          ))}
        </div>
      </main>

      {/* Features */}
      <section className="border-t border-gray-100 bg-white py-16 px-4">
        <div className="mx-auto grid max-w-4xl grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map((f) => (
            <div key={f.title} className="flex flex-col items-center gap-3 text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-50 text-brand-600">
                <f.icon className="h-6 w-6" />
              </div>
              <h3 className="font-semibold text-gray-900">{f.title}</h3>
              <p className="text-sm text-gray-500">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <footer className="border-t border-gray-100 py-6 text-center text-xs text-gray-400">
        CopayAI · hackIAthon Viamatica 2026 · Los estimados son referenciales — confirma con tu aseguradora.
      </footer>
    </div>
  );
}
