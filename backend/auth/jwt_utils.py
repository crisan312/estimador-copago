"""
JWT: access token (60 min) + refresh token (30 días).
Roles: PATIENT | STAFF | DOCTOR | ANALYST | ADMIN | DPO
"""
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Literal

from jose import JWTError, jwt

from config import settings

ROLES = Literal["PATIENT", "STAFF", "DOCTOR", "ANALYST", "ADMIN", "DPO"]

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "PATIENT":  {"chat", "appointments:own", "kpi:own", "recommendations:own"},
    "STAFF":    {"chat", "appointments:all", "patients:read"},
    "DOCTOR":   {"chat", "appointments:own_doctor", "kpi:doctor", "patients:read"},
    "ANALYST":  {"kpi:all", "recommendations:all", "reports:read"},
    "ADMIN":    {"*"},  # full access
    "DPO":      {"audit:read", "arco:all", "users:read", "compliance:all"},
}


def create_access_token(user_id: str, email: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_access_expire_minutes)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "type": "access",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_expire_days)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def has_permission(role: str, permission: str) -> bool:
    perms = ROLE_PERMISSIONS.get(role, set())
    return "*" in perms or permission in perms
