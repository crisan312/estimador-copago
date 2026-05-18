"use client";
import { useRouter } from "next/navigation";
import { Play } from "lucide-react";

export default function DemoButton() {
  const router = useRouter();
  return (
    <button
      onClick={() => router.push("/chat?demo=1")}
      className="btn-secondary"
    >
      <Play className="h-4 w-4 text-brand-600" />
      Demo en vivo
    </button>
  );
}
