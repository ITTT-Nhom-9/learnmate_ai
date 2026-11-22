import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models import Course, User, UserStatus

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
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def admin_headers(db_factory):
    db = db_factory()
    admin = User(
        email="admin_crud@test.com",
        password_hash=get_password_hash("Secret123!"),
        full_name="Admin Test",
        role="ADMIN",
        status=UserStatus.ACTIVE.value,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    token = create_access_token(admin.id)
    db.close()
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def student_headers(db_factory):
    db = db_factory()
    student = User(
        email="student_crud@test.com",
        password_hash=get_password_hash("Secret123!"),
        full_name="Student Test",
        role="STUDENT",
        status=UserStatus.ACTIVE.value,
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    token = create_access_token(student.id)
    db.close()
    return {"Authorization": f"Bearer {token}"}


def test_student_cannot_create_course(client, student_headers):
    resp = client.post(
        API,
        json={"code": "CS999", "title": "Học máy", "description": "Mô tả", "status": "ACTIVE"},
        headers=student_headers,
    )
    assert resp.status_code == 403


def test_admin_create_update_delete_course(client, admin_headers):
    # 1. Tạo môn học mới
    res_create = client.post(
        API,
        json={"code": "CS999", "title": "Học máy nâng cao", "description": "Nhập môn AI và ML", "status": "ACTIVE"},
        headers=admin_headers,
    )
    assert res_create.status_code == 201
    data = res_create.json()
    course_id = data["id"]
    assert data["code"] == "CS999"
    assert len(data["lessons"]) == 1
    lesson_id = data["lessons"][0]["id"]
    assert len(data["lessons"][0]["topics"]) == 1
    topic_id = data["lessons"][0]["topics"][0]["id"]

    # 2. Tạo trùng mã code -> 409
    res_dup = client.post(
        API,
        json={"code": "cs999", "title": "Trùng mã"},
        headers=admin_headers,
    )
    assert res_dup.status_code == 409

    # 3. Cập nhật thông tin môn
    res_update = client.put(
        f"{API}/{course_id}",
        json={"title": "Học máy và Thị giác máy tính", "status": "ACTIVE"},
        headers=admin_headers,
    )
    assert res_update.status_code == 200
    assert res_update.json()["title"] == "Học máy và Thị giác máy tính"

    # 4. Thêm bài học mới
    res_lesson = client.post(
        f"{API}/{course_id}/lessons",
        json={"title": "Bài 2: Mạng Nơ-ron Nhân tạo", "order_index": 2},
        headers=admin_headers,
    )
    assert res_lesson.status_code == 201
    new_lesson_id = res_lesson.json()["id"]

    # 5. Thêm chủ đề mới vào bài 2
    res_topic = client.post(
        f"{API}/{course_id}/lessons/{new_lesson_id}/topics",
        json={"name": "Perceptron và Hàm kích hoạt", "description": "Cơ chế hoạt động của perceptron"},
        headers=admin_headers,
    )
    assert res_topic.status_code == 201
    new_topic_id = res_topic.json()["id"]

    # 6. Sửa chủ đề
    res_topic_update = client.put(
        f"{API}/{course_id}/topics/{new_topic_id}",
        json={"name": "Multi-layer Perceptron (MLP)", "description": "Mạng nơ-ron đa tầng"},
        headers=admin_headers,
    )
    assert res_topic_update.status_code == 200
    assert res_topic_update.json()["name"] == "Multi-layer Perceptron (MLP)"

    # 7. Soạn nội dung Markdown cho bài 2
    res_content = client.post(
        f"{API}/{course_id}/lessons/{new_lesson_id}/contents",
        json={"content_type": "MARKDOWN", "body": "## Giới thiệu MLP\n\nMạng nơ-ron đa tầng gồm các lớp..."},
        headers=admin_headers,
    )
    assert res_content.status_code == 200
    assert len(res_content.json()["contents"]) == 1
    assert "Giới thiệu MLP" in res_content.json()["contents"][0]["body"]

    # 8. Xóa chủ đề
    res_del_topic = client.delete(f"{API}/{course_id}/topics/{new_topic_id}", headers=admin_headers)
    assert res_del_topic.status_code == 200

    # 9. Xóa bài học
    res_del_lesson = client.delete(f"{API}/{course_id}/lessons/{new_lesson_id}", headers=admin_headers)
    assert res_del_lesson.status_code == 200

    # 10. Xóa môn học
    res_del_course = client.delete(f"{API}/{course_id}", headers=admin_headers)
    assert res_del_course.status_code == 200
    assert res_del_course.json()["action"] == "DELETED"
