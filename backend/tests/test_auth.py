from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import (
    create_access_token,
    decode_token,
    hash_refresh_token,
    utcnow,
    verify_password,
)
from app.main import app
from app.models import RefreshToken, User, UserStatus

API = "/api/v1/auth"
PASSWORD = "MatKhau@123"


@pytest.fixture()
def db_factory():
    """SQLite in-memory dung chung 1 connection (StaticPool) cho moi test."""
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


def register(client, email="sv@univ.edu.vn", password=PASSWORD, full_name="Trần Văn A"):
    return client.post(f"{API}/register", json={"email": email, "password": password, "full_name": full_name})


def login(client, email="sv@univ.edu.vn", password=PASSWORD):
    return client.post(f"{API}/login", json={"email": email, "password": password})


def auth_header(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}


# ==============================================================================
# /auth/register
# ==============================================================================

def test_register_success_hashes_password_with_bcrypt(client, db_factory):
    res = register(client, email="  SV@Univ.edu.vn ")
    assert res.status_code == 201
    body = res.json()
    assert body["email"] == "sv@univ.edu.vn"
    assert body["full_name"] == "Trần Văn A"
    assert body["role"] == "STUDENT"
    assert isinstance(body["user_id"], int)
    assert "created_at" in body
    assert "password" not in body and "password_hash" not in body

    with db_factory() as db:
        user = db.scalar(select(User).where(User.email == "sv@univ.edu.vn"))
        assert user.password_hash != PASSWORD
        assert user.password_hash.startswith("$2b$12$")  # BCrypt work factor 12
        assert verify_password(PASSWORD, user.password_hash)


def test_register_duplicate_email_rejected(client):
    assert register(client).status_code == 201
    res = register(client, email="SV@UNIV.EDU.VN")  # trung email khong phan biet hoa thuong
    assert res.status_code == 400
    assert "Email" in res.json()["detail"]


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "khong-phai-email", "password": PASSWORD, "full_name": "A"},
        {"email": "a@b.vn", "password": "1234567", "full_name": "A"},  # < 8 ky tu
        {"email": "a@b.vn", "password": "a" * 73, "full_name": "A"},  # > 72 byte BCrypt
        {"email": "a@b.vn", "password": PASSWORD, "full_name": "   "},
        {"email": "a@b.vn", "password": PASSWORD, "full_name": "x" * 151},
        {"email": "a@b.vn", "password": PASSWORD},
    ],
)
def test_register_validation_errors(client, payload):
    assert client.post(f"{API}/register", json=payload).status_code == 422


# ==============================================================================
# /auth/login
# ==============================================================================

def test_login_success_returns_token_pair(client, db_factory):
    register(client)
    res = login(client, email="SV@univ.edu.vn")
    assert res.status_code == 200
    body = res.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 900
    assert body["user"]["email"] == "sv@univ.edu.vn"
    assert body["user"]["role"] == "STUDENT"

    claims = decode_token(body["access_token"])
    assert claims["sub"] == str(body["user"]["id"])
    assert claims["type"] == "access"
    assert claims["exp"] - claims["iat"] == 15 * 60

    with db_factory() as db:
        stored = db.scalar(select(RefreshToken))
        # CSDL chi luu ban bam SHA-256, khong luu token goc
        assert stored.token_hash == hash_refresh_token(body["refresh_token"])
        assert stored.token_hash != body["refresh_token"]
        assert stored.revoked_at is None
        lifetime = stored.expires_at - utcnow()
        assert timedelta(days=6, hours=23) < lifetime <= timedelta(days=7)


@pytest.mark.parametrize("email,password", [("sv@univ.edu.vn", "SaiMatKhau1"), ("khongco@univ.edu.vn", PASSWORD)])
def test_login_invalid_credentials(client, email, password):
    register(client)
    res = login(client, email=email, password=password)
    assert res.status_code == 401
    assert res.json()["detail"] == "Email hoặc mật khẩu không đúng"


def test_login_locked_account_forbidden(client, db_factory):
    register(client)
    with db_factory() as db:
        db.scalar(select(User)).status = UserStatus.LOCKED.value
        db.commit()
    assert login(client).status_code == 403


