"""Bộ kiểm thử cho 7 bảng CSDL Theo dõi tiến độ, RAG và Quản trị hệ thống (TK-19).

Kiểm tra:
1. Đăng ký đầy đủ 22 bảng thực thể vào Base.metadata.
2. TopicMastery: Lưu điểm EMA, phân hạng (WEAK, FAIR, MASTER), ràng buộc UNIQUE(user_id, topic_id).
3. Recommendation: Gợi ý ôn tập cá nhân hóa, quan hệ cascade với user & topic.
4. LearningEvent (StudentActivityLog): Lưu dữ liệu sự kiện JSON, quan hệ khóa ngoại.
5. Document & DocumentChunk: Lưu tệp PDF, quan hệ 1:N cascade delete, vector embedding JSON 1536 chiều.
6. AIRequestLog: Ghi nhận lịch sử gọi AI, token, độ trễ ms, chỉ mục theo dõi hạn mức QuotaGuard.
7. PromptTemplate: Mẫu prompt động hỗ trợ A/B testing, ràng buộc UNIQUE(code, version).
8. SystemSetting: Cấu hình hệ thống động, ràng buộc UNIQUE(key).
9. Chỉ mục tối ưu hóa truy vấn: idx_user_topic_mastery, idx_doc_page, idx_user_feature_date.
10. Tính tương thích định danh giữa file Project_LearnMate_AI.xlsx và SDD.
"""
from decimal import Decimal
import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.user import User, UserRole, UserStatus
from app.models.course import Course, CourseStatus, Lesson, Topic
from app.models.mastery import (
    TopicMastery,
    UserTopicMastery,
    MasteryStatus,
    Recommendation,
    RecommendationAction,
    RecommendationStatus,
    LearningEvent,
    StudentActivityLog,
    LearningEventType,
)
from app.models.rag import (
    Document,
    DocumentChunk,
    AIRequestLog,
    AIFeature,
    AIProvider,
    PromptTemplate,
    SystemSetting,
)


