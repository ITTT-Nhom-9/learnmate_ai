"""Router API cho phân hệ Sinh đề trắc nghiệm AI Quiz (TK-15 / Phân hệ 5).

Cung cấp endpoint:
- POST /ai/quiz/generate: Nhận nội dung bài học, gọi LLM và kiểm định tính toàn vẹn JSON với cơ chế auto-retry tối đa 2 lần (BR-06).
"""
from pathlib import Path
from fastapi import APIRouter, Depends

from app.adapters import LLMProvider, get_llm_adapter
from app.core.security import verify_internal_api_key
from app.schemas.quiz_schema import QuizGenerationResponse, QuizGenerationSpec
from app.schemas.tutor_schema import LLMUsageDTO
from app.services.quiz_validator import generate_and_validate_quiz

router = APIRouter(
    prefix="/ai/quiz",
    tags=["AI Quiz"],
    dependencies=[Depends(verify_internal_api_key)],
)

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
QUIZ_PROMPT_FILE = PROMPTS_DIR / "quiz_system.md"

FALLBACK_QUIZ_SYSTEM_PROMPT = (
    "Bạn là chuyên gia Khảo thí của LearnMate AI. Hãy tạo một bộ đề trắc nghiệm khách quan gồm các câu hỏi 4 lựa chọn (A, B, C, D) "
    "bám sát nội dung bài học được cung cấp. Bắt buộc chỉ trả về định dạng JSON thuần túy theo đúng cấu trúc yêu cầu."
)


def get_default_quiz_system_prompt() -> str:
    """Nạp mẫu prompt khảo thí chuẩn từ quiz_system.md."""
    if QUIZ_PROMPT_FILE.is_file():
        try:
            content = QUIZ_PROMPT_FILE.read_text(encoding="utf-8").strip()
            if content:
                return content
        except Exception:
            pass
    return FALLBACK_QUIZ_SYSTEM_PROMPT


def get_quiz_llm_adapter() -> LLMProvider:
    """Dependency cung cấp LLM Adapter (hỗ trợ DI khi viết Unit Test)."""
    return get_llm_adapter()


@router.post(
    "/generate",
    response_model=QuizGenerationResponse,
    summary="Sinh bộ đề trắc nghiệm thích ứng theo cấu trúc JSON chuẩn (BR-06)",
    description=(
        "Cách hoạt động:\n"
        "1. Xác thực header X-API-Key khớp với INTERNAL_API_KEY nội bộ.\n"
        "2. Nạp mẫu khảo thí quiz_system.md và ghép nội dung bài học vào thẻ an toàn <lesson_context>.\n"
        "3. Gọi mô hình LLM với response_mime_type='application/json'.\n"
        "4. Tự động kiểm định tính toàn vẹn (đủ 4 phương án A-B-C-D, 1 đáp án đúng, có lời giải thích).\n"
        "5. Cơ chế auto-retry tối đa 2 lần nếu JSON bị lỗi cú pháp hoặc không hợp lệ theo quy tắc BR-06.\n"
        "6. Trả về bộ đề thi trắc nghiệm hoàn chỉnh."
    ),
)
async def generate_quiz(
    spec: QuizGenerationSpec,
    adapter: LLMProvider = Depends(get_quiz_llm_adapter),
) -> QuizGenerationResponse:
    system_prompt = get_default_quiz_system_prompt()

    bundle, tokens_prompt, tokens_comp, total_tokens, latency = (
        await generate_and_validate_quiz(
            spec=spec,
            system_prompt=system_prompt,
            adapter=adapter,
            max_retries=2,
        )
    )

    return QuizGenerationResponse(
        bundle=bundle,
        provider=adapter.provider_name,
        model=getattr(adapter, "model_name", "gemini-3.5-flash-lite"),
        usage=LLMUsageDTO(
            tokens_prompt=tokens_prompt,
            tokens_completion=tokens_comp,
            total_tokens=total_tokens,
            latency_ms=latency,
        ),
    )
