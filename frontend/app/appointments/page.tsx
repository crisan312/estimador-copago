"use client";
import { useState, useEffect, useCallback } from "react";
import { Calendar, Plus } from "lucide-react";
import TopBar from "../components/TopBar";
import AppointmentCard from "../components/AppointmentCard";
import RoleGuard from "../components/RoleGuard";
import { fetchWithAuth, getUser } from "../lib/auth";

const ALL_ROLES = ["PATIENT", "STAFF", "DOCTOR", "ADMIN"];

interface Appointment {
  id: string; specialty: string; hospital_name: string;
  scheduled_at: string; copay_estimated?: number; status: string;
}

export default function AppointmentsPage() {
  return (
    <RoleGuard allowedRoles={ALL_ROLES}>
      <AppointmentsContent />
    </RoleGuard>
  );
}

function AppointmentsContent() {
  const user = getUser();
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    specialty: "", hospital_name: "", scheduled_at: "", copay_estimated: "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadAppointments = useCallback(async () => {
    setLoading(true);
    const params = statusFilter ? `?status_filter=${statusFilter}` : "";
    const res = await fetchWithAuth(`/api/v1/appointments${params}`);
    if (res.ok) setAppointments(await res.json());
    setLoading(false);
  }, [statusFilter]);

  useEffect(() => { loadAppointments(); }, [loadAppointments]);

  const handleStatusChange = async (id: string, status: string) => {
    await fetchWithAuth(`/api/v1/appointments/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
    loadAppointments();
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const res = await fetchWithAuth("/api/v1/appointments", {
        method: "POST",
        body: JSON.stringify({
          ...form,
          copay_estimated: form.copay_estimated ? parseFloat(form.copay_estimated) : undefined,
          scheduled_at: new Date(form.scheduled_at).toISOString(),
        }),
      });
      if (!res.ok) throw new Error((await res.json()).detail || "Error al crear cita");
      setShowForm(false);
      setForm({ specialty: "", hospital_name: "", scheduled_at: "", copay_estimated: "" });
      loadAppointments();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error desconocido");
    } finally {
      setSaving(false);
    }
  };

  const setF = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm(f => ({ ...f, [k]: e.target.value }));

  return (
    <div className="min-h-screen flex flex-col">
      <TopBar />
      <main className="mx-auto w-full max-w-3xl px-4 py-8 space-y-6">
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Calendar className="h-6 w-6 text-brand-600" />
            <h1 className="text-2xl font-bold text-gray-900">Citas médicas</h1>
          </div>
          <button onClick={() => setShowForm(!showForm)} className="btn-primary">
            <Plus className="h-4 w-4" /> Nueva cita
          </button>
        </header>

        {showForm && (
          <form onSubmit={handleCreate} className="card space-y-4">
            <h2 className="font-semibold text-gray-900">Agendar cita</h2>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs font-medium text-gray-600">Especialidad</label>
                <input required value={form.specialty} onChange={setF("specialty")}
                  placeholder="Cardiología, Medicina General..."
                  className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-gray-600">Hospital</label>
                <input required value={form.hospital_name} onChange={setF("hospital_name")}
                  placeholder="Hospital Vozandes..."
                  className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-gray-600">Fecha y hora</label>
                <input required type="datetime-local" value={form.scheduled_at} onChange={setF("scheduled_at")}
                  className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-gray-600">Copago estimado (USD)</label>
                <input type="number" step="0.01" value={form.copay_estimated} onChange={setF("copay_estimated")}
                  placeholder="0.00"
                  className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
              </div>
            </div>
            {error && <p className="text-sm text-red-600 bg-red-50 rounded-xl px-4 py-2">{error}</p>}
            <div className="flex gap-2">
              <button type="submit" disabled={saving} className="btn-primary">{saving ? "Guardando..." : "Confirmar cita"}</button>
              <button type="button" onClick={() => setShowForm(false)} className="btn-secondary">Cancelar</button>
            </div>
          </form>
        )}

        {/* Filtros */}
        <div className="flex gap-2 flex-wrap">
          {["", "CONFIRMED", "PENDING", "COMPLETED", "CANCELLED"].map(s => (
            <button key={s} onClick={() => setStatusFilter(s)}
              className={`rounded-full px-4 py-1.5 text-xs font-semibold border transition-colors ${
                statusFilter === s
                  ? "bg-brand-600 text-white border-brand-600"
                  : "bg-white text-gray-600 border-gray-200 hover:border-brand-400"
              }`}>
              {s === "" ? "Todas" : s === "CONFIRMED" ? "Confirmadas" : s === "PENDING" ? "Pendientes" : s === "COMPLETED" ? "Completadas" : "Canceladas"}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="space-y-3">
            {[...Array(3)].map((_, i) => <div key={i} className="h-24 rounded-2xl bg-gray-100 animate-pulse" />)}
          </div>
        ) : appointments.length === 0 ? (
          <div className="card text-center py-10 text-gray-400">
            <Calendar className="h-8 w-8 mx-auto mb-2 opacity-40" />
            <p className="text-sm">No hay citas en este filtro</p>
          </div>
        ) : (
          <div className="space-y-3">
            {appointments.map(appt => (
              <AppointmentCard
                key={appt.id}
                appointment={appt}
                showActions={["STAFF", "ADMIN", "DOCTOR"].includes(user?.role || "")}
                onCancel={id => handleStatusChange(id, "CANCELLED")}
                onConfirm={id => handleStatusChange(id, "COMPLETED")}
              />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