# ==============================================================================
# /auth/refresh  (JWT Rotation)
# ==============================================================================

def test_refresh_rotates_token(client, db_factory):
    register(client)
    old_refresh = login(client).json()["refresh_token"]

    res = client.post(f"{API}/refresh", json={"refresh_token": old_refresh})
    assert res.status_code == 200
    body = res.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 900
    assert body["refresh_token"] != old_refresh
    assert decode_token(body["access_token"])["type"] == "access"

    with db_factory() as db:
        old = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(old_refresh)))
        new = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(body["refresh_token"])))
        assert old.revoked_at is not None
        assert new.revoked_at is None

    # Token moi tiep tuc dung duoc
    assert client.post(f"{API}/refresh", json={"refresh_token": body["refresh_token"]}).status_code == 200


def test_refresh_reuse_of_rotated_token_revokes_all_sessions(client, db_factory):
    register(client)
    old_refresh = login(client).json()["refresh_token"]
    new_refresh = client.post(f"{API}/refresh", json={"refresh_token": old_refresh}).json()["refresh_token"]

    # Ke tan cong dung lai token cu -> bi tu choi va toan bo phien bi thu hoi
    assert client.post(f"{API}/refresh", json={"refresh_token": old_refresh}).status_code == 401
    assert client.post(f"{API}/refresh", json={"refresh_token": new_refresh}).status_code == 401

    with db_factory() as db:
        assert all(t.revoked_at is not None for t in db.scalars(select(RefreshToken)))


def test_refresh_unknown_token(client):
    res = client.post(f"{API}/refresh", json={"refresh_token": "token-khong-ton-tai"})
    assert res.status_code == 401


def test_refresh_expired_token(client, db_factory):
    register(client)
    refresh_token = login(client).json()["refresh_token"]
    with db_factory() as db:
        db.scalar(select(RefreshToken)).expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    res = client.post(f"{API}/refresh", json={"refresh_token": refresh_token})
    assert res.status_code == 401
    assert "hết hạn" in res.json()["detail"]


def test_refresh_rejected_when_account_locked(client, db_factory):
    register(client)
    refresh_token = login(client).json()["refresh_token"]
    with db_factory() as db:
        db.scalar(select(User)).status = UserStatus.LOCKED.value
        db.commit()
    assert client.post(f"{API}/refresh", json={"refresh_token": refresh_token}).status_code == 401


# ==============================================================================
# /auth/logout
# ==============================================================================

def test_logout_revokes_refresh_token(client):
    register(client)
    tokens = login(client).json()

    res = client.post(
        f"{API}/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers=auth_header(tokens["access_token"]),
    )
    assert res.status_code == 200
    assert res.json() == {"revoked": True, "message": "Đăng xuất thành công"}

    # Refresh token da bi thu hoi khong the dung de lam moi
    assert client.post(f"{API}/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401


def test_logout_requires_access_token(client):
    register(client)
    tokens = login(client).json()
    assert client.post(f"{API}/logout", json={"refresh_token": tokens["refresh_token"]}).status_code == 401
    res = client.post(
        f"{API}/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers=auth_header("not.a.jwt"),
    )
    assert res.status_code == 401


def test_logout_rejects_expired_access_token(client):
    register(client)
    tokens = login(client).json()
    user_id = decode_token(tokens["access_token"])["sub"]
    expired = create_access_token(user_id, expires_delta=timedelta(seconds=-1))
    res = client.post(f"{API}/logout", json={"refresh_token": tokens["refresh_token"]}, headers=auth_header(expired))
    assert res.status_code == 401


def test_logout_cannot_revoke_other_users_token(client):
    register(client, email="a@univ.edu.vn")
    register(client, email="b@univ.edu.vn")
    tokens_a = login(client, email="a@univ.edu.vn").json()
    tokens_b = login(client, email="b@univ.edu.vn").json()

    res = client.post(
        f"{API}/logout",
        json={"refresh_token": tokens_b["refresh_token"]},
        headers=auth_header(tokens_a["access_token"]),
    )
    assert res.status_code == 401
    # Token cua B van con hieu luc
    assert client.post(f"{API}/refresh", json={"refresh_token": tokens_b["refresh_token"]}).status_code == 200
