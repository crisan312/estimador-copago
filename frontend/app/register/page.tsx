"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { UserCheck } from "lucide-react";
import { register, login } from "../lib/auth";
import TopBar from "../components/TopBar";

const ROLES = [
  { value: "PATIENT", label: "Paciente" },
  { value: "STAFF", label: "Recepcionista" },
  { value: "DOCTOR", label: "Médico / Especialista" },
  { value: "ANALYST", label: "Analista de Datos" },
];

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    email: "", password: "", confirmPassword: "",
    role: "PATIENT", phone: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (form.password !== form.confirmPassword) {
      setError("Las contraseñas no coinciden"); return;
    }
    setLoading(true);
    try {
      await register(form.email, form.password, form.role, form.phone || undefined);
      await login(form.email, form.password);
      router.push("/dashboard");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al registrarse");
    } finally {
      setLoading(false);
    }
  };

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm(f => ({ ...f, [k]: e.target.value }));

  return (
    <div className="min-h-screen flex flex-col">
      <TopBar />
      <main className="flex flex-1 items-center justify-center px-4 py-12">
        <div className="w-full max-w-sm space-y-6">
          <div className="text-center space-y-1">
            <div className="flex justify-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-50">
                <UserCheck className="h-6 w-6 text-brand-600" />
              </div>
            </div>
            <h1 className="text-2xl font-bold text-gray-900">Crear cuenta</h1>
            <p className="text-sm text-gray-500">CopayAI — Ecuador</p>
          </div>

          <form onSubmit={handleSubmit} className="card space-y-4">
            <div className="space-y-1">
              <label className="text-sm font-medium text-gray-700">Correo electrónico</label>
              <input type="email" required value={form.email} onChange={set("email")}
                placeholder="tu@email.com"
                className="w-full rounded-xl border border-gray-200 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
            </div>

            <div className="space-y-1">
              <label className="text-sm font-medium text-gray-700">Rol</label>
              <select value={form.role} onChange={set("role")}
                className="w-full rounded-xl border border-gray-200 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500">
                {ROLES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-sm font-medium text-gray-700">
                WhatsApp <span className="text-gray-400">(opcional, +593...)</span>
              </label>
              <input type="tel" value={form.phone} onChange={set("phone")}
                placeholder="+593991234567"
                className="w-full rounded-xl border border-gray-200 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
            </div>

            <div className="space-y-1">
              <label className="text-sm font-medium text-gray-700">Contraseña</label>
              <input type="password" required minLength={8} value={form.password} onChange={set("password")}
                placeholder="Mínimo 8 caracteres"
                className="w-full rounded-xl border border-gray-200 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
            </div>

            <div className="space-y-1">
              <label className="text-sm font-medium text-gray-700">Confirmar contraseña</label>
              <input type="password" required value={form.confirmPassword} onChange={set("confirmPassword")}
                placeholder="••••••••"
                className="w-full rounded-xl border border-gray-200 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
            </div>

            {error && (
              <p className="text-sm text-red-600 bg-red-50 rounded-xl px-4 py-2">{error}</p>
            )}

            <button type="submit" disabled={loading} className="btn-primary w-full justify-center">
              {loading ? "Creando cuenta..." : "Registrarme"}
            </button>
          </form>

          <p className="text-center text-sm text-gray-500">
            ¿Ya tienes cuenta?{" "}
            <Link href="/login" className="text-brand-600 hover:underline font-medium">Inicia sesión</Link>
          </p>
        </div>
      </main>
    </div>
  );
}
