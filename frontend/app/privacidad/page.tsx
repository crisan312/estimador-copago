import { Metadata } from "next";
import TopBar from "../components/TopBar";
import { Shield, Lock, Database, UserCheck, Mail, Clock } from "lucide-react";

export const metadata: Metadata = {
  title: "CopayAI — Aviso de Privacidad",
  description: "Política de privacidad y protección de datos personales — LOPDP Ecuador",
};

const sections = [
  {
    icon: Shield,
    title: "1. Responsable del tratamiento",
    content: [
      "**Denominación:** CopayAI — hackIAthon Viamatica",
      "**DPO (Delegado de Protección de Datos):** privacidad@copayai.ec",
      "**Marco legal:** Ley Orgánica de Protección de Datos Personales (LOPDP), publicada en el Registro Oficial Suplemento No. 459 del 26 de mayo de 2021.",
    ],
  },
  {
    icon: Database,
    title: "2. Datos que tratamos",
    content: [
      "**Datos de salud (SENSIBLES — Art. 26 LOPDP):** síntomas, malestares y condiciones de salud que describes en la conversación.",
      "**Datos de seguro:** número de póliza, plan, deducible y cobertura.",
      "**Datos de sesión:** identificador de sesión (anonimizado, sin vinculación a tu identidad real).",
      "**Datos técnicos:** hash de IP (SHA-256, no reversible), hash de User-Agent.",
    ],
  },
  {
    icon: UserCheck,
    title: "3. Base legal del tratamiento",
    content: [
      "**Consentimiento explícito** (LOPDP Art. 7): otorgado de forma libre, específica, informada e inequívoca antes de cualquier procesamiento.",
      "El tratamiento de datos de salud requiere consentimiento explícito por ser datos sensibles (Art. 26).",
      "Puedes retirar tu consentimiento en cualquier momento sin que ello afecte la licitud del tratamiento previo.",
    ],
  },
  {
    icon: Clock,
    title: "4. Finalidades y retención",
    content: [
      "**Finalidad 1 — Estimación de copago:** calcular cuánto pagarás por una consulta médica con tu seguro.",
      "**Finalidad 2 — Recomendación de especialidad:** identificar qué tipo de médico necesitas.",
      "**Finalidad 3 — Ranking de hospitales:** mostrarte los hospitales más económicos para ti.",
      "**Retención:** 90 días desde la creación de la conversación. Los datos se eliminan automáticamente al expirar.",
      "**Auditoría:** el registro de auditoría se conserva 7 años en forma anonimizada (obligación SSyP Res. JB-2012-2248).",
    ],
  },
  {
    icon: Lock,
    title: "5. Seguridad y cifrado",
    content: [
      "**Cifrado en reposo:** todos los datos sensibles (síntomas, póliza) se cifran con AES-128-CBC (Fernet) antes de persistir.",
      "**Cifrado en tránsito:** HTTPS/TLS 1.3 en producción.",
      "**Pseudonimización:** los identificadores de sesión se almacenan como SHA-256 (no reversible).",
      "**Audit log inmutable:** el registro de accesos no puede ser modificado ni eliminado (reglas PostgreSQL).",
      "**No PII en logs:** los logs de acceso nunca contienen datos personales en claro.",
    ],
  },
  {
    icon: UserCheck,
    title: "6. Tus derechos ARCO (Arts. 14-19 LOPDP)",
    content: [
      "**Acceso:** obtén una copia de todos tus datos → GET /api/v1/my-data",
      "**Rectificación:** corrección de datos inexactos → contacta al DPO",
      "**Cancelación/Supresión:** elimina todos tus datos → DELETE /api/v1/my-data",
      "**Oposición:** retira tu consentimiento → DELETE /api/v1/consent",
      "**Plazo de respuesta:** 15 días hábiles (Art. 21 LOPDP). El sistema responde de forma inmediata.",
      "**Autoridad de control:** DINARDAP — www.dinardap.gob.ec",
    ],
  },
  {
    icon: Mail,
    title: "7. Transferencias internacionales",
    content: [
      "**No realizamos transferencias internacionales** de datos personales.",
      "La API de inteligencia artificial (Anthropic) procesa los textos de síntomas para generar respuestas. Anthropic actúa como encargado del tratamiento bajo acuerdo contractual compatible con LOPDP Art. 50.",
      "No enviamos número de póliza ni datos de identidad a servicios externos.",
    ],
  },
];

function formatText(text: string) {
  return text.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
}

export default function PrivacidadPage() {
  return (
    <div className="min-h-screen flex flex-col">
      <TopBar />
      <main className="mx-auto w-full max-w-3xl px-4 py-10 space-y-10">
        <header className="space-y-2">
          <div className="flex items-center gap-2">
            <Shield className="h-6 w-6 text-brand-600" />
            <h1 className="text-3xl font-bold text-gray-900">Aviso de Privacidad</h1>
          </div>
          <p className="text-gray-500">
            Conforme a la <strong>Ley Orgánica de Protección de Datos Personales (LOPDP)</strong> del Ecuador.
            Versión 1.0 — vigente desde el 16 de mayo de 2026.
          </p>
          <div className="flex flex-wrap gap-2 pt-1">
            <span className="badge-blue">LOPDP Ecuador</span>
            <span className="badge-green">SSyP Res. JB-2012-2248</span>
            <span className="badge-gray">MSP</span>
            <span className="badge-gray">DINARDAP</span>
          </div>
        </header>

        {sections.map((s) => (
          <section key={s.title} className="card space-y-3">
            <div className="flex items-center gap-2">
              <s.icon className="h-5 w-5 text-brand-600" />
              <h2 className="font-semibold text-gray-900">{s.title}</h2>
            </div>
            <ul className="space-y-2 text-sm text-gray-700">
              {s.content.map((line, i) => (
                <li
                  key={i}
                  className="flex gap-2"
                  dangerouslySetInnerHTML={{ __html: "• " + formatText(line) }}
                />
              ))}
            </ul>
          </section>
        ))}

        <div className="card bg-brand-50 border-brand-100 text-sm text-brand-800 space-y-2">
          <p className="font-semibold">¿Preguntas sobre tu privacidad?</p>
          <p>Contacta a nuestro Delegado de Protección de Datos (DPO): <strong>privacidad@copayai.ec</strong></p>
          <p>Autoridad de supervisión: <strong>DINARDAP</strong> — Dirección Nacional de Registro de Datos Públicos</p>
        </div>

        <a href="/mis-datos" className="btn-primary inline-flex">
          <UserCheck className="h-4 w-4" />
          Gestionar mis datos (Derechos ARCO)
        </a>
      </main>
    </div>
  );
}
