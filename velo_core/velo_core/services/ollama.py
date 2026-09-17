import logging
from typing import Any
from ollama import AsyncClient
from velo_core.config import get_settings
from velo_core.models.schemas import ToolSchema

logger = logging.getLogger(__name__)


class OllamaService:
    def __init__(self):
        self.settings = get_settings()
        self.client = AsyncClient(host=self.settings.ollama_url)
        self.model = self.settings.ollama_model

    def _convert_tools(self, tools: list[ToolSchema]) -> list[dict[str, Any]]:
        """Convert ToolSchema to Ollama tool format."""
        ollama_tools = []
        for tool in tools:
            ollama_tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            })
        return ollama_tools

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolSchema] | None = None,
    ) -> Any:
        """Send chat request to Ollama with optional tools."""
        kwargs = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        if tools:
            kwargs["tools"] = self._convert_tools(tools)

        logger.debug(f"Ollama request: {kwargs}")
        response = await self.client.chat(**kwargs)
        logger.debug(f"Ollama response: {response}")
        return response

    async def generate(self, prompt: str) -> str:
        """Simple generation without tools."""
        response = await self.client.generate(
            model=self.model,
            prompt=prompt,
            stream=False,
        )
        return response.response

    async def health_check(self) -> bool:
        try:
            await self.client.list()
            return True
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False