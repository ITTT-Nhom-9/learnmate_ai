"""Bộ kiểm thử cho API Sinh đề trắc nghiệm thích ứng AI Quiz (TK-15 / Phân hệ 5).

Kiểm tra:
1. Sinh đề trắc nghiệm thành công (POST /api/v1/quizzes/generate và /api/v1/quiz/generate).
2. Lưu trữ đầy đủ CSDL: Bảng quizzes, questions, question_options.
3. Quy tắc bảo mật đề thi BR-04: Dữ liệu trả về Frontend TUYỆT ĐỐI không có is_correct hoặc explanation.
4. Xử lý lỗi: Chưa đăng nhập (401), bài học/chủ đề không tồn tại (404), AI service gặp sự cố (503).
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models import Course, CourseStatus, Lesson, LessonContent, Topic, User
from app.models.quiz import Question, QuestionOption, Quiz
from app.services.ai_quiz_client import AIQuizClient, AIQuizServiceError, get_ai_quiz_client


SAMPLE_QUIZ_AI_RESPONSE = {
    "bundle": {
        "title": "Trắc nghiệm: Cây nhị phân tìm kiếm BST",
        "difficulty": "MEDIUM",
        "total_questions": 2,
        "questions": [
            {
                "content": "Chiều cao trung bình của cây nhị phân tìm kiếm cân bằng có n nút là bao nhiêu?",
                "options": [
                    {"opt_label": "A", "content": "O(n)", "is_correct": False},
                    {"opt_label": "B", "content": "O(log n)", "is_correct": True},
                    {"opt_label": "C", "content": "O(n log n)", "is_correct": False},
                    {"opt_label": "D", "content": "O(1)", "is_correct": False},
                ],
                "explanation": "Cây cân bằng loại bỏ một nửa số nút mỗi bước nên chiều cao là log2(n).",
            },
            {
                "content": "Trường hợp xấu nhất của tìm kiếm trong BST xảy ra khi nào?",
                "options": [
                    {"opt_label": "A", "content": "Cây cân bằng hoàn hảo", "is_correct": False},
                    {"opt_label": "B", "content": "Cây suy biến thành danh sách liên kết", "is_correct": True},
                    {"opt_label": "C", "content": "Khóa cần tìm nằm ở nút gốc", "is_correct": False},
                    {"opt_label": "D", "content": "Cây có số nút chẵn", "is_correct": False},
                ],
                "explanation": "Khi chèn các phần tử tăng dần, cây suy biến thành đường thẳng chiều cao n-1.",
            },
        ],
    },
    "provider": "gemini",
    "model": "gemini-3.5-flash-lite",
    "usage": {
        "tokens_prompt": 50,
        "tokens_completion": 100,
        "total_tokens": 150,
        "latency_ms": 320,
    },
}


class FakeAIQuizClient(AIQuizClient):
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.captured_payloads: list[dict] = []

    async def generate_quiz(self, payload: dict) -> dict:
        self.captured_payloads.append(payload)
        if self.should_fail:
            raise AIQuizServiceError("AI_SERVICE_UNAVAILABLE", "AI Service đang bận", status_code=503)
        return SAMPLE_QUIZ_AI_RESPONSE


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
def ai_quiz():
    return FakeAIQuizClient()


@pytest.fixture()
def client(db_factory, ai_quiz):
    def _override_get_db():
        db = db_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_ai_quiz_client] = lambda: ai_quiz
    yield TestClient(app)
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_ai_quiz_client, None)


@pytest.fixture()
def seeded_data(db_factory):
    with db_factory() as db:
        user = User(
            email="student@learnmate.local",
            password_hash=get_password_hash("password123"),
            full_name="Sinh Viên Test",
            role="STUDENT",
            status="ACTIVE",
        )
        course = Course(code="CS101", title="Cấu trúc dữ liệu & Giải thuật", status=CourseStatus.ACTIVE.value)
        db.add_all([user, course])
        db.flush()

        lesson = Lesson(course_id=course.id, title="Bài 1: Cây nhị phân", order_index=1)
        db.add(lesson)
        db.flush()

        topic = Topic(lesson_id=lesson.id, name="Cây BST", description="Binary Search Tree")
        content = LessonContent(
            lesson_id=lesson.id,
            content_type="MARKDOWN",
            body="Cây nhị phân tìm kiếm BST có tính chất mọi khóa cây con trái nhỏ hơn nút gốc.",
        )
        db.add_all([topic, content])
        db.commit()

        return {
            "user_id": user.id,
            "course_id": course.id,
            "lesson_id": lesson.id,
            "topic_id": topic.id,
        }


def auth_header(user_id: int) -> dict:
    token = create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# TESTS
# ==============================================================================

def test_generate_quiz_success_and_br04_security_check(client, db_factory, seeded_data, ai_quiz):
    """
    Kiểm tra sinh quiz thành công và tuân thủ BR-04:
    - Trả về status 201 Created.
    - Lưu đúng các bản ghi Quiz, Question, QuestionOption trong DB (có is_correct).
    - Phản hồi gửi ra Client KHÔNG BAO GIỜ chứa is_correct hoặc explanation.
    """
    response = client.post(
        "/api/v1/quizzes/generate",
        headers=auth_header(seeded_data["user_id"]),
        json={
            "lesson_id": seeded_data["lesson_id"],
            "topic_id": seeded_data["topic_id"],
            "num_questions": 5,
            "difficulty": "MEDIUM",
        },
    )
    assert response.status_code == 201
    data = response.json()

    assert "id" in data
    assert data["title"] == "Trắc nghiệm: Cây nhị phân tìm kiếm BST"
    assert data["total_questions"] == 2
    assert len(data["questions"]) == 2

    # KIỂM TRA BẢO MẬT BR-04: Tuyệt đối không để lộ đáp án đúng và lời giải
    response_raw_text = response.text
    assert "is_correct" not in response_raw_text
    assert "explanation" not in response_raw_text

    # Kiểm tra cấu trúc từng phương án
    for q in data["questions"]:
        assert "content" in q
        assert len(q["options"]) == 4
        for opt in q["options"]:
            assert "id" in opt
            assert opt["opt_label"] in ["A", "B", "C", "D"]
            assert "is_correct" not in opt

    # KIỂM TRA LƯU TRỮ CSDL: Trong DB phải có đầy đủ is_correct và explanation
    with db_factory() as db:
        quiz_in_db = db.scalar(select(Quiz).where(Quiz.id == data["id"]))
        assert quiz_in_db is not None
        assert quiz_in_db.topic_id == seeded_data["topic_id"]

        questions_in_db = db.scalars(select(Question).where(Question.quiz_id == quiz_in_db.id)).all()
        assert len(questions_in_db) == 2
        for q_db in questions_in_db:
            assert len(q_db.explanation) > 0  # Có explanation trong DB
            options_in_db = db.scalars(select(QuestionOption).where(QuestionOption.question_id == q_db.id)).all()
            assert len(options_in_db) == 4
            correct_opts = [o for o in options_in_db if o.is_correct]
            assert len(correct_opts) == 1  # Có đúng 1 đáp án đúng trong DB


def test_generate_quiz_alias_endpoint(client, seeded_data):
    """Kiểm tra tuyến đường alias POST /api/v1/quiz/generate."""
    response = client.post(
        "/api/v1/quiz/generate",
        headers=auth_header(seeded_data["user_id"]),
        json={
            "lesson_id": seeded_data["lesson_id"],
            "num_questions": 5,
        },
    )
    assert response.status_code == 201
    assert response.json()["total_questions"] == 2


def test_generate_quiz_unauthorized(client, seeded_data):
    """Chặn 401 khi không có JWT Token."""
    response = client.post(
        "/api/v1/quizzes/generate",
        json={"lesson_id": seeded_data["lesson_id"]},
    )
    assert response.status_code == 401


def test_generate_quiz_not_found(client, seeded_data):
    """Báo 404 khi bài học không tồn tại."""
    response = client.post(
        "/api/v1/quizzes/generate",
        headers=auth_header(seeded_data["user_id"]),
        json={"lesson_id": 99999},
    )
    assert response.status_code == 404


def test_generate_quiz_ai_service_unavailable(client, seeded_data):
    """Báo 503 khi AI Microservice gặp sự cố kết nối."""
    failing_client = FakeAIQuizClient(should_fail=True)
    app.dependency_overrides[get_ai_quiz_client] = lambda: failing_client
    try:
        response = client.post(
            "/api/v1/quizzes/generate",
            headers=auth_header(seeded_data["user_id"]),
            json={"lesson_id": seeded_data["lesson_id"]},
        )
        assert response.status_code == 503
        assert "ai service" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.pop(get_ai_quiz_client, None)
