"""Bộ kiểm thử API Nộp bài & Chấm điểm trắc nghiệm (Phân hệ 5 / BR-08).

Kiểm tra:
1. Chấm đúng/sai từng câu, điểm thang 10, lưu quiz_attempts và attempt_answers.
2. Câu bỏ trống / không gửi lên được tính sai và vẫn được lưu lịch sử.
3. Validation: câu không thuộc đề, phương án không thuộc câu, nộp trùng câu, đề không tồn tại.
4. Bắt buộc đăng nhập (401).
"""
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models import Course, CourseStatus, Lesson, Topic, User
from app.models.quiz import AttemptAnswer, Question, QuestionOption, Quiz, QuizAttempt
from app.services.quiz_submission_service import calculate_score

SUBMIT_URL = "/api/v1/quiz/submit"


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


@pytest.fixture()
def seeded(db_factory):
    """Đề 3 câu, mỗi câu 4 phương án, đáp án đúng lần lượt là B, C, A."""
    correct_labels = ["B", "C", "A"]
    with db_factory() as db:
        user = User(
            email="student@learnmate.local",
            password_hash=get_password_hash("password123"),
            full_name="Sinh Viên Test",
            role="STUDENT",
            status="ACTIVE",
        )
        course = Course(code="CS101", title="CTDL & GT", status=CourseStatus.ACTIVE.value)
        db.add_all([user, course])
        db.flush()
        lesson = Lesson(course_id=course.id, title="Bài 1", order_index=1)
        db.add(lesson)
        db.flush()
        topic = Topic(lesson_id=lesson.id, name="BST", description="BST")
        db.add(topic)
        db.flush()
        quiz = Quiz(topic_id=topic.id, title="Quiz BST", difficulty="MEDIUM", total_questions=3)
        db.add(quiz)
        db.flush()

        questions = []
        for i, correct in enumerate(correct_labels):
            q = Question(quiz_id=quiz.id, content=f"Câu {i + 1}", explanation=f"Giải thích {i + 1}")
            db.add(q)
            db.flush()
            opts = {}
            for label in "ABCD":
                o = QuestionOption(
                    question_id=q.id, opt_label=label, content=f"PA {label}", is_correct=(label == correct)
                )
                db.add(o)
                db.flush()
                opts[label] = o.id
            questions.append({"id": q.id, "options": opts, "correct": correct})

        db.commit()
        return {"user_id": user.id, "quiz_id": quiz.id, "questions": questions}


def auth_header(user_id: int) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


def test_calculate_score():
    assert calculate_score(0, 3) == Decimal("0.00")
    assert calculate_score(1, 3) == Decimal("3.33")
    assert calculate_score(2, 3) == Decimal("6.67")
    assert calculate_score(3, 3) == Decimal("10.00")
    assert calculate_score(0, 0) == Decimal("0.00")


