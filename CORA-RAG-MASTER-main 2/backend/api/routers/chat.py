"""Endpoints de chat: preguntas a CORA e historial de conversaciones."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.api.dependencies import (
    get_chat_query_use_case,
    get_current_principal,
    get_manage_chats_use_case,
)
from backend.api.schemas.chat import ChatQueryRequest, ChatQueryResponse
from backend.application.use_cases.ask_cora import ChatQueryUseCase
from backend.application.use_cases.manage_chats import ManageChatsUseCase
from backend.core.security.identity import Principal
from backend.domain.chat import Chat

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat/query", response_model=ChatQueryResponse)
def chat_query(
    payload: ChatQueryRequest,
    principal: Principal = Depends(get_current_principal),
    use_case: ChatQueryUseCase = Depends(get_chat_query_use_case),
) -> ChatQueryResponse:
    result = use_case.execute(
        principal,
        question=payload.question,
        chat_id=payload.chat_id,
        top_k=payload.top_k,
        score_threshold=payload.score_threshold,
    )
    return ChatQueryResponse(chat_id=result.chat_id, answer=result.answer, sources=result.sources)


@router.get("/chats")
def get_chats(
    principal: Principal = Depends(get_current_principal),
    use_case: ManageChatsUseCase = Depends(get_manage_chats_use_case),
) -> dict:
    return {"chats": use_case.list_chats(principal)}


@router.get("/chats/{chat_id}", response_model=Chat)
def get_chat(
    chat_id: str,
    principal: Principal = Depends(get_current_principal),
    use_case: ManageChatsUseCase = Depends(get_manage_chats_use_case),
) -> Chat:
    return use_case.get_chat(principal, chat_id)


@router.delete("/chats/{chat_id}")
def remove_chat(
    chat_id: str,
    principal: Principal = Depends(get_current_principal),
    use_case: ManageChatsUseCase = Depends(get_manage_chats_use_case),
) -> dict:
    use_case.delete_chat(principal, chat_id)
    return {"deleted": True}
