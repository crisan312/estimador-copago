"use client";
import { useState, useEffect } from "react";
import { Shield, Users, FileText, CheckCircle, XCircle, AlertTriangle } from "lucide-react";
import TopBar from "../components/TopBar";
import RoleGuard from "../components/RoleGuard";
import { fetchWithAuth, ROLE_LABELS, ROLE_COLORS } from "../lib/auth";

export default function AdminPage() {
  return (
    <RoleGuard allowedRoles={["ADMIN", "DPO"]}>
      <AdminContent />
    </RoleGuard>
  );
}

type Tab = "users" | "audit" | "arco";

interface User {
  user_id: string; email: string; role: string; is_active: boolean;
  has_whatsapp: boolean; last_login_at: string | null; created_at: string;
}

interface AuditEntry {
  id: number; event_type: string; resource: string;
  resource_id: string; details: Record<string, unknown>; created_at: string;
}

interface ArcoRequest {
  id: string; reason: string; status: string;
  requested_at: string; processed_at: string | null;
}

function AdminContent() {
  const [tab, setTab] = useState<Tab>("users");
  const [users, setUsers] = useState<User[]>([]);
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [arco, setArco] = useState<ArcoRequest[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    if (tab === "users") {
      fetchWithAuth("/api/v1/admin/users").then(r => r.json()).then(setUsers).finally(() => setLoading(false));
    } else if (tab === "audit") {
      fetchWithAuth("/api/v1/admin/audit-log?limit=50").then(r => r.json()).then(setAudit).finally(() => setLoading(false));
    } else {
      fetchWithAuth("/api/v1/admin/arco-requests").then(r => r.json()).then(setArco).finally(() => setLoading(false));
    }
  }, [tab]);

  const processArco = async (id: string, status: "COMPLETED" | "REJECTED") => {
    await fetchWithAuth(`/api/v1/admin/arco-requests/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
    setArco(prev => prev.map(r => r.id === id ? { ...r, status, processed_at: new Date().toISOString() } : r));
  };

  const toggleUserActive = async (userId: string, isActive: boolean) => {
    await fetchWithAuth(`/api/v1/admin/users/${userId}`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: !isActive }),
    });
    setUsers(prev => prev.map(u => u.user_id === userId ? { ...u, is_active: !isActive } : u));
  };

  return (
    <div className="min-h-screen flex flex-col">
      <TopBar />
      <main className="mx-auto w-full max-w-5xl px-4 py-8 space-y-6">
        <header className="flex items-center gap-2">
          <Shield className="h-6 w-6 text-brand-600" />
          <h1 className="text-2xl font-bold text-gray-900">Administración</h1>
        </header>

        <div className="flex gap-1 border-b border-gray-200">
          {(["users", "audit", "arco"] as Tab[]).map(t => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                tab === t ? "border-brand-600 text-brand-700" : "border-transparent text-gray-500 hover:text-gray-700"
              }`}>
              {t === "users" ? <><Users className="h-4 w-4 inline mr-1" />Usuarios</>
               : t === "audit" ? <><FileText className="h-4 w-4 inline mr-1" />Auditoría</>
               : <><AlertTriangle className="h-4 w-4 inline mr-1" />ARCO</>}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => <div key={i} className="h-14 rounded-xl bg-gray-100 animate-pulse" />)}
          </div>
        ) : tab === "users" ? (
          <div className="space-y-2">
            {users.map(u => (
              <div key={u.user_id} className="card flex items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{u.email}</p>
                    <p className="text-xs text-gray-400">
                      {u.last_login_at ? `Último acceso: ${new Date(u.last_login_at).toLocaleDateString("es-EC")}` : "Sin accesos"}
                    </p>
                  </div>
                  <span className={`text-xs font-semibold rounded-full px-2 py-0.5 ${ROLE_COLORS[u.role]}`}>
                    {ROLE_LABELS[u.role] || u.role}
                  </span>
                  {u.has_whatsapp && <span className="text-xs text-green-600 font-medium">📱 WA</span>}
                </div>
                <button
                  onClick={() => toggleUserActive(u.user_id, u.is_active)}
                  className={`text-xs font-semibold rounded-full px-3 py-1 transition-colors ${
                    u.is_active ? "bg-green-100 text-green-700 hover:bg-red-100 hover:text-red-700" : "bg-gray-100 text-gray-500 hover:bg-green-100 hover:text-green-700"
                  }`}>
                  {u.is_active ? "Activo" : "Inactivo"}
                </button>
              </div>
            ))}
          </div>
        ) : tab === "audit" ? (
          <div className="space-y-2">
            {audit.map(entry => (
              <div key={entry.id} className="rounded-xl bg-gray-50 border border-gray-100 px-4 py-3 flex items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-semibold text-brand-700">{entry.event_type}</span>
                    <span className="text-xs text-gray-400">→ {entry.resource}</span>
                  </div>
                  {entry.details && (
                    <p className="text-xs text-gray-500 mt-0.5 font-mono">
                      {JSON.stringify(entry.details).slice(0, 80)}
                    </p>
                  )}
                </div>
                <span className="text-xs text-gray-400 shrink-0">
                  {new Date(entry.created_at).toLocaleString("es-EC")}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div className="space-y-3">
            {arco.length === 0 && (
              <div className="card text-center py-10 text-gray-400">
                <CheckCircle className="h-8 w-8 mx-auto mb-2 opacity-40" />
                <p className="text-sm">No hay solicitudes ARCO pendientes</p>
              </div>
            )}
            {arco.map(req => (
              <div key={req.id} className="card space-y-2">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{req.reason || "Sin motivo especificado"}</p>
                    <p className="text-xs text-gray-400">{new Date(req.requested_at).toLocaleString("es-EC")}</p>
                  </div>
                  <span className={`text-xs font-semibold rounded-full px-3 py-1 ${
                    req.status === "PENDING" ? "bg-amber-100 text-amber-700" :
                    req.status === "COMPLETED" ? "bg-green-100 text-green-700" :
                    "bg-red-100 text-red-700"
                  }`}>{req.status}</span>
                </div>
                {req.status === "PENDING" && (
                  <div className="flex gap-2">
                    <button onClick={() => processArco(req.id, "COMPLETED")}
                      className="inline-flex items-center gap-1 rounded-xl bg-green-50 border border-green-200 px-3 py-1.5 text-xs font-semibold text-green-700 hover:bg-green-100 transition-colors">
                      <CheckCircle className="h-3 w-3" /> Aprobar supresión
                    </button>
                    <button onClick={() => processArco(req.id, "REJECTED")}
                      className="inline-flex items-center gap-1 rounded-xl bg-red-50 border border-red-200 px-3 py-1.5 text-xs font-semibold text-red-700 hover:bg-red-100 transition-colors">
                      <XCircle className="h-3 w-3" /> Rechazar
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
