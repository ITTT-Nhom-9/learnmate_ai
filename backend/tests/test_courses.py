import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models import (
    Course,
    CourseStatus,
    Enrollment,
    Lesson,
    LessonContent,
    Topic,
    User,
    UserStatus,
)
from app.services.course_service import AlreadyEnrolledError, CourseService

API = "/api/v1/courses"


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
    """2 mon ACTIVE (CS101 co 2 bai/3 chu de, IT001 khong co bai) + 1 mon INACTIVE + 2 sinh vien."""
    with db_factory() as db:
        pw = get_password_hash("MatKhau@123")
        u1 = User(email="a@univ.edu.vn", password_hash=pw, full_name="Sinh Viên A")
        u2 = User(email="b@univ.edu.vn", password_hash=pw, full_name="Sinh Viên B")

        cs = Course(code="CS101", title="Cấu trúc dữ liệu", description="DSA")
        l2 = Lesson(title="Bài 2: Cây", order_index=2)
        l1 = Lesson(title="Bài 1: Danh sách liên kết", order_index=1)
        l1.topics = [Topic(name="Singly Linked List"), Topic(name="Doubly Linked List")]
        l1.contents = [LessonContent(content_type="MARKDOWN", body="# Linked list")]
        l2.topics = [Topic(name="BST")]
        cs.lessons = [l2, l1]

        it = Course(code="IT001", title="Nhập môn lập trình")
        hidden = Course(code="ZZ999", title="Môn đã ẩn", status=CourseStatus.INACTIVE.value)

        db.add_all([u1, u2, cs, it, hidden])
        db.commit()
        return {
            "u1": u1.id, "u2": u2.id,
            "cs": cs.id, "it": it.id, "hidden": hidden.id,
        }


def auth(user_id: int) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


# ==============================================================================
# Xac thuc
# ==============================================================================

@pytest.mark.parametrize(
    "method,path",
    [("get", ""), ("get", "/1"), ("get", "/1/lessons/1"), ("post", "/1/enroll")],
)
def test_endpoints_require_access_token(client, method, path):
    res = getattr(client, method)(f"{API}{path}")
    assert res.status_code == 401


def test_locked_user_is_forbidden(client, db_factory, seeded):
    with db_factory() as db:
        db.get(User, seeded["u1"]).status = UserStatus.LOCKED.value
        db.commit()
    assert client.get(API, headers=auth(seeded["u1"])).status_code == 403


# ==============================================================================
# GET /courses
# ==============================================================================

def test_list_courses_returns_active_courses_with_counts(client, seeded):
    res = client.get(API, headers=auth(seeded["u1"]))
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 2
    codes = [c["code"] for c in body["courses"]]
    assert codes == ["CS101", "IT001"]  # mon INACTIVE bi an

    cs, it = body["courses"]
    assert (cs["total_lessons"], cs["topic_count"]) == (2, 3)
    assert (it["total_lessons"], it["topic_count"]) == (0, 0)
    assert cs["is_enrolled"] is False and cs["enrolled_at"] is None
    assert cs["progress_pct"] == 0.0
    assert (body["page"], body["limit"]) == (1, 10)


def test_list_courses_reflects_enrollment_per_user(client, seeded):
    client.post(f"{API}/{seeded['cs']}/enroll", headers=auth(seeded["u1"]))

    mine = {c["code"]: c for c in client.get(API, headers=auth(seeded["u1"])).json()["courses"]}
    other = {c["code"]: c for c in client.get(API, headers=auth(seeded["u2"])).json()["courses"]}

    assert mine["CS101"]["is_enrolled"] is True
    assert mine["CS101"]["enrolled_at"] is not None
    assert mine["IT001"]["is_enrolled"] is False
    assert other["CS101"]["is_enrolled"] is False


def test_list_courses_empty(client, db_factory):
    with db_factory() as db:
        u = User(email="x@univ.edu.vn", password_hash="x", full_name="X")
        db.add(u)
        db.commit()
        uid = u.id
    res = client.get(API, headers=auth(uid))
    assert res.status_code == 200
    assert res.json() == {"courses": [], "total": 0, "page": 1, "limit": 10}


# ==============================================================================
# GET /courses/{id}
# ==============================================================================

