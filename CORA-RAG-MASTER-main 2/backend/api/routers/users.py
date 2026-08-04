"""Endpoints de gestión de usuarios — Pilar II. Todos exigen rol ADMIN."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends

from backend.api.dependencies import get_manage_users_use_case, require_admin
from backend.api.schemas.users import CreateUserRequest, UpdateUserRequest, UserResponse
from backend.application.use_cases.manage_users import ManageUsersUseCase
from backend.core.security.identity import Principal
from backend.domain.user import User

router = APIRouter(prefix="/api", tags=["users"])


def _to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        department=user.department,
        role=user.role,
        is_active=user.is_active,
        must_change_password=user.must_change_password,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


@router.get("/users", response_model=List[UserResponse])
def list_users(
    principal: Principal = Depends(require_admin),
    use_case: ManageUsersUseCase = Depends(get_manage_users_use_case),
) -> List[UserResponse]:
    return [_to_response(u) for u in use_case.list_users(principal)]


@router.post("/users", response_model=UserResponse)
def create_user(
    payload: CreateUserRequest,
    principal: Principal = Depends(require_admin),
    use_case: ManageUsersUseCase = Depends(get_manage_users_use_case),
) -> UserResponse:
    user = use_case.create_user(
        principal,
        email=payload.email,
        full_name=payload.full_name,
        department=payload.department,
        role=payload.role,
        password=payload.password,
    )
    return _to_response(user)


@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: str,
    payload: UpdateUserRequest,
    principal: Principal = Depends(require_admin),
    use_case: ManageUsersUseCase = Depends(get_manage_users_use_case),
) -> UserResponse:
    user = use_case.update_user(
        principal,
        user_id,
        full_name=payload.full_name,
        department=payload.department,
        role=payload.role,
        is_active=payload.is_active,
    )
    return _to_response(user)


@router.delete("/users/{user_id}")
def delete_user(
    user_id: str,
    principal: Principal = Depends(require_admin),
    use_case: ManageUsersUseCase = Depends(get_manage_users_use_case),
) -> dict:
    use_case.delete_user(principal, user_id)
    return {"deleted": True}
