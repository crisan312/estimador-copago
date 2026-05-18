"use client";
import { useState } from "react";
import TopBar from "../components/TopBar";
import { UserCheck, Trash2, Download, Shield, AlertTriangle } from "lucide-react";

const BASE = process.env.NEXT_PUBLIC_API_URL || "";

function getSessionId(): string {
  if (typeof window === "undefined") return "";
  return sessionStorage.getItem("copay_session") || "";
}

export default function MisDatosPage() {
  const [myData, setMyData] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleted, setDeleted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchMyData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${BASE}/api/v1/my-data`, {
        headers: { "X-Session-Id": getSessionId() },
      });
      if (!res.ok) throw new Error("No se pudo obtener los datos.");
      setMyData(await res.json());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error desconocido");
    } finally {
      setLoading(false);
    }
  };

  const requestDeletion = async () => {
    if (!confirm("¿Confirmas que deseas eliminar TODOS tus datos? Esta acción no se puede deshacer.")) return;
    setDeleting(true);
    try {
      const res = await fetch(`${BASE}/api/v1/my-data`, {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
          "X-Session-Id": getSessionId(),
        },
        body: JSON.stringify({ reason: "Solicitud del titular — derecho de supresión LOPDP Art. 16" }),
      });
      if (res.ok) {
        setDeleted(true);
        setMyData(null);
        sessionStorage.removeItem("copay_session");
      }
    } catch {
      setError("Error al procesar la solicitud.");
    } finally {
      setDeleting(false);
    }
  };

  const downloadData = () => {
    if (!myData) return;
    const blob = new Blob([JSON.stringify(myData, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `mis-datos-copayai-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen flex flex-col">
      <TopBar />
      <main className="mx-auto w-full max-w-2xl px-4 py-10 space-y-6">
        <header className="space-y-1">
          <div className="flex items-center gap-2">
            <UserCheck className="h-6 w-6 text-brand-600" />
            <h1 className="text-2xl font-bold text-gray-900">Mis datos</h1>
          </div>
          <p className="text-sm text-gray-500">
            Ejerce tus derechos ARCO conforme a la <strong>LOPDP Ecuador</strong> (Arts. 14-19).
          </p>
        </header>

        {deleted ? (
          <div className="card bg-green-50 border-green-100 text-green-800 space-y-2">
            <p className="font-semibold">✅ Todos tus datos han sido eliminados.</p>
            <p className="text-sm">El registro de auditoría se conserva de forma anónima por obligación legal (7 años — SSyP Res. JB-2012-2248).</p>
          </div>
        ) : (
          <>
            {/* Acceso */}
            <div className="card space-y-3">
              <div className="flex items-center gap-2">
                <Download className="h-4 w-4 text-brand-600" />
                <h2 className="font-semibold text-gray-900">Acceso a mis datos (Art. 14 LOPDP)</h2>
              </div>
              <p className="text-sm text-gray-600">Obtén una copia completa de todos los datos que hemos procesado en tu sesión actual.</p>
              <div className="flex gap-2">
                <button onClick={fetchMyData} disabled={loading} className="btn-primary">
                  {loading ? "Consultando..." : "Ver mis datos"}
                </button>
                {myData && (
                  <button onClick={downloadData} className="btn-secondary">
                    <Download className="h-4 w-4" /> Descargar JSON
                  </button>
                )}
              </div>

              {myData && (
                <div className="rounded-xl bg-gray-50 p-4 text-xs font-mono overflow-auto max-h-60 text-gray-700">
                  <pre>{JSON.stringify(myData, null, 2)}</pre>
                </div>
              )}
            </div>

            {/* Supresión */}
            <div className="card border-red-100 space-y-3">
              <div className="flex items-center gap-2">
                <Trash2 className="h-4 w-4 text-red-600" />
                <h2 className="font-semibold text-gray-900">Eliminar mis datos (Art. 16 LOPDP)</h2>
              </div>
              <p className="text-sm text-gray-600">
                Elimina permanentemente todas tus conversaciones, cálculos de copago e historial de pólizas.
                El proceso es inmediato e irreversible.
              </p>
              <div className="flex items-start gap-2 rounded-lg bg-amber-50 p-3 text-xs text-amber-800">
                <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                <span>El registro de auditoría se mantiene de forma <strong>anónima</strong> por obligación legal (7 años). No contiene datos de salud ni identificadores personales.</span>
              </div>
              <button
                onClick={requestDeletion}
                disabled={deleting}
                className="inline-flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-2 text-sm font-semibold text-red-700 hover:bg-red-100 transition-colors"
              >
                <Trash2 className="h-4 w-4" />
                {deleting ? "Eliminando..." : "Eliminar todos mis datos"}
              </button>
            </div>

            {error && (
              <p className="text-sm text-red-600 bg-red-50 rounded-xl px-4 py-3">{error}</p>
            )}
          </>
        )}

        <div className="card bg-brand-50 border-brand-100 text-sm text-brand-800 space-y-1">
          <div className="flex items-center gap-2">
            <Shield className="h-4 w-4" />
            <strong>Contacto DPO</strong>
          </div>
          <p>Para solicitudes de rectificación u oposición: <strong>privacidad@copayai.ec</strong></p>
          <p>Plazo legal de respuesta: <strong>15 días hábiles</strong> (LOPDP Art. 21).</p>
          <p>Autoridad de control: <strong>DINARDAP</strong> — dinardap.gob.ec</p>
        </div>
      </main>
    </div>
  );
}
