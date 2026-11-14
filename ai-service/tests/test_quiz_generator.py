"""Bộ kiểm thử cho phân hệ Sinh đề trắc nghiệm AI Quiz (TK-15 / Phân hệ 5).

Kiểm tra:
1. Bóc tách JSON từ phản hồi LLM (extract_json_object).
2. Kiểm định tính toàn vẹn câu hỏi trắc nghiệm theo BR-06 (4 phương án A-B-C-D, 1 đáp án đúng).
3. Cơ chế tự động thử lại tối đa 2 lần khi gặp lỗi cấu trúc (BR-06 auto-retry).
4. Endpoint POST /ai/quiz/generate (FastAPI TestClient) bảo mật qua X-API-Key.
"""
import json
from typing import AsyncIterator, List, Optional
import pytest
from fastapi.testclient import TestClient

from app.adapters.base_adapter import LLMMessage, LLMProvider, LLMResponse, LLMStreamChunk
from app.core.config import settings
from app.core.exceptions import AIException
from app.main import app
from app.routers.quiz_router import get_quiz_llm_adapter
from app.schemas.quiz_schema import (
    QuizBundleOut,
    QuizDifficultyEnum,
    QuizGenerationSpec,
    QuizOptionDTO,
    QuizQuestionSpec,
)
from app.services.quiz_validator import (
    extract_json_object,
    generate_and_validate_quiz,
    validate_quiz_json,
)

client = TestClient(app)

SAMPLE_VALID_QUIZ_JSON = {
    "title": "Trắc nghiệm: Cây nhị phân tìm kiếm BST",
    "difficulty": "MEDIUM",
    "total_questions": 2,
    "questions": [
        {
            "content": "Chiều cao trung bình của cây nhị phân tìm kiếm cân bằng có n nút là bao nhiêu?",
            "options": [
                {"opt_label": "A", "content": "O(n)", "is_correct": False},
                {"opt_label": "B", "content": "O(log n)", "is_correct": True},
                {"opt_label": "C", "content": "O(n log n)", "is_correct": False},
                {"opt_label": "D", "content": "O(1)", "is_correct": False},
            ],
            "explanation": "Cây cân bằng loại bỏ một nửa số nút sau mỗi phép so sánh nên chiều cao là log2(n).",
        },
        {
            "content": "Trường hợp xấu nhất của tìm kiếm trong BST xảy ra khi nào?",
            "options": [
                {"opt_label": "A", "content": "Cây cân bằng hoàn hảo", "is_correct": False},
                {"opt_label": "B", "content": "Cây suy biến thành danh sách liên kết", "is_correct": True},
                {"opt_label": "C", "content": "Khóa cần tìm nằm ở nút gốc", "is_correct": False},
                {"opt_label": "D", "content": "Cây có số nút chẵn", "is_correct": False},
            ],
            "explanation": "Khi chèn các phần tử có thứ tự tăng dần, cây suy biến thành đường thẳng chiều cao n-1.",
        },
    ],
}


