"""Kiểm thử tính năng RAG trích xuất và lưu trữ Vector Embedding PDF (TK-24 / Phân hệ 8).

Đáp ứng và xác thực 100% các tiêu chí:
- BR-09: Tệp .pdf chuẩn, kích thước tối đa 20MB, từ chối tệp quét ảnh không có text.
- FR-RG-01: Tải lên slide, giáo trình PDF theo môn học.
- FR-RG-02: Băm nhỏ văn bản thành các đoạn (chunks) 500 từ kèm 50 từ gối đầu (overlap), lưu số trang gốc.
- FR-RG-04: Quản lý tài liệu (danh sách, chi tiết, xóa cascade).
- SDD Bảng 17: Vector embedding 1536 chiều (chuẩn OpenAI text-embedding-3-small) lưu vào cột JSON.
"""
import io
import math
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import pypdf
from app.core.database import Base, get_db
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.course import Course, Enrollment
from app.models.rag import Document, DocumentChunk, AIRequestLog
from app.models.user import User
from app.services.rag_service import (
    RAGService,
    generate_deterministic_embedding,
    MAX_FILE_SIZE_BYTES,
    EMBEDDING_DIM,
)


def make_pdf_bytes(pages_text: list[str]) -> bytes:
    """Tạo tệp PDF hợp lệ trong bộ nhớ với danh sách văn bản theo từng trang."""
    import unicodedata

    def _safe_ascii(t: str) -> str:
        # Chuẩn hóa ký tự có dấu thành ASCII để đưa vào stream Type1 PDF
        normalized = "".join(
            c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn"
        )
        return normalized.replace("đ", "d").replace("Đ", "D")

    objects = []
    font_id = 1
    objects.append("1 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj")

    page_ids = []
    current_obj_id = 2
    content_objects = []
    page_objects = []

    for text in pages_text:
        c_id = current_obj_id
        current_obj_id += 1
        safe_text = _safe_ascii(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream = f"BT /F1 12 Tf 50 750 Td ({safe_text}) Tj ET"
        c_obj = f"{c_id} 0 obj\n<< /Length {len(stream)} >>\nstream\n{stream}\nendstream\nendobj"
        content_objects.append(c_obj)

        p_id = current_obj_id
        current_obj_id += 1
        page_ids.append(p_id)

    pages_root_id = current_obj_id
    current_obj_id += 1
    catalog_id = current_obj_id

    for c_id, p_id in zip(range(2, 2 + len(pages_text) * 2, 2), page_ids):
        p_obj = (
            f"{p_id} 0 obj\n"
            f"<< /Type /Page /Parent {pages_root_id} 0 R /MediaBox [0 0 612 792] "
            f"/Contents {c_id} 0 R /Resources << /Font << /F1 {font_id} 0 R >> >> >>\nendobj"
        )
        page_objects.append(p_obj)

    kids_str = " ".join(f"{pid} 0 R" for pid in page_ids)
    pages_root_obj = f"{pages_root_id} 0 obj\n<< /Type /Pages /Kids [{kids_str}] /Count {len(page_ids)} >>\nendobj"
    catalog_obj = f"{catalog_id} 0 obj\n<< /Type /Catalog /Pages {pages_root_id} 0 R >>\nendobj"

    all_objs = objects + content_objects + page_objects + [pages_root_obj, catalog_obj]

    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = [0]
    for obj_str in all_objs:
        offsets.append(out.tell())
        out.write(obj_str.encode("latin-1") + b"\n")

    xref_pos = out.tell()
    out.write(f"xref\n0 {len(all_objs)+1}\n0000000000 65535 f \n".encode("latin-1"))
    for off in offsets[1:]:
        out.write(f"{off:010d} 00000 n \n".encode("latin-1"))
    out.write(f"trailer\n<< /Size {len(all_objs)+1} /Root {catalog_id} 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("latin-1"))
    return out.getvalue()


def make_blank_scanned_pdf_bytes() -> bytes:
    """Tạo tệp PDF hợp lệ nhưng không chứa văn bản (mô phỏng tài liệu quét ảnh scan)."""
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


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
def seeded_env(db_factory):
    """Khởi tạo môi trường dữ liệu mẫu:
    - user1: Sinh viên đã ghi danh môn CS101
    - user2: Sinh viên chưa ghi danh
    - admin_user: Quản trị viên
    - course: Môn CS101
    """
    with db_factory() as db:
        pw = get_password_hash("Password123!")
        u1 = User(email="student1@univ.edu.vn", password_hash=pw, full_name="Sinh Viên 1", role="STUDENT")
        u2 = User(email="student2@univ.edu.vn", password_hash=pw, full_name="Sinh Viên 2", role="STUDENT")
        admin = User(email="admin@univ.edu.vn", password_hash=pw, full_name="Quản Trị Viên", role="ADMIN")
        course = Course(code="CS101", title="Cấu trúc Dữ liệu và Giải thuật")

        db.add_all([u1, u2, admin, course])
        db.flush()

        db.add(Enrollment(user_id=u1.id, course_id=course.id))
        db.commit()

        return {
            "u1": u1.id,
            "u2": u2.id,
            "admin": admin.id,
            "course": course.id,
        }


# =========================================================================
# 1. KIỂM THỬ THUẬT TOÁN VECTOR EMBEDDING 1536 CHIỀU
# =========================================================================

def test_deterministic_embedding_dimension_and_l2_norm():
    """Kiểm tra vector sinh ra luôn có đúng 1536 chiều và độ dài chuẩn hóa L2 = 1.0."""
    text = "Cơ sở dữ liệu quan hệ và mô hình thực thể kết hợp ERD"
    vec = generate_deterministic_embedding(text)

    # Đúng 1536 chiều (SDD Bảng 17)
    assert len(vec) == EMBEDDING_DIM
    assert isinstance(vec, list)
    assert all(isinstance(x, float) for x in vec)

    # Chuẩn hóa L2 xấp xỉ 1.0
    l2_norm = math.sqrt(sum(x * x for x in vec))
    assert abs(l2_norm - 1.0) < 1e-3

    # Tính xác định: cùng text phải ra cùng vector
    vec_repeat = generate_deterministic_embedding(text)
    assert vec == vec_repeat


def test_deterministic_embedding_similarity():
    """Kiểm tra văn bản có ngữ nghĩa tương đồng có Cosine Similarity cao hơn văn bản không liên quan."""
    text_db1 = "Hệ quản trị cơ sở dữ liệu quan hệ SQL bảng khóa chính khóa ngoại"
    text_db2 = "Mô hình quan hệ cơ sở dữ liệu khóa chính và truy vấn SQL"
    text_cooking = "Cách làm món phở bò truyền thống thơm ngon đậm đà gia vị"

    vec1 = generate_deterministic_embedding(text_db1)
    vec2 = generate_deterministic_embedding(text_db2)
    vec3 = generate_deterministic_embedding(text_cooking)

    # Cosine Similarity = Dot Product (vì cả hai đã chuẩn hóa L2)
    sim_db = sum(a * b for a, b in zip(vec1, vec2))
    sim_cross = sum(a * b for a, b in zip(vec1, vec3))

    assert sim_db > sim_cross


# =========================================================================
# 2. KIỂM THỬ TRÍCH XUẤT VĂN BẢN VÀ BĂM CHUNK 500 TỪ (FR-RG-02 / BR-09)
# =========================================================================

def test_extract_text_invalid_pdf_header(db_factory):
    """Ném lỗi HTTP 400 nếu tệp không có header %PDF-."""
    with db_factory() as db:
        srv = RAGService(db)
        with pytest.raises(Exception) as exc_info:
            srv.extract_text_from_pdf(b"This is not a PDF file.")
        assert "không phải là định dạng PDF hợp lệ" in str(exc_info.value.detail)


def test_extract_text_scanned_pdf_empty_text_rejected(db_factory):
    """Quy tắc BR-09: Từ chối tệp quét ảnh không có văn bản."""
    blank_pdf = make_blank_scanned_pdf_bytes()
    with db_factory() as db:
        srv = RAGService(db)
        with pytest.raises(Exception) as exc_info:
            srv.extract_text_from_pdf(blank_pdf)
        assert exc_info.value.status_code == 400
        assert "tài liệu quét ảnh không được hỗ trợ theo quy tắc BR-09" in str(exc_info.value.detail)


def test_chunking_500_words_with_50_overlap(db_factory):
    """FR-RG-02: Chia đoạn 500 từ kèm 50 từ gối đầu (overlap)."""
    with db_factory() as db:
        srv = RAGService(db)
        # Tạo văn bản gồm 1100 từ: 1100 từ sẽ chia thành:
        # Step = 450 từ
        # Chunk 0: 0 -> 500 (500 từ)
        # Chunk 1: 450 -> 950 (500 từ)
        # Chunk 2: 900 -> 1100 (200 từ)
        words = [f"word{i}" for i in range(1100)]
        pages_text = [
            (1, " ".join(words[:600])),
            (2, " ".join(words[600:])),
        ]

        chunks = srv.chunk_document_text(pages_text, chunk_size_words=500, overlap_words=50)

        assert len(chunks) == 3
        assert chunks[0]["chunk_index"] == 0
        assert chunks[0]["word_count"] == 500
        assert chunks[0]["page_number"] == 1

        assert chunks[1]["chunk_index"] == 1
        assert chunks[1]["word_count"] == 500
        # Kiểm tra tính gối đầu (overlap 50 từ):
        # 50 từ cuối của chunk 0 phải xuất hiện ở 50 từ đầu của chunk 1
        chunk0_words = chunks[0]["content"].split()
        chunk1_words = chunks[1]["content"].split()
        assert chunk0_words[-50:] == chunk1_words[:50]

        assert chunks[2]["chunk_index"] == 2
        assert chunks[2]["word_count"] == 200
        chunk2_words = chunks[2]["content"].split()
        assert chunk1_words[-50:] == chunk2_words[:50]


# =========================================================================
# 3. KIỂM THỬ ENDPOINT POST /api/v1/rag/upload
# =========================================================================

def test_upload_unauthorized_requires_token(client):
    """Chặn truy cập nếu không có token xác thực (401)."""
    res = client.post("/api/v1/rag/upload")
    assert res.status_code == 401


def test_upload_course_not_found(client, seeded_env):
    """Trả về 404 nếu course_id không tồn tại."""
    pdf_bytes = make_pdf_bytes(["Nội dung môn học"])
    files = {"file": ("tailieu.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    data = {"course_id": 9999}
    res = client.post(
        "/api/v1/rag/upload",
        files=files,
        data=data,
        headers=auth_header(seeded_env["u1"]),
    )
    assert res.status_code == 404
    assert "Không tìm thấy môn học" in res.json()["detail"]


def test_upload_student_not_enrolled_forbidden(client, seeded_env):
    """Trả về 403 nếu sinh viên chưa ghi danh môn học."""
    pdf_bytes = make_pdf_bytes(["Nội dung môn học"])
    files = {"file": ("tailieu.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    data = {"course_id": seeded_env["course"]}
    res = client.post(
        "/api/v1/rag/upload",
        files=files,
        data=data,
        headers=auth_header(seeded_env["u2"]),  # u2 chưa ghi danh
    )
    assert res.status_code == 403
    assert "chưa ghi danh" in res.json()["detail"]


def test_upload_invalid_extension_rejected(client, seeded_env):
    """BR-09: Từ chối tệp không có đuôi .pdf."""
    files = {"file": ("tailieu.docx", io.BytesIO(b"dummy text"), "application/vnd.openxmlformats")}
    data = {"course_id": seeded_env["course"]}
    res = client.post(
        "/api/v1/rag/upload",
        files=files,
        data=data,
        headers=auth_header(seeded_env["u1"]),
    )
    assert res.status_code == 400
    assert "Chỉ chấp nhận tệp định dạng .pdf" in res.json()["detail"]


def test_upload_empty_file_rejected(client, seeded_env):
    """Từ chối tệp rỗng 0 bytes."""
    files = {"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")}
    data = {"course_id": seeded_env["course"]}
    res = client.post(
        "/api/v1/rag/upload",
        files=files,
        data=data,
        headers=auth_header(seeded_env["u1"]),
    )
    assert res.status_code == 400
    assert "rỗng" in res.json()["detail"]


def test_upload_scanned_image_empty_text_rejected(client, seeded_env):
    """BR-09: Tệp PDF quét ảnh không có text bị từ chối 400."""
    scanned_pdf = make_blank_scanned_pdf_bytes()
    files = {"file": ("scanned_document.pdf", io.BytesIO(scanned_pdf), "application/pdf")}
    data = {"course_id": seeded_env["course"]}
    res = client.post(
        "/api/v1/rag/upload",
        files=files,
        data=data,
        headers=auth_header(seeded_env["u1"]),
    )
    assert res.status_code == 400
    assert "tài liệu quét ảnh không được hỗ trợ" in res.json()["detail"]


def test_upload_file_size_exceeds_20mb_rejected(client, seeded_env):
    """BR-09: Tệp PDF có kích thước vượt quá 20MB bị từ chối với mã HTTP 413."""
    # Tạo nội dung giả lập 20MB + 1024 bytes bắt đầu bằng %PDF-
    large_pdf_header = b"%PDF-1.4\n" + b"0" * (MAX_FILE_SIZE_BYTES + 1024)
    files = {"file": ("oversized.pdf", io.BytesIO(large_pdf_header), "application/pdf")}
    data = {"course_id": seeded_env["course"]}
    res = client.post(
        "/api/v1/rag/upload",
        files=files,
        data=data,
        headers=auth_header(seeded_env["u1"]),
    )
    assert res.status_code == 413
    assert "vượt quá giới hạn cho phép tối đa 20MB" in res.json()["detail"]


def test_upload_success_end_to_end_and_db_persistence(client, seeded_env, db_factory):
    """Kiểm thử tải lên thành công:
    - Trả về mã 201 Created kèm đầy đủ metadata.
    - Lưu vào bảng documents và document_chunks.
    - Vector embedding có đúng 1536 chiều.
    - Ghi nhận vào ai_request_logs (feature RAG).
    """
    page1 = "Trang một: Giới thiệu hệ quản trị cơ sở dữ liệu quan hệ và các đặc trưng của mô hình dữ liệu."
    page2 = "Trang hai: Đại số quan hệ gồm các phép chọn, chiếu, tích Descartes, kết nối tự nhiên và phép chia."
    pdf_bytes = make_pdf_bytes([page1, page2])

    files = {"file": ("giao_trinh_csdl.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    data = {"course_id": seeded_env["course"]}

    res = client.post(
        "/api/v1/rag/upload",
        files=files,
        data=data,
        headers=auth_header(seeded_env["u1"]),
    )

    assert res.status_code == 201
    body = res.json()
    assert body["file_name"] == "giao_trinh_csdl.pdf"
    assert body["course_id"] == seeded_env["course"]
    assert body["total_pages"] == 2
    assert body["total_chunks"] >= 1
    assert body["embedding_dim"] == 1536
    doc_id = body["document_id"]

    # Kiểm tra lưu trữ trong CSDL
    with db_factory() as db:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        assert doc is not None
        assert doc.file_name == "giao_trinh_csdl.pdf"
        assert doc.uploaded_by == seeded_env["u1"]

        chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).all()
        assert len(chunks) == body["total_chunks"]
        for c in chunks:
            assert c.chunk_index >= 0
            assert c.page_number in [1, 2]
            assert isinstance(c.embedding, list)
            assert len(c.embedding) == 1536  # Chuẩn 1536 chiều
            # Kiểm tra L2 norm của vector
            norm = math.sqrt(sum(x * x for x in c.embedding))
            assert abs(norm - 1.0) < 1e-2

        # Kiểm tra ghi log ai_request_logs
        log = db.query(AIRequestLog).filter(AIRequestLog.feature == "RAG").first()
        assert log is not None
        assert log.user_id == seeded_env["u1"]
        assert log.provider == "openai"


# =========================================================================
# 4. KIỂM THỬ QUẢN LÝ TÀI LIỆU (FR-RG-04: DANH SÁCH, CHI TIẾT, XÓA CASCADE)
# =========================================================================

def test_list_and_get_document_detail(client, seeded_env):
    """Kiểm tra danh sách và xem chi tiết tài liệu."""
    pdf_bytes = make_pdf_bytes(["Nội dung tài liệu học tập kiến trúc máy tính."])
    files = {"file": ("ktmt.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    data = {"course_id": seeded_env["course"]}

    up_res = client.post(
        "/api/v1/rag/upload",
        files=files,
        data=data,
        headers=auth_header(seeded_env["u1"]),
    )
    doc_id = up_res.json()["document_id"]

    # Lấy danh sách tài liệu
    list_res = client.get(
        f"/api/v1/rag/documents?course_id={seeded_env['course']}",
        headers=auth_header(seeded_env["u1"]),
    )
    assert list_res.status_code == 200
    list_body = list_res.json()
    assert list_body["total"] >= 1
    assert any(d["id"] == doc_id for d in list_body["items"])

    # Lấy chi tiết tài liệu
    detail_res = client.get(
        f"/api/v1/rag/documents/{doc_id}",
        headers=auth_header(seeded_env["u1"]),
    )
    assert detail_res.status_code == 200
    detail_body = detail_res.json()
    assert detail_body["id"] == doc_id
    assert len(detail_body["chunks"]) >= 1
    assert detail_body["chunks"][0]["embedding_dim"] == 1536


def test_delete_document_cascade_chunks(client, seeded_env, db_factory):
    """Xóa tài liệu và kiểm tra lan truyền CASCADE DELETE toàn bộ chunks."""
    pdf_bytes = make_pdf_bytes(["Tài liệu sẽ bị xóa sau khi kiểm tra cascade."])
    files = {"file": ("to_delete.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    data = {"course_id": seeded_env["course"]}

    up_res = client.post(
        "/api/v1/rag/upload",
        files=files,
        data=data,
        headers=auth_header(seeded_env["u1"]),
    )
    doc_id = up_res.json()["document_id"]

    # Thực hiện xóa
    del_res = client.delete(
        f"/api/v1/rag/documents/{doc_id}",
        headers=auth_header(seeded_env["u1"]),
    )
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "success"

    # Kiểm tra CSDL: Document và DocumentChunks đều đã bị xóa
    with db_factory() as db:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        assert doc is None
        chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).all()
        assert len(chunks) == 0


def test_delete_document_forbidden_for_other_student(client, seeded_env):
    """Sinh viên khác không có quyền xóa tài liệu của người khác (403)."""
    pdf_bytes = make_pdf_bytes(["Tài liệu của SV 1."])
    files = {"file": ("sv1_doc.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    data = {"course_id": seeded_env["course"]}

    up_res = client.post(
        "/api/v1/rag/upload",
        files=files,
        data=data,
        headers=auth_header(seeded_env["u1"]),
    )
    doc_id = up_res.json()["document_id"]

    # Sinh viên 2 cố gắng xóa tài liệu của Sinh viên 1
    del_res = client.delete(
        f"/api/v1/rag/documents/{doc_id}",
        headers=auth_header(seeded_env["u2"]),
    )
    assert del_res.status_code == 403
    assert "chỉ có thể xóa tài liệu do chính mình tải lên" in del_res.json()["detail"]

    # Nhưng ADMIN có thể xóa
    admin_del = client.delete(
        f"/api/v1/rag/documents/{doc_id}",
        headers=auth_header(seeded_env["admin"]),
    )
    assert admin_del.status_code == 200
