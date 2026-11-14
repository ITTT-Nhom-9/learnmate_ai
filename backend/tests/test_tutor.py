import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db, get_session_factory
from app.core.security import create_access_token, get_password_hash, utcnow
from app.main import app
from app.models import (
    ChatMessage,
    ChatSession,
    ChatSessionStatus,
    Course,
    CourseStatus,
    Lesson,
    LessonContent,
    Topic,
    User,
)
from app.services.ai_tutor_client import AIServiceError, AIStreamChunk, AITutorClient, get_ai_tutor_client
from app.services.quota_guard import QuotaGuard, current_window

API = "/api/v1/tutor"


# ==============================================================================
# Fixtures
# ==============================================================================

class FakeAIClient:
    """Gia lap AI service: phat cac manh chu, hoac nem loi sau N manh."""

    def __init__(self, deltas=("Xin ", "chào ", "em!"), total_tokens=42, fail_after=None):
        self.deltas = list(deltas)
        self.total_tokens = total_tokens
        self.fail_after = fail_after
        self.payloads: list[dict] = []

    async def stream(self, payload):
        self.payloads.append(payload)
        for i, d in enumerate(self.deltas):
            if self.fail_after is not None and i >= self.fail_after:
                raise AIServiceError("LLM_TIMEOUT", "Gemini quá thời gian phản hồi")
            yield AIStreamChunk(delta=d)
        if self.fail_after is not None and self.fail_after >= len(self.deltas):
            raise AIServiceError("LLM_TIMEOUT", "Gemini quá thời gian phản hồi")
        yield AIStreamChunk(done=True, total_tokens=self.total_tokens)


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
def ai():
    return FakeAIClient()


@pytest.fixture()
def client(db_factory, ai):
    def _override_get_db():
        db = db_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_session_factory] = lambda: db_factory
    app.dependency_overrides[get_ai_tutor_client] = lambda: ai
    yield TestClient(app)
    for dep in (get_db, get_session_factory, get_ai_tutor_client):
        app.dependency_overrides.pop(dep, None)


@pytest.fixture()
def seeded(db_factory):
    with db_factory() as db:
        pw = get_password_hash("MatKhau@123")
        u1 = User(email="a@univ.edu.vn", password_hash=pw, full_name="Sinh Viên A")
        u2 = User(email="b@univ.edu.vn", password_hash=pw, full_name="Sinh Viên B")
        cs = Course(code="CS101", title="Cấu trúc dữ liệu")
        lesson = Lesson(title="Bài 1: B-Tree", order_index=1)
        lesson.topics = [Topic(name="Cân bằng cây")]
        lesson.contents = [LessonContent(content_type="MARKDOWN", body="# B-Tree là cây tìm kiếm cân bằng")]
        cs.lessons = [lesson]
        hidden = Course(code="ZZ999", title="Ẩn", status=CourseStatus.INACTIVE.value)
        hidden_lesson = Lesson(title="Bài ẩn", order_index=1)
        hidden.lessons = [hidden_lesson]
        db.add_all([u1, u2, cs, hidden])
        db.commit()
        return {"u1": u1.id, "u2": u2.id, "lesson": lesson.id, "hidden_lesson": hidden_lesson.id}


def auth(user_id: int) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


def parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.strip().split("\n\n"):
        name, data = "message", None
        for line in block.splitlines():
            if line.startswith("event:"):
                name = line[6:].strip()
            elif line.startswith("data:"):
                data = json.loads(line[5:].strip())
        events.append((name, data))
    return events


def ask(client, user_id, lesson_id, message="Em chưa hiểu B-Tree?", mode="EXPLAIN"):
    return client.post(
        f"{API}/chat",
        json={"lesson_id": lesson_id, "message": message, "mode": mode},
        headers=auth(user_id),
    )


def add_user_messages(db_factory, user_id, lesson_id, count, created_at=None):
    with db_factory() as db:
        s = ChatSession(user_id=user_id, lesson_id=lesson_id)
        db.add(s)
        db.flush()
        db.add_all([
            ChatMessage(session_id=s.id, role="USER", content=f"q{i}", created_at=created_at or utcnow())
            for i in range(count)
        ])
        db.commit()