def test_course_detail_returns_ordered_lessons_topics_and_contents(client, seeded):
    res = client.get(f"{API}/{seeded['cs']}", headers=auth(seeded["u1"]))
    assert res.status_code == 200
    body = res.json()
    assert body["code"] == "CS101"
    assert (body["total_lessons"], body["topic_count"]) == (2, 3)
    assert body["is_enrolled"] is False

    lessons = body["lessons"]
    assert [l["order_index"] for l in lessons] == [1, 2]
    assert [t["name"] for t in lessons[0]["topics"]] == ["Singly Linked List", "Doubly Linked List"]
    assert lessons[0]["contents"][0]["body"] == "# Linked list"
    assert [t["name"] for t in lessons[1]["topics"]] == ["BST"]
    assert lessons[1]["contents"] == []
    assert all(t["mastery_score"] == 0.0 for l in lessons for t in l["topics"])


def test_course_detail_shows_enrolled_flag(client, seeded):
    client.post(f"{API}/{seeded['cs']}/enroll", headers=auth(seeded["u1"]))
    body = client.get(f"{API}/{seeded['cs']}", headers=auth(seeded["u1"])).json()
    assert body["is_enrolled"] is True


@pytest.mark.parametrize("key", ["hidden", None])
def test_course_detail_not_found_or_inactive(client, seeded, key):
    course_id = seeded[key] if key else 99999
    res = client.get(f"{API}/{course_id}", headers=auth(seeded["u1"]))
    assert res.status_code == 404
    assert res.json()["detail"] == "Môn học không tồn tại"


def test_course_detail_rejects_invalid_id(client, seeded):
    assert client.get(f"{API}/0", headers=auth(seeded["u1"])).status_code == 422
    assert client.get(f"{API}/abc", headers=auth(seeded["u1"])).status_code == 422


# ==============================================================================
# POST /courses/{id}/enroll
# ==============================================================================

def test_enroll_success(client, db_factory, seeded):
    res = client.post(f"{API}/{seeded['cs']}/enroll", headers=auth(seeded["u1"]))
    assert res.status_code == 201
    body = res.json()
    assert body["user_id"] == seeded["u1"]
    assert body["course_id"] == seeded["cs"]
    assert body["enrollment_id"] > 0
    assert body["enrolled_at"]
    assert body["status"] == "ACTIVE"

    with db_factory() as db:
        assert db.scalar(select(func.count(Enrollment.id))) == 1


def test_enroll_twice_returns_409_and_keeps_single_row(client, db_factory, seeded):
    headers = auth(seeded["u1"])
    assert client.post(f"{API}/{seeded['cs']}/enroll", headers=headers).status_code == 201
    res = client.post(f"{API}/{seeded['cs']}/enroll", headers=headers)
    assert res.status_code == 409
    assert res.json()["detail"] == "Bạn đã ghi danh môn học này"

    with db_factory() as db:
        assert db.scalar(
            select(func.count(Enrollment.id)).where(
                Enrollment.user_id == seeded["u1"], Enrollment.course_id == seeded["cs"]
            )
        ) == 1


def test_different_users_can_enroll_same_course(client, seeded):
    assert client.post(f"{API}/{seeded['cs']}/enroll", headers=auth(seeded["u1"])).status_code == 201
    assert client.post(f"{API}/{seeded['cs']}/enroll", headers=auth(seeded["u2"])).status_code == 201


@pytest.mark.parametrize("key", ["hidden", None])
def test_enroll_missing_or_inactive_course_returns_404(client, seeded, key):
    course_id = seeded[key] if key else 99999
    res = client.post(f"{API}/{course_id}/enroll", headers=auth(seeded["u1"]))
    assert res.status_code == 404


def test_enroll_race_condition_caught_by_unique_constraint(db_factory, seeded, monkeypatch):
    """Mo phong 2 request dong thoi: ca 2 deu vuot qua buoc kiem tra som,
    ban ghi thu 2 phai bi UNIQUE(user_id, course_id) chan va tra AlreadyEnrolledError."""
    with db_factory() as db:
        db.add(Enrollment(user_id=seeded["u1"], course_id=seeded["cs"]))
        db.commit()

    with db_factory() as db:
        service = CourseService(db)
        monkeypatch.setattr(service, "_get_enrollment", lambda *_: None)
        user = db.get(User, seeded["u1"])
        with pytest.raises(AlreadyEnrolledError):
            service.enroll(seeded["cs"], user)
        # Session van dung duoc sau rollback
        assert db.scalar(select(func.count(Enrollment.id))) == 1


