"""Schemas Pydantic cho phân hệ RAG (TK-24 / FR-RG-01, FR-RG-02, BR-09)."""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DocumentChunkOut(BaseModel):
    """Thông tin một đoạn văn bản sau khi băm nhỏ kèm vector embedding."""
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="ID của đoạn chunk")
    chunk_index: int = Field(..., description="Thứ tự của đoạn trong tài liệu (0..N-1)")
    page_number: int = Field(..., description="Số trang gốc trong file PDF để trích dẫn")
    content: str = Field(..., description="Nội dung văn bản đoạn (~500 từ)")
    embedding_dim: Optional[int] = Field(default=1536, description="Số chiều của vector embedding (1536)")
    created_at: datetime


class DocumentUploadResponse(BaseModel):
    """Phản hồi sau khi tải lên và hoàn tất lập chỉ mục (Indexing) tệp PDF."""
    document_id: int = Field(..., description="Mã định danh tài liệu")
    course_id: int = Field(..., description="Mã môn học liên kết")
    file_name: str = Field(..., description="Tên tệp PDF gốc")
    file_size: int = Field(..., description="Kích thước tệp (bytes, tối đa 20MB theo BR-09)")
    total_pages: int = Field(..., description="Tổng số trang trích xuất được")
    total_chunks: int = Field(..., description="Tổng số đoạn chunk 500 từ được tạo ra")
    embedding_dim: int = Field(default=1536, description="Kích thước vector embedding (1536 chiều)")
    created_at: datetime = Field(..., description="Thời điểm tải lên")
    message: str = Field(
        default="Tải lên và xử lý vector embedding 1536 chiều thành công.",
        description="Thông báo kết quả",
    )


class DocumentListItem(BaseModel):
    """Dòng tóm tắt tài liệu trong danh sách tài liệu môn học."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    file_name: str
    file_size: int
    total_chunks: int = Field(default=0, description="Số đoạn chunk đã lập chỉ mục")
    created_at: datetime


class DocumentListResponse(BaseModel):
    """Danh sách các tài liệu đã tải lên cho môn học."""
    total: int = Field(..., description="Tổng số tài liệu")
    items: List[DocumentListItem] = Field(default_factory=list)


class DocumentDetailResponse(BaseModel):
    """Chi tiết tài liệu và danh sách các đoạn chunk băm nhỏ."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    file_name: str
    file_size: int
    total_chunks: int
    created_at: datetime
    chunks: List[DocumentChunkOut] = Field(default_factory=list)


class SourceCitation(BaseModel):
    """Thông tin trích dẫn nguồn số trang của đoạn văn bản tham chiếu (FR-RG-03)."""
    model_config = ConfigDict(from_attributes=True)

    chunk_id: int = Field(..., description="Mã đoạn chunk trong CSDL")
    document_id: int = Field(..., description="Mã tài liệu giáo trình")
    file_name: str = Field(..., description="Tên tệp giáo trình PDF")
    page_number: int = Field(..., description="Số trang gốc trong tệp PDF để trích dẫn")
    similarity_score: float = Field(..., description="Điểm tương đồng Cosine Similarity (0.0 .. 1.0)")
    snippet: str = Field(..., description="Đoạn trích dẫn nội dung văn bản ngắn")


class RAGQueryRequest(BaseModel):
    """Dữ liệu yêu cầu hỏi đáp theo giáo trình PDF (POST /api/v1/rag/query)."""
    course_id: int = Field(..., description="Mã môn học cần tra cứu")
    query: str = Field(..., min_length=2, max_length=1000, description="Câu hỏi của sinh viên")
    document_ids: Optional[List[int]] = Field(
        default=None,
        description="Danh sách ID tài liệu cần giới hạn phạm vi (nếu bỏ trống sẽ tìm trên toàn bộ tài liệu môn học)",
    )
    top_k: int = Field(default=3, ge=1, le=10, description="Số đoạn văn bản tương đồng nhất cần truy xuất (mặc định 3 theo SDD)")


class RAGQueryResponse(BaseModel):
    """Kết quả trả lời câu hỏi dựa trên PDF kèm số trang trích dẫn (FR-RG-03, FR-RG-05)."""
    query: str = Field(..., description="Câu hỏi gốc của sinh viên")
    answer: str = Field(..., description="Nội dung giải đáp của AI kèm trích dẫn số trang rõ ràng")
    is_out_of_scope: bool = Field(default=False, description="Đánh dấu câu hỏi ngoài phạm vi tài liệu (FR-RG-05)")
    citations: List[SourceCitation] = Field(default_factory=list, description="Danh sách các trích dẫn số trang bài giảng")
    total_sources: int = Field(default=0, description="Tổng số nguồn trích dẫn được sử dụng")
