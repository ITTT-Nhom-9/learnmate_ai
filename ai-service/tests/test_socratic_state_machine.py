"""Bộ kiểm thử đơn vị cho cỗ máy trạng thái Socratic 5 giai đoạn (TK-14 / Phân hệ 4).

Kiểm tra:
1. 5 giai đoạn chuyển trạng thái sư phạm: Khám phá -> Thử thách -> Gợi ý -> Đúc kết -> Đánh giá.
2. Quy tắc nghiệp vụ BR-02:
   - Tối đa 5 bước hỏi đáp gợi mở.
   - Tuyệt đối không đưa ra đáp án/lời giải ở các bước 1-4.
   - Tự động tổng kết và đưa lời giải ở bước 5.
3. Luồng ngoại lệ 4a (SRS):
   - Sinh viên sai / không biết 2 lần liên tiếp -> kích hoạt gợi ý tăng cường (PROVIDE_INTENSIVE_HINT).
4. Khả năng kết thúc sớm khi sinh viên trả lời đúng hoàn toàn (CORRECT).
5. Bộ lọc bảo vệ chống lộ đáp án (Anti-Spoiler Guardian).
6. Bộ phân tích trạng thái JSON và Markdown (parse_socratic_response).
7. Các endpoint POST /ai/socratic/chat và POST /ai/socratic/stream (FastAPI TestClient).
"""
import json
from typing import AsyncIterator, List, Optional
import pytest
from fastapi.testclient import TestClient

from app.adapters.base_adapter import LLMMessage, LLMProvider, LLMResponse, LLMStreamChunk
from app.core.config import settings
from app.main import app
from app.routers.socratic_router import get_socratic_llm_adapter
from app.schemas.socratic_schema import (
    MAX_SOCRATIC_STEPS,
    SocraticFeedback,
    SocraticStage,
    StudentEvaluation,
)
from app.services.socratic_state_machine import SocraticStateMachine, StateTransitionResult

client = TestClient(app)


