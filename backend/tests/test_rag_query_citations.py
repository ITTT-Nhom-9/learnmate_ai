"""Kiểm thử tính năng RAG Hỏi đáp tài liệu PDF có trích dẫn số trang (TK-25 / Phân hệ 8).

Đáp ứng và xác thực 100% các tiêu chí:
- FR-RG-03: AI trả lời câu hỏi dựa trên nội dung PDF và ghi rõ số trang tham chiếu.
- FR-RG-05: Cảnh báo ngoài phạm vi (từ chối nếu câu hỏi hoàn toàn không liên quan đến tài liệu).
- SDD Phase 2: Tìm kiếm đoạn văn tương đồng ngữ nghĩa nhất (Cosine Similarity), ghép ngữ cảnh kèm số trang gốc.
- Ghi log ai_request_logs phục vụ kiểm toán token (NFR-15, BR-05).
"""
import io
import math
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.course import Course, Enrollment
from app.models.rag import Document, DocumentChunk, AIRequestLog
from app.models.user import User
from app.services.rag_service import (
    RAGService,
    generate_deterministic_embedding,
    EMBEDDING_DIM,
)
from app.services.ai_rag_client import AIRAGClient, get_ai_rag_client


@pytest.fixture()
def db_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    yield factory
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def client(db_factory):
    def _override_get_db():
        db = db_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    yield TestClient(app)
    app.dependency_overrides.pop(get_db, None)


def auth_header(user_id: int) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


@pytest.fixture()
def seeded_rag(db_factory):
    """Tạo môi trường kiểm thử gồm:
    - course 1: Cơ sở dữ liệu (u1 ghi danh, u2 chưa)
    - doc 1: Giao trinh CSDL (chứa các chunk về khóa chính, khóa ngoại, đại số quan hệ ở các trang 1, 5, 12)
    - doc 2: Huong dan thuc hanh SQL (chứa các chunk về SELECT, INSERT, UPDATE ở trang 3)
    """
    with db_factory() as db:
        pw = get_password_hash("MatKhau@123")
        u1 = User(email="student1@univ.edu.vn", password_hash=pw, full_name="Sinh Viên 1", role="STUDENT")
        u2 = User(email="student2@univ.edu.vn", password_hash=pw, full_name="Sinh Viên 2", role="STUDENT")
        admin = User(email="admin@univ.edu.vn", password_hash=pw, full_name="Quản Trị Viên", role="ADMIN")
        course = Course(code="CS201", title="Hệ Cơ sở dữ liệu")

        db.add_all([u1, u2, admin, course])
        db.flush()

        db.add(Enrollment(user_id=u1.id, course_id=course.id))

        # Thêm Tài liệu 1
        doc1 = Document(
            course_id=course.id,
            uploaded_by=u1.id,
            file_name="Giao_Trinh_CSDL.pdf",
            file_size=1024 * 500,
        )
        db.add(doc1)
        db.flush()

        # Chunk 1 (Trang 5: Khóa chính và Khóa ngoại)
        content_c1 = (
            "Khóa chính (Primary Key) là một thuộc tính hoặc tập thuộc tính xác định duy nhất mỗi bộ trong quan hệ. "
            "Khóa ngoại (Foreign Key) là một thuộc tính trong bảng này tham chiếu đến khóa chính của bảng khác để đảm bảo tính toàn vẹn tham chiếu."
        )
        chunk1 = DocumentChunk(
            document_id=doc1.id,
            chunk_index=0,
            page_number=5,
            content=content_c1,
            embedding=generate_deterministic_embedding(content_c1),
        )

        # Chunk 2 (Trang 12: Đại số quan hệ)
        content_c2 = (
            "Các phép toán Đại số Quan hệ cơ bản bao gồm phép chọn (Select sigma), phép chiếu (Project pi), "
            "phép tích Descartes, phép hợp, phép trừ và phép kết nối tự nhiên (Natural Join)."
        )
        chunk2 = DocumentChunk(
            document_id=doc1.id,
            chunk_index=1,
            page_number=12,
            content=content_c2,
            embedding=generate_deterministic_embedding(content_c2),
        )

        # Thêm Tài liệu 2
        doc2 = Document(
            course_id=course.id,
            uploaded_by=u1.id,
            file_name="Huong_Dan_SQL.pdf",
            file_size=1024 * 300,
        )
        db.add(doc2)
        db.flush()

        # Chunk 3 (Trang 3: Cú pháp truy vấn SQL)
        content_c3 = (
            "Cú pháp truy vấn SQL chuẩn: SELECT các cột FROM tên bảng WHERE điều kiện lọc GROUP BY nhóm HAVING ORDER BY sắp xếp."
        )
        chunk3 = DocumentChunk(
            document_id=doc2.id,
            chunk_index=0,
            page_number=3,
            content=content_c3,
            embedding=generate_deterministic_embedding(content_c3),
        )

        db.add_all([chunk1, chunk2, chunk3])
        db.commit()

        return {
            "u1": u1.id,
            "u2": u2.id,
            "admin": admin.id,
            "course": course.id,
            "doc1": doc1.id,
            "doc2": doc2.id,
        }