def test_unique_constraint_exists_at_db_level(db_factory, seeded):
    with db_factory() as db:
        db.add_all([
            Enrollment(user_id=seeded["u1"], course_id=seeded["it"]),
            Enrollment(user_id=seeded["u1"], course_id=seeded["it"]),
        ])
        with pytest.raises(IntegrityError):
            db.commit()


# ==============================================================================
# Phan trang GET /courses?page=&limit=
# ==============================================================================

def test_list_courses_pagination(client, seeded):
    headers = auth(seeded["u1"])
    p1 = client.get(API, params={"page": 1, "limit": 1}, headers=headers).json()
    p2 = client.get(API, params={"page": 2, "limit": 1}, headers=headers).json()
    p3 = client.get(API, params={"page": 3, "limit": 1}, headers=headers).json()

    assert [c["code"] for c in p1["courses"]] == ["CS101"]
    assert [c["code"] for c in p2["courses"]] == ["IT001"]
    assert p3["courses"] == []
    assert p1["total"] == p2["total"] == p3["total"] == 2  # total la tong so mon, khong phai so mon cua trang
    assert (p2["page"], p2["limit"]) == (2, 1)


@pytest.mark.parametrize("params", [{"page": 0}, {"limit": 0}, {"limit": 101}, {"page": "x"}])
def test_list_courses_rejects_invalid_pagination(client, seeded, params):
    assert client.get(API, params=params, headers=auth(seeded["u1"])).status_code == 422


# ==============================================================================
# GET /courses/{id}/lessons/{lesson_id}
# ==============================================================================

def _lesson_id(db_factory, course_id: int, order_index: int) -> int:
    with db_factory() as db:
        return db.scalar(
            select(Lesson.id).where(Lesson.course_id == course_id, Lesson.order_index == order_index)
        )


def test_lesson_detail_returns_topics_and_contents(client, db_factory, seeded):
    lesson_id = _lesson_id(db_factory, seeded["cs"], 1)
    res = client.get(f"{API}/{seeded['cs']}/lessons/{lesson_id}", headers=auth(seeded["u1"]))
    assert res.status_code == 200
    body = res.json()
    assert body["id"] == lesson_id
    assert body["course_id"] == seeded["cs"]
    assert body["title"] == "Bài 1: Danh sách liên kết"
    assert [t["name"] for t in body["topics"]] == ["Singly Linked List", "Doubly Linked List"]
    assert body["topics"][0]["mastery_score"] == 0.0
    assert body["contents"] == [{"id": body["contents"][0]["id"], "content_type": "MARKDOWN", "body": "# Linked list"}]


def test_lesson_detail_404_when_lesson_belongs_to_other_course(client, db_factory, seeded):
    lesson_id = _lesson_id(db_factory, seeded["cs"], 1)
    res = client.get(f"{API}/{seeded['it']}/lessons/{lesson_id}", headers=auth(seeded["u1"]))
    assert res.status_code == 404
    assert res.json()["detail"] == "Bài học không tồn tại"
    assert client.get(f"{API}/{seeded['cs']}/lessons/99999", headers=auth(seeded["u1"])).status_code == 404


def test_lesson_detail_404_when_course_inactive(client, db_factory, seeded):
    with db_factory() as db:
        lesson = Lesson(course_id=seeded["hidden"], title="Bài ẩn", order_index=1)
        db.add(lesson)
        db.commit()
        lesson_id = lesson.id
    res = client.get(f"{API}/{seeded['hidden']}/lessons/{lesson_id}", headers=auth(seeded["u1"]))
    assert res.status_code == 404


# ==============================================================================
# CORS: khong tra "*" khi allow_credentials=True (ke ca response 401)
# ==============================================================================

def test_cors_echoes_allowed_origin_on_401(client):
    origin = "http://localhost:5173"
    res = client.get(API, headers={"Origin": origin})
    assert res.status_code == 401
    assert res.headers["access-control-allow-origin"] == origin
    assert res.headers["access-control-allow-credentials"] == "true"


def test_cors_preflight_allows_frontend_origin(client):
    res = client.options(
        API,
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    assert res.status_code == 200
    assert res.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


def test_cors_rejects_unknown_origin(client):
    res = client.get(API, headers={"Origin": "http://evil.example.com"})
    assert "access-control-allow-origin" not in res.headers
