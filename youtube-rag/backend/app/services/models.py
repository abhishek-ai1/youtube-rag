"""Ollama model management service."""

import logging
from typing import List, Dict

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class ModelService:
    """Queries Ollama to list and validate available models."""

    @staticmethod
    async def list_available() -> List[Dict[str, str]]:
        """
        Return the models that are both configured AND pulled in Ollama.
        """
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
                resp.raise_for_status()
                data = resp.json()

            pulled = {m["name"] for m in data.get("models", [])}
            result = []
            for name in settings.AVAILABLE_MODELS:
                # Ollama may store names with :latest suffix
                is_available = name in pulled or f"{name}:latest" in pulled
                result.append(
                    {"name": name, "available": is_available}
                )

            return result

        except httpx.HTTPError as exc:
            logger.error("Cannot reach Ollama: %s", exc)
            return [
                {"name": name, "available": False}
                for name in settings.AVAILABLE_MODELS
            ]
