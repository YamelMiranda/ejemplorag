"""Adapter hacia Groq como proveedor de LLM."""
from __future__ import annotations

from langchain_groq import ChatGroq

from backend.application.ports.llm_port import LLMPort
from backend.core.exceptions import GenerationError


class GroqLLM(LLMPort):
    def __init__(self, api_key: str, model_name: str, temperature: float = 0.1, max_tokens: int = 1024):
        if not api_key:
            raise GenerationError(
                "No se encontró GROQ_API_KEY. Configúrala en el archivo .env "
                "(ver .env.example) para que CORA pueda generar respuestas."
            )
        self._client = ChatGroq(
            api_key=api_key,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def generate(self, prompt: str) -> str:
        try:
            response = self._client.invoke([prompt])
        except Exception as exc:
            raise GenerationError(f"El proveedor de LLM falló al generar la respuesta: {exc}") from exc
        return response.content
