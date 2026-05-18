"""
Router de KPIs — métricas por rol, todas anónimas y agregadas.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from auth.dependencies import CurrentUser, get_current_user
from services import kpi_service, forecast_service

router = APIRouter(prefix="/api/v1/kpi", tags=["KPI"])


@router.get("/me")
async def get_my_kpis(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Retorna los KPIs correspondientes al rol del usuario autenticado."""
    role = current_user.role

    if role == "PATIENT":
        return await kpi_service.get_patient_kpis(current_user.user_id)

    elif role == "DOCTOR":
        from db.database_pg import get_pool
        pool = await get_pool()
        async with pool.acquire() as conn:
            profile = await conn.fetchrow(
                "SELECT specialty_area FROM user_profiles WHERE user_id = $1",
                current_user.user_id,
            )
        specialty = profile["specialty_area"] if profile else None
        return await kpi_service.get_doctor_kpis(current_user.user_id, specialty)

    elif role == "STAFF":
        return await kpi_service.get_staff_kpis()

    elif role == "ANALYST":
        return await kpi_service.get_analyst_kpis()

    elif role == "ADMIN":
        return await kpi_service.get_admin_kpis()

    elif role == "DPO":
        return await kpi_service.get_dpo_kpis()

    raise HTTPException(400, f"Rol no reconocido: {role}")


@router.get("/system")
async def get_system_kpis(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """KPIs globales del sistema — solo ADMIN y ANALYST."""
    if current_user.role not in ("ADMIN", "ANALYST"):
        raise HTTPException(403, "Acceso restringido a ADMIN y ANALYST")
    return await kpi_service.get_analyst_kpis()


@router.get("/compliance")
async def get_compliance_kpis(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """KPIs de compliance LOPDP — solo DPO y ADMIN."""
    if current_user.role not in ("DPO", "ADMIN"):
        raise HTTPException(403, "Acceso restringido a DPO y ADMIN")
    return await kpi_service.get_dpo_kpis()


@router.get("/accuracy")
async def get_estimator_accuracy(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """
    Precisión del estimador de copago (outcome tracking).
    Compara los pagos reales registrados contra lo estimado — MAPE y
    precisión global y por especialidad. Solo ADMIN, ANALYST y DOCTOR.
    """
    if current_user.role not in ("ADMIN", "ANALYST", "DOCTOR"):
        raise HTTPException(403, "Acceso restringido a ADMIN, ANALYST y DOCTOR")
    return await forecast_service.get_accuracy_stats()
