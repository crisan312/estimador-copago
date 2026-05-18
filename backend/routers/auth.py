"""
Router de autenticación: registro, login, refresh, me.
JWT propio con roles RBAC — LOPDP: password hasheado bcrypt, sin PII en tokens.
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from jose import JWTError
from pydantic import BaseModel, EmailStr, field_validator
from db.database_pg import get_pool
from auth.jwt_utils import (
    create_access_token, create_refresh_token,
    decode_token, hash_token,
)
from auth.password_utils import hash_password, verify_password
from auth.dependencies import CurrentUser, get_current_user
from services import audit_service
from db.rls import make_session_hash
from config import settings

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    role: str = "PATIENT"
    phone_whatsapp: str | None = None

    @field_validator("password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        return v

    @field_validator("role")
    @classmethod
    def valid_role(cls, v: str) -> str:
        allowed = {"PATIENT", "STAFF", "DOCTOR", "ANALYST"}
        if v not in allowed:
            raise ValueError(f"Rol inválido. Opciones: {', '.join(allowed)}")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str
    user_id: str


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest):
    pool = await get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchval("SELECT id FROM users WHERE email = $1", req.email)
        if existing:
            raise HTTPException(status.HTTP_409_CONFLICT, "Email ya registrado")

        user_id = str(uuid.uuid4())
        pw_hash = hash_password(req.password)

        await conn.execute(
            """INSERT INTO users (id, email, password_hash, role, phone_whatsapp)
               VALUES ($1, $2, $3, $4, $5)""",
            user_id, req.email, pw_hash, req.role, req.phone_whatsapp,
        )
        await conn.execute(
            "INSERT INTO user_profiles (user_id) VALUES ($1) ON CONFLICT DO NOTHING",
            user_id,
        )

    await audit_service.log_event(
        session_hash=make_session_hash(user_id),
        event_type=audit_service.AuditEvent.DATA_MODIFIED,
        resource="users",
        resource_id=user_id,
        details={"action": "register", "role": req.role},
    )
    return {"user_id": user_id, "email": req.email, "role": req.role}


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, password_hash, role, is_active FROM users WHERE email = $1",
            req.email,
        )
    if not row or not verify_password(req.password, row["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas")
    if not row["is_active"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cuenta desactivada")

    user_id = str(row["id"])
    role = row["role"]

    access = create_access_token(user_id, req.email, role)
    refresh = create_refresh_token(user_id)

    # persist refresh token
    pool = await get_pool()
    async with pool.acquire() as conn:
        expires = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_expire_days)
        await conn.execute(
            """INSERT INTO refresh_tokens (user_id, token_hash, expires_at)
               VALUES ($1, $2, $3)""",
            user_id, hash_token(refresh), expires,
        )
        await conn.execute(
            "UPDATE users SET last_login_at = NOW() WHERE id = $1", user_id,
        )

    await audit_service.log_event(
        session_hash=make_session_hash(user_id),
        event_type=audit_service.AuditEvent.DATA_ACCESSED,
        resource="auth",
        resource_id=user_id,
        details={"action": "login"},
    )
    return TokenResponse(access_token=access, refresh_token=refresh, role=role, user_id=user_id)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(req: RefreshRequest):
    try:
        payload = decode_token(req.refresh_token)
        if payload.get("type") != "refresh":
            raise ValueError
    except (JWTError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token inválido")

    user_id = payload["sub"]
    token_hash = hash_token(req.refresh_token)

    pool = await get_pool()
    async with pool.acquire() as conn:
        rt = await conn.fetchrow(
            """SELECT id, expires_at, revoked_at FROM refresh_tokens
               WHERE user_id = $1 AND token_hash = $2""",
            user_id, token_hash,
        )
        if not rt or rt["revoked_at"] or rt["expires_at"] < datetime.now(timezone.utc):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token expirado o revocado")

        user = await conn.fetchrow(
            "SELECT email, role, is_active FROM users WHERE id = $1", user_id,
        )
        if not user or not user["is_active"]:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Cuenta desactivada")

        # rotate: revoke old, issue new
        await conn.execute(
            "UPDATE refresh_tokens SET revoked_at = NOW() WHERE id = $1", rt["id"],
        )
        new_refresh = create_refresh_token(user_id)
        expires = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_expire_days)
        await conn.execute(
            "INSERT INTO refresh_tokens (user_id, token_hash, expires_at) VALUES ($1, $2, $3)",
            user_id, hash_token(new_refresh), expires,
        )

    new_access = create_access_token(user_id, user["email"], user["role"])
    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        role=user["role"],
        user_id=user_id,
    )


@router.post("/logout")
async def logout(
    req: RefreshRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    token_hash = hash_token(req.refresh_token)
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE refresh_tokens SET revoked_at = NOW() WHERE token_hash = $1",
            token_hash,
        )
    return {"ok": True}


@router.get("/me")
async def get_me(current_user: Annotated[CurrentUser, Depends(get_current_user)]):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT u.email, u.role, u.phone_whatsapp, u.whatsapp_opt_in,
                      u.last_login_at, u.created_at, p.city, p.specialty_area
               FROM users u
               LEFT JOIN user_profiles p ON p.user_id = u.id
               WHERE u.id = $1""",
            current_user.user_id,
        )
    if not row:
        raise HTTPException(404, "Usuario no encontrado")
    return {
        "user_id": current_user.user_id,
        "email": row["email"],
        "role": row["role"],
        "phone_whatsapp": row["phone_whatsapp"],
        "whatsapp_opt_in": row["whatsapp_opt_in"],
        "last_login_at": row["last_login_at"],
        "created_at": row["created_at"],
        "city": row["city"],
        "specialty_area": row["specialty_area"],
    }
