"""
Router de Recomendaciones IA — A7-InsightAnalyst.
"""
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from auth.dependencies import CurrentUser, get_current_user
from services import recommendation_service

router = APIRouter(prefix="/api/v1/recommendations", tags=["Recommendations"])

ANALYST_ROLES = {"ADMIN", "ANALYST"}


@router.get("")
async def list_insights(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    analysis_type: str | None = None,
):
    """Lista los últimos insights disponibles (de caché Redis o DB)."""
    if current_user.role not in ANALYST_ROLES:
        raise HTTPException(403, "Acceso restringido a ADMIN y ANALYST")

    types_to_fetch = (
        [analysis_type] if analysis_type
        else recommendation_service.ANALYSIS_TYPES
    )
    results = {}
    for at in types_to_fetch:
        cached = await recommendation_service.get_cached_insight(at)
        if cached:
            results[at] = cached
    return {"insights": results, "cached": True}


@router.post("/generate")
async def generate_insights(
    background_tasks: BackgroundTasks,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    analysis_type: str | None = None,
    force: bool = False,
):
    """Dispara generación de insights IA en background."""
    if current_user.role not in ANALYST_ROLES:
        raise HTTPException(403, "Acceso restringido a ADMIN y ANALYST")

    if analysis_type and analysis_type not in recommendation_service.ANALYSIS_TYPES:
        raise HTTPException(400, f"Tipo inválido. Opciones: {recommendation_service.ANALYSIS_TYPES}")

    if analysis_type:
        background_tasks.add_task(recommendation_service.generate_insight, analysis_type, force)
    else:
        background_tasks.add_task(recommendation_service.generate_all_insights, force)

    return {
        "ok": True,
        "message": f"Generando {'todos los insights' if not analysis_type else analysis_type}",
        "expected_time_seconds": 10 if analysis_type else 60,
    }


@router.get("/patient")
async def get_patient_recommendation(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    conversation_id: str | None = None,
):
    """Recomendaciones personalizadas para el paciente post-consulta."""
    if current_user.role != "PATIENT":
        raise HTTPException(403, "Solo disponible para pacientes")

    if not conversation_id:
        return {"recommendations": None, "message": "Completa una consulta para ver recomendaciones"}

    from services.redis_store import load_conversation
    from db.rls import make_session_hash
    data = await load_conversation(conversation_id)
    if not data:
        raise HTTPException(404, "Consulta no encontrada")

    rec = await recommendation_service.get_patient_recommendations(
        session_hash=make_session_hash(current_user.user_id),
        patient_context=data.get("patient_context", {}),
    )
    return {"recommendations": rec}


class DismissRequest(BaseModel):
    recommendation_id: str


@router.post("/dismiss")
async def dismiss_recommendation(
    req: DismissRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    from db.database_pg import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE recommendations SET dismissed_at = NOW() WHERE id = $1",
            req.recommendation_id,
        )
    return {"ok": True}
