"""Kiểm thử API Thống kê tiến độ học tập & Điểm Radar (TK-21 / Phân hệ 6, UC-07).

- GET /api/v1/progress/summary: % hoàn thành, thẻ chỉ số, cảnh báo đỏ (BR-08), lịch sử làm bài.
- GET /api/v1/progress/radar:   Điểm năng lực tối đa 6 trục theo chủ đề.
"""
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models import Course, CourseStatus, Enrollment, Lesson, Topic, User
from app.models.mastery import (
    MasteryStatus,
    Recommendation,
    RecommendationAction,
    RecommendationStatus,
    TopicMastery,
)
from app.models.quiz import Quiz, QuizAttempt, QuizAttemptStatus
from app.services.mastery_service import MasteryService
from app.services.progress_service import classify_percent

API = "/api/v1/progress"


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


def auth(user_id: int) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


TOPIC_NAMES = ["T1", "T2", "T3", "T4", "T5", "T6", "T7"]


@pytest.fixture()
def seeded(db_factory):
    """Môn DB101 (2 bài, 7 chủ đề) đã ghi danh bởi u1; u2 chưa ghi danh; 1 môn INACTIVE."""
    with db_factory() as db:
        pw = get_password_hash("MatKhau@123")
        u1 = User(email="p1@univ.edu.vn", password_hash=pw, full_name="SV Một")
        u2 = User(email="p2@univ.edu.vn", password_hash=pw, full_name="SV Hai")
        course = Course(code="DB101", title="Cơ sở dữ liệu")
        # Bài 2 thêm trước để kiểm tra sắp theo order_index chứ không theo id
        l2 = Lesson(title="Bài 2", order_index=2)
        l1 = Lesson(title="Bài 1", order_index=1)
        l1.topics = [Topic(name=n) for n in TOPIC_NAMES[:4]]
        l2.topics = [Topic(name=n) for n in TOPIC_NAMES[4:]]
        course.lessons = [l2, l1]
        empty = Course(code="EM000", title="Môn chưa có bài")
        hidden = Course(code="ZZ999", title="Ẩn", status=CourseStatus.INACTIVE.value)
        db.add_all([u1, u2, course, empty, hidden])
        db.flush()
        db.add_all([
            Enrollment(user_id=u1.id, course_id=course.id),
            Enrollment(user_id=u1.id, course_id=empty.id),
            Enrollment(user_id=u1.id, course_id=hidden.id),
        ])
        db.commit()
        topics = {t.name: t.id for t in db.query(Topic).all()}
        return {
            "u1": u1.id, "u2": u2.id,
            "course": course.id, "empty": empty.id, "hidden": hidden.id,
            "topics": topics,
        }


def _attempt(db, user_id: int, topic_id: int, score: str, duration: int = 60) -> QuizAttempt:
    quiz = Quiz(topic_id=topic_id, title=f"Quiz {topic_id}", difficulty="MEDIUM", total_questions=10)
    db.add(quiz)
    db.flush()
    attempt = QuizAttempt(
        quiz_id=quiz.id, user_id=user_id, score=Decimal(score),
        duration_sec=duration, status=QuizAttemptStatus.SUBMITTED.value,
    )
    db.add(attempt)
    db.flush()
    return attempt


def _set_mastery(db, user_id: int, topic_id: int, score: float, practiced_at: datetime):
    db.add(TopicMastery(
        user_id=user_id, topic_id=topic_id, mastery_score=Decimal(str(score)),
        status=classify_percent(score).value, last_practiced_at=practiced_at,
    ))


@pytest.fixture()
def practiced(db_factory, seeded):
    """u1 đã luyện: T1=85 (MASTER), T2=65 (FAIR), T3=40 (WEAK), T5=20 (WEAK), T7=40 (WEAK, cũ hơn)."""
    t = seeded["topics"]
    u = seeded["u1"]
    base = datetime(2026, 11, 1, 8, 0, 0)
    with db_factory() as db:
        _set_mastery(db, u, t["T1"], 85.0, base + timedelta(days=1))
        _set_mastery(db, u, t["T2"], 65.0, base + timedelta(days=2))
        _set_mastery(db, u, t["T3"], 40.0, base + timedelta(days=5))
        _set_mastery(db, u, t["T5"], 20.0, base + timedelta(days=4))
        _set_mastery(db, u, t["T7"], 40.0, base + timedelta(days=3))

        _attempt(db, u, t["T1"], "8.50", 100)
        _attempt(db, u, t["T3"], "3.00", 50)
        _attempt(db, u, t["T3"], "5.00", 70)   # lượt gần nhất của T3
        _attempt(db, u, t["T5"], "2.00", 30)
        _attempt(db, u, t["T7"], "4.00", 40)
        # Lượt chưa nộp không được tính
        db.add(QuizAttempt(
            quiz_id=_attempt(db, u, t["T2"], "6.50", 90).quiz_id, user_id=u,
            score=Decimal("0"), duration_sec=999, status=QuizAttemptStatus.IN_PROGRESS.value,
        ))
        # Lượt của sinh viên khác không được tính
        _attempt(db, seeded["u2"], t["T1"], "1.00", 500)

        db.add(Recommendation(
            user_id=u, topic_id=t["T5"], action_type=RecommendationAction.SOCRATIC_CHAT.value,
            priority=1, status=RecommendationStatus.PENDING.value,
        ))
        db.add(Recommendation(
            user_id=u, topic_id=t["T3"], action_type=RecommendationAction.RETAKE_QUIZ.value,
            priority=1, status=RecommendationStatus.COMPLETED.value,
        ))
        db.commit()
    return seeded


