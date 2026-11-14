"""QuotaGuard (BR-05): gioi han so cau hoi AI Tutor cua moi sinh vien trong 1 ngay.

- Moi tin nhan role=USER trong chat_messages tinh la 1 luot hoi.
- "Ngay" tinh theo gio Viet Nam (UTC+7, khong co DST), reset luc 00:00.
- Cot created_at luu UTC dang naive nen moc thoi gian duoc quy doi ve UTC naive truoc khi so sanh.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.chat import ChatMessage, ChatRole, ChatSession

VN_TZ = timezone(timedelta(hours=7))


class QuotaExceededError(Exception):
    def __init__(self, limit: int, reset_at: datetime):
        super().__init__(f"Đã dùng hết {limit} lượt hỏi AI Tutor hôm nay")
        self.limit = limit
        self.reset_at = reset_at  # aware UTC

    @property
    def message(self) -> str:
        return str(self)

    def retry_after_seconds(self, now: datetime | None = None) -> int:
        now = now or datetime.now(timezone.utc)
        return max(1, int((self.reset_at - now).total_seconds()))


@dataclass(frozen=True)
class QuotaWindow:
    start_utc: datetime  # naive UTC - dung de so sanh voi chat_messages.created_at
    reset_at: datetime  # aware UTC - thoi diem quota duoc lam moi


def current_window(now: datetime | None = None) -> QuotaWindow:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    local_midnight = now.astimezone(VN_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    start = local_midnight.astimezone(timezone.utc)
    return QuotaWindow(
        start_utc=start.replace(tzinfo=None),
        reset_at=start + timedelta(days=1),
    )


class QuotaGuard:
    def __init__(self, db: Session, limit: int | None = None, now: datetime | None = None):
        self.db = db
        self.limit = settings.TUTOR_DAILY_QUOTA if limit is None else limit
        self.window = current_window(now)

    def used(self, user_id: int) -> int:
        return self.db.scalar(
            select(func.count(ChatMessage.id))
            .join(ChatSession, ChatSession.id == ChatMessage.session_id)
            .where(
                ChatSession.user_id == user_id,
                ChatMessage.role == ChatRole.USER.value,
                ChatMessage.created_at >= self.window.start_utc,
            )
        ) or 0

    def remaining(self, user_id: int) -> int:
        return max(0, self.limit - self.used(user_id))

    def ensure_available(self, user_id: int) -> int:
        """Tra ve so luot con lai TRUOC khi hoi; nem QuotaExceededError neu da het."""
        remaining = self.remaining(user_id)
        if remaining <= 0:
            raise QuotaExceededError(self.limit, self.window.reset_at)
        return remaining
