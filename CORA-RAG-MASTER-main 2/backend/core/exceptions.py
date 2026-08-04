"""Jerarquía de excepciones de dominio de CORA.

Los adapters (FastAPI, ChromaDB, Groq, etc.) no deben filtrarse hacia los
casos de uso ni el dominio: cualquier fallo se traduce a una de estas
excepciones, y es la capa API (backend/api) la que las mapea a códigos HTTP.
"""


class CoraError(Exception):
    """Error base del que heredan todos los errores de dominio de CORA."""


class ValidationError(CoraError):
    """Un dato de entrada no cumple las reglas de negocio (p. ej. extensión no permitida)."""


class NotFoundError(CoraError):
    """El recurso solicitado (documento, chat, mensaje) no existe."""


class IngestionError(CoraError):
    """Falló la carga, el chunking o el embedding de un documento durante la ingesta."""


class RetrievalError(CoraError):
    """Falló la recuperación de contexto contra el Repositorio de Conocimiento."""


class GenerationError(CoraError):
    """El proveedor de LLM no pudo generar una respuesta (config faltante, error del proveedor)."""


class AuthenticationError(CoraError):
    """No hay una sesión válida (falta, expiró o el token fue manipulado)."""


class AuthorizationError(CoraError):
    """El principal actual está autenticado pero no tiene permiso para la acción solicitada."""
