import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from app.core.database import Base
from app.models import (
    User,
    RefreshToken,
    UserRole,
    UserStatus,
    Course,
    Enrollment,
    Lesson,
    Topic,
    LessonContent,
    CourseStatus,
    ContentType,
)


@pytest.fixture(scope="function")
def db_session():
    """
    Tạo in-memory SQLite database riêng biệt cho mỗi unit test để đảm bảo tính cô lập 100%.
    Bật PRAGMA foreign_keys=ON để kiểm tra toàn vẹn khóa ngoại và cascade delete.
    """
    engine = create_engine("sqlite:///:memory:", echo=False)

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


# ==============================================================================
# 1. Tests cho Bảng users và refresh_tokens
# ==============================================================================

def test_create_user_success(db_session):
    user = User(
        email="student@learnmate.edu.vn",
        password_hash="$2b$12$hashedpasswordexamplestring1234567890",
        full_name="Nguyễn Văn A",
        role=UserRole.STUDENT.value,
        status=UserStatus.ACTIVE.value
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.id is not None
    assert user.email == "student@learnmate.edu.vn"
    assert user.role == "STUDENT"
    assert user.status == "ACTIVE"
    assert user.created_at is not None


def test_user_email_unique_constraint(db_session):
    user1 = User(
        email="duplicate@learnmate.edu.vn",
        password_hash="hash1",
        full_name="User 1"
    )
    user2 = User(
        email="duplicate@learnmate.edu.vn",
        password_hash="hash2",
        full_name="User 2"
    )
    db_session.add(user1)
    db_session.commit()

    db_session.add(user2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_refresh_token_relationship_and_cascade(db_session):
    user = User(
        email="token_user@learnmate.edu.vn",
        password_hash="hash",
        full_name="Token User"
    )
    db_session.add(user)
    db_session.commit()

    token = RefreshToken(
        user_id=user.id,
        token_hash="sample_refresh_token_hash_value_123",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7)
    )
    db_session.add(token)
    db_session.commit()

    # Kiểm tra quan hệ 2 chiều
    assert len(user.refresh_tokens) == 1
    assert user.refresh_tokens[0].token_hash == "sample_refresh_token_hash_value_123"
    assert token.user.id == user.id

    # Kiểm tra Cascade Delete: Xóa User -> RefreshToken bị xóa theo
    db_session.delete(user)
    db_session.commit()

    assert db_session.query(RefreshToken).filter_by(id=token.id).first() is None


# ==============================================================================
# 2. Tests cho Bảng courses và enrollments
# ==============================================================================

def test_create_course_success(db_session):
    course = Course(
        code="CS101",
        title="Nhập môn Trí tuệ Nhân tạo",
        description="Khóa học cung cấp kiến thức nền tảng về AI và Machine Learning",
        status=CourseStatus.ACTIVE.value
    )
    db_session.add(course)
    db_session.commit()
    db_session.refresh(course)

    assert course.id is not None
    assert course.code == "CS101"
    assert course.status == "ACTIVE"


def test_course_code_unique_constraint(db_session):
    c1 = Course(code="MATH101", title="Toán cao cấp 1")
    c2 = Course(code="MATH101", title="Toán cao cấp 2")
    db_session.add(c1)
    db_session.commit()

    db_session.add(c2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_enrollment_unique_constraint(db_session):
    user = User(email="learner@learnmate.edu.vn", password_hash="hash", full_name="Học Viên")
    course = Course(code="PHY101", title="Vật lý đại cương")
    db_session.add_all([user, course])
    db_session.commit()

    # Ghi danh lần 1
    enrollment1 = Enrollment(user_id=user.id, course_id=course.id)
    db_session.add(enrollment1)
    db_session.commit()

    # Ghi danh lần 2 cùng user và course -> Vi phạm UNIQUE uq_user_course
    enrollment2 = Enrollment(user_id=user.id, course_id=course.id)
    db_session.add(enrollment2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# ==============================================================================
# 3. Tests cho Bảng lessons, topics, lesson_contents
# ==============================================================================

def test_create_lesson_topic_content_hierarchy(db_session):
    course = Course(code="DB101", title="Hệ Quản trị Cơ sở Dữ liệu")
    db_session.add(course)
    db_session.commit()

    # Tạo Lesson
    lesson = Lesson(
        course_id=course.id,
        title="Bài 1: Tổng quan về Mô hình Quan hệ",
        order_index=1
    )
    db_session.add(lesson)
    db_session.commit()

    # Tạo Topic
    topic = Topic(
        lesson_id=lesson.id,
        name="Đại số quan hệ và Chuẩn hóa 3NF",
        description="Các phép toán chọn, chiếu, kết nối và các dạng chuẩn 1NF, 2NF, 3NF"
    )
    # Tạo LessonContent
    content = LessonContent(
        lesson_id=lesson.id,
        content_type=ContentType.MARKDOWN.value,
        body="# Đại số quan hệ\nNội dung chi tiết bài học..."
    )
    db_session.add_all([topic, content])
    db_session.commit()

    assert len(course.lessons) == 1
    assert len(lesson.topics) == 1
    assert len(lesson.contents) == 1
    assert lesson.topics[0].name == "Đại số quan hệ và Chuẩn hóa 3NF"
    assert lesson.contents[0].content_type == "MARKDOWN"


def test_cascade_delete_course_hierarchy(db_session):
    course = Course(code="OS101", title="Hệ Điều Hành")
    db_session.add(course)
    db_session.commit()

    lesson = Lesson(course_id=course.id, title="Tiến trình và Luồng")
    db_session.add(lesson)
    db_session.commit()

    topic = Topic(lesson_id=lesson.id, name="Đồng bộ hóa Semaphore")
    content = LessonContent(lesson_id=lesson.id, content_type=ContentType.PDF.value, body="link_to_file.pdf")
    db_session.add_all([topic, content])
    db_session.commit()

    lesson_id = lesson.id
    topic_id = topic.id
    content_id = content.id

    # Xóa Course -> Toàn bộ Lesson, Topic, Content thuộc Course đó phải bị xóa theo (Cascade)
    db_session.delete(course)
    db_session.commit()

    assert db_session.query(Lesson).filter_by(id=lesson_id).first() is None
    assert db_session.query(Topic).filter_by(id=topic_id).first() is None
    assert db_session.query(LessonContent).filter_by(id=content_id).first() is None
