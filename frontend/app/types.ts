export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

export interface CopayData {
  costo_consulta_usd: number;
  copago_estimado_usd: number;
  cobertura_pct: number;
  seguro_cubre_usd: number;
  deducible_aplicado: number;
  tope_alcanzado: boolean;
  confianza: number;
  especialidad_cubierta: boolean;
  hospital_en_red: boolean | null;
  advertencias: string[];
  desglose: {
    costo_bruto: number;
    menos_deducible: number;
    costo_a_cubrir: number;
    seguro_cubre: number;
    tu_parte: number;
  };
}

export interface Hospital {
  id: string;
  nombre: string;
  tipo: "HOSPITAL" | "CLINICA" | "CENTRO_MEDICO";
  direccion: string;
  telefono: string;
  ciudad: string;
  en_red_autorizada: boolean;
  copago_estimado_usd: number;
  costo_consulta_usd: number;
  tiempo_espera_promedio_min: number;
  rating_atencion: number;
  distancia_km: number;
  disponible_hoy: boolean;
}

export interface SpecialtyData {
  especialidad_primaria: string;
  especialidad_alternativa: string;
  tipo_consulta: "CONSULTA_EXTERNA" | "URGENCIAS" | "EMERGENCIA";
  urgencia: "EMERGENCIA" | "URGENTE" | "NORMAL" | "PREVENTIVO";
  tiempo_espera_recomendado: string;
  razon: string;
}

export interface TokenBudget {
  used: number;
  budget: number;
  remaining: number;
  usage_pct: number;
  alert: boolean;
}

export interface SSEEvent {
  type: "message" | "thinking" | "copay" | "hospitals" | "specialty" | "state" | "token_budget" | "completed" | "error" | "done";
  role?: "user" | "assistant";
  content?: string;
  agent?: string;
  message?: string;
  conversation_id?: string;
  state?: string;
  [key: string]: unknown;
}
