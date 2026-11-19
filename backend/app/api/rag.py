"""Router API cho phân hệ RAG - Hỏi đáp và quản lý tài liệu giáo trình PDF.

Phân hệ 8: RAG Lõi (TK-24 / FR-RG-01, FR-RG-02, FR-RG-04, BR-09).
Endpoints:
- POST /api/v1/rag/upload: Tải lên giáo trình PDF (<=20MB, BR-09), trích xuất văn bản, băm chunk và lưu vector embedding 1536 chiều.
- GET /api/v1/rag/documents: Lấy danh sách các tài liệu đã tải lên theo môn học.
- GET /api/v1/rag/documents/{document_id}: Xem chi tiết tài liệu và các đoạn chunk đã băm.
- DELETE /api/v1/rag/documents/{document_id}: Xóa tài liệu và xóa cascade các vector embedding liên quan.
"""
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.rag import (
    DocumentUploadResponse,
    DocumentListResponse,
    DocumentDetailResponse,
    RAGQueryRequest,
    RAGQueryResponse,
)
from app.services.ai_rag_client import AIRAGClient, get_ai_rag_client
from app.services.rag_service import RAGService

router = APIRouter(tags=["RAG"])


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tải lên tài liệu giáo trình PDF và lập chỉ mục Vector Embedding 1536 chiều (FR-RG-01, FR-RG-02, BR-09)",
)
def upload_document(
    course_id: int = Form(..., description="ID môn học liên kết với tài liệu"),
    file: UploadFile = File(..., description="Tệp giáo trình PDF chuẩn (tối đa 20MB)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tiếp nhận tệp PDF, kiểm tra dung lượng <= 20MB (BR-09), trích xuất văn bản,
    chia nhỏ thành các đoạn chunk 500 từ kèm 50 từ gối đầu (overlap) và lưu trữ
    vector embedding 1536 chiều vào bảng document_chunks.
    """
    service = RAGService(db)
    return service.upload_and_index_document(current_user, course_id, file)


@router.get(
    "/documents",
    response_model=DocumentListResponse,
    summary="Lấy danh sách các tài liệu PDF đã lập chỉ mục (FR-RG-04)",
)
def list_documents(
    course_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Xem danh sách tài liệu cá nhân hoặc tài liệu thuộc môn học."""
    service = RAGService(db)
    return service.list_documents(current_user, course_id)


@router.get(
    "/documents/{document_id}",
    response_model=DocumentDetailResponse,
    summary="Xem chi tiết tài liệu và danh sách các đoạn chunk băm nhỏ (FR-RG-04)",
)
def get_document_detail(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lấy thông tin tài liệu kèm nội dung các chunk và số trang gốc."""
    service = RAGService(db)
    return service.get_document_detail(current_user, document_id)


@router.delete(
    "/documents/{document_id}",
    summary="Xóa tài liệu và các đoạn chunk embedding liên quan (FR-RG-04)",
)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Xóa tài liệu khỏi hệ thống; cơ chế CASCADE DELETE sẽ tự động dọn sạch các vector embedding."""
    service = RAGService(db)
    service.delete_document(current_user, document_id)
    return {
        "status": "success",
        "message": f"Đã xóa tài liệu có ID {document_id} và toàn bộ vector embedding liên quan thành công.",
    }


@router.post(
    "/query",
    response_model=RAGQueryResponse,
    summary="Hỏi đáp theo tài liệu giáo trình PDF có trích dẫn số trang bài giảng (TK-25 / FR-RG-03, FR-RG-05)",
)
async def query_rag(
    request: RAGQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ai_client: AIRAGClient = Depends(get_ai_rag_client),
):
    """Tìm kiếm các đoạn văn bản tương đồng ngữ nghĩa nhất (Cosine Similarity),
    gửi vào ngữ cảnh để AI trả lời có ghi rõ trích dẫn số trang bài giảng (FR-RG-03).
    Tự động từ chối nếu câu hỏi nằm ngoài phạm vi tài liệu (FR-RG-05).
    """
    service = RAGService(db)
    return await service.query_and_answer(current_user, request, ai_client=ai_client)