# ==============================================================================
# POST /tutor/chat
# ==============================================================================

def test_chat_requires_access_token(client, seeded):
    res = client.post(f"{API}/chat", json={"lesson_id": seeded["lesson"], "message": "hi"})
    assert res.status_code == 401


def test_chat_streams_sse_and_saves_history(client, db_factory, seeded, ai):
    res = ask(client, seeded["u1"], seeded["lesson"])
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/event-stream")

    events = parse_sse(res.text)
    tokens = [d["token"] for e, d in events if e == "message"]
    assert tokens == ["Xin ", "chào ", "em!"]
    assert events[0][1] == {"token": "Xin ", "hint_level": 0, "is_concluded": False}

    name, done = events[-1]
    assert name == "done"
    assert done["tokens_used"] == 42
    assert done["quota_remaining"] == settings.TUTOR_DAILY_QUOTA - 1

    with db_factory() as db:
        msgs = db.scalars(select(ChatMessage).order_by(ChatMessage.id)).all()
        assert [(m.role, m.content) for m in msgs] == [
            ("USER", "Em chưa hiểu B-Tree?"),
            ("ASSISTANT", "Xin chào em!"),
        ]
        assert msgs[1].id == done["message_id"]
        assert msgs[1].tokens_used == 42

    payload = ai.payloads[0]
    assert payload["message"] == "Em chưa hiểu B-Tree?"
    assert payload["history"] == []
    assert "Bài 1: B-Tree" in payload["lesson_context"]
    assert "B-Tree là cây tìm kiếm cân bằng" in payload["lesson_context"]


def test_chat_reuses_session_and_sends_history(client, db_factory, seeded, ai):
    ask(client, seeded["u1"], seeded["lesson"], message="Câu 1")
    ask(client, seeded["u1"], seeded["lesson"], message="Câu 2")

    with db_factory() as db:
        assert db.scalar(select(func.count(ChatSession.id))) == 1
    assert ai.payloads[1]["history"] == [
        {"role": "user", "content": "Câu 1"},
        {"role": "assistant", "content": "Xin chào em!"},
    ]


def test_chat_history_window_is_limited(client, db_factory, seeded, ai, monkeypatch):
    monkeypatch.setattr(settings, "TUTOR_HISTORY_WINDOW", 3)
    for i in range(3):
        ask(client, seeded["u1"], seeded["lesson"], message=f"Câu {i}")
    assert len(ai.payloads[-1]["history"]) == 3
    assert ai.payloads[-1]["history"][-1] == {"role": "assistant", "content": "Xin chào em!"}


def test_socratic_mode_increments_hint_level_and_concludes_at_step_5(client, db_factory, seeded):
    levels = []
    for _ in range(5):
        events = parse_sse(ask(client, seeded["u1"], seeded["lesson"], mode="SOCRATIC").text)
        levels.append((events[0][1]["hint_level"], events[0][1]["is_concluded"]))
    assert levels == [(1, False), (2, False), (3, False), (4, False), (5, True)]

    with db_factory() as db:
        s = db.scalar(select(ChatSession).where(ChatSession.mode == "SOCRATIC"))
        assert s.status == ChatSessionStatus.COMPLETED.value

    # Phien da ket thuc -> luot tiep theo mo phien Socratic moi
    events = parse_sse(ask(client, seeded["u1"], seeded["lesson"], mode="SOCRATIC").text)
    assert events[0][1]["hint_level"] == 1


def test_modes_use_separate_sessions(client, db_factory, seeded):
    ask(client, seeded["u1"], seeded["lesson"], mode="EXPLAIN")
    ask(client, seeded["u1"], seeded["lesson"], mode="SOCRATIC")
    with db_factory() as db:
        assert db.scalar(select(func.count(ChatSession.id))) == 2


@pytest.mark.parametrize("lesson_key", ["missing", "hidden_lesson"])
def test_chat_unknown_or_hidden_lesson_returns_404(client, seeded, lesson_key):
    lesson_id = seeded.get(lesson_key, 9999)
    assert ask(client, seeded["u1"], lesson_id).status_code == 404