# ==============================================================================
# Xác thực & quyền truy cập
# ==============================================================================

@pytest.mark.parametrize("path", ["/summary?course_id=1", "/radar?course_id=1"])
def test_endpoints_require_access_token(client, path):
    assert client.get(f"{API}{path}").status_code == 401


@pytest.mark.parametrize("path", ["/summary", "/radar"])
def test_course_id_is_required(client, seeded, path):
    assert client.get(f"{API}{path}", headers=auth(seeded["u1"])).status_code == 422


@pytest.mark.parametrize("path", ["/summary", "/radar"])
def test_unknown_or_inactive_course_returns_404(client, seeded, path):
    for cid in (9999, seeded["hidden"]):
        res = client.get(f"{API}{path}?course_id={cid}", headers=auth(seeded["u1"]))
        assert res.status_code == 404
        assert res.json()["detail"] == "Môn học không tồn tại"


@pytest.mark.parametrize("path", ["/summary", "/radar"])
def test_not_enrolled_returns_403(client, seeded, path):
    res = client.get(f"{API}{path}?course_id={seeded['course']}", headers=auth(seeded["u2"]))
    assert res.status_code == 403
    assert res.json()["detail"] == "Bạn chưa ghi danh môn học này"


# ==============================================================================
# GET /progress/summary
# ==============================================================================

def test_summary_without_any_practice(client, seeded):
    res = client.get(f"{API}/summary?course_id={seeded['course']}", headers=auth(seeded["u1"]))
    assert res.status_code == 200
    body = res.json()
    assert body["course_code"] == "DB101"
    assert body["overall_progress_pct"] == 0.0
    assert body["stats"] == {
        "total_topics": 7, "mastered_topics": 0, "fair_topics": 0, "weak_topics": 0,
        "not_started_topics": 7, "total_attempts": 0, "average_quiz_score": 0.0,
        "total_study_time_sec": 0, "last_practiced_at": None,
    }
    assert body["weak_topics"] == []
    assert body["recent_attempts"] == []


def test_summary_course_without_topics(client, seeded):
    res = client.get(f"{API}/summary?course_id={seeded['empty']}", headers=auth(seeded["u1"]))
    assert res.status_code == 200
    assert res.json()["overall_progress_pct"] == 0.0
    assert res.json()["stats"]["total_topics"] == 0


def test_summary_progress_and_stats(client, db_factory, practiced):
    res = client.get(f"{API}/summary?course_id={practiced['course']}", headers=auth(practiced["u1"]))
    assert res.status_code == 200
    body = res.json()

    # (85 + 65 + 40 + 20 + 40) / 7 chủ đề = 35.71
    assert body["overall_progress_pct"] == 35.71
    with db_factory() as db:
        expected = MasteryService(db).calculate_course_progress(practiced["u1"], practiced["course"])
    assert body["overall_progress_pct"] == expected

    stats = body["stats"]
    assert (stats["mastered_topics"], stats["fair_topics"], stats["weak_topics"]) == (1, 1, 3)
    assert stats["not_started_topics"] == 2
    # 6 lượt SUBMITTED của u1: 8.5 + 3 + 5 + 2 + 4 + 6.5 = 29 -> 4.83
    assert stats["total_attempts"] == 6
    assert stats["average_quiz_score"] == 4.83
    assert stats["total_study_time_sec"] == 100 + 50 + 70 + 30 + 40 + 90
    assert stats["last_practiced_at"].startswith("2026-11-06")


def test_summary_weak_topics_alert_red(client, practiced):
    t = practiced["topics"]
    body = client.get(
        f"{API}/summary?course_id={practiced['course']}", headers=auth(practiced["u1"])
    ).json()
    weak = body["weak_topics"]

    # Yếu nhất trước; T3 và T7 cùng 40 -> T3 luyện gần hơn đứng trước. T4/T6 chưa học không báo đỏ.
    assert [w["topic_id"] for w in weak] == [t["T5"], t["T3"], t["T7"]]
    assert all(w["alert_level"] == "RED" and w["status"] == "WEAK" for w in weak)

    t5, t3, _ = weak
    assert t5["mastery_score"] == 20.0
    assert t5["lesson_title"] == "Bài 2"
    assert t5["recommended_action"] == "SOCRATIC_CHAT"   # lấy từ khuyến nghị PENDING
    assert t3["recommended_action"] == "REVIEW_THEORY"   # khuyến nghị COMPLETED bị bỏ qua
    assert t3["attempt_count"] == 2
    assert t3["last_quiz_score"] == 5.0


