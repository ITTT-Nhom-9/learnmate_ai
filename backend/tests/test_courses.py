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
    [("get", ""), ("get", "/1"), ("post", "/1/enroll")],
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
    codes = [c["code"] for c in body["items"]]
    assert codes == ["CS101", "IT001"]  # mon INACTIVE bi an

    cs, it = body["items"]
    assert (cs["lesson_count"], cs["topic_count"]) == (2, 3)
    assert (it["lesson_count"], it["topic_count"]) == (0, 0)
    assert cs["is_enrolled"] is False and cs["enrolled_at"] is None


def test_list_courses_reflects_enrollment_per_user(client, seeded):
    client.post(f"{API}/{seeded['cs']}/enroll", headers=auth(seeded["u1"]))

    mine = {c["code"]: c for c in client.get(API, headers=auth(seeded["u1"])).json()["items"]}
    other = {c["code"]: c for c in client.get(API, headers=auth(seeded["u2"])).json()["items"]}

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
    assert res.json() == {"total": 0, "items": []}


# ==============================================================================
# GET /courses/{id}
# ==============================================================================

def test_course_detail_returns_ordered_lessons_topics_and_contents(client, seeded):
    res = client.get(f"{API}/{seeded['cs']}", headers=auth(seeded["u1"]))
    assert res.status_code == 200
    body = res.json()
    assert body["code"] == "CS101"
    assert (body["lesson_count"], body["topic_count"]) == (2, 3)
    assert body["is_enrolled"] is False

    lessons = body["lessons"]
    assert [l["order_index"] for l in lessons] == [1, 2]
    assert [t["name"] for t in lessons[0]["topics"]] == ["Singly Linked List", "Doubly Linked List"]
    assert lessons[0]["contents"][0]["body"] == "# Linked list"
    assert [t["name"] for t in lessons[1]["topics"]] == ["BST"]
    assert lessons[1]["contents"] == []


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
