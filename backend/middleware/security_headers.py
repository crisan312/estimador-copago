"""
Security headers — OWASP + SSyP Resolución JB-2012-2248
CSP con nonce sería ideal pero fuera de scope; usamos política restrictiva base.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Prevención de ataques XSS, clickjacking, MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"

        # CSP — restringe fuentes de contenido (LOPDP + OWASP)
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        response.headers["Content-Security-Policy"] = csp

        # HSTS — solo en producción (fuerza HTTPS)
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        # No cachear respuestas con datos personales
        if request.url.path.startswith("/api/v1/") and request.url.path not in ("/api/v1/health", "/api/v1/hospitals"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"

        return response
