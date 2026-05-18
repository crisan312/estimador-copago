const BASE = process.env.NEXT_PUBLIC_API_URL || "";
const ACCESS_KEY = "copay_access";
const REFRESH_KEY = "copay_refresh";
const USER_KEY = "copay_user";

export interface AuthUser {
  user_id: string;
  email: string;
  role: "PATIENT" | "STAFF" | "DOCTOR" | "ANALYST" | "ADMIN" | "DPO";
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACCESS_KEY);
}

export function getUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function saveTokens(accessToken: string, refreshToken: string, user: AuthUser) {
  localStorage.setItem(ACCESS_KEY, accessToken);
  localStorage.setItem(REFRESH_KEY, refreshToken);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
  localStorage.removeItem(USER_KEY);
}

export function isAuthenticated(): boolean {
  return !!getAccessToken();
}

export async function login(email: string, password: string): Promise<AuthUser> {
  const res = await fetch(`${BASE}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Credenciales inválidas");
  }
  const data = await res.json();
  const user: AuthUser = { user_id: data.user_id, email, role: data.role };
  saveTokens(data.access_token, data.refresh_token, user);
  return user;
}

export async function register(email: string, password: string, role = "PATIENT", phone?: string) {
  const res = await fetch(`${BASE}/api/v1/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, role, phone_whatsapp: phone || undefined }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Error al registrarse");
  }
  return res.json();
}

export async function logout() {
  const refresh = localStorage.getItem(REFRESH_KEY);
  const access = getAccessToken();
  if (refresh && access) {
    await fetch(`${BASE}/api/v1/auth/logout`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${access}` },
      body: JSON.stringify({ refresh_token: refresh }),
    }).catch(() => {});
  }
  clearTokens();
}

export async function fetchWithAuth(url: string, init: RequestInit = {}): Promise<Response> {
  const token = getAccessToken();
  const headers = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string>),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
  return fetch(`${BASE}${url}`, { ...init, headers });
}

export const ROLE_LABELS: Record<string, string> = {
  PATIENT: "Paciente",
  STAFF: "Recepcionista",
  DOCTOR: "Médico",
  ANALYST: "Analista",
  ADMIN: "Administrador",
  DPO: "DPO",
};

export const ROLE_COLORS: Record<string, string> = {
  PATIENT: "bg-blue-100 text-blue-800",
  STAFF: "bg-green-100 text-green-800",
  DOCTOR: "bg-purple-100 text-purple-800",
  ANALYST: "bg-amber-100 text-amber-800",
  ADMIN: "bg-red-100 text-red-800",
  DPO: "bg-gray-100 text-gray-800",
};
