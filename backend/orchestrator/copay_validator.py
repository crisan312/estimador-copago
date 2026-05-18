"""
A8 — Validador Determinista de Copago (guardrail NO-LLM).

A4-CopayCalculator estima el copago con un LLM. Los modelos de lenguaje
cometen errores en cálculos aritméticos multi-paso (deducible → cobertura →
coaseguro → tope). En un estimador de costos de salud, un número equivocado
erosiona la confianza del paciente y constituye un riesgo de cumplimiento.

Este módulo RECALCULA el copago con aritmética pura de Python a partir de los
campos verificables de la póliza y lo compara contra la salida de A4. Si la
discrepancia supera `copay_variance_warning_threshold`, el valor determinista
—reproducible y auditable— pasa a ser el autoritativo.

Características:
  · Sin LLM · sin tokens · latencia ~0 ms
  · 100 % reproducible → auditable (LOPDP Art. 37 / SSyP)
  · Usa los umbrales ya definidos en config.py
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field

from config import settings


# ── Bandas de costo de referencia por especialidad (USD · Ecuador 2026) ──────
# Se usan solo para detectar un costo de consulta groseramente fuera de rango.
_COST_BANDS: dict[str, tuple[float, float]] = {
    "medicina general": (25, 55),
    "pediatria": (30, 70),
    "cardiologia": (60, 120),
    "neurologia": (60, 120),
    "dermatologia": (50, 100),
    "ginecologia": (50, 110),
    "obstetricia": (50, 110),
    "ortopedia": (60, 130),
    "traumatologia": (60, 130),
    "oftalmologia": (50, 110),
    "otorrinolaringologia": (55, 115),
    "gastroenterologia": (60, 120),
    "endocrinologia": (60, 120),
    "psiquiatria": (60, 130),
    "urologia": (60, 120),
    "neumologia": (60, 120),
    "reumatologia": (60, 120),
    "_default": (40, 130),
}


def _strip(text: str) -> str:
    """Normaliza a minúsculas sin acentos para emparejar especialidades."""
    nfkd = unicodedata.normalize("NFKD", (text or "").strip().lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _f(value, default: float = 0.0) -> float:
    """Conversión robusta a float — nunca lanza excepción."""
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


@dataclass
class CopayValidation:
    copago_determinista_usd: float
    copago_modelo_usd: float
    variacion_pct: float
    discrepancia: bool
    copago_autoritativo_usd: float
    fuente: str                 # llm_validado | deterministico_corregido | llm_sin_validar
    desglose: dict
    notas: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "verificado": True,
            "copago_determinista_usd": self.copago_determinista_usd,
            "copago_modelo_usd": self.copago_modelo_usd,
            "variacion_pct": self.variacion_pct,
            "discrepancia": self.discrepancia,
            "copago_autoritativo_usd": self.copago_autoritativo_usd,
            "fuente": self.fuente,
            "desglose": self.desglose,
            "notas": self.notas,
        }


def compute_copay(costo_consulta: float, poliza: dict) -> dict:
    """
    Recalcula el copago de forma determinista. Implementa la misma fórmula
    que el prompt de A4, pero con aritmética exacta de Python.

    Orden: deducible → costo cubrible → cobertura → coaseguro → tope anual.
    """
    deducible_anual = _f(poliza.get("deducible_anual"))
    deducible_consumido = _f(poliza.get("deducible_consumido"))
    copago_pct = _f(poliza.get("copago_pct"))
    coaseguro_pct = _f(poliza.get("coaseguro_pct"))
    # cobertura = lo que el seguro paga; copago_pct = lo que paga el paciente
    cobertura_pct = min(100.0, max(0.0, 100.0 - copago_pct))

    # 1) Deducible: el paciente paga de su bolsillo hasta agotarlo
    deducible_disponible = max(0.0, deducible_anual - deducible_consumido)
    deducible_aplicado = min(deducible_disponible, costo_consulta) if deducible_disponible > 0 else 0.0
    costo_tras_deducible = max(0.0, costo_consulta - deducible_aplicado)

    # 2) El seguro cubre un % del costo restante, menos el coaseguro
    seguro_cubre = costo_tras_deducible * (cobertura_pct / 100.0) * (1.0 - coaseguro_pct / 100.0)

    # 3) Tope anual de cobertura del seguro
    tope_alcanzado = False
    tope_anual = _f(poliza.get("tope_anual_usd"))
    tope_consumido = _f(poliza.get("tope_consumido_usd"))
    if tope_anual > 0:
        tope_disponible = max(0.0, tope_anual - tope_consumido)
        if seguro_cubre > tope_disponible:
            seguro_cubre = tope_disponible
            tope_alcanzado = True

    # 4) El paciente paga: deducible + (costo restante no cubierto por el seguro)
    copago = max(0.0, costo_tras_deducible - seguro_cubre + deducible_aplicado)

    return {
        "costo_consulta_usd": round(costo_consulta, 2),
        "deducible_aplicado": round(deducible_aplicado, 2),
        "costo_tras_deducible": round(costo_tras_deducible, 2),
        "cobertura_pct": round(cobertura_pct, 2),
        "coaseguro_pct": round(coaseguro_pct, 2),
        "seguro_cubre_usd": round(seguro_cubre, 2),
        "copago_estimado_usd": round(copago, 2),
        "tope_alcanzado": tope_alcanzado,
    }


def validate(a4_data: dict, poliza: dict, especialidad: str = "") -> CopayValidation:
    """
    Compara la estimación de A4 contra el cálculo determinista.

    a4_data       — dict de salida de A4-CopayCalculator
    poliza        — dict de la póliza (campos: deducible_anual, copago_pct, ...)
    especialidad  — para validar la banda de costo de referencia
    """
    notas: list[str] = []
    costo = _f(a4_data.get("costo_consulta_usd"))
    copago_modelo = _f(a4_data.get("copago_estimado_usd"))

    # Sin costo de consulta no se puede recalcular la aritmética
    if costo <= 0:
        return CopayValidation(
            copago_determinista_usd=copago_modelo,
            copago_modelo_usd=copago_modelo,
            variacion_pct=0.0,
            discrepancia=False,
            copago_autoritativo_usd=copago_modelo,
            fuente="llm_sin_validar",
            desglose={},
            notas=["A4 no entregó costo de consulta — validación aritmética omitida."],
        )

    # Sanity-check: ¿el costo de consulta está dentro de lo esperable?
    low, high = _COST_BANDS.get(_strip(especialidad), _COST_BANDS["_default"])
    if costo < low * 0.5 or costo > high * 1.5:
        notas.append(
            f"Costo de consulta (${costo:.2f}) fuera del rango esperado para "
            f"{especialidad or 'la especialidad'} (${low:.0f}–${high:.0f})."
        )

    # Recálculo determinista
    det = compute_copay(costo, poliza)
    copago_det = det["copago_estimado_usd"]

    base = max(copago_det, 1.0)  # evita división por cero en copagos ~0
    variacion = abs(copago_det - copago_modelo) / base
    discrepancia = variacion > settings.copay_variance_warning_threshold

    if discrepancia:
        notas.append(
            f"El cálculo del modelo (${copago_modelo:.2f}) difiere "
            f"{variacion * 100:.0f}% del cálculo determinista verificado "
            f"(${copago_det:.2f}). Se muestra el valor verificado."
        )
        autoritativo = copago_det
        fuente = "deterministico_corregido"
    else:
        autoritativo = copago_modelo
        fuente = "llm_validado"

    return CopayValidation(
        copago_determinista_usd=copago_det,
        copago_modelo_usd=copago_modelo,
        variacion_pct=round(variacion * 100, 1),
        discrepancia=discrepancia,
        copago_autoritativo_usd=autoritativo,
        fuente=fuente,
        desglose=det,
        notas=notas,
    )
