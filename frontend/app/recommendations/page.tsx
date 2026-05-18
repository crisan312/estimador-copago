"use client";
import { useState, useEffect } from "react";
import { TrendingUp, RefreshCw, AlertTriangle, CheckCircle, Info } from "lucide-react";
import TopBar from "../components/TopBar";
import RoleGuard from "../components/RoleGuard";
import { fetchWithAuth } from "../lib/auth";

const ANALYST_ROLES = ["ADMIN", "ANALYST"];

const ANALYSIS_LABELS: Record<string, string> = {
  HOSPITAL_RANKING: "Ranking de Hospitales",
  COST_OPTIMIZATION: "Optimización de Costos",
  SPECIALTY_TREND: "Tendencias por Especialidad",
  SERVICE_QUALITY: "Calidad del Servicio",
  SYSTEM_HEALTH: "Salud del Sistema",
};

const IMPACT_STYLES: Record<string, string> = {
  HIGH:   "bg-red-50 text-red-700 border-red-100",
  MEDIUM: "bg-amber-50 text-amber-700 border-amber-100",
  LOW:    "bg-blue-50 text-blue-700 border-blue-100",
};

interface Finding {
  title: string; description: string; impact: string; data_point: string;
}
interface Recommendation {
  action: string; priority: string; expected_benefit: string;
}
interface Insight {
  executive_summary: string;
  findings: Finding[];
  recommendations: Recommendation[];
  score: number;
}

export default function RecommendationsPage() {
  return (
    <RoleGuard allowedRoles={ANALYST_ROLES}>
      <RecommendationsContent />
    </RoleGuard>
  );
}

function RecommendationsContent() {
  const [insights, setInsights] = useState<Record<string, Insight>>({});
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [selected, setSelected] = useState<string>("HOSPITAL_RANKING");

  const loadInsights = async () => {
    setLoading(true);
    const res = await fetchWithAuth("/api/v1/recommendations");
    if (res.ok) {
      const data = await res.json();
      setInsights(data.insights || {});
    }
    setLoading(false);
  };

  const generateAll = async (force = false) => {
    setGenerating(true);
    await fetchWithAuth("/api/v1/recommendations/generate", {
      method: "POST",
      body: JSON.stringify({ force }),
    });
    setTimeout(loadInsights, 15000); // wait for background tasks
    setGenerating(false);
  };

  useEffect(() => { loadInsights(); }, []);

  const current = insights[selected];

  return (
    <div className="min-h-screen flex flex-col">
      <TopBar />
      <main className="mx-auto w-full max-w-5xl px-4 py-8 space-y-6">
        <header className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-6 w-6 text-brand-600" />
            <h1 className="text-2xl font-bold text-gray-900">Recomendaciones IA</h1>
          </div>
          <div className="flex gap-2">
            <button onClick={() => generateAll(false)} disabled={generating} className="btn-secondary">
              <RefreshCw className={`h-4 w-4 ${generating ? "animate-spin" : ""}`} />
              {generating ? "Generando..." : "Actualizar"}
            </button>
            <button onClick={() => generateAll(true)} disabled={generating} className="btn-primary">
              Regenerar todo
            </button>
          </div>
        </header>

        {/* Selector de tipo */}
        <div className="flex gap-2 flex-wrap">
          {Object.entries(ANALYSIS_LABELS).map(([key, label]) => (
            <button key={key} onClick={() => setSelected(key)}
              className={`rounded-full px-4 py-1.5 text-xs font-semibold border transition-colors ${
                selected === key
                  ? "bg-brand-600 text-white border-brand-600"
                  : insights[key]
                    ? "bg-green-50 text-green-700 border-green-200 hover:border-brand-400"
                    : "bg-white text-gray-500 border-gray-200 hover:border-brand-400"
              }`}>
              {label}
              {insights[key] && selected !== key && <span className="ml-1.5 text-green-500">✓</span>}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="space-y-4">
            {[...Array(3)].map((_, i) => <div key={i} className="h-32 rounded-2xl bg-gray-100 animate-pulse" />)}
          </div>
        ) : current ? (
          <InsightView insight={current} title={ANALYSIS_LABELS[selected]} />
        ) : (
          <div className="card text-center py-16 space-y-3 text-gray-400">
            <TrendingUp className="h-10 w-10 mx-auto opacity-30" />
            <p className="font-semibold">No hay insights para {ANALYSIS_LABELS[selected]}</p>
            <p className="text-sm">Haz clic en "Actualizar" para generar el análisis con datos del sistema.</p>
          </div>
        )}
      </main>
    </div>
  );
}

function InsightView({ insight, title }: { insight: Insight; title: string }) {
  const scoreColor = insight.score >= 0.7 ? "text-red-600" : insight.score >= 0.4 ? "text-amber-600" : "text-green-600";
  return (
    <div className="space-y-5">
      {/* Summary */}
      <div className="card bg-brand-50 border-brand-100 space-y-2">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-brand-900">{title}</h2>
          <span className={`text-sm font-bold ${scoreColor}`}>
            Relevancia: {Math.round(insight.score * 100)}%
          </span>
        </div>
        <p className="text-sm text-brand-800">{insight.executive_summary}</p>
      </div>

      {/* Findings */}
      {insight.findings?.length > 0 && (
        <div className="space-y-3">
          <h3 className="font-semibold text-gray-700 flex items-center gap-2">
            <Info className="h-4 w-4" /> Hallazgos
          </h3>
          {insight.findings.map((f, i) => (
            <div key={i} className={`rounded-2xl border p-4 space-y-1 ${IMPACT_STYLES[f.impact] || IMPACT_STYLES.LOW}`}>
              <div className="flex items-center justify-between">
                <p className="font-semibold text-sm">{f.title}</p>
                <span className="text-xs font-bold opacity-70">{f.impact}</span>
              </div>
              <p className="text-xs">{f.description}</p>
              {f.data_point && (
                <p className="text-xs font-mono opacity-70 pt-1 border-t border-current/10">📊 {f.data_point}</p>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Recommendations */}
      {insight.recommendations?.length > 0 && (
        <div className="space-y-3">
          <h3 className="font-semibold text-gray-700 flex items-center gap-2">
            <CheckCircle className="h-4 w-4 text-green-600" /> Acciones recomendadas
          </h3>
          {insight.recommendations.map((r, i) => (
            <div key={i} className="card space-y-1">
              <div className="flex items-start gap-2">
                <span className={`text-xs font-semibold rounded-full px-2 py-0.5 shrink-0 ${
                  r.priority === "IMMEDIATE" ? "bg-red-100 text-red-700" :
                  r.priority === "SHORT_TERM" ? "bg-amber-100 text-amber-700" :
                  "bg-blue-100 text-blue-700"
                }`}>{r.priority === "IMMEDIATE" ? "Inmediato" : r.priority === "SHORT_TERM" ? "Corto plazo" : "Largo plazo"}</span>
                <p className="text-sm font-medium text-gray-900">{r.action}</p>
              </div>
              <p className="text-xs text-gray-500 pl-0">{r.expected_benefit}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