def test_summary_recent_attempts(client, practiced):
    body = client.get(
        f"{API}/summary?course_id={practiced['course']}", headers=auth(practiced["u1"])
    ).json()
    recent = body["recent_attempts"]
    assert len(recent) == 6
    ids = [r["attempt_id"] for r in recent]
    assert ids == sorted(ids, reverse=True)
    assert recent[0]["topic_name"] == "T2" and recent[0]["score"] == 6.5
    assert {"quiz_title", "difficulty", "duration_sec"} <= recent[0].keys()


def test_summary_reflects_real_quiz_flow(client, db_factory, seeded):
    """Cập nhật Mastery thật qua MasteryService (EMA) rồi đọc lại qua API."""
    t1 = seeded["topics"]["T1"]
    with db_factory() as db:
        _attempt(db, seeded["u1"], t1, "5.00")
        db.commit()
        MasteryService(db).update_mastery_after_quiz(seeded["u1"], t1, quiz_score=5.0)

    body = client.get(
        f"{API}/summary?course_id={seeded['course']}", headers=auth(seeded["u1"])
    ).json()
    # EMA: 0 * 0.7 + 50 * 0.3 = 15% -> WEAK, kèm khuyến nghị REVIEW_THEORY do BR-08 tạo
    assert [w["topic_id"] for w in body["weak_topics"]] == [t1]
    assert body["weak_topics"][0]["mastery_score"] == 15.0
    assert body["weak_topics"][0]["recommended_action"] == "REVIEW_THEORY"
    assert body["overall_progress_pct"] == round(15.0 / 7, 2)


# ==============================================================================
# GET /progress/radar
# ==============================================================================

def test_radar_defaults_to_six_axes_and_prioritizes_practiced(client, practiced):
    t = practiced["topics"]
    res = client.get(f"{API}/radar?course_id={practiced['course']}", headers=auth(practiced["u1"]))
    assert res.status_code == 200
    body = res.json()

    assert body["max_axes"] == 6
    assert body["total_topics"] == 7
    assert body["truncated"] is True
    # 5 chủ đề đã luyện + 1 chủ đề chưa học đầu tiên theo giáo trình (T4); T6 bị loại.
    # Trục giữ thứ tự giáo trình.
    assert [a["topic_name"] for a in body["axes"]] == ["T1", "T2", "T3", "T4", "T5", "T7"]
    assert body["labels"] == ["T1", "T2", "T3", "T4", "T5", "T7"]
    assert body["scores"] == [85.0, 65.0, 40.0, 0.0, 20.0, 40.0]

    by_name = {a["topic_name"]: a for a in body["axes"]}
    assert (by_name["T1"]["status"], by_name["T1"]["label_vi"]) == ("MASTER", "Giỏi")
    assert (by_name["T2"]["status"], by_name["T2"]["label_vi"]) == ("FAIR", "Khá")
    assert (by_name["T3"]["status"], by_name["T3"]["label_vi"]) == ("WEAK", "Yếu")
    assert by_name["T4"] == {
        "topic_id": t["T4"], "topic_name": "T4", "lesson_id": by_name["T4"]["lesson_id"],
        "mastery_score": 0.0, "status": "NOT_STARTED", "label_vi": "Chưa học",
        "is_practiced": False,
    }


def test_radar_keeps_most_recent_practiced_when_too_many(client, practiced):
    res = client.get(
        f"{API}/radar?course_id={practiced['course']}&max_axes=3", headers=auth(practiced["u1"])
    )
    # 3 chủ đề luyện gần nhất: T3 (ngày 6), T5 (ngày 5), T7 (ngày 4)
    assert res.json()["labels"] == ["T3", "T5", "T7"]


def test_radar_returns_all_topics_when_within_limit(client, practiced):
    body = client.get(
        f"{API}/radar?course_id={practiced['course']}&max_axes=12", headers=auth(practiced["u1"])
    ).json()
    assert body["truncated"] is False
    assert body["labels"] == TOPIC_NAMES


@pytest.mark.parametrize("bad", [2, 13])
def test_radar_rejects_invalid_axes(client, seeded, bad):
    res = client.get(
        f"{API}/radar?course_id={seeded['course']}&max_axes={bad}", headers=auth(seeded["u1"])
    )
    assert res.status_code == 422


def test_radar_classifies_low_scores_on_percent_scale(client, db_factory, seeded):
    """Mastery 0.9% phải là WEAK (không bị hiểu nhầm là thang tỷ lệ 0-1)."""
    with db_factory() as db:
        _set_mastery(db, seeded["u1"], seeded["topics"]["T1"], 0.9, datetime(2026, 11, 1))
        db.commit()
    body = client.get(
        f"{API}/radar?course_id={seeded['course']}", headers=auth(seeded["u1"])
    ).json()
    assert body["axes"][0]["status"] == MasteryStatus.WEAK.value
