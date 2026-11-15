"""Router API cho phân hệ Socratic Learning (TK-14 / Phân hệ 4).

Cung cấp các endpoint:
- POST /ai/socratic/chat: Xử lý hỏi đáp gợi mở Socratic phi trạng thái, trả về phản hồi đầy đủ và JSON phân tích trạng thái.
- POST /ai/socratic/stream: Phát luồng phản hồi SSE kèm dữ liệu trạng thái bước (1..5) và cờ is_concluded (BR-02).
"""
import json
from pathlib import Path
from typing import AsyncIterator, List, Optional, Tuple

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.adapters import LLMMessage, LLMProvider, get_llm_adapter
from app.core.exceptions import AIException, mask_sensitive_text
from app.core.security import verify_internal_api_key
from app.schemas.socratic_schema import (
    SocraticFeedback,
    SocraticStepRequest,
    SocraticStepResponse,
    STEP_TO_STAGE,
    STAGE_NAMES,
)
from app.schemas.tutor_schema import LLMUsageDTO
from app.services.socratic_state_machine import (
    MAX_SOCRATIC_STEPS,
    SocraticStateMachine,
    StateTransitionResult,
)

router = APIRouter(
    prefix="/ai/socratic",
    tags=["AI Socratic"],
    dependencies=[Depends(verify_internal_api_key)],
)

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
SOCRATIC_PROMPT_FILE = PROMPTS_DIR / "socratic_system.md"

FALLBACK_SOCRATIC_SYSTEM_PROMPT = (
    "Bạn là LearnMate AI Socratic, người hướng dẫn học tập bằng phương pháp gợi mở từng bước. "
    "Tuyệt đối không đưa đáp án ở bước 1, 2, 3 và 4. Chỉ tổng kết và đưa lời giải ở bước 5 (BR-02). "
    "Mỗi lượt chỉ đặt một câu hỏi chính ngắn gọn, tập trung định hướng tư duy."
)


def get_default_socratic_system_prompt() -> str:
    """Nạp mẫu prompt chuẩn sư phạm từ socratic_system.md (TK-11)."""
    if SOCRATIC_PROMPT_FILE.is_file():
        try:
            content = SOCRATIC_PROMPT_FILE.read_text(encoding="utf-8").strip()
            if content:
                return content
        except Exception:
            pass
    return FALLBACK_SOCRATIC_SYSTEM_PROMPT


def get_socratic_llm_adapter() -> LLMProvider:
    """Dependency cung cấp LLM Adapter (hỗ trợ DI khi viết Unit Test)."""
    return get_llm_adapter()


def _prepare_socratic_context(
    request: SocraticStepRequest, transition: StateTransitionResult
) -> Tuple[str, List[LLMMessage]]:
    """Ráp system prompt, ngữ cảnh bài học và chỉ thị chuyển bước trạng thái cho LLM."""
    base_prompt = get_default_socratic_system_prompt()

    # Thêm chỉ thị bước hiện tại của máy trạng thái
    step_directive = (
        f"\n\n[CHỈ THỊ ĐIỀU PHỐI BƯỚC SƯ PHẠM (BR-02)]\n"
        f"- Bạn đang ở Bước {transition.next_step}/{MAX_SOCRATIC_STEPS} – {transition.stage_name}.\n"
    )

    if transition.action == "PROVIDE_INTENSIVE_HINT":
        step_directive += (
            "- Ngoại lệ 4a (SRS): Sinh viên đang lúng túng hoặc chưa nắm được vấn đề liên tiếp 2 lần. "
            "Hãy đưa ra một gợi ý rõ ràng hơn kèm một ví dụ trực quan ngắn gọn, sau đó đặt câu hỏi đơn giản hơn. "
            "Tuyệt đối không nói đáp án cuối cùng.\n"
        )
    elif transition.next_step < MAX_SOCRATIC_STEPS:
        step_directive += (
            "- TUYỆT ĐỐI KHÔNG ĐƯỢC NÊU ĐÁP ÁN HOẶC KẾT QUẢ CUỐI CÙNG. "
            "Chỉ nhận xét ngắn gọn và kết thúc bằng một câu hỏi gợi mở duy nhất theo cấu trúc:\n"
            f"**Bước {transition.next_step}/5 – {transition.stage_name}**\n\n"
            "[Nhận xét ngắn]\n\n"
            "**Câu hỏi:** [Một câu hỏi gợi mở duy nhất]\n"
        )
    else:
        step_directive += (
            "- ĐÂY LÀ BƯỚC 5/5 (TỔNG KẾT): Hãy tổng kết toàn bộ tiến trình suy luận, "
            "trình bày lời giải chính xác, chỉ ra điểm sinh viên đã làm tốt và điểm cần lưu ý.\n"
        )

    system_prompt = base_prompt + step_directive

    if request.lesson_context and request.lesson_context.strip():
        system_prompt += (
            f"\n\n<lesson_context>\n{request.lesson_context.strip()}\n</lesson_context>"
        )

    messages: List[LLMMessage] = [
        LLMMessage(role=item.role, content=item.content) for item in request.history
    ]
    messages.append(
        LLMMessage(
            role="user",
            content=f"<student_query>\n{request.message.strip()}\n</student_query>",
        )
    )

    return system_prompt, messages


