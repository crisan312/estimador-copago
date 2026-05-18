"""
Generador de resumen estructurado para el endpoint /summary.
El PDF descargable queda como mejora futura (requiere reportlab/weasyprint).
"""
from datetime import datetime


def build_summary(memory) -> dict:
    ctx = memory.patient_context
    copago = ctx.get("copago", {})
    hospitales = ctx.get("hospitales", [])
    mejor = hospitales[0] if hospitales else {}

    return {
        "conversation_id": memory.conversation_id,
        "generated_at": datetime.utcnow().isoformat(),
        "patient": {
            "sintoma_principal": ctx.get("sintoma_principal", ""),
            "especialidad": ctx.get("especialidad", ""),
        },
        "copay": {
            "copago_estimado_usd": copago.get("copago_estimado_usd", 0),
            "cobertura_pct": copago.get("cobertura_pct", 0),
            "seguro_cubre_usd": copago.get("seguro_cubre_usd", 0),
            "costo_consulta_usd": copago.get("costo_consulta_usd", 0),
            "deducible_aplicado": copago.get("deducible_aplicado", 0),
            "confianza": copago.get("confianza", 0),
            "advertencias": copago.get("advertencias", []),
        },
        "best_hospital": {
            "nombre": mejor.get("nombre", ""),
            "direccion": mejor.get("direccion", ""),
            "telefono": mejor.get("telefono", ""),
            "copago_estimado_usd": mejor.get("copago_estimado_usd", 0),
        },
        "hospitals": hospitales[:5],
        "turns": len(memory.turns),
    }
