import { Metadata } from "next";
import TopBar from "../../components/TopBar";
import CopayCard from "../../components/CopayCard";
import HospitalList from "../../components/HospitalList";

export const metadata: Metadata = { title: "CopayAI — Resumen de consulta" };

async function fetchSummary(id: string) {
  // Componente server: usa la URL interna de Docker (api:8000), nunca localhost
  const base =
    process.env.INTERNAL_API_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://localhost:8000";
  try {
    const res = await fetch(`${base}/api/v1/conversation/${id}/summary`, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export default async function ResultPage({ params }: { params: { id: string } }) {
  const summary = await fetchSummary(params.id);

  if (!summary) {
    return (
      <div className="flex min-h-screen flex-col">
        <TopBar />
        <main className="flex flex-1 items-center justify-center">
          <p className="text-gray-500">Consulta no encontrada o expirada.</p>
        </main>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col">
      <TopBar />
      <main className="mx-auto w-full max-w-2xl space-y-6 px-4 py-8">
        <header>
          <h1 className="text-2xl font-bold text-gray-900">Resumen de tu consulta</h1>
          <p className="mt-1 text-sm text-gray-500">
            {summary.patient.sintoma_principal} · {summary.patient.especialidad}
          </p>
        </header>

        {summary.copay && <CopayCard data={summary.copay} />}
        {summary.hospitals?.length > 0 && <HospitalList hospitals={summary.hospitals} />}

        <p className="text-center text-xs text-gray-400">
          Generado el {new Date(summary.generated_at).toLocaleString("es-EC")} · Los estimados son referenciales.
        </p>
      </main>
    </div>
  );
}
