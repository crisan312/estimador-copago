import { Suspense } from "react";
import { Metadata } from "next";
import TopBar from "../components/TopBar";
import HelpDrawer from "../components/HelpDrawer";
import ChatClient from "./ChatClient";

export const metadata: Metadata = { title: "CopayAI — Consulta" };

export default function ChatPage() {
  return (
    <div className="flex h-screen flex-col">
      <TopBar />
      <Suspense fallback={<div className="flex-1 flex items-center justify-center text-gray-400">Cargando...</div>}>
        <ChatClient />
      </Suspense>
      <HelpDrawer />
    </div>
  );
}