@router.post(
    "/chat",
    response_model=SocraticStepResponse,
    summary="Xử lý gợi mở Socratic phi trạng thái (trả về phản hồi đầy đủ và JSON trạng thái)",
    description=(
        "Cách hoạt động:\n"
        "1. Xác thực header X-API-Key khớp với INTERNAL_API_KEY nội bộ.\n"
        "2. Đánh giá câu trả lời của học viên và tính toán bước chuyển trạng thái (SocraticStateMachine).\n"
        "3. Ráp mẫu prompt socratic_system.md, ngữ cảnh bài học và thẻ bảo vệ <student_query>.\n"
        "4. Gọi LLM Adapter, bóc tách cấu trúc phản hồi và đảm bảo quy tắc không lộ đáp án ở bước 1-4 (BR-02).\n"
        "5. Trả về câu trả lời kèm đối tượng phân tích trạng thái SocraticFeedback."
    ),
)
async def socratic_chat(
    payload: SocraticStepRequest,
    adapter: LLMProvider = Depends(get_socratic_llm_adapter),
) -> SocraticStepResponse:
    # 1. Phát hiện sơ bộ phản hồi của học viên
    detected_eval = SocraticStateMachine.evaluate_student_input(payload.message)

    # 2. Tính toán bước chuyển tiếp theo
    transition = SocraticStateMachine.compute_transition(
        current_step=payload.current_step,
        evaluation=detected_eval,
        current_wrong_streak=payload.wrong_streak,
    )

    # 3. Chuẩn bị prompt và tin nhắn
    system_prompt, messages = _prepare_socratic_context(payload, transition)

    # 4. Gọi mô hình LLM
    result = await adapter.chat(
        messages,
        system_prompt=system_prompt,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
    )

    # 5. Phân tích phản hồi qua Parser trạng thái
    feedback = SocraticStateMachine.parse_socratic_response(
        raw_text=result.content,
        current_step=transition.next_step,
        current_wrong_streak=transition.wrong_streak,
        detected_eval=detected_eval,
    )

    # Đảm bảo cờ kết thúc và bước đồng bộ với transition
    if transition.is_concluded:
        feedback.is_concluded = True
        feedback.step = MAX_SOCRATIC_STEPS

    return SocraticStepResponse(
        reply=result.content,
        feedback=feedback,
        provider=result.provider,
        model=result.model,
        usage=LLMUsageDTO(
            tokens_prompt=result.tokens_prompt,
            tokens_completion=result.tokens_completion,
            total_tokens=result.total_tokens,
            latency_ms=result.latency_ms,
        ),
    )


@router.post(
    "/stream",
    summary="Xử lý gợi mở Socratic thời gian thực (Server-Sent Events streaming)",
    description=(
        "Cách hoạt động:\n"
        "1. Tính toán bước trạng thái sư phạm qua SocraticStateMachine.\n"
        "2. Phát luồng chữ qua SSE kèm thông tin step, stage, hint_level, is_concluded.\n"
        "3. Đóng gói kết quả cuối cùng trong sự kiện done kèm thống kê token tiêu thụ."
    ),
)
async def socratic_stream(
    payload: SocraticStepRequest,
    adapter: LLMProvider = Depends(get_socratic_llm_adapter),
) -> StreamingResponse:
    detected_eval = SocraticStateMachine.evaluate_student_input(payload.message)
    transition = SocraticStateMachine.compute_transition(
        current_step=payload.current_step,
        evaluation=detected_eval,
        current_wrong_streak=payload.wrong_streak,
    )

    system_prompt, messages = _prepare_socratic_context(payload, transition)

    async def event_generator() -> AsyncIterator[str]:
        full_content = []
        try:
            async for chunk in adapter.stream(
                messages,
                system_prompt=system_prompt,
                temperature=payload.temperature,
                max_tokens=payload.max_tokens,
            ):
                if chunk.delta:
                    full_content.append(chunk.delta)
                event_data = {
                    "delta": chunk.delta,
                    "done": chunk.done,
                    "step": transition.next_step,
                    "stage": transition.stage.value,
                    "stage_name": transition.stage_name,
                    "hint_level": transition.next_step,
                    "is_concluded": transition.is_concluded,
                    "wrong_streak": transition.wrong_streak,
                }
                if chunk.done:
                    event_data.update(
                        {
                            "provider": adapter.provider_name,
                            "tokens_prompt": chunk.tokens_prompt,
                            "tokens_completion": chunk.tokens_completion,
                            "total_tokens": chunk.total_tokens,
                            "latency_ms": chunk.latency_ms,
                        }
                    )
                yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
        except AIException as exc:
            err_payload = {
                "error_code": exc.error_code,
                "detail": exc.message,
                "done": True,
            }
            yield f"event: error\ndata: {json.dumps(err_payload, ensure_ascii=False)}\n\n"
        except Exception as exc:
            err_payload = {
                "error_code": "STREAM_ERROR",
                "detail": mask_sensitive_text(str(exc)),
                "done": True,
            }
            yield f"event: error\ndata: {json.dumps(err_payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
