"""Router API cho phân hệ RAG trong AI Microservice (TK-25 / SDD)."""
import time
from pathlib import Path
from typing import List, Tuple
from fastapi import APIRouter, Depends

from app.adapters import LLMMessage, get_llm_adapter
from app.core.security import verify_internal_api_key
from app.schemas.rag_schema import (
    RAGQueryRequestDTO,
    RAGQueryResponseDTO,
    RAGCitationDTO,
)

router = APIRouter(
    prefix="/ai/rag",
    tags=["AI RAG"],
    dependencies=[Depends(verify_internal_api_key)],
)

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
DEFAULT_RAG_PROMPT_FILE = PROMPTS_DIR / "rag_system.md"

FALLBACK_RAG_SYSTEM_PROMPT = (
    "Bạn là trợ lý học tập AI của hệ thống LearnMate AI. "
    "Hãy trả lời câu hỏi của sinh viên dựa trên các đoạn trích giáo trình được cung cấp. "
    "Bắt buộc trích dẫn số trang gốc [Trang X] tương ứng với từng luận điểm. "
    "Nếu câu hỏi nằm ngoài phạm vi tài liệu, hãy từ chối lịch sự."
)


def get_default_rag_system_prompt() -> str:
    """Tự động nạp mẫu prompt từ rag_system.md."""
    if DEFAULT_RAG_PROMPT_FILE.is_file():
        try:
            content = DEFAULT_RAG_PROMPT_FILE.read_text(encoding="utf-8").strip()
            if content:
                return content
        except Exception:
            pass
    return FALLBACK_RAG_SYSTEM_PROMPT


def _prepare_rag_prompt(request: RAGQueryRequestDTO) -> Tuple[str, List[LLMMessage]]:
    """Lắp ghép System Prompt, ngữ cảnh tài liệu kèm số trang và câu hỏi sinh viên."""
    base_prompt = (request.system_prompt or get_default_rag_system_prompt()).strip()

    context_lines = []
    for c in request.context_chunks:
        context_lines.append(
            f"--- [Đoạn #{c.chunk_index} | Trang {c.page_number} | Tệp: {c.file_name}] ---\n"
            f"{c.content.strip()}"
        )
    context_str = "\n\n".join(context_lines)

    system_prompt = (
        f"{base_prompt}\n\n"
        f"<document_context>\n{context_str}\n</document_context>"
    )

    user_message = (
        f"<student_query>\n{request.query.strip()}\n</student_query>"
    )

    messages = [
        LLMMessage(role="system", content=system_prompt),
        LLMMessage(role="user", content=user_message),
    ]
    return system_prompt, messages


@router.post(
    "/query",
    response_model=RAGQueryResponseDTO,
    summary="Hỏi đáp theo tài liệu PDF kèm trích dẫn số trang (TK-25 / FR-RG-03)",
)
async def query_rag_document(request: RAGQueryRequestDTO) -> RAGQueryResponseDTO:
    """Xử lý câu hỏi của sinh viên dựa trên các đoạn chunk tài liệu giáo trình."""
    start_time = time.time()

    # Xây dựng danh sách trích dẫn nguồn
    citations: List[RAGCitationDTO] = []
    for c in request.context_chunks:
        snippet = c.content[:150] + "..." if len(c.content) > 150 else c.content
        citations.append(
            RAGCitationDTO(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                file_name=c.file_name,
                page_number=c.page_number,
                similarity=round(c.similarity, 4),
                snippet=snippet,
            )
        )

    # Nếu không có đoạn chunk nào hoặc tương đồng quá thấp -> Cảnh báo ngoài phạm vi (FR-RG-05)
    if not request.context_chunks:
        elapsed_ms = int((time.time() - start_time) * 1000)
        return RAGQueryResponseDTO(
            answer=(
                "Nội dung câu hỏi của bạn nằm ngoài phạm vi tài liệu giáo trình được cung cấp. "
                "Vui lòng đặt câu hỏi liên quan đến nội dung bài giảng để được hỗ trợ chính xác kèm trích dẫn số trang."
            ),
            is_out_of_scope=True,
            citations=[],
            tokens_prompt=len(request.query.split()),
            tokens_completion=0,
            total_tokens=len(request.query.split()),
            latency_ms=max(1, elapsed_ms),
        )

    system_prompt, messages = _prepare_rag_prompt(request)
    adapter = get_llm_adapter()

    llm_resp = await adapter.chat(
        messages=messages,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
    )

    elapsed_ms = int((time.time() - start_time) * 1000)

    return RAGQueryResponseDTO(
        answer=llm_resp.content,
        is_out_of_scope=False,
        citations=citations,
        tokens_prompt=llm_resp.tokens_prompt,
        tokens_completion=llm_resp.tokens_completion,
        total_tokens=llm_resp.total_tokens,
        latency_ms=max(1, elapsed_ms),
    )
