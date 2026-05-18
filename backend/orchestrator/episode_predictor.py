"""
A9 — Predictor de Costo del Episodio (agente predictivo determinista).

A4 estima el copago de UNA consulta. Pero un episodio médico real rara vez
termina ahí: una consulta suele derivar en exámenes y un control. Decirle al
paciente solo el costo de la consulta es engañoso.

A9 predice la RUTA DE ATENCIÓN probable de la especialidad (consulta →
exámenes probables → control) y calcula el gasto de bolsillo esperado del
EPISODIO COMPLETO, con el deducible acumulándose correctamente paso a paso.

Diseño (mismo principio que A8):
  · La aritmética del copago es 100 % determinista — reutiliza
    copay_validator.compute_copay() en cada paso.
  · Las rutas de atención provienen de una tabla curada de referencia
    (clinical pathways del mercado ecuatoriano). Cold-start sin datos.
  · Con el tiempo, la tabla cost_outcomes permite recalibrar las
    probabilidades con datos reales (outcome tracking).

IMPORTANTE — alcance regulatorio: A9 predice COSTOS y USO DE SERVICIOS,
nunca desenlaces clínicos (diagnóstico, pronóstico). Predecir salud
convertiría el sistema en dispositivo médico regulado. A9 se mantiene
deliberadamente en el dominio financiero.

Sin LLM · sin tokens · reproducible · auditable.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from orchestrator.copay_validator import compute_copay, _strip, _f


# ── Rutas de atención de referencia por especialidad (Ecuador 2026) ─────────
# Cada paso: nombre, tipo, costo_base (USD), probabilidad de ocurrir.
# El primer paso (la consulta) siempre tiene probabilidad 1.0.
_PATHWAYS: dict[str, list[dict]] = {
    "medicina general": [
        {"nombre": "Consulta de medicina general", "tipo": "consulta", "costo_base": 40, "probabilidad": 1.0},
        {"nombre": "Exámenes de laboratorio básicos", "tipo": "examen", "costo_base": 35, "probabilidad": 0.55},
        {"nombre": "Consulta de control", "tipo": "consulta", "costo_base": 40, "probabilidad": 0.35},
    ],
    "cardiologia": [
        {"nombre": "Consulta de cardiología", "tipo": "consulta", "costo_base": 80, "probabilidad": 1.0},
        {"nombre": "Electrocardiograma", "tipo": "examen", "costo_base": 35, "probabilidad": 0.90},
        {"nombre": "Perfil lipídico y laboratorio", "tipo": "examen", "costo_base": 45, "probabilidad": 0.65},
        {"nombre": "Ecocardiograma", "tipo": "examen", "costo_base": 130, "probabilidad": 0.45},
        {"nombre": "Consulta de control", "tipo": "consulta", "costo_base": 65, "probabilidad": 0.70},
    ],
    "pediatria": [
        {"nombre": "Consulta pediátrica", "tipo": "consulta", "costo_base": 45, "probabilidad": 1.0},
        {"nombre": "Exámenes de laboratorio", "tipo": "examen", "costo_base": 30, "probabilidad": 0.50},
        {"nombre": "Consulta de control", "tipo": "consulta", "costo_base": 40, "probabilidad": 0.55},
    ],
    "dermatologia": [
        {"nombre": "Consulta dermatológica", "tipo": "consulta", "costo_base": 60, "probabilidad": 1.0},
        {"nombre": "Biopsia / estudio de lesión", "tipo": "procedimiento", "costo_base": 90, "probabilidad": 0.30},
        {"nombre": "Consulta de control", "tipo": "consulta", "costo_base": 50, "probabilidad": 0.50},
    ],
    "ginecologia": [
        {"nombre": "Consulta ginecológica", "tipo": "consulta", "costo_base": 60, "probabilidad": 1.0},
        {"nombre": "Ecografía", "tipo": "examen", "costo_base": 55, "probabilidad": 0.70},
        {"nombre": "Citología / laboratorio", "tipo": "examen", "costo_base": 40, "probabilidad": 0.60},
        {"nombre": "Consulta de control", "tipo": "consulta", "costo_base": 50, "probabilidad": 0.55},
    ],
    "traumatologia": [
        {"nombre": "Consulta de traumatología", "tipo": "consulta", "costo_base": 70, "probabilidad": 1.0},
        {"nombre": "Radiografía", "tipo": "examen", "costo_base": 40, "probabilidad": 0.85},
        {"nombre": "Resonancia / tomografía", "tipo": "examen", "costo_base": 220, "probabilidad": 0.35},
        {"nombre": "Terapia física (sesiones)", "tipo": "procedimiento", "costo_base": 120, "probabilidad": 0.50},
        {"nombre": "Consulta de control", "tipo": "consulta", "costo_base": 55, "probabilidad": 0.75},
    ],
    "neurologia": [
        {"nombre": "Consulta neurológica", "tipo": "consulta", "costo_base": 80, "probabilidad": 1.0},
        {"nombre": "Electroencefalograma", "tipo": "examen", "costo_base": 90, "probabilidad": 0.50},
        {"nombre": "Resonancia magnética", "tipo": "examen", "costo_base": 250, "probabilidad": 0.45},
        {"nombre": "Consulta de control", "tipo": "consulta", "costo_base": 65, "probabilidad": 0.70},
    ],
    "gastroenterologia": [
        {"nombre": "Consulta de gastroenterología", "tipo": "consulta", "costo_base": 75, "probabilidad": 1.0},
        {"nombre": "Exámenes de laboratorio", "tipo": "examen", "costo_base": 45, "probabilidad": 0.70},
        {"nombre": "Endoscopía / colonoscopía", "tipo": "procedimiento", "costo_base": 280, "probabilidad": 0.40},
        {"nombre": "Consulta de control", "tipo": "consulta", "costo_base": 60, "probabilidad": 0.70},
    ],
    "oftalmologia": [
        {"nombre": "Consulta oftalmológica", "tipo": "consulta", "costo_base": 55, "probabilidad": 1.0},
        {"nombre": "Estudios de agudeza / fondo de ojo", "tipo": "examen", "costo_base": 45, "probabilidad": 0.65},
        {"nombre": "Consulta de control", "tipo": "consulta", "costo_base": 45, "probabilidad": 0.40},
    ],
    "otorrinolaringologia": [
        {"nombre": "Consulta otorrinolaringológica", "tipo": "consulta", "costo_base": 60, "probabilidad": 1.0},
        {"nombre": "Audiometría / estudios", "tipo": "examen", "costo_base": 50, "probabilidad": 0.55},
        {"nombre": "Consulta de control", "tipo": "consulta", "costo_base": 50, "probabilidad": 0.45},
    ],
    "endocrinologia": [
        {"nombre": "Consulta de endocrinología", "tipo": "consulta", "costo_base": 75, "probabilidad": 1.0},
        {"nombre": "Panel hormonal y laboratorio", "tipo": "examen", "costo_base": 70, "probabilidad": 0.85},
        {"nombre": "Consulta de control", "tipo": "consulta", "costo_base": 60, "probabilidad": 0.80},
    ],
    "urologia": [
        {"nombre": "Consulta de urología", "tipo": "consulta", "costo_base": 70, "probabilidad": 1.0},
        {"nombre": "Ecografía y laboratorio", "tipo": "examen", "costo_base": 60, "probabilidad": 0.75},
        {"nombre": "Consulta de control", "tipo": "consulta", "costo_base": 55, "probabilidad": 0.60},
    ],
    "psiquiatria": [
        {"nombre": "Consulta psiquiátrica", "tipo": "consulta", "costo_base": 80, "probabilidad": 1.0},
        {"nombre": "Consultas de seguimiento", "tipo": "consulta", "costo_base": 65, "probabilidad": 0.85},
    ],
    "neumologia": [
        {"nombre": "Consulta de neumología", "tipo": "consulta", "costo_base": 75, "probabilidad": 1.0},
        {"nombre": "Espirometría / radiografía", "tipo": "examen", "costo_base": 55, "probabilidad": 0.80},
        {"nombre": "Consulta de control", "tipo": "consulta", "costo_base": 60, "probabilidad": 0.65},
    ],
    "_default": [
        {"nombre": "Consulta de especialidad", "tipo": "consulta", "costo_base": 60, "probabilidad": 1.0},
        {"nombre": "Exámenes complementarios", "tipo": "examen", "costo_base": 50, "probabilidad": 0.60},
        {"nombre": "Consulta de control", "tipo": "consulta", "costo_base": 50, "probabilidad": 0.55},
    ],
}

# Umbrales de probabilidad que definen cada escenario
_THRESHOLD_MIN = 0.85   # escenario "casi seguro"
_THRESHOLD_PROBABLE = 0.50


@dataclass
class EpisodePrediction:
    specialty: str
    pathway: list[dict]              # cada paso con copago_paciente calculado
    escenario_minimo_usd: float      # solo pasos casi seguros (prob >= 0.85)
    escenario_probable_usd: float    # pasos probables (prob >= 0.50)
    escenario_completo_usd: float    # todos los pasos
    confidence: float
    notas: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "agente": "A9-EpisodePredictor",
            "especialidad": self.specialty,
            "ruta_atencion": self.pathway,
            "escenario_minimo_usd": self.escenario_minimo_usd,
            "escenario_probable_usd": self.escenario_probable_usd,
            "escenario_completo_usd": self.escenario_completo_usd,
            "rango_estimado": f"${self.escenario_minimo_usd:.2f} – ${self.escenario_completo_usd:.2f}",
            "confianza": self.confidence,
            "notas": self.notas,
        }


def _sum_scenario(steps: list[dict], poliza: dict) -> float:
    """
    Suma el copago de bolsillo de una secuencia de pasos, acumulando el
    deducible: cada paso reduce el deducible disponible para el siguiente.
    """
    total = 0.0
    deducible_consumido = _f(poliza.get("deducible_consumido"))
    for step in steps:
        poliza_step = {**poliza, "deducible_consumido": deducible_consumido}
        det = compute_copay(_f(step["costo_base"]), poliza_step)
        total += det["copago_estimado_usd"]
        # el deducible aplicado en este paso ya no está disponible para el próximo
        deducible_consumido += det["deducible_aplicado"]
    return round(total, 2)


def predict_episode(
    poliza: dict,
    especialidad: str,
    costo_consulta_real: float | None = None,
) -> EpisodePrediction:
    """
    Predice el costo de bolsillo del episodio completo.

    poliza               — dict de la póliza
    especialidad         — especialidad sugerida por A2
    costo_consulta_real  — costo de consulta estimado por A4 (ancla el paso 0)
    """
    notas: list[str] = []
    key = _strip(especialidad)
    pathway_ref = _PATHWAYS.get(key)

    if pathway_ref is None:
        pathway_ref = _PATHWAYS["_default"]
        confidence = 0.60
        notas.append(
            f"No hay ruta de atención específica para «{especialidad or 'la especialidad'}»; "
            "se usa una ruta genérica de referencia."
        )
    else:
        confidence = 0.80

    # Copia de la ruta; anclar el costo de la consulta inicial al valor de A4
    steps = [dict(s) for s in pathway_ref]
    if costo_consulta_real and costo_consulta_real > 0:
        steps[0] = {**steps[0], "costo_base": round(float(costo_consulta_real), 2)}

    # Tres escenarios, cada uno con el deducible acumulado correctamente
    escenario_completo = _sum_scenario(steps, poliza)
    escenario_probable = _sum_scenario(
        [s for s in steps if s["probabilidad"] >= _THRESHOLD_PROBABLE], poliza
    )
    escenario_minimo = _sum_scenario(
        [s for s in steps if s["probabilidad"] >= _THRESHOLD_MIN], poliza
    )

    # Detalle por paso: copago individual (deducible acumulado en orden)
    pathway_detail: list[dict] = []
    deducible_consumido = _f(poliza.get("deducible_consumido"))
    for step in steps:
        poliza_step = {**poliza, "deducible_consumido": deducible_consumido}
        det = compute_copay(_f(step["costo_base"]), poliza_step)
        deducible_consumido += det["deducible_aplicado"]
        pathway_detail.append({
            "paso": step["nombre"],
            "tipo": step["tipo"],
            "probabilidad": step["probabilidad"],
            "costo_base_usd": round(_f(step["costo_base"]), 2),
            "copago_paciente_usd": det["copago_estimado_usd"],
        })

    notas.append(
        "Estimación del episodio completo (consulta + exámenes probables + control). "
        "Las probabilidades son de referencia y se recalibran con datos reales."
    )

    return EpisodePrediction(
        specialty=especialidad or "Medicina General",
        pathway=pathway_detail,
        escenario_minimo_usd=escenario_minimo,
        escenario_probable_usd=escenario_probable,
        escenario_completo_usd=escenario_completo,
        confidence=confidence,
        notas=notas,
    )
