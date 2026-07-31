from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata
from urllib.parse import urlparse

import httpx

from .config import Settings


WEB_SEARCH_TERMS = (
    "web search",
    "search web",
    "search the web",
    "tim web",
    "tim tren web",
    "tim kiem web",
    "tim tren internet",
    "tim kiem internet",
    "tra cuu web",
    "tra cuu internet",
    "tra cuu online",
    "tren mang",
    "nguon web",
    "tin tuc moi nhat",
    "latest news",
)
WEB_SEARCH_COMMAND_PHRASES = (
    "web search",
    "search web",
    "search the web",
    "tìm web",
    "tìm trên web",
    "tìm kiếm web",
    "tìm trên internet",
    "tìm kiếm internet",
    "tra cứu web",
    "tra cứu internet",
    "tra cứu online",
    "trên mạng",
    "nguồn web",
)
INTERNAL_CONTEXT_TERMS = (
    "team minh",
    "nhom minh",
    "t004",
    "t009",
    "discord",
    "kenh",
    "channel",
    "mentor",
    "g10",
    "bai giang",
    "giang vien",
    "slide",
    "transcript",
    "transformer",
    "attention",
    "deadline",
    "blocker",
    "viec cua minh",
    "memory",
    "workshop",
    "hackathon",
)
PUBLIC_QUESTION_PATTERNS = (
    r"^(?:ban co )?biet .+ (?:khong|ko)\??$",
    r"^.+ la ai\??$",
    r"^.+ la gi\??$",
    r"^(?:ai|what|who) (?:la|is) .+",
)
FRESHNESS_TERMS = (
    "moi nhat",
    "gan day",
    "hien nay",
    "hom nay",
    "latest",
    "today",
    "current",
)
VALID_SEARCH_DEPTHS = {"basic", "advanced", "fast", "ultra-fast"}


def _plain(value: str) -> str:
    decomposed = unicodedata.normalize(
        "NFD",
        value.casefold().replace("đ", "d"),
    )
    without_accents = "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    )
    return re.sub(r"\s+", " ", without_accents).strip()


@dataclass(frozen=True)
class WebSearchResult:
    title: str
    url: str
    content: str
    score: float | None = None
    published_date: str | None = None

    @property
    def domain(self) -> str:
        return urlparse(self.url).netloc.removeprefix("www.")


@dataclass(frozen=True)
class WebSearchResponse:
    query: str
    results: list[WebSearchResult]
    answer: str | None = None


class WebSearchError(RuntimeError):
    pass


class TavilyWebSearch:
    """Explicit-intent web search that never sends retrieved private context."""

    def __init__(
        self,
        settings: Settings,
        client: httpx.AsyncClient | None = None,
    ):
        self.settings = settings
        self.client = client

    @property
    def configured(self) -> bool:
        return bool(self.settings.tavily_api_key)

    @staticmethod
    def explicitly_requested(query: str) -> bool:
        value = _plain(query)
        return any(term in value for term in WEB_SEARCH_TERMS)

    @classmethod
    def requested(cls, query: str) -> bool:
        value = _plain(query)
        if cls.explicitly_requested(query):
            return True
        if any(term in value for term in INTERNAL_CONTEXT_TERMS):
            return False
        return (
            any(term in value for term in FRESHNESS_TERMS)
            or any(
                re.search(pattern, value)
                for pattern in PUBLIC_QUESTION_PATTERNS
            )
        )

    @staticmethod
    def search_query(query: str) -> str:
        value = query.strip()
        for phrase in WEB_SEARCH_COMMAND_PHRASES:
            value = re.sub(
                re.escape(phrase),
                " ",
                value,
                flags=re.IGNORECASE,
            )
        cleaned = re.sub(r"\s+", " ", value).strip(" .,:;!?")
        return cleaned or query.strip()

    def _payload(self, query: str) -> dict:
        search_depth = self.settings.tavily_search_depth.casefold()
        if search_depth not in VALID_SEARCH_DEPTHS:
            search_depth = "basic"
        normalized_query = _plain(query)
        is_news = any(
            term in normalized_query
            for term in ("tin tuc moi nhat", "latest news")
        )
        payload = {
            "query": self.search_query(query),
            "search_depth": search_depth,
            "max_results": min(max(self.settings.tavily_max_results, 1), 10),
            "topic": "news" if is_news else "general",
            "include_answer": "basic",
            "include_raw_content": False,
            "include_images": False,
        }
        if is_news:
            payload["time_range"] = "week"
        return payload

    @staticmethod
    def _parse(body: dict, fallback_query: str) -> WebSearchResponse:
        results: list[WebSearchResult] = []
        for raw in body.get("results") or []:
            title = str(raw.get("title") or "").strip()
            url = str(raw.get("url") or "").strip()
            content = str(raw.get("content") or "").strip()
            parsed_url = urlparse(url)
            if (
                not title
                or not content
                or parsed_url.scheme not in {"http", "https"}
                or not parsed_url.netloc
            ):
                continue
            score = raw.get("score")
            results.append(
                WebSearchResult(
                    title=title[:240],
                    url=url,
                    content=content[:1800],
                    score=float(score) if isinstance(score, (int, float)) else None,
                    published_date=(
                        str(raw["published_date"])[:40]
                        if raw.get("published_date")
                        else None
                    ),
                )
            )
        answer = str(body.get("answer") or "").strip() or None
        return WebSearchResponse(
            query=str(body.get("query") or fallback_query),
            results=results,
            answer=answer,
        )

    async def search(self, query: str) -> WebSearchResponse:
        if not self.configured:
            raise WebSearchError("Tavily chưa được cấu hình.")
        headers = {
            "Authorization": f"Bearer {self.settings.tavily_api_key}",
            "Content-Type": "application/json",
        }
        endpoint = f"{self.settings.tavily_api_base_url.rstrip('/')}/search"
        try:
            if self.client is not None:
                response = await self.client.post(
                    endpoint,
                    headers=headers,
                    json=self._payload(query),
                    timeout=20.0,
                )
            else:
                async with httpx.AsyncClient(timeout=20.0) as client:
                    response = await client.post(
                        endpoint,
                        headers=headers,
                        json=self._payload(query),
                    )
            response.raise_for_status()
            body = response.json()
            if not isinstance(body, dict):
                raise WebSearchError("Tavily trả về dữ liệu không hợp lệ.")
        except (httpx.HTTPError, ValueError) as exc:
            raise WebSearchError("Không gọi được Tavily Search.") from exc

        parsed = self._parse(body, self.search_query(query))
        if not parsed.results:
            raise WebSearchError("Tavily không trả về nguồn web phù hợp.")
        return parsed
