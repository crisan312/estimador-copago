"""
FastAPI dependencies para autenticación y autorización por rol.
"""
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError

from auth.jwt_utils import decode_token, has_permission


class CurrentUser:
    def __init__(self, user_id: str, email: str, role: str):
        self.user_id = user_id
        self.email = email
        self.role = role

    def require(self, permission: str):
        if not has_permission(self.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permiso requerido: {permission}",
            )


def _extract_bearer(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acceso requerido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return authorization[7:]


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
) -> CurrentUser:
    token = _extract_bearer(authorization)
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise ValueError("Tipo de token incorrecto")
        return CurrentUser(
            user_id=payload["sub"],
            email=payload["email"],
            role=payload["role"],
        )
    except (JWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_optional(
    authorization: Annotated[str | None, Header()] = None,
) -> CurrentUser | None:
    if not authorization:
        return None
    try:
        return await get_current_user(authorization)
    except HTTPException:
        return None


def require_roles(*roles: str):
    async def _check(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acceso restringido a roles: {', '.join(roles)}",
            )
        return user
    return _check
