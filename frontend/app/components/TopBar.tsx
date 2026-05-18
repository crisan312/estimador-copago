"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { HelpCircle, Pill, LogOut, LayoutDashboard, Calendar, TrendingUp, Shield, ChevronDown } from "lucide-react";
import { getUser, logout, AuthUser, ROLE_LABELS, ROLE_COLORS } from "../lib/auth";

const NAV_BY_ROLE: Record<string, { href: string; label: string }[]> = {
  PATIENT:  [{ href: "/chat", label: "Nueva consulta" }, { href: "/appointments", label: "Mis citas" }],
  STAFF:    [{ href: "/chat", label: "Consulta" }, { href: "/appointments", label: "Citas" }],
  DOCTOR:   [{ href: "/appointments", label: "Citas" }, { href: "/dashboard", label: "Dashboard" }],
  ANALYST:  [{ href: "/dashboard", label: "Dashboard" }, { href: "/recommendations", label: "IA Insights" }],
  ADMIN:    [{ href: "/dashboard", label: "Dashboard" }, { href: "/appointments", label: "Citas" }, { href: "/recommendations", label: "IA" }, { href: "/admin", label: "Admin" }],
  DPO:      [{ href: "/dashboard", label: "Dashboard" }, { href: "/admin", label: "Compliance" }],
};

export default function TopBar() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const router = useRouter();

  useEffect(() => {
    setUser(getUser());
  }, []);

  const handleLogout = async () => {
    await logout();
    setUser(null);
    setMenuOpen(false);
    router.push("/login");
  };

  const navLinks = user ? (NAV_BY_ROLE[user.role] || []) : [
    { href: "/", label: "Inicio" },
    { href: "/chat", label: "Nueva consulta" },
  ];

  return (
    <header className="sticky top-0 z-40 border-b border-gray-100 bg-white/80 backdrop-blur-sm">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
        <Link href={user ? "/dashboard" : "/"} className="flex items-center gap-2 font-bold text-brand-700">
          <Pill className="h-5 w-5" />
          CopayAI
        </Link>

        <nav className="hidden items-center gap-5 text-sm font-medium text-gray-600 sm:flex">
          {navLinks.map(l => (
            <Link key={l.href} href={l.href} className="hover:text-brand-700 transition-colors">
              {l.label}
            </Link>
          ))}
          <Link href="/help" className="hover:text-brand-700 transition-colors">Ayuda</Link>
        </nav>

        <div className="flex items-center gap-2">
          {user ? (
            <div className="relative">
              <button
                onClick={() => setMenuOpen(!menuOpen)}
                className="flex items-center gap-2 rounded-xl border border-gray-200 px-3 py-1.5 text-sm hover:bg-gray-50 transition-colors"
              >
                <span className={`text-xs font-semibold rounded-full px-2 py-0.5 ${ROLE_COLORS[user.role]}`}>
                  {ROLE_LABELS[user.role]}
                </span>
                <span className="hidden sm:inline text-gray-700 max-w-[120px] truncate">{user.email}</span>
                <ChevronDown className="h-3.5 w-3.5 text-gray-400" />
              </button>

              {menuOpen && (
                <div className="absolute right-0 mt-2 w-52 rounded-2xl border border-gray-100 bg-white shadow-xl overflow-hidden z-50">
                  <div className="px-4 py-3 border-b border-gray-50">
                    <p className="text-xs font-semibold text-gray-500 truncate">{user.email}</p>
                    <p className="text-xs text-gray-400">{ROLE_LABELS[user.role]}</p>
                  </div>
                  <div className="p-1.5 space-y-0.5">
                    <MenuItem href="/dashboard" icon={<LayoutDashboard className="h-3.5 w-3.5" />} label="Dashboard" onClick={() => setMenuOpen(false)} />
                    <MenuItem href="/appointments" icon={<Calendar className="h-3.5 w-3.5" />} label="Citas" onClick={() => setMenuOpen(false)} />
                    {["ANALYST", "ADMIN"].includes(user.role) && (
                      <MenuItem href="/recommendations" icon={<TrendingUp className="h-3.5 w-3.5" />} label="IA Insights" onClick={() => setMenuOpen(false)} />
                    )}
                    {["ADMIN", "DPO"].includes(user.role) && (
                      <MenuItem href="/admin" icon={<Shield className="h-3.5 w-3.5" />} label="Administración" onClick={() => setMenuOpen(false)} />
                    )}
                    <MenuItem href="/mis-datos" icon={<HelpCircle className="h-3.5 w-3.5" />} label="Mis datos (ARCO)" onClick={() => setMenuOpen(false)} />
                  </div>
                  <div className="border-t border-gray-50 p-1.5">
                    <button onClick={handleLogout}
                      className="w-full flex items-center gap-2 rounded-xl px-3 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors">
                      <LogOut className="h-3.5 w-3.5" />
                      Cerrar sesión
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Link href="/login" className="text-sm font-medium text-gray-600 hover:text-brand-700 transition-colors">Ingresar</Link>
              <Link href="/register" className="btn-primary text-xs py-1.5 px-3">Registrarse</Link>
            </div>
          )}
        </div>
      </div>

      {/* Overlay para cerrar menú */}
      {menuOpen && (
        <div className="fixed inset-0 z-30" onClick={() => setMenuOpen(false)} />
      )}
    </header>
  );
}

function MenuItem({ href, icon, label, onClick }: {
  href: string; icon: React.ReactNode; label: string; onClick: () => void;
}) {
  return (
    <Link href={href} onClick={onClick}
      className="flex items-center gap-2 rounded-xl px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors">
      <span className="text-gray-400">{icon}</span>
      {label}
    </Link>
  );
}
