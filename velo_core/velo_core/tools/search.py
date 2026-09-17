import httpx
import logging
from typing import Optional
from bs4 import BeautifulSoup
from velo_core.tools.base import tool, register_tool

logger = logging.getLogger(__name__)


@tool(
    name="search_web",
    description="Search the web using DuckDuckGo HTML (no API key required)",
    requires_permission=False,
)
async def search_web(query: str, max_results: int = 5) -> str:
    try:
        url = "https://html.duckduckgo.com/html/"
        params = {"q": query}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, data=params, headers=headers)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        results = []

        for result in soup.select(".result__snippet")[:max_results]:
            text = result.get_text(strip=True)
            if text:
                results.append(text)

        if not results:
            # Fallback selector
            for result in soup.select(".web-result-description")[:max_results]:
                text = result.get_text(strip=True)
                if text:
                    results.append(text)

        if not results:
            return "No results found"

        return "\n\n".join(f"{i+1}. {r}" for i, r in enumerate(results))

    except Exception as e:
        logger.error(f"Search error: {e}")
        return f"Search error: {str(e)}"


register_tool(search_web)