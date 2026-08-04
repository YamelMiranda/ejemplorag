"""Endpoint de estadísticas para el Dashboard."""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends

from backend.api.dependencies import (
    get_current_principal,
    get_manage_chats_use_case,
    get_manage_documents_use_case,
    get_user_directory,
)
from backend.application.ports.user_directory_port import UserDirectoryPort
from backend.application.use_cases.manage_chats import ManageChatsUseCase
from backend.application.use_cases.manage_documents import ManageDocumentsUseCase
from backend.core.security.identity import Principal

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard/stats")
def dashboard_stats(
    principal: Principal = Depends(get_current_principal),
    documents_use_case: ManageDocumentsUseCase = Depends(get_manage_documents_use_case),
    chats_use_case: ManageChatsUseCase = Depends(get_manage_chats_use_case),
    user_directory: UserDirectoryPort = Depends(get_user_directory),
) -> dict:
    documents = [asdict(doc) for doc in documents_use_case.list_documents(principal)]
    return {
        "total_documents": documents_use_case.total_documents(principal),
        "total_chats": chats_use_case.count_chats(),
        "total_queries": chats_use_case.count_user_messages(),
        "total_users": user_directory.count(),
        "recent_documents": documents[:5],
    }
