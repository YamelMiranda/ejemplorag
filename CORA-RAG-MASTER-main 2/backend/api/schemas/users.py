"""DTOs de entrada/salida del router de gestión de usuarios."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from backend.domain.user import Role


class CreateUserRequest(BaseModel):
    email: str
    full_name: str
    department: str
    role: Role
    password: str


class UpdateUserRequest(BaseModel):
    full_name: Optional[str] = None
    department: Optional[str] = None
    role: Optional[Role] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    department: str
    role: Role
    is_active: bool
    must_change_password: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None