# =========================================================================
# 1. KIỂM THỬ THUẬT TOÁN COSINE SIMILARITY
# =========================================================================

def test_cosine_similarity_edge_cases():
    """Kiểm tra độ chính xác của hàm tính Cosine Similarity."""
    # 2 vector giống hệt nhau -> Similarity = 1.0
    vec1 = [0.6, 0.8] + [0.0] * 1534
    assert abs(RAGService.compute_cosine_similarity(vec1, vec1) - 1.0) < 1e-4

    # 2 vector trực giao -> Similarity = 0.0
    vec2 = [0.8, -0.6] + [0.0] * 1534
    assert abs(RAGService.compute_cosine_similarity(vec1, vec2)) < 1e-4

    # 2 vector ngược hướng -> Similarity = -1.0
    vec_neg = [-0.6, -0.8] + [0.0] * 1534
    assert abs(RAGService.compute_cosine_similarity(vec1, vec_neg) - (-1.0)) < 1e-4

    # Vector rỗng hoặc lệch kích thước -> 0.0 an toàn
    assert RAGService.compute_cosine_similarity([], vec1) == 0.0
    assert RAGService.compute_cosine_similarity(vec1, [1.0]) == 0.0


# =========================================================================
# 2. KIỂM THỬ XÁC THỰC VÀ PHÂN QUYỀN ENDPOINT POST /api/v1/rag/query
# =========================================================================

def test_rag_query_unauthorized_requires_auth(client, seeded_rag):
    """401 khi không gửi token xác thực."""
    payload = {
        "course_id": seeded_rag["course"],
        "query": "Khóa ngoại là gì?",
    }
    res = client.post("/api/v1/rag/query", json=payload)
    assert res.status_code == 401


def test_rag_query_course_not_found(client, seeded_rag):
    """404 khi course_id không tồn tại."""
    payload = {
        "course_id": 99999,
        "query": "Khóa ngoại là gì?",
    }
    res = client.post(
        "/api/v1/rag/query",
        json=payload,
        headers=auth_header(seeded_rag["u1"]),
    )
    assert res.status_code == 404
    assert "Không tìm thấy môn học" in res.json()["detail"]


def test_rag_query_student_not_enrolled_forbidden(client, seeded_rag):
    """403 khi sinh viên chưa ghi danh môn học."""
    payload = {
        "course_id": seeded_rag["course"],
        "query": "Khóa ngoại là gì?",
    }
    res = client.post(
        "/api/v1/rag/query",
        json=payload,
        headers=auth_header(seeded_rag["u2"]),  # u2 chưa ghi danh
    )
    assert res.status_code == 403
    assert "chưa ghi danh môn học này" in res.json()["detail"]


# =========================================================================
# 3. KIỂM THỬ CẢNH BÁO NGOÀI PHẠM VI (FR-RG-05)
# =========================================================================