class FakeSocraticAdapter(LLMProvider):
    provider_name = "gemini"

    def __init__(self, canned_response: Optional[str] = None):
        self.canned_response = canned_response or (
            "**Bước 2/5 – Thử thách**\n\n"
            "Bạn đã nhận thấy cây có thể nghiêng về một phía.\n\n"
            "**Câu hỏi:** Nếu cây có n nút nhưng chỉ có nhánh phải, chiều cao h bằng bao nhiêu?"
        )
        self.captured_system_prompt: Optional[str] = None
        self.captured_messages: List[LLMMessage] = []

    async def chat(
        self,
        messages: List[LLMMessage],
        *,
        system_prompt: Optional[str] = None,
        temperature: float = 0.4,
        max_tokens: Optional[int] = None,
        response_mime_type: Optional[str] = None,
    ) -> LLMResponse:
        self.captured_system_prompt = system_prompt
        self.captured_messages = messages
        return LLMResponse(
            content=self.canned_response,
            provider="gemini",
            model="gemini-3.5-flash-lite",
            tokens_prompt=30,
            tokens_completion=20,
            total_tokens=50,
            latency_ms=110,
        )

    async def stream(
        self,
        messages: List[LLMMessage],
        *,
        system_prompt: Optional[str] = None,
        temperature: float = 0.4,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[LLMStreamChunk]:
        self.captured_system_prompt = system_prompt
        self.captured_messages = messages
        yield LLMStreamChunk(delta="**Bước 2/5", done=False)
        yield LLMStreamChunk(delta=" – Thử thách**\n\n**Câu hỏi:** Chiều cao là gì?", done=False)
        yield LLMStreamChunk(
            delta="",
            done=True,
            tokens_prompt=15,
            tokens_completion=15,
            total_tokens=30,
            latency_ms=95,
        )


# ==============================================================================
# 1. KIỂM THỬ MÁY TRẠNG THÁI (STATE MACHINE LOGIC)
# ==============================================================================

def test_socratic_progressive_5_stages():
    """Kiểm tra tiến trình chuyển trạng thái tuần tự qua đủ 5 giai đoạn."""
    # Bước 1 -> Bước 2
    r1 = SocraticStateMachine.compute_transition(current_step=1, evaluation=None)
    assert r1.next_step == 2
    assert r1.stage == SocraticStage.CHALLENGE
    assert r1.stage_name == "Thử thách"
    assert r1.is_concluded is False
    assert r1.action == "PROMPT_NEXT_QUESTION"

    # Bước 2 -> Bước 3
    r2 = SocraticStateMachine.compute_transition(current_step=2, evaluation=StudentEvaluation.PARTIALLY_CORRECT)
    assert r2.next_step == 3
    assert r2.stage == SocraticStage.HINT
    assert r2.stage_name == "Gợi ý"
    assert r2.is_concluded is False

    # Bước 3 -> Bước 4
    r3 = SocraticStateMachine.compute_transition(current_step=3, evaluation=None)
    assert r3.next_step == 4
    assert r3.stage == SocraticStage.SYNTHESIZE
    assert r3.stage_name == "Củng cố suy luận"
    assert r3.is_concluded is False

    # Bước 4 -> Bước 5 (Tổng kết theo BR-02)
    r4 = SocraticStateMachine.compute_transition(current_step=4, evaluation=None)
    assert r4.next_step == 5
    assert r4.stage == SocraticStage.EVALUATE
    assert r4.stage_name == "Tổng kết"
    assert r4.is_concluded is True
    assert r4.action == "CONCLUDE_AND_SUMMARIZE"


def test_socratic_early_conclusion_when_correct():
    """BR-02: Nếu sinh viên trả lời đúng hoàn toàn ở bất kỳ bước nào, kết thúc sớm thành công."""
    res = SocraticStateMachine.compute_transition(
        current_step=2, evaluation=StudentEvaluation.CORRECT, current_wrong_streak=1
    )
    assert res.next_step == 5
    assert res.stage == SocraticStage.EVALUATE
    assert res.is_concluded is True
    assert res.action == "CONCLUDE_AND_SUMMARIZE"
    assert res.wrong_streak == 0


def test_socratic_exception_4a_two_consecutive_failures():
    """SRS Ngoại lệ 4a: Sai hoặc không biết 2 lần liên tiếp -> kích hoạt gợi ý tăng cường."""
    # Lần 1: Sai -> wrong_streak = 1
    r1 = SocraticStateMachine.compute_transition(
        current_step=1, evaluation=StudentEvaluation.WRONG, current_wrong_streak=0
    )
    assert r1.wrong_streak == 1
    assert r1.action == "PROMPT_NEXT_QUESTION"

    # Lần 2: Tiếp tục nói không biết -> wrong_streak chạm 2 -> Kích hoạt gợi ý chuyên sâu
    r2 = SocraticStateMachine.compute_transition(
        current_step=r1.next_step, evaluation=StudentEvaluation.DONT_KNOW, current_wrong_streak=r1.wrong_streak
    )
    assert r2.action == "PROVIDE_INTENSIVE_HINT"
    assert r2.wrong_streak == 0  # Đã reset sau khi trợ giúp
    assert r2.next_step >= 3    # Nhảy tới giai đoạn HINT


def test_evaluate_student_input_keywords():
    """Kiểm tra nhận diện câu trả lời không biết / bối rối từ sinh viên."""
    assert SocraticStateMachine.evaluate_student_input("Em không biết làm sao cả") == StudentEvaluation.DONT_KNOW
    assert SocraticStateMachine.evaluate_student_input("Bí rồi, cho em lời giải đi") == StudentEvaluation.DONT_KNOW
    assert SocraticStateMachine.evaluate_student_input("Khó hiểu quá") == StudentEvaluation.DONT_KNOW
    assert SocraticStateMachine.evaluate_student_input("Theo em thì nút gốc có giá trị lớn hơn") is None


# ==============================================================================
# 2. KIỂM THỬ BỘ LỌC BẢO VỆ BR-02 VÀ PARSER TRẠNG THÁI
# ==============================================================================

def test_sanitize_spoilers_in_steps_1_to_4():
    """BR-02: Bước 1-4 không được tiết lộ đáp án trực tiếp."""
    leaked_text = "Bạn đã suy nghĩ tốt. Đáp án là: O(log n)."
    sanitized = SocraticStateMachine.sanitize_spoilers(leaked_text, step=2)
    assert "đáp án là" not in sanitized.lower()
    assert "hãy cùng suy luận để tìm ra điều này" in sanitized

    # Bước 5 thì được phép giữ lại đáp án
    step5_text = "Tổng kết: Đáp án là: O(log n)."
    assert SocraticStateMachine.sanitize_spoilers(step5_text, step=5) == step5_text


def test_parse_socratic_response_from_markdown():
    """Bóc tách phản hồi Markdown chuẩn theo cấu trúc socratic_system.md."""
    raw_md = (
        "**Bước 3/5 – Gợi ý**\n\n"
        "Hãy nhớ lại định nghĩa về chiều cao h của cây cân bằng.\n\n"
        "**Câu hỏi:** Với n = 7 nút, cây đầy 3 tầng có chiều cao bằng bao nhiêu?"
    )
    feedback = SocraticStateMachine.parse_socratic_response(raw_md, current_step=3)

    assert feedback.step == 3
    assert feedback.stage == SocraticStage.HINT
    assert feedback.stage_name == "Gợi ý"
    assert "chiều cao h" in feedback.feedback
    assert "n = 7 nút" in feedback.guidance_question
    assert feedback.explanation is None  # BR-02: Bước 3 không có explanation
    assert feedback.is_concluded is False


def test_parse_socratic_response_from_json():
    """Bóc tách phản hồi JSON trực tiếp từ mô hình AI."""
    raw_json = json.dumps({
        "step": 4,
        "stage": "SYNTHESIZE",
        "evaluation": "PARTIALLY_CORRECT",
        "feedback": "Bạn đã tính đúng chiều cao của cây cân bằng.",
        "guidance_question": "Giờ hãy so sánh với trường hợp cây suy biến thành đường thẳng.",
        "explanation": "Lời giải chi tiết...",  # Cố tình chèn explanation vào bước 4
        "is_concluded": True,                 # Cố tình đặt concluded sai ở bước 4
    })
    feedback = SocraticStateMachine.parse_socratic_response(raw_json, current_step=4)

    assert feedback.step == 4
    assert feedback.stage == SocraticStage.SYNTHESIZE
    # BR-02 Enforcer phải tự động dọn dẹp cờ vi phạm
    assert feedback.explanation is None
    assert feedback.is_concluded is False
    assert feedback.guidance_question is not None


def test_parse_socratic_response_step_5_concludes():
    """Bước 5 bóc tách thành công và đánh dấu kết thúc phiên hội thoại."""
    raw_step5 = (
        "**Bước 5/5 – Tổng kết**\n\n"
        "- **Kết luận:** Chi phí tìm kiếm phụ thuộc trực tiếp vào chiều cao h của cây.\n"
        "- **Lời giải/giải thích:** Cây cân bằng cho O(log n), cây suy biến cho O(n).\n"
        "- **Điểm cần ghi nhớ:** Luôn duy trì cân bằng cho cây."
    )
    feedback = SocraticStateMachine.parse_socratic_response(raw_step5, current_step=5)

    assert feedback.step == 5
    assert feedback.stage == SocraticStage.EVALUATE
    assert feedback.is_concluded is True
    assert feedback.explanation is not None


# ==============================================================================
# 3. KIỂM THỬ API ENDPOINTS (ROUTER TESTCLIENT)
# ==============================================================================

def test_socratic_chat_endpoint_success():
    """Kiểm tra gọi endpoint POST /ai/socratic/chat thành công với API Key hợp lệ."""
    app.dependency_overrides[get_socratic_llm_adapter] = lambda: FakeSocraticAdapter()
    try:
        response = client.post(
            "/ai/socratic/chat",
            headers={"X-API-Key": settings.INTERNAL_API_KEY},
            json={
                "message": "Cây nhị phân tìm kiếm hoạt động thế nào?",
                "lesson_context": "Bài 1: Cấu trúc dữ liệu cây",
                "current_step": 1,
                "wrong_streak": 0,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "reply" in data
        assert "feedback" in data
        assert data["feedback"]["step"] == 2  # Chuyển từ bước 1 sang bước 2
        assert data["feedback"]["stage"] == "CHALLENGE"
        assert data["feedback"]["is_concluded"] is False
        assert data["provider"] == "gemini"
        assert data["usage"]["total_tokens"] == 50
    finally:
        app.dependency_overrides.pop(get_socratic_llm_adapter, None)


def test_socratic_chat_unauthorized_without_key():
    """Kiểm tra chặn truy cập khi thiếu hoặc sai X-API-Key."""
    response = client.post(
        "/ai/socratic/chat",
        headers={"X-API-Key": "invalid_key_xyz"},
        json={"message": "Xin chào"},
    )
    assert response.status_code == 401


def test_socratic_stream_endpoint():
    """Kiểm tra luồng SSE streaming tại POST /ai/socratic/stream."""
    app.dependency_overrides[get_socratic_llm_adapter] = lambda: FakeSocraticAdapter()
    try:
        response = client.post(
            "/ai/socratic/stream",
            headers={"X-API-Key": settings.INTERNAL_API_KEY},
            json={
                "message": "Em chưa hiểu về chiều cao cây",
                "current_step": 1,
            },
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        lines = [line.strip() for line in response.text.split("\n") if line.startswith("data:")]
        assert len(lines) >= 2

        first_data = json.loads(lines[0].replace("data:", "").strip())
        assert first_data["step"] == 2
        assert first_data["stage"] == "CHALLENGE"
        assert first_data["is_concluded"] is False
    finally:
        app.dependency_overrides.pop(get_socratic_llm_adapter, None)