@pytest.mark.parametrize(
    "body",
    [
        {"lesson_id": 1, "message": "   "},
        {"lesson_id": 1, "message": ""},
        {"lesson_id": 1, "message": "x" * 4001},
        {"lesson_id": 1, "message": "ok", "mode": "OTHER"},
        {"message": "ok"},
    ],
)
def test_chat_invalid_body_returns_422(client, seeded, body):
    res = client.post(f"{API}/chat", json=body, headers=auth(seeded["u1"]))
    assert res.status_code == 422


def test_ai_error_before_any_token_refunds_quota(client, db_factory, seeded, ai):
    ai.fail_after = 0
    events = parse_sse(ask(client, seeded["u1"], seeded["lesson"]).text)
    assert events == [("error", {"error_code": "LLM_TIMEOUT", "detail": "Gemini quá thời gian phản hồi"})]
    with db_factory() as db:
        assert db.scalar(select(func.count(ChatMessage.id))) == 0
        assert QuotaGuard(db).remaining(seeded["u1"]) == settings.TUTOR_DAILY_QUOTA


def test_ai_error_restores_socratic_hint_level(client, db_factory, seeded, ai):
    ai.fail_after = 0
    ask(client, seeded["u1"], seeded["lesson"], mode="SOCRATIC")
    with db_factory() as db:
        assert db.scalar(select(ChatSession.hint_level)) == 0


def test_ai_error_mid_stream_keeps_partial_reply(client, db_factory, seeded, ai):
    ai.fail_after = 2
    events = parse_sse(ask(client, seeded["u1"], seeded["lesson"]).text)
    assert [e for e, _ in events] == ["message", "message", "error"]
    with db_factory() as db:
        msgs = db.scalars(select(ChatMessage).order_by(ChatMessage.id)).all()
        assert [(m.role, m.content) for m in msgs] == [("USER", "Em chưa hiểu B-Tree?"), ("ASSISTANT", "Xin chào ")]


def test_empty_ai_reply_is_error_and_refunds(client, db_factory, seeded, ai):
    ai.deltas = ["", "   "]
    events = parse_sse(ask(client, seeded["u1"], seeded["lesson"]).text)
    assert events[-1][0] == "error"
    assert events[-1][1]["error_code"] == "EMPTY_RESPONSE"
    with db_factory() as db:
        assert db.scalar(select(func.count(ChatMessage.id))) == 0


# ==============================================================================
# QuotaGuard (BR-05)
# ==============================================================================

def test_quota_blocks_51st_question_with_429(client, db_factory, seeded, ai):
    add_user_messages(db_factory, seeded["u1"], seeded["lesson"], settings.TUTOR_DAILY_QUOTA - 1)

    last = parse_sse(ask(client, seeded["u1"], seeded["lesson"]).text)[-1]
    assert last[0] == "done" and last[1]["quota_remaining"] == 0

    res = ask(client, seeded["u1"], seeded["lesson"])
    assert res.status_code == 429
    assert int(res.headers["Retry-After"]) > 0
    assert len(ai.payloads) == 1  # khong goi AI khi da het quota

    # Sinh vien khac khong bi anh huong
    assert ask(client, seeded["u2"], seeded["lesson"]).status_code == 200


def test_quota_ignores_messages_from_previous_day(client, db_factory, seeded):
    yesterday = current_window().start_utc - timedelta(seconds=1)
    add_user_messages(db_factory, seeded["u1"], seeded["lesson"], settings.TUTOR_DAILY_QUOTA, created_at=yesterday)
    assert ask(client, seeded["u1"], seeded["lesson"]).status_code == 200


def test_quota_window_uses_vietnam_midnight():
    # 2026-11-14 18:30 UTC = 2026-11-15 01:30 gio VN -> cua so bat dau 2026-11-14 17:00 UTC
    w = current_window(datetime(2026, 11, 14, 18, 30, tzinfo=timezone.utc))
    assert w.start_utc == datetime(2026, 11, 14, 17, 0)
    assert w.reset_at == datetime(2026, 11, 15, 17, 0, tzinfo=timezone.utc)

    # 2026-11-14 16:59 UTC = 23:59 gio VN ngay 14 -> cua so bat dau 2026-11-13 17:00 UTC
    w = current_window(datetime(2026, 11, 14, 16, 59, tzinfo=timezone.utc))
    assert w.start_utc == datetime(2026, 11, 13, 17, 0)


