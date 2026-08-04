"""Endpoints de autenticación — Pilar II.

El token de sesión viaja en una cookie httpOnly (no en el cuerpo de la
respuesta ni en localStorage): mitiga robo de sesión vía XSS. El frontend
nunca maneja el JWT directamente.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from backend.api.dependencies import (
    get_change_password_use_case,
    get_current_principal,
    get_login_use_case,
)
from backend.api.schemas.auth import ChangePasswordRequest, LoginRequest, PrincipalResponse
from backend.application.use_cases.auth import ChangePasswordUseCase, LoginResult, LoginUseCase
from backend.core.config import get_settings
from backend.core.security.identity import Principal

router = APIRouter(prefix="/api", tags=["auth"])


def _to_response(principal: Principal) -> PrincipalResponse:
    return PrincipalResponse(
        id=principal.id,
        display_name=principal.display_name,
        roles=principal.roles,
        department=principal.department,
        email=principal.email,
        must_change_password=principal.must_change_password,
    )


def _set_session_cookie(response: Response, result: LoginResult) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=result.token,
        httponly=True,
        samesite="lax",
        secure=settings.environment == "production",
        max_age=settings.jwt_expire_minutes * 60,
        path="/",
    )


@router.post("/auth/login", response_model=PrincipalResponse)
def login(
    payload: LoginRequest,
    response: Response,
    use_case: LoginUseCase = Depends(get_login_use_case),
) -> PrincipalResponse:
    result = use_case.execute(payload.email, payload.password)
    _set_session_cookie(response, result)
    return _to_response(result.principal)


@router.post("/auth/logout")
def logout(response: Response) -> dict:
    settings = get_settings()
    response.delete_cookie(key=settings.session_cookie_name, path="/")
    return {"logged_out": True}


@router.get("/auth/me", response_model=PrincipalResponse)
def me(principal: Principal = Depends(get_current_principal)) -> PrincipalResponse:
    return _to_response(principal)


@router.post("/auth/change-password", response_model=PrincipalResponse)
def change_password(
    payload: ChangePasswordRequest,
    response: Response,
    principal: Principal = Depends(get_current_principal),
    use_case: ChangePasswordUseCase = Depends(get_change_password_use_case),
) -> PrincipalResponse:
    result = use_case.execute(principal, payload.current_password, payload.new_password)
    _set_session_cookie(response, result)
    return _to_response(result.principal)
