"""Punto de entrada de CORA.

La implementación real vive en `backend/api/main.py` (capa API de la
arquitectura por capas: core, domain, application, infrastructure, api).
Este archivo se mantiene en la raíz solo por compatibilidad con:

    uvicorn main:app --reload --port 8000
"""
from backend.api.main import app

__all__ = ["app"]
