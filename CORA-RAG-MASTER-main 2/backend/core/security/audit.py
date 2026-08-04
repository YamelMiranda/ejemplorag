"""Puerto de auditoría — Pilar III (Gobernanza y Trazabilidad).

Toda acción relevante del sistema (subida de documento, consulta al LLM,
eliminación de un documento) se registra a través de `AuditLogger`. El
adapter concreto que persiste estos eventos en SQLite vive en
`backend/infrastructure/persistence/sqlite/audit_repository.py`; este módulo
solo define el contrato y el evento, para que los casos de uso no dependan
de un motor de persistencia concreto.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class AuditEvent:
    actor: str
    action: str
    resource: str
    success: bool
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AuditLogger(ABC):
    """Puerto de auditoría. Cada evento debe quedar registrado de forma
    verificable e inmutable para soportar auditorías y cumplimiento normativo."""

    @abstractmethod
    def record(self, event: AuditEvent) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_events(self, since: Optional[datetime] = None) -> List[AuditEvent]:
        """Eventos más recientes primero. `since=None` trae todo el
        historial disponible."""
        raise NotImplementedError


class NullAuditLogger(AuditLogger):
    """Adapter de último recurso (no persiste nada) — solo para tests o
    entornos donde el repositorio de auditoría aún no está disponible. El
    adapter real (SQLite) debe usarse siempre en producción."""

    def record(self, event: AuditEvent) -> None:
        return None

    def list_events(self, since: Optional[datetime] = None) -> List[AuditEvent]:
        return []
