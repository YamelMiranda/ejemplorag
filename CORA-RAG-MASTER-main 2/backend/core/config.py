"""Configuración central de CORA.

Toda la configuración es tipada y validada con pydantic-settings. Los
secretos (GROQ_API_KEY) se leen únicamente desde variables de entorno o un
archivo .env local que nunca se committea (ver .gitignore y
SECURITY_ROADMAP.md, Pilar I) — nada de valores hardcodeados en el código.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Carpeta raíz del proyecto (CORA_rag-master), tres niveles arriba de este archivo:
# backend/core/config.py -> backend/core -> backend -> raíz
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"

    # Carpeta de datos (misma que usan los notebooks originales: ../data/...)
    data_dir: Path = BASE_DIR / "data"

    # LLM (Groq)
    groq_api_key: Optional[SecretStr] = Field(default=None)
    groq_model_name: str = "llama-3.3-70b-versatile"

    # Embeddings — modelo multilingüe: "all-MiniLM-L6-v2" es solo-inglés y
    # daba muy poca separación semántica entre documentos en español (ver
    # SECURITY_ROADMAP.md / diagnóstico de retrieval). Confirmado con datos
    # reales: con el modelo en inglés, un documento relevante y uno
    # irrelevante quedaban casi empatados (~0.46 vs ~0.50); con este modelo
    # multilingüe, el relevante saca una ventaja clara (~0.26 vs ~0.02-0.09).
    embedding_model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"

    # ChromaDB — Repositorio de Conocimiento Empresarial
    vectorstore_collection_name: str = "cora_knowledge_repository"

    # Chunking
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # Retrieval. No existe un umbral que separe perfectamente lo relevante
    # de lo irrelevante con un corpus tan desbalanceado como el actual (un
    # documento con 150+ chunks tiene muchas más chances de sacar un
    # puntaje "decente" al azar que uno con 1 solo chunk, aunque el segundo
    # sea el realmente relevante — medido con datos reales). 0.20 es un
    # piso conservador: filtra coincidencias claramente débiles sin
    # descartar documentos pequeños legítimos. Ajustable por env; subirlo
    # reduce falsos positivos pero puede ocultar documentos cortos reales.
    default_top_k: int = 5
    default_score_threshold: float = 0.20

    # Piso relativo: se descartan los candidatos que queden más de esta
    # cantidad de puntos de similitud por debajo del mejor resultado de esa
    # consulta puntual. Complementa a default_score_threshold — evita que
    # un documento sin relación real "acompañe" al documento correcto solo
    # porque ambos superan el piso absoluto (medido con datos reales:
    # con la pregunta "cuales son los 4 pilares...", el documento correcto
    # sacaba 65% y uno sin relación 40% — ambos por encima del piso
    # absoluto de 20%, pero muy lejos entre sí).
    relative_score_margin: float = 0.15

    # Sesión (JWT) — Pilar II. Sin default: un secreto adivinable o vacío
    # invalidaría toda la autenticación, así que el arranque debe fallar
    # claramente si falta en vez de generar uno silencioso.
    jwt_secret_key: SecretStr
    jwt_expire_minutes: int = 480
    session_cookie_name: str = "cora_session"

    # Admin inicial — Pilar II. Sin usuarios en el directorio no hay forma
    # de crear el primero desde el panel (nadie tendría sesión todavía), así
    # que se crea uno en el arranque a partir de estas variables. Sin
    # default por la misma razón que jwt_secret_key: nada de contraseñas
    # adivinables.
    bootstrap_admin_email: str
    bootstrap_admin_password: SecretStr
    bootstrap_admin_full_name: str = "Administrador CORA"
    bootstrap_admin_department: str = "Tecnología"

    # Documentos permitidos al subir
    allowed_extensions: List[str] = [".pdf", ".txt", ".html", ".htm"]

    # CORS: orígenes explícitos permitidos. Nunca "*" — el panel admin y
    # cualquier otro cliente deben declararse aquí (o vía env CORS_ALLOW_ORIGINS).
    cors_allow_origins: List[str] = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ]

    @field_validator("cors_allow_origins", "allowed_extensions", mode="before")
    @classmethod
    def _split_csv(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def pdf_dir(self) -> Path:
        return self.data_dir / "pdf"

    @property
    def text_dir(self) -> Path:
        return self.data_dir / "text_files"

    @property
    def vector_store_dir(self) -> Path:
        return self.data_dir / "vector_store"

    @property
    def chat_db_path(self) -> Path:
        return self.data_dir / "cora_history.db"

    @property
    def audit_db_path(self) -> Path:
        return self.data_dir / "cora_audit.db"

    def ensure_directories(self) -> None:
        for directory in (self.data_dir, self.pdf_dir, self.text_dir, self.vector_store_dir):
            directory.mkdir(parents=True, exist_ok=True)


_settings: "Settings | None" = None


def get_settings() -> Settings:
    """Devuelve la instancia única (singleton) de configuración de CORA."""
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.ensure_directories()
    return _settings
