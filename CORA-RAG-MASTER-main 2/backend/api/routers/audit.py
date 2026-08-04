"""Endpoint del registro de auditoría — Pilar III. Solo ADMIN: expone
actividad de todos los usuarios."""
from __future__ import annotations

from dataclasses import asdict
from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from backend.api.dependencies import get_audit_log_use_case, require_admin
from backend.application.use_cases.audit_log import GetAuditLogUseCase
from backend.core.security.identity import Principal

router = APIRouter(prefix="/api", tags=["audit"])


@router.get("/audit")
def get_audit_log(
    period: Optional[str] = Query(None, pattern="^(daily|weekly|monthly)$"),
    principal: Principal = Depends(require_admin),
    use_case: GetAuditLogUseCase = Depends(get_audit_log_use_case),
) -> List[dict]:
    entries = use_case.execute(principal, period=period)
    return [asdict(entry) for entry in entries]
