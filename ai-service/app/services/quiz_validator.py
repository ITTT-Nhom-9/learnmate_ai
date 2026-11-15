"""Dịch vụ kiểm định tính toàn vẹn bộ đề trắc nghiệm và cơ chế tự động thử lại (BR-06 / TK-15).

Nhiệm vụ:
- Bóc tách chuỗi JSON từ phản hồi của mô hình LLM.
- Kiểm tra hợp lệ nghiêm ngặt theo lược đồ Pydantic QuizBundleOut.
- Thực thi quy tắc BR-06: nếu JSON bị lỗi cú pháp hoặc vi phạm schema, tự động thử lại tối đa 2 lần (auto-retry).
"""
import json
import logging
import re
from typing import Any, Dict, Optional

from app.adapters.base_adapter import LLMMessage, LLMProvider
from app.core.exceptions import AIException
from app.schemas.quiz_schema import QuizBundleOut, QuizGenerationSpec

logger = logging.getLogger("ai_service.quiz_validator")

# Biểu thức chính quy bóc tách JSON bọc trong khối markdown ```json ... ```
JSON_BLOCK_REGEX = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def extract_json_object(raw_text: str) -> Dict[str, Any]:
    """Trích xuất từ điển JSON hợp lệ từ chuỗi văn bản thô do LLM trả về."""
    clean_text = raw_text.strip()

    # 1. Thử bóc tách từ khối mã ```json ... ```
    match = JSON_BLOCK_REGEX.search(clean_text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError as exc:
            logger.warning(f"Lỗi cú pháp JSON trong khối markdown: {exc}")

    # 2. Thử parse trực tiếp toàn bộ chuỗi
    if clean_text.startswith("{") and clean_text.endswith("}"):
        try:
            return json.loads(clean_text)
        except json.JSONDecodeError as exc:
            logger.warning(f"Lỗi cú pháp JSON trực tiếp: {exc}")

    # 3. Tìm vị trí dấu ngoặc nhọn đầu tiên và cuối cùng
    start_idx = clean_text.find("{")
    end_idx = clean_text.rfind("}")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        candidate = clean_text[start_idx : end_idx + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as exc:
            logger.warning(f"Lỗi cú pháp JSON khi cắt chuỗi: {exc}")

    raise ValueError("Không tìm thấy đối tượng JSON hợp lệ trong phản hồi của mô hình")


def validate_quiz_json(payload: Dict[str, Any]) -> QuizBundleOut:
    """Xác thực đối tượng JSON với lược đồ Pydantic QuizBundleOut theo quy tắc BR-06."""
    return QuizBundleOut.model_validate(payload)


async def generate_and_validate_quiz(
    spec: QuizGenerationSpec,
    system_prompt: str,
    adapter: LLMProvider,
    max_retries: int = 2,
) -> tuple[QuizBundleOut, int, int, int, int]:
    """
    Sinh đề thi trắc nghiệm qua LLM và tự động kiểm định với cơ chế tự thử lại (BR-06).

    Args:
        spec: Thông số yêu cầu sinh đề.
        system_prompt: Mẫu system prompt đã chuẩn bị.
        adapter: Adapter kết nối mô hình LLM (Gemini / OpenAI).
        max_retries: Số lần thử lại tối đa khi gặp lỗi cú pháp (mặc định 2 lần theo BR-06).

    Returns:
        tuple gồm (QuizBundleOut, tokens_prompt, tokens_completion, total_tokens, latency_ms)
    """
    # Xây dựng tin nhắn gửi sang LLM
    context_lines = [
        f"Bài học: {spec.lesson_title}",
    ]
    if spec.topic_name:
        context_lines.append(f"Chủ đề trọng tâm: {spec.topic_name}")
    context_lines.append(f"Độ khó: {spec.difficulty.value}")
    context_lines.append(f"Số lượng câu hỏi: {spec.num_questions}")
    context_lines.append(f"\nNội dung bài học:\n{spec.lesson_content}")

    user_message = (
        f"<lesson_context>\n" + "\n".join(context_lines) + f"\n</lesson_context>\n\n"
        f"Hãy sinh bộ đề thi gồm đúng {spec.num_questions} câu hỏi trắc nghiệm độ khó {spec.difficulty.value} "
        f"dưới dạng JSON tuân thủ đúng cấu trúc yêu cầu."
    )

    messages = [LLMMessage(role="user", content=user_message)]

    last_error: Optional[Exception] = None
    accumulated_prompt_tokens = 0
    accumulated_comp_tokens = 0
    total_latency = 0

    # Vòng lặp thử nghiệm: 1 lần chạy chính + tối đa 2 lần retry (tổng cộng 3 lượt)
    for attempt in range(max_retries + 1):
        try:
            logger.info(f"Bắt đầu sinh đề trắc nghiệm (Lần thử {attempt + 1}/{max_retries + 1})...")
            result = await adapter.chat(
                messages,
                system_prompt=system_prompt,
                temperature=spec.temperature,
                response_mime_type="application/json",
            )

            accumulated_prompt_tokens += result.tokens_prompt
            accumulated_comp_tokens += result.tokens_completion
            total_latency += result.latency_ms

            # 1. Bóc tách JSON
            json_data = extract_json_object(result.content)

            # 2. Kiểm định tính toàn vẹn theo Pydantic
            validated_bundle = validate_quiz_json(json_data)

            # Đảm bảo trường độ khó đồng bộ với spec
            validated_bundle.difficulty = spec.difficulty

            logger.info(
                f"Kiểm định bộ đề trắc nghiệm thành công: {len(validated_bundle.questions)} câu hỏi."
            )
            return (
                validated_bundle,
                accumulated_prompt_tokens,
                accumulated_comp_tokens,
                accumulated_prompt_tokens + accumulated_comp_tokens,
                total_latency,
            )

        except (ValueError, json.JSONDecodeError, Exception) as exc:
            last_error = exc
            logger.warning(
                f"Lần thử {attempt + 1} thất bại do lỗi cấu trúc JSON: {exc}. "
                + (f"Tiến hành thử lại ({attempt + 1}/{max_retries})..." if attempt < max_retries else "")
            )

    raise AIException(
        error_code="QUIZ_SCHEMA_INVALID",
        message=f"Không thể sinh bộ câu hỏi trắc nghiệm hợp lệ sau {max_retries} lần thử lại. Chi tiết: {last_error}",
    )
