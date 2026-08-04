"""Inyección de dependencias de CORA.

Único lugar donde se decide qué implementación concreta satisface cada
puerto de `backend/application/ports`. Activar RBAC/JWT/AD reales, o
cambiar de proveedor de LLM/vector store, es cambiar las funciones de este
módulo — ningún caso de uso ni router necesita tocarse.
"""
from __future__ import annotations

from functools import lru_cache

from fastapi import Depends, Request

from backend.application.ports.chat_repository_port import ChatRepositoryPort
from backend.application.ports.document_loader_port import DocumentLoaderPort
from backend.application.ports.document_registry_port import DocumentRegistryPort
from backend.application.ports.document_storage_port import DocumentStoragePort
from backend.application.ports.embedding_port import EmbeddingPort
from backend.application.ports.llm_port import LLMPort
from backend.application.ports.user_directory_port import UserDirectoryPort
from backend.application.ports.vector_store_port import VectorStorePort
from backend.application.use_cases.answer_query import AnswerQueryUseCase
from backend.application.use_cases.ask_cora import ChatQueryUseCase
from backend.application.use_cases.audit_log import GetAuditLogUseCase
from backend.application.use_cases.auth import ChangePasswordUseCase, LoginUseCase
from backend.application.use_cases.ingest_document import IngestDocumentUseCase
from backend.application.use_cases.manage_chats import ManageChatsUseCase
from backend.application.use_cases.manage_documents import ManageDocumentsUseCase
from backend.application.use_cases.manage_users import ManageUsersUseCase
from backend.core.config import get_settings
from backend.core.exceptions import AuthenticationError, AuthorizationError
from backend.core.security.audit import AuditLogger
from backend.core.security.authorization import AccessPolicy, NullAccessPolicy
from backend.core.security.identity import Principal
from backend.core.security.tokens import TokenService
from backend.domain.user import Role
from backend.infrastructure.embeddings.sentence_transformer_embedder import (
    SentenceTransformerEmbedder,
)
from backend.infrastructure.llm.groq_llm import GroqLLM
from backend.infrastructure.loaders.langchain_document_loader import LangchainDocumentLoader
from backend.infrastructure.persistence.sqlite.audit_repository import SqliteAuditLogger
from backend.infrastructure.persistence.sqlite.chat_repository import SqliteChatRepository
from backend.infrastructure.persistence.sqlite.document_registry_repository import (
    SqliteDocumentRegistry,
)
from backend.infrastructure.persistence.sqlite.user_repository import SqliteUserDirectory
from backend.infrastructure.security.jwt_token_service import JWTTokenService
from backend.infrastructure.storage.filesystem_document_storage import (
    FilesystemDocumentStorage,
)
from backend.infrastructure.vectorstore.chroma_vector_store import ChromaVectorStore


@lru_cache
def get_access_policy() -> AccessPolicy:
    # TODO(seguridad): reemplazar por una política RBAC real (Pilar II).
    return NullAccessPolicy()


@lru_cache
def get_audit_logger() -> AuditLogger:
    settings = get_settings()
    return SqliteAuditLogger(settings.audit_db_path)


@lru_cache
def get_embedder() -> EmbeddingPort:
    settings = get_settings()
    return SentenceTransformerEmbedder(settings.embedding_model_name)


@lru_cache
def get_vector_store() -> VectorStorePort:
    settings = get_settings()
    return ChromaVectorStore(
        collection_name=settings.vectorstore_collection_name,
        persist_directory=str(settings.vector_store_dir),
    )


@lru_cache
def get_llm() -> LLMPort:
    settings = get_settings()
    api_key = settings.groq_api_key.get_secret_value() if settings.groq_api_key else ""
    return GroqLLM(api_key=api_key, model_name=settings.groq_model_name)


@lru_cache
def get_document_storage() -> DocumentStoragePort:
    settings = get_settings()
    return FilesystemDocumentStorage(
        pdf_dir=settings.pdf_dir,
        text_dir=settings.text_dir,
        allowed_extensions=settings.allowed_extensions,
    )


