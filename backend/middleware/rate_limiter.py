import time
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from config import settings


class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._minute_window: dict[str, list[float]] = defaultdict(list)
        self._hour_window: dict[str, list[float]] = defaultdict(list)

    def _client_key(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        return forwarded.split(",")[0].strip() if forwarded else request.client.host

    def _check(self, key: str, now: float) -> bool:
        minute_hits = self._minute_window[key]
        hour_hits = self._hour_window[key]
        self._minute_window[key] = [t for t in minute_hits if now - t < 60]
        self._hour_window[key] = [t for t in hour_hits if now - t < 3600]

        is_chat = True  # conservative: apply conversation limit globally
        limit_min = settings.rate_limit_per_minute
        limit_hr = (
            settings.conversation_rate_limit_per_hour if is_chat else settings.rate_limit_per_hour
        )

        if len(self._minute_window[key]) >= limit_min:
            return False
        if len(self._hour_window[key]) >= limit_hr:
            return False

        self._minute_window[key].append(now)
        self._hour_window[key].append(now)
        return True

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/api/"):
            key = self._client_key(request)
            if not self._check(key, time.time()):
                return JSONResponse(
                    {"detail": "Demasiadas solicitudes. Por favor espera un momento."},
                    status_code=429,
                )
        return await call_next(request)