def test_submit_all_correct(client, db_factory, seeded):
    qs = seeded["questions"]
    resp = client.post(
        SUBMIT_URL,
        headers=auth_header(seeded["user_id"]),
        json={
            "quiz_id": seeded["quiz_id"],
            "duration_sec": 120,
            "answers": [{"question_id": q["id"], "selected_option_id": q["options"][q["correct"]]} for q in qs],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["score"] == 10.0
    assert data["correct_count"] == 3
    assert data["wrong_count"] == 0
    assert all(a["is_correct"] for a in data["answers"])


def test_submit_mixed_grades_and_persists_history(client, db_factory, seeded):
    q1, q2, q3 = seeded["questions"]
    resp = client.post(
        SUBMIT_URL,
        headers=auth_header(seeded["user_id"]),
        json={
            "quiz_id": seeded["quiz_id"],
            "duration_sec": 95,
            "answers": [
                {"question_id": q1["id"], "selected_option_id": q1["options"]["B"]},  # đúng
                {"question_id": q2["id"], "selected_option_id": q2["options"]["A"]},  # sai
                # q3 không gửi -> bỏ trống
            ],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["score"] == 3.33
    assert data["total_questions"] == 3
    assert data["correct_count"] == 1
    assert data["wrong_count"] == 2
    assert data["unanswered_count"] == 1
    assert data["status"] == "SUBMITTED"

    by_q = {a["question_id"]: a for a in data["answers"]}
    assert by_q[q1["id"]]["is_correct"] is True
    assert by_q[q2["id"]]["is_correct"] is False
    assert by_q[q2["id"]]["selected_label"] == "A"
    assert by_q[q2["id"]]["correct_label"] == "C"
    assert by_q[q2["id"]]["explanation"] == "Giải thích 2"
    assert by_q[q3["id"]]["selected_option_id"] is None
    assert by_q[q3["id"]]["is_correct"] is False

    with db_factory() as db:
        attempt = db.get(QuizAttempt, data["attempt_id"])
        assert attempt.user_id == seeded["user_id"]
        assert attempt.score == Decimal("3.33")
        assert attempt.duration_sec == 95
        rows = db.scalars(select(AttemptAnswer).where(AttemptAnswer.attempt_id == attempt.id)).all()
        assert len(rows) == 3
        saved = {r.question_id: r for r in rows}
        assert saved[q1["id"]].is_correct is True
        assert saved[q2["id"]].is_correct is False
        assert saved[q2["id"]].selected_option_id == q2["options"]["A"]
        assert saved[q3["id"]].selected_option_id is None
        assert saved[q3["id"]].is_correct is False


def test_submit_empty_answers_scores_zero(client, seeded):
    resp = client.post(
        SUBMIT_URL,
        headers=auth_header(seeded["user_id"]),
        json={"quiz_id": seeded["quiz_id"], "duration_sec": 10, "answers": []},
    )
    assert resp.status_code == 201
    assert resp.json()["score"] == 0.0
    assert resp.json()["unanswered_count"] == 3


def test_submit_option_not_belonging_to_question(client, db_factory, seeded):
    q1, q2, _ = seeded["questions"]
    resp = client.post(
        SUBMIT_URL,
        headers=auth_header(seeded["user_id"]),
        json={
            "quiz_id": seeded["quiz_id"],
            "duration_sec": 10,
            "answers": [{"question_id": q1["id"], "selected_option_id": q2["options"]["C"]}],
        },
    )
    assert resp.status_code == 400
    with db_factory() as db:
        assert db.scalars(select(QuizAttempt)).all() == []


def test_submit_question_not_in_quiz(client, seeded):
    resp = client.post(
        SUBMIT_URL,
        headers=auth_header(seeded["user_id"]),
        json={"quiz_id": seeded["quiz_id"], "duration_sec": 10, "answers": [{"question_id": 99999}]},
    )
    assert resp.status_code == 400


def test_submit_duplicate_question(client, seeded):
    q1 = seeded["questions"][0]
    ans = {"question_id": q1["id"], "selected_option_id": q1["options"]["B"]}
    resp = client.post(
        SUBMIT_URL,
        headers=auth_header(seeded["user_id"]),
        json={"quiz_id": seeded["quiz_id"], "duration_sec": 10, "answers": [ans, ans]},
    )
    assert resp.status_code == 400


def test_submit_quiz_not_found(client, seeded):
    resp = client.post(
        SUBMIT_URL,
        headers=auth_header(seeded["user_id"]),
        json={"quiz_id": 99999, "duration_sec": 10, "answers": []},
    )
    assert resp.status_code == 404


def test_submit_negative_duration_rejected(client, seeded):
    resp = client.post(
        SUBMIT_URL,
        headers=auth_header(seeded["user_id"]),
        json={"quiz_id": seeded["quiz_id"], "duration_sec": -1, "answers": []},
    )
    assert resp.status_code == 422


def test_submit_unauthorized(client, seeded):
    resp = client.post(SUBMIT_URL, json={"quiz_id": seeded["quiz_id"], "duration_sec": 10, "answers": []})
    assert resp.status_code == 401
