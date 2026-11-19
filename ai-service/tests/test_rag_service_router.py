"""Kiểm thử RAG Router trong AI Microservice (TK-25)."""
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)
AUTH_HEADERS = {"X-API-Key": settings.INTERNAL_API_KEY}


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
    assert data["answer"] != ""
