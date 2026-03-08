"""
Serper API Client — Grey Zone Web Search (Ch 17.3)
Uses Serper.dev API to search the web when Amma needs context for grey-zone classification.
"""
import os
from typing import Optional, Dict, Any, List


SERPER_API_URL = "https://google.serper.dev/search"


class SerperClient:
    """Searches the web via Serper.dev to help classify grey-zone apps/sites."""

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.environ.get("SERPER_API_KEY", "")
        self._available = bool(self.api_key)

    @property
    def is_available(self) -> bool:
        return self._available

    async def search(self, query: str, num_results: int = 3) -> Optional[Dict[str, Any]]:
        """Run a web search. Returns raw Serper JSON or None."""
        if not self._available:
            return None
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    SERPER_API_URL,
                    json={"q": query, "num": num_results},
                    headers={
                        "X-API-KEY": self.api_key,
                        "Content-Type": "application/json",
                    },
                    timeout=5.0,
                )
                if response.status_code == 200:
                    return response.json()
        except ImportError:
            print("[Serper] httpx not installed — web search disabled.")
            self._available = False
        except Exception as e:
            print(f"[Serper] Search error: {e}")
        return None

    async def get_grey_zone_context(self, app: str, window_title: str = "") -> Optional[str]:
        """Search for context about a grey-zone app to help Gemini classify it.

        Returns a short context string with web snippets, or None.
        """
        query = f"{app} {window_title}".strip()[:80]
        results = await self.search(query, num_results=3)
        if not results:
            return None

        snippets: List[str] = []
        for item in results.get("organic", [])[:3]:
            snippet = item.get("snippet", "")
            if snippet:
                snippets.append(snippet[:200])

        return " | ".join(snippets) if snippets else None