@lru_cache
def get_document_loader() -> DocumentLoaderPort:
    return LangchainDocumentLoader()


@lru_cache
def get_document_registry() -> DocumentRegistryPort:
    settings = get_settings()
    registry = SqliteDocumentRegistry(settings.chat_db_path)
    registry.init()
    return registry


@lru_cache
def get_chat_repository() -> ChatRepositoryPort:
    settings = get_settings()
    repository = SqliteChatRepository(settings.chat_db_path)
    repository.init()
    return repository


def get_ingest_document_use_case() -> IngestDocumentUseCase:
    settings = get_settings()
    return IngestDocumentUseCase(
        document_storage=get_document_storage(),
        document_registry=get_document_registry(),
        document_loader=get_document_loader(),
        embedder=get_embedder(),
        vector_store=get_vector_store(),
        access_policy=get_access_policy(),
        audit_logger=get_audit_logger(),
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )


def get_answer_query_use_case() -> AnswerQueryUseCase:
    settings = get_settings()
    return AnswerQueryUseCase(
        embedder=get_embedder(),
        vector_store=get_vector_store(),
        llm=get_llm(),
        access_policy=get_access_policy(),
        audit_logger=get_audit_logger(),
        relative_score_margin=settings.relative_score_margin,
    )


def get_chat_query_use_case() -> ChatQueryUseCase:
    return ChatQueryUseCase(
        chat_repository=get_chat_repository(),
        answer_query=get_answer_query_use_case(),
    )


def get_manage_documents_use_case() -> ManageDocumentsUseCase:
    return ManageDocumentsUseCase(
        document_storage=get_document_storage(),
        document_registry=get_document_registry(),
        vector_store=get_vector_store(),
        access_policy=get_access_policy(),
        audit_logger=get_audit_logger(),
    )


def get_manage_chats_use_case() -> ManageChatsUseCase:
    return ManageChatsUseCase(
        chat_repository=get_chat_repository(),
        access_policy=get_access_policy(),
    )


# ---------------------------------------------------------------------------
# Identidad y sesión — Pilar II
# ---------------------------------------------------------------------------
@lru_cache
def get_user_directory() -> UserDirectoryPort:
    settings = get_settings()
    directory = SqliteUserDirectory(settings.chat_db_path)
    directory.init()
    return directory


@lru_cache
def get_token_service() -> TokenService:
    settings = get_settings()
    return JWTTokenService(
        secret_key=settings.jwt_secret_key.get_secret_value(),
        expire_minutes=settings.jwt_expire_minutes,
    )


def get_login_use_case() -> LoginUseCase:
    return LoginUseCase(
        user_directory=get_user_directory(),
        token_service=get_token_service(),
        audit_logger=get_audit_logger(),
    )


def get_manage_users_use_case() -> ManageUsersUseCase:
    return ManageUsersUseCase(
        user_directory=get_user_directory(),
        audit_logger=get_audit_logger(),
    )


def get_change_password_use_case() -> ChangePasswordUseCase:
    return ChangePasswordUseCase(
        user_directory=get_user_directory(),
        token_service=get_token_service(),
        audit_logger=get_audit_logger(),
    )


def get_audit_log_use_case() -> GetAuditLogUseCase:
    return GetAuditLogUseCase(
        audit_logger=get_audit_logger(),
        user_directory=get_user_directory(),
    )


def get_current_principal(request: Request) -> Principal:
    """Dependency de FastAPI: resuelve quién hace la request a partir de la
    cookie de sesión. Reemplaza al `Principal` de sistema fijo que existía
    antes de implementar login real (ver core/security/identity.py)."""
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise AuthenticationError("No autenticado: inicia sesión para continuar")
    return get_token_service().verify(token)


def require_admin(principal: Principal = Depends(get_current_principal)) -> Principal:
    if Role.ADMIN.value not in principal.roles:
        raise AuthorizationError("Se requiere rol de administrador")
    return principal
