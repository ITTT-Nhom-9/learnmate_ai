"""Nghiệp vụ Thống kê tiến độ học tập & Điểm năng lực Radar (TK-21 / Phân hệ 6, UC-07).

Nguồn dữ liệu:
- topic_mastery (user_topic_mastery): Điểm Mastery EMA 0-100% của từng chủ đề.
- quiz_attempts (+ quizzes): Lịch sử nộp bài trắc nghiệm, điểm thang 10, thời lượng.
- recommendations: Hành động ôn tập đang chờ (PENDING) cho chủ đề yếu.

Quy tắc:
- % hoàn thành môn = trung bình Mastery của TẤT CẢ chủ đề trong môn (chủ đề chưa học = 0%),
  thống nhất với MasteryService.calculate_course_progress.
- Cảnh báo đỏ (BR-08): chủ đề đã luyện tập và có Mastery < 60%, xếp từ yếu nhất.
- Radar tối đa `max_axes` trục (mặc định 6). Khi môn có nhiều chủ đề hơn, ưu tiên chủ đề đã
  luyện tập gần nhất, phần còn lại lấp theo thứ tự giáo trình; các trục luôn hiển thị theo
  thứ tự giáo trình để biểu đồ ổn định giữa các lần tải.
"""
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.course import Course, CourseStatus, Enrollment, Lesson, Topic
from app.models.mastery import (
    MasteryStatus,
    Recommendation,
    RecommendationAction,
    RecommendationStatus,
    TopicMastery,
)
from app.models.quiz import Quiz, QuizAttempt, QuizAttemptStatus
from app.models.user import User
from app.schemas.progress import (
    ProgressStats,
    ProgressSummaryResponse,
    RadarAxis,
    RadarResponse,
    RecentAttempt,
    WeakTopicAlert,
)
from app.services.course_service import CourseError, CourseNotFoundError
from app.services.mastery_service import MasteryEngine

DEFAULT_RADAR_AXES = 6
RECENT_ATTEMPTS_LIMIT = 10
NOT_STARTED = "NOT_STARTED"
NOT_STARTED_LABEL_VI = "Chưa học"


_LABELS_VI = {
    MasteryStatus.MASTER: "Giỏi",
    MasteryStatus.FAIR: "Khá",
    MasteryStatus.WEAK: "Yếu",
}


def classify_percent(score: float) -> MasteryStatus:
    """Phân hạng Mastery trên thang 0-100% (topic_mastery luôn lưu thang 100).

    Không dùng MasteryEngine.classify_status vì hàm đó tự nhận diện (0, 1] là thang tỷ lệ,
    khiến Mastery rất thấp (vd 0.9%) bị xếp nhầm thành MASTER.
    """
    if score >= MasteryEngine.MASTER_THRESHOLD:
        return MasteryStatus.MASTER
    if score >= MasteryEngine.WEAK_THRESHOLD:
        return MasteryStatus.FAIR
    return MasteryStatus.WEAK


class NotEnrolledError(CourseError):
    status_code = 403


@dataclass
class _TopicRow:
    topic: Topic
    lesson: Lesson


@dataclass
class _AttemptAgg:
    count: int = 0
    score_sum: float = 0.0
    duration_sum: int = 0
    last_attempt_id: int = 0
    last_score: float | None = None