def test_rag_query_out_of_scope_rejection(client, seeded_rag):
    """FR-RG-05: Từ chối câu hỏi hoàn toàn không liên quan đến giáo trình (ví dụ: công thức nấu ăn)."""
    payload = {
        "course_id": seeded_rag["course"],
        "query": "Cách nấu món phở bò Nam Định chuẩn vị gia truyền và luộc thịt bò thơm ngon",
    }
    res = client.post(
        "/api/v1/rag/query",
        json=payload,
        headers=auth_header(seeded_rag["u1"]),
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_out_of_scope"] is True
    assert "nằm ngoài phạm vi tài liệu giáo trình" in data["answer"]
    assert data["citations"] == []
    assert data["total_sources"] == 0


def test_rag_query_empty_documents_course(client, db_factory):
    """Khóa học chưa tải lên tài liệu nào cũng trả về cảnh báo ngoài phạm vi an toàn."""
    with db_factory() as db:
        pw = get_password_hash("MatKhau@123")
        u = User(email="fresh@univ.edu.vn", password_hash=pw, full_name="Fresh SV")
        c = Course(code="EMPTY101", title="Môn Chưa Có Sách")
        db.add_all([u, c])
        db.flush()
        db.add(Enrollment(user_id=u.id, course_id=c.id))
        db.commit()
        u_id, c_id = u.id, c.id

    payload = {
        "course_id": c_id,
        "query": "Nội dung bài học số một là gì?",
    }
    res = client.post(
        "/api/v1/rag/query",
        json=payload,
        headers=auth_header(u_id),
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_out_of_scope"] is True
    assert data["citations"] == []


# =========================================================================
# 4. KIỂM THỬ TRẢ LỜI CÓ TRÍCH DẪN SỐ TRANG (FR-RG-03 & COSINE SIMILARITY)
# =========================================================================

def test_rag_query_success_with_page_citations(client, seeded_rag, db_factory):
    """FR-RG-03: Trả về câu trả lời có trích dẫn số trang chính xác và lưu log kiểm toán."""
    payload = {
        "course_id": seeded_rag["course"],
        "query": "Khóa chính và khóa ngoại trong cơ sở dữ liệu quan hệ có vai trò gì?",
        "top_k": 2,
    }
    res = client.post(
        "/api/v1/rag/query",
        json=payload,
        headers=auth_header(seeded_rag["u1"]),
    )
    assert res.status_code == 200
    data = res.json()

    assert data["is_out_of_scope"] is False
    assert data["total_sources"] >= 1
    assert len(data["citations"]) >= 1

    # Kiểm tra trích dẫn số trang
    top_cite = data["citations"][0]
    assert top_cite["page_number"] == 5  # Đoạn về khóa chính/ngoại nằm ở Trang 5!
    assert top_cite["file_name"] == "Giao_Trinh_CSDL.pdf"
    assert top_cite["similarity_score"] > 0.20
    assert "Khóa chính" in top_cite["snippet"] or "Khóa ngoại" in top_cite["snippet"]

    # Câu trả lời phải có dẫn chứng số trang
    assert "Trang 5" in data["answer"]

    # Kiểm tra ghi log vào bảng ai_request_logs (NFR-15, BR-05)
    with db_factory() as db:
        log = (
            db.query(AIRequestLog)
            .filter(AIRequestLog.user_id == seeded_rag["u1"], AIRequestLog.feature == "RAG")
            .order_by(AIRequestLog.id.desc())
            .first()
        )
        assert log is not None
        assert log.provider == "openai"
        assert log.latency_ms > 0


def test_rag_query_filter_by_specific_document_id(client, seeded_rag):
    """Lọc tìm kiếm chỉ trong phạm vi tài liệu doc2 (Huong Dan SQL, Trang 3)."""
    payload = {
        "course_id": seeded_rag["course"],
        "query": "Cú pháp câu lệnh truy vấn SELECT SQL",
        "document_ids": [seeded_rag["doc2"]],  # Chỉ tìm trong doc 2
        "top_k": 1,
    }
    res = client.post(
        "/api/v1/rag/query",
        json=payload,
        headers=auth_header(seeded_rag["u1"]),
    )
    assert res.status_code == 200
    data = res.json()

    assert data["is_out_of_scope"] is False
    assert len(data["citations"]) == 1
    cite = data["citations"][0]
    assert cite["document_id"] == seeded_rag["doc2"]
    assert cite["file_name"] == "Huong_Dan_SQL.pdf"
    assert cite["page_number"] == 3
    assert "SELECT" in cite["snippet"]