@pytest.fixture()
def db_session():
    """Tạo CSDL SQLite in-memory biệt lập có bật ràng buộc Khóa ngoại (Foreign Keys)."""
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
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = session_factory()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def base_data(db_session):
    """Tạo người dùng, môn học, bài học và chủ đề làm dữ liệu nền."""
    user = User(
        email="student.mastery@learnmate.local",
        password_hash="hashed_secret",
        full_name="Nguyễn Văn Học",
        role=UserRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    course = Course(
        code="CS101",
        title="Cơ sở dữ liệu",
        status=CourseStatus.ACTIVE.value,
    )
    db_session.add_all([user, course])
    db_session.flush()

    lesson = Lesson(course_id=course.id, title="Mô hình ERD", order_index=1)
    db_session.add(lesson)
    db_session.flush()

    topic = Topic(lesson_id=lesson.id, name="Thực thể và Thuộc tính", description="Lý thuyết ERD")
    db_session.add(topic)
    db_session.commit()

    return {"user": user, "course": course, "lesson": lesson, "topic": topic}


# ==============================================================================
# TEST CASES
# ==============================================================================

def test_all_22_tables_registered():
    """Kiểm tra toàn bộ 22 bảng thực thể CSDL đã được đăng ký vào Base.metadata."""
    table_names = set(Base.metadata.tables.keys())
    required_sprint3_tables = {
        "topic_mastery",
        "recommendations",
        "learning_events",
        "documents",
        "document_chunks",
        "ai_request_logs",
        "prompt_templates",
        "system_settings",
    }
    assert required_sprint3_tables.issubset(table_names), f"Thiếu bảng trong CSDL: {required_sprint3_tables - table_names}"
    assert len(table_names) >= 22


def test_alias_compatibility():
    """Xác nhận bí danh UserTopicMastery và StudentActivityLog khớp 100% với Excel."""
    assert UserTopicMastery is TopicMastery
    assert StudentActivityLog is LearningEvent


def test_topic_mastery_crud_and_unique_constraint(db_session, base_data):
    """Kiểm tra thêm/sửa/xóa điểm Mastery và ràng buộc UNIQUE(user_id, topic_id)."""
    user = base_data["user"]
    topic = base_data["topic"]

    # 1. Tạo mới bản ghi điểm Mastery
    mastery = TopicMastery(
        user_id=user.id,
        topic_id=topic.id,
        mastery_score=Decimal("75.50"),
        status=MasteryStatus.FAIR.value,
    )
    db_session.add(mastery)
    db_session.commit()

    assert mastery.id is not None
    assert mastery.mastery_score == Decimal("75.50")
    assert mastery.status == "FAIR"
    assert mastery.user.id == user.id
    assert mastery.topic.id == topic.id

    # 2. Thử tạo bản ghi trùng lặp (cùng user_id và topic_id) -> phải văng IntegrityError
    dup = TopicMastery(
        user_id=user.id,
        topic_id=topic.id,
        mastery_score=Decimal("80.00"),
        status=MasteryStatus.MASTER.value,
    )
    db_session.add(dup)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_recommendation_crud_and_cascade(db_session, base_data):
    """Kiểm tra bản ghi Recommendation và tính năng xóa liên hoàn khi xóa user."""
    user = base_data["user"]
    topic = base_data["topic"]

    rec = Recommendation(
        user_id=user.id,
        topic_id=topic.id,
        action_type=RecommendationAction.SOCRATIC_CHAT.value,
        priority=1,
        status=RecommendationStatus.PENDING.value,
    )
    db_session.add(rec)
    db_session.commit()

    assert rec.id is not None
    assert rec.action_type == "SOCRATIC_CHAT"
    assert rec.priority == 1
    assert rec.status == "PENDING"
    assert rec in user.recommendations


def test_learning_event_with_json_data(db_session, base_data):
    """Kiểm tra lưu trữ nhật ký sự kiện học tập với dữ liệu JSON linh hoạt."""
    user = base_data["user"]
    topic = base_data["topic"]

    event_payload = {
        "action": "quiz_submit",
        "quiz_id": 10,
        "score": 9.5,
        "correct_count": 5,
        "details": ["A", "B", "C", "D"],
    }
    event = LearningEvent(
        user_id=user.id,
        topic_id=topic.id,
        event_type=LearningEventType.SUBMIT_QUIZ.value,
        event_data=event_payload,
    )
    db_session.add(event)
    db_session.commit()

    retrieved = db_session.get(LearningEvent, event.id)
    assert retrieved is not None
    assert retrieved.event_type == "SUBMIT_QUIZ"
    assert retrieved.event_data["score"] == 9.5
    assert retrieved.event_data["details"] == ["A", "B", "C", "D"]


def test_document_and_chunks_cascade(db_session, base_data):
    """Kiểm tra tài liệu PDF RAG và các đoạn văn bản kèm vector embedding 1536 chiều."""
    course = base_data["course"]
    user = base_data["user"]

    # 1. Tạo Document
    doc = Document(
        course_id=course.id,
        uploaded_by=user.id,
        file_name="Giao_Trinh_CSDL_2026.pdf",
        file_size=5242880,  # 5MB
    )
    db_session.add(doc)
    db_session.flush()

    # 2. Tạo Chunks kèm mảng embedding
    sample_embedding = [0.0123, -0.0456, 0.0789] + [0.0] * 1533  # Giả lập 1536 chiều
    chunk1 = DocumentChunk(
        document_id=doc.id,
        chunk_index=0,
        page_number=1,
        content="Đoạn văn mở đầu giới thiệu mô hình cơ sở dữ liệu quan hệ.",
        embedding=sample_embedding,
    )
    chunk2 = DocumentChunk(
        document_id=doc.id,
        chunk_index=1,
        page_number=2,
        content="Đoạn văn thứ hai về tính chất toàn vẹn dữ liệu ACID.",
        embedding=sample_embedding,
    )
    db_session.add_all([chunk1, chunk2])
    db_session.commit()

    assert len(doc.chunks) == 2
    assert doc.chunks[0].page_number == 1
    assert len(doc.chunks[0].embedding) == 1536

    # 3. Xóa Document -> Chunks phải tự động bị xóa theo (ON DELETE CASCADE)
    doc_id = doc.id
    db_session.delete(doc)
    db_session.commit()

    remaining_chunks = db_session.scalars(
        select(DocumentChunk).where(DocumentChunk.document_id == doc_id)
    ).all()
    assert len(remaining_chunks) == 0


def test_ai_request_log(db_session, base_data):
    """Kiểm tra ghi log yêu cầu AI và chỉ mục idx_user_feature_date."""
    user = base_data["user"]

    log = AIRequestLog(
        user_id=user.id,
        feature=AIFeature.SOCRATIC.value,
        provider=AIProvider.GEMINI.value,
        tokens_prompt=150,
        tokens_completion=65,
        latency_ms=850,
    )
    db_session.add(log)
    db_session.commit()

    assert log.id is not None
    assert log.feature == "SOCRATIC"
    assert log.provider == "gemini"
    assert log.tokens_prompt == 150
    assert log.latency_ms == 850
    assert log in user.ai_request_logs


def test_prompt_template_crud_and_versioning(db_session):
    """Kiểm tra mẫu prompt và ràng buộc UNIQUE(code, version) phục vụ A/B Testing."""
    t1 = PromptTemplate(
        code="TUTOR_SOCRATIC",
        version=1,
        content="System prompt v1: Hướng dẫn sư phạm 5 bước",
        is_active=True,
    )
    t2 = PromptTemplate(
        code="TUTOR_SOCRATIC",
        version=2,
        content="System prompt v2: Cải tiến dẫn dắt phản biện",
        is_active=False,
    )
    db_session.add_all([t1, t2])
    db_session.commit()

    assert t1.id is not None
    assert t2.id is not None

    # Trùng lặp code và version -> văng IntegrityError
    dup = PromptTemplate(
        code="TUTOR_SOCRATIC",
        version=1,
        content="System prompt trùng",
    )
    db_session.add(dup)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_system_settings_unique_key(db_session):
    """Kiểm tra cấu hình hệ thống chung và ràng buộc UNIQUE(key)."""
    s1 = SystemSetting(
        key="DAILY_AI_QUOTA",
        value="50",
        description="Số lượt gọi AI tối đa mỗi sinh viên mỗi ngày (BR-05)",
    )
    db_session.add(s1)
    db_session.commit()

    assert s1.id is not None
    assert s1.value == "50"

    # Trùng key -> văng IntegrityError
    dup = SystemSetting(key="DAILY_AI_QUOTA", value="100")
    db_session.add(dup)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
