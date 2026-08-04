"""DTOs de entrada/salida del router de chat."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel

from backend.core.config import get_settings
from backend.domain.chat import DocumentReference

_settings = get_settings()


class ChatQueryRequest(BaseModel):
    question: str
    chat_id: Optional[str] = None
    top_k: int = _settings.default_top_k
    score_threshold: float = _settings.default_score_threshold


class ChatQueryResponse(BaseModel):
    chat_id: str
    answer: str
    sources: List[DocumentReference]