class ProgressService:
    def __init__(self, db: Session):
        self.db = db

    # --------------------------------------------------------------------------
    # GET /progress/summary
    # --------------------------------------------------------------------------
    def get_summary(self, user: User, course_id: int) -> ProgressSummaryResponse:
        course = self._get_enrolled_course(user.id, course_id)
        rows = self._topic_rows(course.id)
        topic_ids = [r.topic.id for r in rows]
        masteries = self._mastery_map(user.id, topic_ids)
        attempts = self._attempt_aggregates(user.id, topic_ids)

        mastered = fair = weak = 0
        for m in masteries.values():
            status = classify_percent(self._score(m))
            if status == MasteryStatus.MASTER:
                mastered += 1
            elif status == MasteryStatus.FAIR:
                fair += 1
            else:
                weak += 1

        total_attempts = sum(a.count for a in attempts.values())
        score_sum = sum(a.score_sum for a in attempts.values())
        stats = ProgressStats(
            total_topics=len(rows),
            mastered_topics=mastered,
            fair_topics=fair,
            weak_topics=weak,
            not_started_topics=len(rows) - len(masteries),
            total_attempts=total_attempts,
            average_quiz_score=round(score_sum / total_attempts, 2) if total_attempts else 0.0,
            total_study_time_sec=sum(a.duration_sum for a in attempts.values()),
            last_practiced_at=max((m.last_practiced_at for m in masteries.values()), default=None),
        )

        return ProgressSummaryResponse(
            course_id=course.id,
            course_code=course.code,
            course_title=course.title,
            overall_progress_pct=self._overall_progress(topic_ids, masteries),
            stats=stats,
            weak_topics=self._weak_topic_alerts(user.id, rows, masteries, attempts),
            recent_attempts=self._recent_attempts(user.id, topic_ids),
        )

    # --------------------------------------------------------------------------
    # GET /progress/radar
    # --------------------------------------------------------------------------
    def get_radar(
        self, user: User, course_id: int, max_axes: int = DEFAULT_RADAR_AXES
    ) -> RadarResponse:
        course = self._get_enrolled_course(user.id, course_id)
        rows = self._topic_rows(course.id)
        masteries = self._mastery_map(user.id, [r.topic.id for r in rows])

        selected = self._select_radar_topics(rows, masteries, max_axes)
        axes = [self._radar_axis(r, masteries.get(r.topic.id)) for r in selected]
        return RadarResponse(
            course_id=course.id,
            max_axes=max_axes,
            total_topics=len(rows),
            truncated=len(rows) > len(axes),
            axes=axes,
            labels=[a.topic_name for a in axes],
            scores=[a.mastery_score for a in axes],
        )

    # --------------------------------------------------------------------------
    # Truy vấn dữ liệu
    # --------------------------------------------------------------------------
    def _get_enrolled_course(self, user_id: int, course_id: int) -> Course:
        course = self.db.scalar(
            select(Course).where(Course.id == course_id, Course.status == CourseStatus.ACTIVE.value)
        )
        if course is None:
            raise CourseNotFoundError("Môn học không tồn tại")
        enrolled = self.db.scalar(
            select(Enrollment.id).where(Enrollment.user_id == user_id, Enrollment.course_id == course_id)
        )
        if enrolled is None:
            raise NotEnrolledError("Bạn chưa ghi danh môn học này")
        return course

    def _topic_rows(self, course_id: int) -> list[_TopicRow]:
        """Toàn bộ chủ đề của môn theo thứ tự giáo trình (bài học -> chủ đề)."""
        result = self.db.execute(
            select(Topic, Lesson)
            .join(Lesson, Lesson.id == Topic.lesson_id)
            .where(Lesson.course_id == course_id)
            .order_by(Lesson.order_index, Lesson.id, Topic.id)
        ).all()
        return [_TopicRow(topic=t, lesson=l) for t, l in result]

    def _mastery_map(self, user_id: int, topic_ids: list[int]) -> dict[int, TopicMastery]:
        if not topic_ids:
            return {}
        return {
            m.topic_id: m
            for m in self.db.scalars(
                select(TopicMastery).where(
                    TopicMastery.user_id == user_id,
                    TopicMastery.topic_id.in_(topic_ids),
                )
            )
        }

    def _submitted_attempts_query(self, user_id: int, topic_ids: list[int]):
        return (
            select(QuizAttempt, Quiz)
            .join(Quiz, Quiz.id == QuizAttempt.quiz_id)
            .where(
                QuizAttempt.user_id == user_id,
                QuizAttempt.status == QuizAttemptStatus.SUBMITTED.value,
                Quiz.topic_id.in_(topic_ids),
            )
        )

    def _attempt_aggregates(self, user_id: int, topic_ids: list[int]) -> dict[int, _AttemptAgg]:
        """Gom số lượt, tổng điểm, tổng thời gian và điểm lượt gần nhất theo chủ đề (1 truy vấn)."""
        if not topic_ids:
            return {}
        rows = self.db.execute(
            select(
                Quiz.topic_id,
                func.count(QuizAttempt.id),
                func.coalesce(func.sum(QuizAttempt.score), 0),
                func.coalesce(func.sum(QuizAttempt.duration_sec), 0),
                func.max(QuizAttempt.id),
            )
            .join(Quiz, Quiz.id == QuizAttempt.quiz_id)
            .where(
                QuizAttempt.user_id == user_id,
                QuizAttempt.status == QuizAttemptStatus.SUBMITTED.value,
                Quiz.topic_id.in_(topic_ids),
            )
            .group_by(Quiz.topic_id)
        ).all()
        aggs = {
            tid: _AttemptAgg(
                count=int(cnt),
                score_sum=float(score_sum),
                duration_sum=int(dur_sum),
                last_attempt_id=int(last_id),
            )
            for tid, cnt, score_sum, dur_sum, last_id in rows
        }
        if aggs:
            last_scores = dict(
                self.db.execute(
                    select(QuizAttempt.id, QuizAttempt.score).where(
                        QuizAttempt.id.in_([a.last_attempt_id for a in aggs.values()])
                    )
                ).all()
            )
            for agg in aggs.values():
                score = last_scores.get(agg.last_attempt_id)
                agg.last_score = float(score) if score is not None else None
        return aggs

    def _recent_attempts(self, user_id: int, topic_ids: list[int]) -> list[RecentAttempt]:
        if not topic_ids:
            return []
        rows = self.db.execute(
            self._submitted_attempts_query(user_id, topic_ids)
            .add_columns(Topic.name)
            .join(Topic, Topic.id == Quiz.topic_id)
            .order_by(QuizAttempt.id.desc())
            .limit(RECENT_ATTEMPTS_LIMIT)
        ).all()
        return [
            RecentAttempt(
                attempt_id=attempt.id,
                quiz_id=quiz.id,
                quiz_title=quiz.title,
                topic_id=quiz.topic_id,
                topic_name=topic_name,
                difficulty=quiz.difficulty,
                score=float(attempt.score),
                duration_sec=attempt.duration_sec,
            )
            for attempt, quiz, topic_name in rows
        ]

    def _pending_actions(self, user_id: int, topic_ids: list[int]) -> dict[int, str]:
        """Hành động ôn tập ưu tiên cao nhất đang PENDING của từng chủ đề."""
        if not topic_ids:
            return {}
        recs = self.db.scalars(
            select(Recommendation)
            .where(
                Recommendation.user_id == user_id,
                Recommendation.topic_id.in_(topic_ids),
                Recommendation.status == RecommendationStatus.PENDING.value,
            )
            .order_by(Recommendation.priority.asc(), Recommendation.id.desc())
        )
        actions: dict[int, str] = {}
        for rec in recs:
            actions.setdefault(rec.topic_id, rec.action_type)
        return actions

    # --------------------------------------------------------------------------
    # Tính toán
    # --------------------------------------------------------------------------
    @staticmethod
    def _score(mastery: TopicMastery | None) -> float:
        return float(mastery.mastery_score or 0.0) if mastery is not None else 0.0

    def _overall_progress(self, topic_ids: list[int], masteries: dict[int, TopicMastery]) -> float:
        if not topic_ids:
            return 0.0
        avg = sum(self._score(masteries.get(tid)) for tid in topic_ids) / len(topic_ids)
        return min(100.0, max(0.0, round(avg, 2)))

    def _weak_topic_alerts(
        self,
        user_id: int,
        rows: list[_TopicRow],
        masteries: dict[int, TopicMastery],
        attempts: dict[int, _AttemptAgg],
    ) -> list[WeakTopicAlert]:
        weak_rows = [
            r
            for r in rows
            if r.topic.id in masteries
            and self._score(masteries[r.topic.id]) < MasteryEngine.WEAK_THRESHOLD
        ]
        if not weak_rows:
            return []

        actions = self._pending_actions(user_id, [r.topic.id for r in weak_rows])
        # Yếu nhất lên đầu; cùng điểm thì chủ đề luyện gần đây hơn lên trước (sort ổn định 2 bước)
        weak_rows.sort(
            key=lambda r: masteries[r.topic.id].last_practiced_at or datetime.min, reverse=True
        )
        weak_rows.sort(key=lambda r: self._score(masteries[r.topic.id]))
        alerts = []
        for r in weak_rows:
            m = masteries[r.topic.id]
            agg = attempts.get(r.topic.id, _AttemptAgg())
            alerts.append(
                WeakTopicAlert(
                    topic_id=r.topic.id,
                    topic_name=r.topic.name,
                    lesson_id=r.lesson.id,
                    lesson_title=r.lesson.title,
                    mastery_score=self._score(m),
                    attempt_count=agg.count,
                    last_quiz_score=agg.last_score,
                    last_practiced_at=m.last_practiced_at,
                    recommended_action=actions.get(
                        r.topic.id, RecommendationAction.REVIEW_THEORY.value
                    ),
                )
            )
        return alerts

    @staticmethod
    def _select_radar_topics(
        rows: list[_TopicRow], masteries: dict[int, TopicMastery], max_axes: int
    ) -> list[_TopicRow]:
        if len(rows) <= max_axes:
            return rows
        order = {r.topic.id: i for i, r in enumerate(rows)}
        practiced = sorted(
            (r for r in rows if r.topic.id in masteries),
            key=lambda r: masteries[r.topic.id].last_practiced_at or datetime.min,
            reverse=True,
        )
        unpracticed = [r for r in rows if r.topic.id not in masteries]
        chosen = (practiced + unpracticed)[:max_axes]
        return sorted(chosen, key=lambda r: order[r.topic.id])

    def _radar_axis(self, row: _TopicRow, mastery: TopicMastery | None) -> RadarAxis:
        if mastery is None:
            status, label = NOT_STARTED, NOT_STARTED_LABEL_VI
        else:
            rank = classify_percent(self._score(mastery))
            status, label = rank.value, _LABELS_VI[rank]
        return RadarAxis(
            topic_id=row.topic.id,
            topic_name=row.topic.name,
            lesson_id=row.lesson.id,
            mastery_score=self._score(mastery),
            status=status,
            label_vi=label,
            is_practiced=mastery is not None,
        )
