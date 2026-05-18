"use client";

const STATUS_STYLES: Record<string, string> = {
  PENDING:   "bg-amber-100 text-amber-800",
  CONFIRMED: "bg-blue-100 text-blue-800",
  COMPLETED: "bg-green-100 text-green-800",
  CANCELLED: "bg-red-100 text-red-800",
  NO_SHOW:   "bg-gray-100 text-gray-700",
};

const STATUS_LABELS: Record<string, string> = {
  PENDING:   "Pendiente",
  CONFIRMED: "Confirmada",
  COMPLETED: "Completada",
  CANCELLED: "Cancelada",
  NO_SHOW:   "No asistió",
};

interface Appointment {
  id: string;
  specialty: string;
  hospital_name: string;
  scheduled_at: string;
  copay_estimated?: number;
  status: string;
}

interface Props {
  appointment: Appointment;
  onCancel?: (id: string) => void;
  onConfirm?: (id: string) => void;
  showActions?: boolean;
}

export default function AppointmentCard({ appointment, onCancel, onConfirm, showActions = true }: Props) {
  const date = new Date(appointment.scheduled_at);
  const dateStr = date.toLocaleDateString("es-EC", { day: "2-digit", month: "short", year: "numeric" });
  const timeStr = date.toLocaleTimeString("es-EC", { hour: "2-digit", minute: "2-digit" });

  return (
    <div className="card space-y-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-semibold text-gray-900">{appointment.specialty}</p>
          <p className="text-sm text-gray-500">{appointment.hospital_name}</p>
        </div>
        <span className={`text-xs font-semibold rounded-full px-3 py-1 ${STATUS_STYLES[appointment.status] || STATUS_STYLES.PENDING}`}>
          {STATUS_LABELS[appointment.status] || appointment.status}
        </span>
      </div>

      <div className="flex items-center gap-4 text-sm text-gray-600">
        <span>📅 {dateStr}</span>
        <span>🕐 {timeStr}</span>
        {appointment.copay_estimated != null && (
          <span className="font-semibold text-brand-600">💲{appointment.copay_estimated.toFixed(2)}</span>
        )}
      </div>

      {showActions && appointment.status === "CONFIRMED" && (
        <div className="flex gap-2 pt-1">
          {onConfirm && (
            <button
              onClick={() => onConfirm(appointment.id)}
              className="btn-primary text-xs py-1.5 px-3"
            >
              Completar
            </button>
          )}
          {onCancel && (
            <button
              onClick={() => onCancel(appointment.id)}
              className="inline-flex items-center gap-1 rounded-xl border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-semibold text-red-700 hover:bg-red-100 transition-colors"
            >
              Cancelar
            </button>
          )}
        </div>
      )}
    </div>
  );
}
