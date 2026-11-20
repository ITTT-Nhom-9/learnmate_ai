"""Kiểm thử RAG Router trong AI Microservice (TK-25)."""
from typing import AsyncIterator, List, Optional
import pytest
from fastapi.testclient import TestClient

from app.adapters.base_adapter import LLMMessage, LLMProvider, LLMResponse, LLMStreamChunk
from app.core.config import settings
from app.main import app
from app.routers.rag_router import get_rag_llm_adapter

client = TestClient(app)
AUTH_HEADERS = {"X-API-Key": settings.INTERNAL_API_KEY}


class FakeRAGAdapter(LLMProvider):
    provider_name = "gemini"

    async def chat(
        self,
        messages: List[LLMMessage],
        *,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        response_mime_type: Optional[str] = None,
    ) -> LLMResponse:
        return LLMResponse(
            content="Khóa chính là tập thuộc tính xác định duy nhất một bộ [Trang 7 - CSDL.pdf].",
            provider="gemini",
            model="gemini-1.5-flash",
            tokens_prompt=20,
            tokens_completion=15,
            total_tokens=35,
            latency_ms=50,
        )

    async def stream(
        self,
        messages: List[LLMMessage],
        *,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[LLMStreamChunk]:
        raise NotImplementedError


def test_ai_rag_query_unauthorized():
    """Từ chối nếu thiếu hoặc sai API key nội bộ (401)."""
    res = client.post("/ai/rag/query", json={"query": "test"})
    assert res.status_code == 401


def test_ai_rag_query_out_of_scope_when_no_context():
    """Trả về cảnh báo ngoài phạm vi khi không có đoạn context nào."""
    payload = {
        "query": "Hệ điều hành Linux là gì?",
        "context_chunks": [],
    }
    res = client.post("/ai/rag/query", json=payload, headers=AUTH_HEADERS)
    assert res.status_code == 200
    data = res.json()
    assert data["is_out_of_scope"] is True
    assert "nằm ngoài phạm vi" in data["answer"]
    assert data["citations"] == []


def test_ai_rag_query_with_context_and_citations():
    """Xử lý câu hỏi có ngữ cảnh và trả về danh sách trích dẫn số trang."""
    fake_adapter = FakeRAGAdapter()
    app.dependency_overrides[get_rag_llm_adapter] = lambda: fake_adapter

    try:
        payload = {
            "query": "Khóa chính trong CSDL là gì?",
            "context_chunks": [
                {
                    "chunk_id": 101,
                    "document_id": 1,
                    "file_name": "CSDL.pdf",
                    "page_number": 7,
                    "content": "Khóa chính là tập thuộc tính xác định duy nhất một bộ.",
                    "similarity": 0.85,
                }
            ],
        }
        res = client.post("/ai/rag/query", json=payload, headers=AUTH_HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert data["is_out_of_scope"] is False
        assert len(data["citations"]) == 1
        assert data["citations"][0]["page_number"] == 7
        assert data["citations"][0]["file_name"] == "CSDL.pdf"
        assert "Khóa chính" in data["answer"]
        assert data["tokens_prompt"] == 20
        assert data["tokens_completion"] == 15
        assert data["total_tokens"] == 35
    finally:
        app.dependency_overrides.clear()
