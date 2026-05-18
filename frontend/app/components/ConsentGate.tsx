"use client";
import { useState, useEffect, useCallback } from "react";
import ConsentModal from "./ConsentModal";

const BASE = process.env.NEXT_PUBLIC_API_URL || "";

function getSessionId(): string {
  if (typeof window === "undefined") return "";
  let id = sessionStorage.getItem("copay_session");
  if (!id) {
    id = crypto.randomUUID();
    sessionStorage.setItem("copay_session", id);
  }
  return id;
}

async function checkConsent(): Promise<boolean> {
  try {
    const res = await fetch(`${BASE}/api/v1/consent/status`, {
      headers: { "X-Session-Id": getSessionId() },
    });
    const data = await res.json();
    return data.consented === true;
  } catch {
    return false;
  }
}

async function giveConsent(): Promise<boolean> {
  try {
    const res = await fetch(`${BASE}/api/v1/consent`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Session-Id": getSessionId(),
      },
      body: JSON.stringify({ accepted: true }),
    });
    return res.ok;
  } catch {
    return false;
  }
}

export default function ConsentGate({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<"loading" | "consented" | "pending">("loading");

  useEffect(() => {
    checkConsent().then((ok) => setStatus(ok ? "consented" : "pending"));
  }, []);

  const handleAccept = useCallback(async () => {
    const ok = await giveConsent();
    if (ok) setStatus("consented");
  }, []);

  const handleDecline = useCallback(() => {
    window.location.href = "https://www.google.com";
  }, []);

  if (status === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" />
      </div>
    );
  }

  return (
    <>
      {status === "pending" && (
        <ConsentModal onAccept={handleAccept} onDecline={handleDecline} />
      )}
      {children}
    </>
  );
}
