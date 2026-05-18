"""
Middleware de consentimiento — LOPDP Art. 7.
Bloquea cualquier endpoint de procesamiento de datos si el titular no ha
otorgado consentimiento previo, explícito e informado.
Rutas exentas: /api/v1/consent, /api/v1/health, /api/v1/hospitals (datos públicos)
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from db.rls import make_session_hash
from services.consent_service import check_consent

EXEMPT_PATHS = {
    "/api/v1/consent",
    "/api/v1/health",
    "/api/v1/hospitals",
    "/api/v1/demo-config",
}

CONSENT_REQUIRED_PREFIXES = (
    "/api/v1/chat",
    "/api/v1/conversation",
    "/api/v1/my-data",
    "/api/v1/demo",
)


class ConsentMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        needs_consent = any(path.startswith(p) for p in CONSENT_REQUIRED_PREFIXES)
        if not needs_consent or path in EXEMPT_PATHS:
            return await call_next(request)

        session_id = request.headers.get("X-Session-Id", "")
        if not session_id:
            return JSONResponse(
                {
                    "detail": "Se requiere consentimiento previo (LOPDP Art. 7). "
                              "Por favor acepta la política de privacidad.",
                    "consent_required": True,
                    "consent_url": "/api/v1/consent",
                },
                status_code=403,
            )

        session_hash = make_session_hash(session_id)
        consented = await check_consent(session_hash)
        if not consented:
            return JSONResponse(
                {
                    "detail": "Consentimiento no otorgado o expirado (LOPDP Art. 7). "
                              "Por favor acepta la política de privacidad para continuar.",
                    "consent_required": True,
                    "consent_url": "/api/v1/consent",
                },
                status_code=403,
            )

        return await call_next(request)
