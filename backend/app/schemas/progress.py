"""Schema phản hồi API Thống kê tiến độ học tập & Điểm Radar (TK-21 / Phân hệ 6, UC-07).

- GET /api/v1/progress/summary: % hoàn thành môn, thẻ chỉ số nhanh, cảnh báo đỏ, lịch sử làm bài.
- GET /api/v1/progress/radar:   Điểm năng lực tối đa 6 trục (mỗi trục = 1 chủ đề) cho Chart.js.
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

# Trạng thái chủ đề hiển thị trên Dashboard: 3 hạng Mastery (BR-08) + chủ đề chưa luyện tập.
TopicProgressStatus = Literal["WEAK", "FAIR", "MASTER", "NOT_STARTED"]


# ------------------------------------------------------------------------------
# GET /progress/summary
# ------------------------------------------------------------------------------

class ProgressStats(BaseModel):
    """Số liệu cho hàng 4 thẻ chỉ số nhanh (SCR-07)."""

    total_topics: int
    mastered_topics: int       # MASTER (>= 80%)
    fair_topics: int           # FAIR (60% - 79%)
    weak_topics: int           # WEAK (< 60%) đã luyện tập -> số cảnh báo đỏ
    not_started_topics: int    # Chưa làm bài quiz nào
    total_attempts: int
    average_quiz_score: float  # Thang 10, trung bình các lượt nộp bài
    total_study_time_sec: int
    last_practiced_at: datetime | None = None


class WeakTopicAlert(BaseModel):
    """Chủ đề yếu cần cải thiện gấp (Alert Red, BR-08: Mastery < 60%)."""

    topic_id: int
    topic_name: str
    lesson_id: int
    lesson_title: str
    mastery_score: float
    status: Literal["WEAK"] = "WEAK"
    alert_level: Literal["RED"] = "RED"
    attempt_count: int
    last_quiz_score: float | None = None  # Thang 10
    last_practiced_at: datetime | None = None
    recommended_action: str


class RecentAttempt(BaseModel):
    """Một dòng trong bảng lịch sử làm bài."""

    attempt_id: int
    quiz_id: int
    quiz_title: str
    topic_id: int
    topic_name: str
    difficulty: str
    score: float  # Thang 10
    duration_sec: int
    created_at: datetime | None = None
    last_practiced_at: datetime | None = None


class ProgressSummaryResponse(BaseModel):
    course_id: int
    course_code: str
    course_title: str
    overall_progress_pct: float
    stats: ProgressStats
    weak_topics: list[WeakTopicAlert]
    recent_attempts: list[RecentAttempt]


# ------------------------------------------------------------------------------
# GET /progress/radar
# ------------------------------------------------------------------------------

class RadarAxis(BaseModel):
    topic_id: int
    topic_name: str
    lesson_id: int
    mastery_score: float
    status: TopicProgressStatus
    label_vi: str  # Giỏi | Khá | Yếu | Chưa học
    is_practiced: bool


class RadarResponse(BaseModel):
    course_id: int
    max_axes: int
    total_topics: int
    truncated: bool  # True nếu môn có nhiều chủ đề hơn số trục hiển thị
    axes: list[RadarAxis]
    # Mảng song song tiện truyền thẳng vào Chart.js (data.labels / datasets[0].data)
    labels: list[str]
    scores: list[float]
