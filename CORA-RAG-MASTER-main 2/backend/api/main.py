"""API de CORA — capa FastAPI.

Traduce HTTP <-> casos de uso. No contiene lógica de negocio: valida input,
resuelve el principal actual, invoca el caso de uso correspondiente y deja
que el exception handler global mapee la jerarquía de
`backend.core.exceptions` a códigos HTTP.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from backend.api.dependencies import (
    get_access_policy,
    get_audit_logger,
    get_chat_repository,
    get_document_registry,
    get_document_storage,
    get_embedder,
    get_token_service,
    get_user_directory,
    get_vector_store,
)
from backend.api.routers import audit, auth, chat, dashboard, documents, health, users
from backend.core.config import BASE_DIR, get_settings
from backend.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    CoraError,
    GenerationError,
    IngestionError,
    NotFoundError,
    RetrievalError,
    ValidationError,
)
from backend.core.logging import get_logger
from backend.domain.user import Role

logger = get_logger(__name__)

ADMIN_PANEL_PATH = BASE_DIR / "static" / "cora-admin.html"

_ERROR_STATUS_CODES: dict[type[CoraError], int] = {
    ValidationError: 400,
    AuthenticationError: 401,
    AuthorizationError: 403,
    NotFoundError: 404,
    IngestionError: 500,
    RetrievalError: 500,
    GenerationError: 500,
}


def _status_code_for(exc: CoraError) -> int:
    for exc_type, status_code in _ERROR_STATUS_CODES.items():
        if isinstance(exc, exc_type):
            return status_code
    return 500


def _bootstrap_admin() -> None:
    """Crea el primer usuario ADMIN si el directorio está vacío — sin esto
    nadie podría iniciar sesión ni crear el resto de usuarios desde el
    panel (ver SECURITY_ROADMAP.md, Pilar II)."""
    settings = get_settings()
    directory = get_user_directory()
    if directory.count() > 0:
        return

    directory.create_user(
        email=settings.bootstrap_admin_email,
        full_name=settings.bootstrap_admin_full_name,
        department=settings.bootstrap_admin_department,
        role=Role.ADMIN,
        password=settings.bootstrap_admin_password.get_secret_value(),
    )
    logger.info("Admin inicial creado: %s", settings.bootstrap_admin_email)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    # Construye aquí, en secuencia, los singletons de infraestructura que
    # dependen de `@lru_cache` (backend/api/dependencies.py). Si se dejan
    # perezosos, la primera vez que dos requests concurrentes disparan el
    # mismo constructor en threads distintos (ver run_in_threadpool de
    # FastAPI) se puede correr una condición de carrera real dentro de
    # ChromaDB (`SharedSystemClient._create_system_if_not_exists` no es
    # segura ante inicializaciones concurrentes del mismo path) y falla con
    # un 500 intermitente. `get_llm()` se deja fuera a propósito: no debe
    # impedir que arranque el servidor si todavía no hay GROQ_API_KEY.
    get_chat_repository()
    get_document_registry()
    get_document_storage()
    get_access_policy()
    get_audit_logger()
    get_vector_store()
    get_embedder()
    get_user_directory()
    get_token_service()
    _bootstrap_admin()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="CORA RAG API", lifespan=_lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(CoraError)
    def handle_cora_error(request: Request, exc: CoraError) -> JSONResponse:
        status_code = _status_code_for(exc)
        if status_code >= 500:
            logger.error("Error no controlado en %s", request.url.path, exc_info=exc)
        return JSONResponse(status_code=status_code, content={"detail": str(exc)})

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(audit.router)
    app.include_router(chat.router)
    app.include_router(documents.router)
    app.include_router(dashboard.router)

    # Sirve el panel admin en el mismo origen que la API (sin CORS que
    # mantener): el HTML usa API_BASE = "/api", relativo al host desde el
    # que se sirve.
    @app.get("/", include_in_schema=False)
    def serve_admin_panel() -> FileResponse:
        return FileResponse(ADMIN_PANEL_PATH)

    return app


app = create_app()
