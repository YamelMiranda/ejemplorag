"""Puerto hacia el proveedor de LLM que genera las respuestas de CORA."""
from __future__ import annotations

from abc import ABC, abstractmethod


class LLMPort(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        raise NotImplementedError
