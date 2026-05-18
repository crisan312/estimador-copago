"use client";
import { Suspense, useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Shield } from "lucide-react";
import { login, isAuthenticated } from "../lib/auth";
import TopBar from "../components/TopBar";

// Usuarios demo para evaluación del jurado — contraseña común
const DEMO_PASSWORD = "CopayAdmin2026!";
const DEMO_USERS = [
  { role: "ADMIN", email: "admin@copayai.ec", desc: "Panel completo · audit log" },
  { role: "DPO", email: "dpo@copayai.ec", desc: "Cumplimiento LOPDP · ARCO" },
  { role: "DOCTOR", email: "doctor@copayai.ec", desc: "Citas · KPIs Cardiología" },
  { role: "ANALYST", email: "analista@copayai.ec", desc: "KPIs · precisión · insights" },
  { role: "STAFF", email: "staff@copayai.ec", desc: "Gestión de citas" },
  { role: "PATIENT", email: "paciente@copayai.ec", desc: "Mis datos · mis citas" },
];

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="flex min-h-screen items-center justify-center"><div className="h-6 w-6 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" /></div>}>
      <LoginForm />
    </Suspense>
  );
}

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const next = params.get("next") || "/dashboard";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isAuthenticated()) router.replace(next);
  }, [router, next]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
      router.push(next);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al iniciar sesión");
    } finally {
      setLoading(false);
    }
  };

  // Acceso rápido para el jurado: inicia sesión con un clic
  const quickLogin = async (demoEmail: string) => {
    setError(null);
    setEmail(demoEmail);
    setPassword(DEMO_PASSWORD);
    setLoading(true);
    try {
      await login(demoEmail, DEMO_PASSWORD);
      router.push(next);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al iniciar sesión");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      <TopBar />
      <main className="flex flex-1 items-center justify-center px-4 py-12">
        <div className="w-full max-w-sm space-y-6">
          <div className="text-center space-y-1">
            <div className="flex justify-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-50">
                <Shield className="h-6 w-6 text-brand-600" />
              </div>
            </div>
            <h1 className="text-2xl font-bold text-gray-900">Iniciar sesión</h1>
            <p className="text-sm text-gray-500">CopayAI — Ecuador</p>
          </div>

          <form onSubmit={handleSubmit} className="card space-y-4">
            <div className="space-y-1">
              <label className="text-sm font-medium text-gray-700">Correo electrónico</label>
              <input
                type="email"
                required
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="tu@email.com"
                className="w-full rounded-xl border border-gray-200 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-gray-700">Contraseña</label>
              <input
                type="password"
                required
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full rounded-xl border border-gray-200 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>

            {error && (
              <p className="text-sm text-red-600 bg-red-50 rounded-xl px-4 py-2">{error}</p>
            )}

            <button type="submit" disabled={loading} className="btn-primary w-full justify-center">
              {loading ? "Ingresando..." : "Ingresar"}
            </button>
          </form>

          <p className="text-center text-sm text-gray-500">
            ¿No tienes cuenta?{" "}
            <Link href="/register" className="text-brand-600 hover:underline font-medium">
              Regístrate
            </Link>
          </p>

          {/* ── Acceso rápido para el jurado ──────────────────────────── */}
          <div className="card space-y-3 border-brand-100 bg-brand-50/40">
            <div className="text-center">
              <p className="text-sm font-semibold text-gray-800">
                Acceso rápido — Jurado hackIAthon
              </p>
              <p className="text-xs text-gray-500">
                Selecciona un rol para ingresar con un clic
              </p>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {DEMO_USERS.map(u => (
                <button
                  key={u.email}
                  type="button"
                  disabled={loading}
                  onClick={() => quickLogin(u.email)}
                  className="rounded-xl border border-brand-200 bg-white px-3 py-2 text-left transition hover:border-brand-400 hover:bg-brand-50 disabled:opacity-50"
                >
                  <span className="block text-sm font-semibold text-brand-700">{u.role}</span>
                  <span className="block text-[11px] leading-tight text-gray-500">{u.desc}</span>
                </button>
              ))}
            </div>
            <p className="text-center text-[11px] text-gray-400">
              Contraseña común: <code className="font-mono">{DEMO_PASSWORD}</code>
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
