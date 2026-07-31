import asyncio
import json

import httpx

from app.chat_service import ChatService
from app.config import Settings
from app.web_search import (
    TavilyWebSearch,
    WebSearchResponse,
    WebSearchResult,
)


def web_settings() -> Settings:
    return Settings(
        tavily_api_key="test-key",
        tavily_api_base_url="https://api.tavily.test",
        tavily_search_depth="basic",
        tavily_max_results=5,
    )


def test_web_search_requires_explicit_user_intent():
    assert TavilyWebSearch.requested(
        "Tìm trên web lịch phát hành Python phiên bản mới nhất"
    )
    assert TavilyWebSearch.requested("latest news về AI agents")
    assert TavilyWebSearch.requested("Biết Độ Mixi không?")
    assert TavilyWebSearch.requested("Tavily là gì?")
    assert not TavilyWebSearch.requested(
        "Team mình đang chốt việc gì và còn blocker nào?"
    )
    assert not TavilyWebSearch.requested(
        "Giảng viên giải thích Transformer là gì?"
    )


def test_search_query_removes_only_web_command_and_keeps_vietnamese():
    query = TavilyWebSearch.search_query(
        "Tìm trên web lịch phát hành Python mới nhất"
    )
    assert query == "lịch phát hành Python mới nhất"


def test_tavily_search_uses_bearer_auth_and_parses_safe_results():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://api.tavily.test/search"
        assert request.headers["Authorization"] == "Bearer test-key"
        payload = json.loads(request.content)
        assert payload["query"] == "Python 3.14 release date"
        assert payload["search_depth"] == "basic"
        assert payload["max_results"] == 5
        assert payload["include_raw_content"] is False
        assert "api_key" not in payload
        assert "safe_search" not in payload
        return httpx.Response(
            200,
            json={
                "query": payload["query"],
                "answer": "Python 3.14 was released in October 2025.",
                "results": [
                    {
                        "title": "Python 3.14 release",
                        "url": "https://python.org/downloads/release/python-3140/",
                        "content": "Python 3.14.0 is the newest major release.",
                        "score": 0.98,
                        "published_date": "2025-10-07",
                    },
                    {
                        "title": "Unsafe URL",
                        "url": "javascript:alert(1)",
                        "content": "Must be discarded.",
                    },
                ],
            },
        )

    async def run_search() -> WebSearchResponse:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as client:
            service = TavilyWebSearch(web_settings(), client)
            return await service.search(
                "Tìm kiếm web Python 3.14 release date"
            )

    response = asyncio.run(run_search())

    assert response.answer == "Python 3.14 was released in October 2025."
    assert len(response.results) == 1
    assert response.results[0].domain == "python.org"


def test_latest_news_keeps_freshness_terms_and_uses_news_window():
    service = TavilyWebSearch(web_settings())
    payload = service._payload("Tin tức mới nhất về AI agents")

    assert payload["query"] == "Tin tức mới nhất về AI agents"
    assert payload["topic"] == "news"
    assert payload["time_range"] == "week"


def test_web_answer_cleanup_and_citation_are_web_specific():
    result = WebSearchResult(
        title="Tavily documentation",
        url="https://docs.tavily.com/documentation/api-reference/endpoint/search",
        content="Search API documentation.",
    )

    citation = ChatService._web_citation(result)
    answer = ChatService._clean_web_answer(
        "<think>hidden</think>Tavily có Search API. [W1]"
    )

    assert citation.channel_id == "web"
    assert citation.channel_name == "docs.tavily.com"
    assert citation.permalink == result.url
    assert answer == "Tavily có Search API."
