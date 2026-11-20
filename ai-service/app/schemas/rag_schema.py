"""Lược đồ Pydantic cho phân hệ RAG trong AI Microservice (TK-25 / SDD)."""
from typing import List, Optional
from pydantic import BaseModel, Field


class RAGChunkContext(BaseModel):
    """Thông tin một đoạn văn bản trích dẫn gửi từ Backend sang AI Service."""

    chunk_id: int
    chunk_index: int = 0
    document_id: int
    file_name: str
    page_number: int
    content: str
    similarity: float = Field(default=0.0, description="Độ tương đồng Cosine Similarity")


class RAGQueryRequestDTO(BaseModel):
    """Yêu cầu hỏi đáp theo tài liệu PDF."""

    query: str = Field(..., min_length=1, max_length=5000, description="Câu hỏi của sinh viên")
    context_chunks: List[RAGChunkContext] = Field(
        default_factory=list,
        description="Danh sách các đoạn văn bản tương đồng nhất (Top K)",
    )
    system_prompt: Optional[str] = Field(
        default=None,
        description="System prompt tùy biến nếu có",
    )
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=1500, ge=1, le=8192)


class RAGCitationDTO(BaseModel):
    """Trích dẫn số trang và tệp nguồn trong câu trả lời."""

    chunk_id: int
    document_id: int
    file_name: str
    page_number: int
    similarity: float
    snippet: str


class RAGQueryResponseDTO(BaseModel):
    """Phản hồi câu trả lời dựa trên PDF kèm số trang trích dẫn."""

    answer: str = Field(..., description="Nội dung giải đáp của AI kèm trích dẫn số trang")
    is_out_of_scope: bool = Field(default=False, description="Đánh dấu câu hỏi ngoài phạm vi tài liệu")
    citations: List[RAGCitationDTO] = Field(default_factory=list, description="Danh sách trích dẫn nguồn")
    tokens_prompt: int = 0
    tokens_completion: int = 0
    total_tokens: int = 0
    latency_ms: int = 0
