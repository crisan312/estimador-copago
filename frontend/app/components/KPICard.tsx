interface KPICardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: { value: number; label: string };
  color?: "blue" | "green" | "amber" | "red" | "purple" | "gray";
  icon?: React.ReactNode;
}

const colorMap = {
  blue:   "bg-blue-50 border-blue-100 text-blue-700",
  green:  "bg-green-50 border-green-100 text-green-700",
  amber:  "bg-amber-50 border-amber-100 text-amber-700",
  red:    "bg-red-50 border-red-100 text-red-700",
  purple: "bg-purple-50 border-purple-100 text-purple-700",
  gray:   "bg-gray-50 border-gray-100 text-gray-700",
};

export default function KPICard({
  title, value, subtitle, trend, color = "blue", icon,
}: KPICardProps) {
  const cls = colorMap[color];
  return (
    <div className={`rounded-2xl border p-5 space-y-2 ${cls}`}>
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wide opacity-70">{title}</p>
        {icon && <span className="opacity-60">{icon}</span>}
      </div>
      <p className="text-3xl font-bold">{value}</p>
      {subtitle && <p className="text-xs opacity-70">{subtitle}</p>}
      {trend && (
        <div className={`flex items-center gap-1 text-xs font-medium ${trend.value >= 0 ? "text-green-700" : "text-red-700"}`}>
          <span>{trend.value >= 0 ? "▲" : "▼"}</span>
          <span>{Math.abs(trend.value)}% {trend.label}</span>
        </div>
      )}
    </div>
  );
}
