"""
Router de hospitales — datos públicos, no requieren consentimiento.
"""
from fastapi import APIRouter
from services.hospital_service import get_hospitals, get_all

router = APIRouter(prefix="/api/v1/hospitals", tags=["Hospitales"])


@router.get("")
async def list_hospitals(city: str | None = None, specialty: str | None = None):
    hospitals = get_hospitals(city, specialty) if (city or specialty) else get_all()
    return {"hospitals": hospitals, "total": len(hospitals)}
