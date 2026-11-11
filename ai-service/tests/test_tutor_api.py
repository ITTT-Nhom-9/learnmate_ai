import json
from typing import AsyncIterator, List, Optional
from fastapi.testclient import TestClient

from app.adapters.base_adapter import LLMMessage, LLMProvider, LLMResponse, LLMStreamChunk
from app.core.config import settings
from app.core.exceptions import LLMRateLimitError
from app.main import app
from app.routers.tutor_router import get_tutor_llm_adapter

client = TestClient(app)


class FakeLLMAdapter(LLMProvider):
    provider_name = "gemini"

    def __init__(self, should_fail_stream: bool = False) -> None:
        self.captured_system_prompt: Optional[str] = None
        self.captured_messages: List[LLMMessage] = []
        self.should_fail_stream = should_fail_stream

    async def chat(
        self,
        messages: List[LLMMessage],
        *,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        response_mime_type: Optional[str] = None,
    ) -> LLMResponse:
        self.captured_system_prompt = system_prompt
        self.captured_messages = messages
        return LLMResponse(
            content="Đây là câu trả lời từ Gemini.",
            provider="gemini",
            model="gemini-3.5-flash-lite",
            tokens_prompt=25,
            tokens_completion=15,
            total_tokens=40,
            latency_ms=120,
        )

    async def stream(
        self,
        messages: List[LLMMessage],
        *,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[LLMStreamChunk]:
        self.captured_system_prompt = system_prompt
        self.captured_messages = messages
        if self.should_fail_stream:
            raise LLMRateLimitError("Simulated 429")
        yield LLMStreamChunk(delta="Phần 1. ", done=False)
        yield LLMStreamChunk(delta="Phần 2.", done=False)
        yield LLMStreamChunk(
            delta="",
            done=True,
            tokens_prompt=10,
            tokens_completion=8,
            total_tokens=18,
            latency_ms=85,
        )


def test_tutor_chat_requires_internal_api_key():
    resp_missing = client.post("/ai/tutor/chat", json={"message": "Hello"})
    assert resp_missing.status_code == 401

    resp_wrong = client.post(
        "/ai/tutor/chat",
        headers={"X-API-Key": "wrong_key"},
        json={"message": "Hello"},
    )
    assert resp_wrong.status_code == 401


def test_tutor_chat_success_with_prompt_isolation(monkeypatch):
    monkeypatch.setattr(settings, "INTERNAL_API_KEY", "test_internal_key")
    fake_adapter = FakeLLMAdapter()
    app.dependency_overrides[get_tutor_llm_adapter] = lambda: fake_adapter

    try:
        resp = client.post(
            "/ai/tutor/chat",
            headers={"X-API-Key": "test_internal_key"},
            json={
                "message": "Giải thích đệ quy?",
                "lesson_context": "Bài 3: Hàm và Đệ quy",
                "history": [
                    {"role": "user", "content": "Hàm là gì?"},
                    {"role": "assistant", "content": "Hàm là khối mã tái sử dụng."},
                ],
                "temperature": 0.5,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    data = resp.json()
    assert data["reply"] == "Đây là câu trả lời từ Gemini."
    assert data["provider"] == "gemini"
    assert data["model"] == "gemini-3.5-flash-lite"
    assert data["usage"] == {
        "tokens_prompt": 25,
        "tokens_completion": 15,
        "total_tokens": 40,
        "latency_ms": 120,
    }

    assert "<lesson_context>" in (fake_adapter.captured_system_prompt or "")
    assert "Bài 3: Hàm và Đệ quy" in (fake_adapter.captured_system_prompt or "")
    assert len(fake_adapter.captured_messages) == 3
    assert fake_adapter.captured_messages[-1].role == "user"
    assert fake_adapter.captured_messages[-1].content.startswith("<student_query>")
    assert "Giải thích đệ quy?" in fake_adapter.captured_messages[-1].content


def test_tutor_stream_sse_success(monkeypatch):
    monkeypatch.setattr(settings, "INTERNAL_API_KEY", "test_internal_key")
    fake_adapter = FakeLLMAdapter()
    app.dependency_overrides[get_tutor_llm_adapter] = lambda: fake_adapter

    try:
        resp = client.post(
            "/ai/tutor/stream",
            headers={"X-API-Key": "test_internal_key"},
            json={"message": "Giải thích biến trong Python"},
        )
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")

    events = []
    for line in resp.text.splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[len("data: ") :]))

    assert len(events) == 3
    assert events[0] == {"delta": "Phần 1. ", "done": False}
    assert events[1] == {"delta": "Phần 2.", "done": False}
    assert events[2]["done"] is True
    assert events[2]["total_tokens"] == 18


def test_tutor_stream_sse_emits_error_event(monkeypatch):
    monkeypatch.setattr(settings, "INTERNAL_API_KEY", "test_internal_key")
    fake_adapter = FakeLLMAdapter(should_fail_stream=True)
    app.dependency_overrides[get_tutor_llm_adapter] = lambda: fake_adapter

    try:
        resp = client.post(
            "/ai/tutor/stream",
            headers={"X-API-Key": "test_internal_key"},
            json={"message": "Test error"},
        )
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert "event: error" in resp.text
    assert "LLM_RATE_LIMIT" in resp.text

