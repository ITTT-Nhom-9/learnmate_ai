"""Nghiệp vụ Đề xuất & Khuyến nghị ôn tập cá nhân hóa (Phân hệ 6 / BR-08).

Chịu trách nhiệm:
- Tự động tạo nhiệm vụ ôn tập lý thuyết/gợi mở khi sinh viên có điểm Mastery dưới 60%.
- Truy vấn danh sách khuyến nghị ôn tập đang chờ xử lý (PENDING).
- Đánh dấu hoàn thành khuyến nghị khi sinh viên đã cải thiện năng lực.
"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.mastery import (
    Recommendation,
    RecommendationAction,
    RecommendationStatus,
)


class RecommendationService:
    def __init__(self, db: Session):
        self.db = db

    def create_review_task(
        self,
        user_id: int,
        topic_id: int,
        action_type: str = RecommendationAction.REVIEW_THEORY.value,
        priority: int = 1,
    ) -> Recommendation:
        """
        Tạo nhiệm vụ ôn tập cho chủ đề yếu (< 60%).
        Nếu đã tồn tại nhiệm vụ PENDING cùng loại cho chủ đề này, giữ nguyên để tránh trùng lặp.
        """
        existing = self.db.scalar(
            select(Recommendation).where(
                Recommendation.user_id == user_id,
                Recommendation.topic_id == topic_id,
                Recommendation.action_type == action_type,
                Recommendation.status == RecommendationStatus.PENDING.value,
            )
        )
        if existing:
            return existing

        task = Recommendation(
            user_id=user_id,
            topic_id=topic_id,
            action_type=action_type,
            priority=priority,
            status=RecommendationStatus.PENDING.value,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(task)
        self.db.flush()
        return task

    def get_pending_recommendations(
        self, user_id: int, limit: int = 10
    ) -> list[Recommendation]:
        """Lấy danh sách các khuyến nghị ôn tập ưu tiên cao nhất của sinh viên."""
        return list(
            self.db.scalars(
                select(Recommendation)
                .where(
                    Recommendation.user_id == user_id,
                    Recommendation.status == RecommendationStatus.PENDING.value,
                )
                .order_by(Recommendation.priority.asc(), desc(Recommendation.created_at))
                .limit(limit)
            ).all()
        )

    def complete_review_tasks_for_topic(
        self, user_id: int, topic_id: int, action_type: Optional[str] = None
    ) -> int:
        """
        Đánh dấu hoàn thành các khuyến nghị khi sinh viên đã vượt qua bài quiz hoặc ôn tập xong.
        """
        query = select(Recommendation).where(
            Recommendation.user_id == user_id,
            Recommendation.topic_id == topic_id,
            Recommendation.status == RecommendationStatus.PENDING.value,
        )
        if action_type:
            query = query.where(Recommendation.action_type == action_type)

        tasks = list(self.db.scalars(query).all())
        for task in tasks:
            task.status = RecommendationStatus.COMPLETED.value
        if tasks:
            self.db.flush()
        return len(tasks)
