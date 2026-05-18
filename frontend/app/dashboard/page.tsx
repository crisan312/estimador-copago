"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  Activity, Calendar, DollarSign, Users, Shield,
  TrendingUp, AlertTriangle, BarChart3,
} from "lucide-react";
import TopBar from "../components/TopBar";
import KPICard from "../components/KPICard";
import RoleGuard from "../components/RoleGuard";
import { getUser, fetchWithAuth, AuthUser, ROLE_LABELS } from "../lib/auth";

const ALL_ROLES = ["PATIENT", "STAFF", "DOCTOR", "ANALYST", "ADMIN", "DPO"];

export default function DashboardPage() {
  return (
    <RoleGuard allowedRoles={ALL_ROLES}>
      <DashboardContent />
    </RoleGuard>
  );
}

function DashboardContent() {
  const [kpis, setKpis] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    const u = getUser();
    setUser(u);
    fetchWithAuth("/api/v1/kpi/me")
      .then(r => r.json())
      .then(setKpis)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen flex flex-col">
      <TopBar />
      <main className="mx-auto w-full max-w-5xl px-4 py-8 space-y-6">
        <header className="space-y-1">
          <h1 className="text-2xl font-bold text-gray-900">
            Dashboard — {user ? ROLE_LABELS[user.role] : ""}
          </h1>
          <p className="text-sm text-gray-500">
            {user?.email} · {new Date().toLocaleDateString("es-EC", { weekday: "long", day: "numeric", month: "long" })}
          </p>
        </header>

        {loading ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-28 rounded-2xl bg-gray-100 animate-pulse" />
            ))}
          </div>
        ) : kpis ? (
          <KPIGrid kpis={kpis} role={user?.role || "PATIENT"} />
        ) : (
          <p className="text-sm text-gray-500">No se pudieron cargar los KPIs.</p>
        )}

        {/* Quick actions */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <QuickCard href="/chat" icon={<Activity className="h-5 w-5" />} title="Nueva consulta" desc="Estima tu copago médico con IA" color="blue" />
          <QuickCard href="/appointments" icon={<Calendar className="h-5 w-5" />} title="Mis citas" desc="Ver y gestionar tus citas" color="green" />
          {(user?.role === "ANALYST" || user?.role === "ADMIN") && (
            <QuickCard href="/recommendations" icon={<TrendingUp className="h-5 w-5" />} title="Recomendaciones IA" desc="Insights del sistema" color="purple" />
          )}
          {(user?.role === "ADMIN" || user?.role === "DPO") && (
            <QuickCard href="/admin" icon={<Shield className="h-5 w-5" />} title="Administración" desc="Usuarios, auditoría, ARCO" color="red" />
          )}
          <QuickCard href="/mis-datos" icon={<Users className="h-5 w-5" />} title="Mis datos (ARCO)" desc="Ejerce tus derechos LOPDP" color="gray" />
        </div>
      </main>
    </div>
  );
}

function KPIGrid({ kpis, role }: { kpis: Record<string, unknown>; role: string }) {
  if (role === "PATIENT") {
    const s = kpis.summary as Record<string, number> || {};
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPICard title="Consultas completadas" value={s.completed_consultations ?? 0} color="green" icon={<Activity className="h-4 w-4" />} />
        <KPICard title="Citas próximas" value={s.upcoming_appointments ?? 0} color="blue" icon={<Calendar className="h-4 w-4" />} />
        <KPICard title="Gasto total copagos" value={`$${(s.total_copay_usd ?? 0).toFixed(2)}`} color="amber" icon={<DollarSign className="h-4 w-4" />} />
        <KPICard title="Copago promedio" value={`$${(s.avg_copay_usd ?? 0).toFixed(2)}`} color="purple" icon={<BarChart3 className="h-4 w-4" />} />
      </div>
    );
  }

  if (role === "STAFF") {
    const t = kpis.today as Record<string, number> || {};
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPICard title="Confirmadas hoy" value={t.confirmed ?? 0} color="blue" />
        <KPICard title="Completadas hoy" value={t.completed ?? 0} color="green" />
        <KPICard title="No asistieron" value={t.no_show ?? 0} color="red" />
        <KPICard title="Solicitudes ARCO" value={(kpis.pending_arco_requests as number) ?? 0} color="amber" icon={<AlertTriangle className="h-4 w-4" />} />
      </div>
    );
  }

  if (role === "ANALYST" || role === "ADMIN") {
    const rate = (kpis.chatbot_completion_rate_7d as number) ?? 0;
    const token = kpis.token_usage_7d as Record<string, number> || {};
    const system = kpis.system as Record<string, unknown> || {};
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPICard title="Tasa completación 7d" value={`${rate}%`} color="green" icon={<TrendingUp className="h-4 w-4" />} />
        <KPICard title="Tokens usados 7d" value={(token.total ?? 0).toLocaleString()} subtitle={`~$${token.estimated_cost_usd ?? 0} USD`} color="blue" />
        {role === "ADMIN" && !!system.users_by_role && (
          <KPICard title="Usuarios activos" value={Object.values(system.users_by_role as Record<string, number>).reduce((a, b) => a + b, 0)} color="purple" icon={<Users className="h-4 w-4" />} />
        )}
        {role === "ADMIN" && (
          <KPICard title="Solicitudes ARCO" value={(system.pending_arco_deletions as number) ?? 0} color="amber" icon={<AlertTriangle className="h-4 w-4" />} />
        )}
      </div>
    );
  }

  if (role === "DPO") {
    const c = kpis.consent_status as Record<string, number> || {};
    const a = kpis.arco_requests as Record<string, number> || {};
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPICard title="Consentimientos activos" value={c.active ?? 0} color="green" icon={<Shield className="h-4 w-4" />} />
        <KPICard title="Consentimientos retirados" value={c.withdrawn ?? 0} color="gray" />
        <KPICard title="Solicitudes ARCO pendientes" value={a.pending ?? 0} color="amber" icon={<AlertTriangle className="h-4 w-4" />} />
        <KPICard title="Accesos a datos sensibles 24h" value={(kpis.sensitive_data_accesses_24h as number) ?? 0} color="red" />
      </div>
    );
  }

  return null;
}

function QuickCard({ href, icon, title, desc, color }: {
  href: string; icon: React.ReactNode; title: string; desc: string;
  color: "blue" | "green" | "purple" | "red" | "gray" | "amber";
}) {
  const colors = {
    blue: "bg-blue-50 hover:bg-blue-100 text-blue-700 border-blue-100",
    green: "bg-green-50 hover:bg-green-100 text-green-700 border-green-100",
    purple: "bg-purple-50 hover:bg-purple-100 text-purple-700 border-purple-100",
    red: "bg-red-50 hover:bg-red-100 text-red-700 border-red-100",
    gray: "bg-gray-50 hover:bg-gray-100 text-gray-700 border-gray-100",
    amber: "bg-amber-50 hover:bg-amber-100 text-amber-700 border-amber-100",
  };
  return (
    <a href={href} className={`rounded-2xl border p-5 space-y-2 transition-colors ${colors[color]}`}>
      <div className="flex items-center gap-2">
        {icon}
        <span className="font-semibold text-sm">{title}</span>
      </div>
      <p className="text-xs opacity-70">{desc}</p>
    </a>
  );
}
