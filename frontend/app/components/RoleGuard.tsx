"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getUser, AuthUser } from "../lib/auth";

interface Props {
  allowedRoles: string[];
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export default function RoleGuard({ allowedRoles, children, fallback }: Props) {
  const [user, setUser] = useState<AuthUser | null | undefined>(undefined);
  const router = useRouter();

  useEffect(() => {
    const u = getUser();
    setUser(u);
    if (!u) {
      router.replace(`/login?next=${encodeURIComponent(window.location.pathname)}`);
    }
  }, [router]);

  if (user === undefined) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" />
      </div>
    );
  }

  if (!user || !allowedRoles.includes(user.role)) {
    return fallback ? (
      <>{fallback}</>
    ) : (
      <div className="flex min-h-screen items-center justify-center">
        <div className="card max-w-sm text-center space-y-2">
          <p className="text-lg font-semibold text-gray-900">Acceso restringido</p>
          <p className="text-sm text-gray-500">
            Tu rol <strong>{user?.role}</strong> no tiene permiso para ver esta página.
          </p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