def test_quota_counts_only_user_messages(db_factory, seeded):
    with db_factory() as db:
        s = ChatSession(user_id=seeded["u1"], lesson_id=seeded["lesson"])
        db.add(s)
        db.flush()
        db.add_all([
            ChatMessage(session_id=s.id, role="USER", content="q", created_at=utcnow()),
            ChatMessage(session_id=s.id, role="ASSISTANT", content="a", created_at=utcnow()),
        ])
        db.commit()
        assert QuotaGuard(db).used(seeded["u1"]) == 1
        assert QuotaGuard(db).used(seeded["u2"]) == 0


# ==============================================================================
# GET /tutor/history/{lesson_id}
# ==============================================================================

def test_history_requires_access_token(client, seeded):
    assert client.get(f"{API}/history/{seeded['lesson']}").status_code == 401


def test_history_empty_when_no_session(client, seeded):
    res = client.get(f"{API}/history/{seeded['lesson']}", headers=auth(seeded["u1"]))
    assert res.status_code == 200
    body = res.json()
    assert body["session_id"] is None
    assert body["messages"] == []
    assert body["quota_remaining"] == settings.TUTOR_DAILY_QUOTA


def test_history_returns_latest_session_messages(client, seeded):
    ask(client, seeded["u1"], seeded["lesson"], message="Câu 1", mode="SOCRATIC")
    ask(client, seeded["u1"], seeded["lesson"], message="Câu 2", mode="SOCRATIC")

    body = client.get(f"{API}/history/{seeded['lesson']}", headers=auth(seeded["u1"])).json()
    assert body["mode"] == "SOCRATIC"
    assert body["hint_level"] == 2
    assert body["quota_remaining"] == settings.TUTOR_DAILY_QUOTA - 2
    assert [(m["role"], m["content"]) for m in body["messages"]] == [
        ("USER", "Câu 1"), ("ASSISTANT", "Xin chào em!"),
        ("USER", "Câu 2"), ("ASSISTANT", "Xin chào em!"),
    ]


def test_history_limit_returns_most_recent(client, seeded):
    for i in range(3):
        ask(client, seeded["u1"], seeded["lesson"], message=f"Câu {i}")
    body = client.get(f"{API}/history/{seeded['lesson']}?limit=2", headers=auth(seeded["u1"])).json()
    assert [m["content"] for m in body["messages"]] == ["Câu 2", "Xin chào em!"]


def test_history_is_isolated_per_user(client, seeded):
    ask(client, seeded["u1"], seeded["lesson"])
    body = client.get(f"{API}/history/{seeded['lesson']}", headers=auth(seeded["u2"])).json()
    assert body["session_id"] is None and body["messages"] == []


def test_history_unknown_lesson_returns_404(client, seeded):
    assert client.get(f"{API}/history/9999", headers=auth(seeded["u1"])).status_code == 404


# ==============================================================================
# AITutorClient: doc luong SSE tu AI service
# ==============================================================================

async def _lines(*lines):
    for line in lines:
        yield line


async def test_client_parses_sse_chunks():
    chunks = [c async for c in AITutorClient._parse_sse(_lines(
        'data: {"delta": "Xin ", "done": false}', "",
        'data: {"delta": "chào", "done": false}', "",
        'data: {"delta": "", "done": true, "total_tokens": 7}', "",
    ))]
    assert [c.delta for c in chunks] == ["Xin ", "chào", ""]
    assert chunks[-1].done and chunks[-1].total_tokens == 7


async def test_client_raises_on_error_event():
    with pytest.raises(AIServiceError) as exc:
        async for _ in AITutorClient._parse_sse(_lines(
            "event: error", 'data: {"error_code": "LLM_TIMEOUT", "detail": "timeout", "done": true}', "",
        )):
            pass
    assert exc.value.error_code == "LLM_TIMEOUT"


async def test_client_unreachable_service_raises_unavailable():
    client = AITutorClient("http://127.0.0.1:1", "key", timeout=1)
    with pytest.raises(AIServiceError) as exc:
        async for _ in client.stream({"message": "hi"}):
            pass
    assert exc.value.error_code == "AI_SERVICE_UNAVAILABLE"
