"""Logging estructurado de CORA.

Reemplaza los `print()` dispersos en el código original. Todo evento de
seguridad relevante (ingesta, consulta, auth) debe pasar además por
`backend.core.security.audit`, que persiste en el registro de auditoría —
este módulo es solo para diagnóstico operativo, no es la fuente de verdad
de trazabilidad (Pilar III).
"""
import logging
import os
import sys

_CONFIGURED = False


def _configure() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level_name, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
        stream=sys.stdout,
    )
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    _configure()
    return logging.getLogger(name)
