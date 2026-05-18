import type { Metadata } from "next";
import "./globals.css";
import ConsentGate from "./components/ConsentGate";

export const metadata: Metadata = {
  title: "CopayAI — ¿Cuánto pagaré por mi consulta?",
  description: "Estimador agéntico de copago y cobertura médica para Ecuador",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body className="min-h-screen bg-gray-50">
        <ConsentGate>{children}</ConsentGate>
      </body>
    </html>
  );
}