class MockQuizAdapter(LLMProvider):
    provider_name = "gemini"

    def __init__(self, responses: Optional[List[str]] = None):
        self.responses = responses or [json.dumps(SAMPLE_VALID_QUIZ_JSON, ensure_ascii=False)]
        self.call_count = 0
        self.captured_messages: List[LLMMessage] = []

    async def chat(
        self,
        messages: List[LLMMessage],
        *,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
        response_mime_type: Optional[str] = None,
    ) -> LLMResponse:
        self.captured_messages = messages
        idx = min(self.call_count, len(self.responses) - 1)
        resp_text = self.responses[idx]
        self.call_count += 1

        return LLMResponse(
            content=resp_text,
            provider="gemini",
            model="gemini-3.5-flash-lite",
            tokens_prompt=40,
            tokens_completion=80,
            total_tokens=120,
            latency_ms=250,
        )

    async def stream(
        self,
        messages: List[LLMMessage],
        *,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[LLMStreamChunk]:
        yield LLMStreamChunk(delta="unused", done=True)


# ==============================================================================
# 1. KIỂM THỬ TRÍCH XUẤT VÀ VALIDATE SCHEMA JSON
# ==============================================================================

def test_extract_json_object_from_markdown_block():
    raw = f"Dưới đây là đề thi:\n```json\n{json.dumps(SAMPLE_VALID_QUIZ_JSON)}\n```\nChúc bạn làm tốt!"
    extracted = extract_json_object(raw)
    assert extracted["title"] == SAMPLE_VALID_QUIZ_JSON["title"]
    assert len(extracted["questions"]) == 2


def test_validate_quiz_json_success():
    bundle = validate_quiz_json(SAMPLE_VALID_QUIZ_JSON)
    assert isinstance(bundle, QuizBundleOut)
    assert len(bundle.questions) == 2
    assert bundle.questions[0].options[1].is_correct is True


def test_validate_quiz_json_fails_when_missing_options():
    invalid_data = {
        "title": "Quiz lỗi",
        "total_questions": 1,
        "questions": [
            {
                "content": "Câu hỏi thiếu phương án?",
                "options": [
                    {"opt_label": "A", "content": "A", "is_correct": True},
                    {"opt_label": "B", "content": "B", "is_correct": False},
                ],  # Thiếu C và D
                "explanation": "Giải thích",
            }
        ],
    }
    with pytest.raises(Exception):
        validate_quiz_json(invalid_data)


def test_validate_quiz_json_fails_when_multiple_correct_options():
    invalid_data = {
        "title": "Quiz lỗi 2 đáp án đúng",
        "total_questions": 1,
        "questions": [
            {
                "content": "Câu hỏi có 2 đáp án đúng?",
                "options": [
                    {"opt_label": "A", "content": "A", "is_correct": True},
                    {"opt_label": "B", "content": "B", "is_correct": True},  # Vi phạm: 2 đáp án True
                    {"opt_label": "C", "content": "C", "is_correct": False},
                    {"opt_label": "D", "content": "D", "is_correct": False},
                ],
                "explanation": "Giải thích",
            }
        ],
    }
    with pytest.raises(Exception):
        validate_quiz_json(invalid_data)


# ==============================================================================
# 2. KIỂM THỬ CƠ CHẾ AUTO-RETRY TỐI ĐA 2 LẦN (BR-06)
# ==============================================================================

@pytest.mark.asyncio
async def test_auto_retry_recovers_on_second_attempt():
    """Lần 1 LLM trả về chuỗi lỗi cú pháp, lần 2 trả về JSON hợp lệ -> thành công."""
    adapter = MockQuizAdapter(
        responses=[
            "Đây không phải là JSON hợp lệ { malformed",  # Lần 1: Lỗi cú pháp
            json.dumps(SAMPLE_VALID_QUIZ_JSON),            # Lần 2: Thành công
        ]
    )
    spec = QuizGenerationSpec(
        lesson_title="Cấu trúc dữ liệu",
        lesson_content="Nội dung bài học BST...",
        num_questions=2,
    )
    bundle, prompt_tok, comp_tok, total_tok, latency = await generate_and_validate_quiz(
        spec=spec,
        system_prompt="system prompt",
        adapter=adapter,
        max_retries=2,
    )
    assert adapter.call_count == 2
    assert len(bundle.questions) == 2


@pytest.mark.asyncio
async def test_auto_retry_exceeds_max_retries_raises_exception():
    """Cả 3 lượt (1 chính + 2 retry) đều lỗi -> ném ngoại lệ AIException QUIZ_SCHEMA_INVALID."""
    adapter = MockQuizAdapter(
        responses=[
            "Lỗi lần 1",
            "Lỗi lần 2",
            "Lỗi lần 3",
        ]
    )
    spec = QuizGenerationSpec(
        lesson_title="Bài học lỗi",
        lesson_content="Nội dung...",
        num_questions=2,
    )
    with pytest.raises(AIException) as excinfo:
        await generate_and_validate_quiz(
            spec=spec,
            system_prompt="system prompt",
            adapter=adapter,
            max_retries=2,
        )
    assert excinfo.value.error_code == "QUIZ_SCHEMA_INVALID"
    assert adapter.call_count == 3  # Đã thử đủ 3 lần


# ==============================================================================
# 3. KIỂM THỬ ENDPOINT POST /ai/quiz/generate
# ==============================================================================

def test_quiz_generate_endpoint_success():
    app.dependency_overrides[get_quiz_llm_adapter] = lambda: MockQuizAdapter()
    try:
        response = client.post(
            "/ai/quiz/generate",
            headers={"X-API-Key": settings.INTERNAL_API_KEY},
            json={
                "lesson_title": "Cây nhị phân tìm kiếm",
                "topic_name": "Độ phức tạp thuật toán",
                "lesson_content": "Cây nhị phân cân bằng có chiều cao log2(n)...",
                "num_questions": 2,
                "difficulty": "MEDIUM",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "bundle" in data
        assert len(data["bundle"]["questions"]) == 2
        assert data["bundle"]["difficulty"] == "MEDIUM"
        assert data["provider"] == "gemini"
        assert data["usage"]["total_tokens"] > 0
    finally:
        app.dependency_overrides.pop(get_quiz_llm_adapter, None)


def test_quiz_generate_endpoint_unauthorized():
    response = client.post(
        "/ai/quiz/generate",
        headers={"X-API-Key": "sai_key"},
        json={
            "lesson_title": "Bài học",
            "lesson_content": "Nội dung...",
        },
    )
    assert response.status_code == 401
