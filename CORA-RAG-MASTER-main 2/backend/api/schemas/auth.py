"""DTOs de entrada/salida del router de autenticación."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class PrincipalResponse(BaseModel):
    id: str
    display_name: str
    roles: List[str]
    department: Optional[str] = None
    email: Optional[str] = None
    must_change_password: bool = False
