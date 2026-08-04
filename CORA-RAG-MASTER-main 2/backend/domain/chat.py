"""Entidades de dominio para el historial de conversaciones de CORA."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class DocumentReference(BaseModel):
    """Referencia trazable a un chunk del Repositorio de Conocimiento usado
    para construir una respuesta (Pilar III: cada respuesta es rastreable
    hasta los documentos autorizados que la respaldan)."""

    chunk_id: str
    source_file: str
    file_type: str
    page: Optional[int] = None
    similarity_score: float
    snippet: str


class Message(BaseModel):
    id: str
    chat_id: str
    role: MessageRole
    content: str
    sources: List[DocumentReference] = Field(default_factory=list)
    created_at: datetime


class Chat(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[Message] = Field(default_factory=list)
