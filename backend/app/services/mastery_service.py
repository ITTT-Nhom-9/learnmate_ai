"""Lõi thích ứng & Thuật toán tính độ thông thạo kiến thức EMA (Mastery Engine).

Hiện thực hóa toàn diện:
- Task [TK-20] từ Project_LearnMate_AI.xlsx:
  Công thức EMA: Mastery_moi = alpha * Diem_moi + (1 - alpha) * Mastery_cu (alpha = 0.3)
  Cập nhật điểm từ 0.00 đến 1.00 (và chuẩn 0.00% - 100.00%), tự động gán nhãn: Yếu, Khá, Giỏi.
- Quy tắc nghiệp vụ LearnMate_AI_SRS.docx:
  * BR-01: Mastery mới = Mastery cũ * 0.7 + Điểm quiz mới * 0.3.
  * BR-03: Thích ứng độ khó (>= 80% HARD, 60% - 79% MEDIUM, < 60% EASY).
  * BR-08: Ngưỡng cảnh báo chủ đề yếu (< 60%), tự động kích hoạt nhiệm vụ ôn tập.
- Thiết kế hệ thống LearnMate_AI_Thiet_ke_he_thong(csdl, model).docx (Bảng 7, Bảng 16, Bảng 18):
  * Cập nhật bảng topic_mastery (user_topic_mastery).
  * Kích hoạt recommendation_service tạo bản ghi recommendations.
  * Ghi nhật ký hành vi học tập vào learning_events (student_activity_logs).
"""
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.course import Lesson, Topic
from app.models.mastery import (
    LearningEvent,
    LearningEventType,
    MasteryStatus,
    RecommendationAction,
    TopicMastery,
    UserTopicMastery,
)
from app.models.quiz import Quiz, QuizAttempt, QuizDifficulty
from app.services.recommendation_service import RecommendationService

logger = logging.getLogger(__name__)


class MasteryEngine:
    """Động cơ tính toán giải thuật EMA và phân loại năng lực thích ứng."""

    ALPHA: float = 0.3  # Trọng số EMA: 30% kết quả mới + 70% lịch sử (BR-01)
    WEAK_THRESHOLD: float = 60.0  # Dưới 60%: Yếu (WEAK, BR-08)
    MASTER_THRESHOLD: float = 80.0  # Từ 80% trở lên: Giỏi (MASTER)

    @classmethod
    def calculate_ema(
        cls, current_score: float, quiz_score: float, alpha: float = ALPHA
    ) -> float:
        """
        Công thức Exponential Moving Average (EMA) chuẩn:
        Mastery_moi = (Mastery_cu * (1 - alpha)) + (Diem_quiz * alpha)

        Thang đo mặc định: 0.00% - 100.00%.
        Giới hạn nghiêm ngặt [0.0, 100.0], làm tròn 2 chữ số thập phân.
        """
        alpha_clamped = min(1.0, max(0.0, float(alpha)))
        new_score = (float(current_score) * (1.0 - alpha_clamped)) + (float(quiz_score) * alpha_clamped)
        return min(100.0, max(0.0, round(new_score, 2)))

    @classmethod
    def calculate_ema_ratio(
        cls, current_ratio: float, quiz_ratio: float, alpha: float = ALPHA
    ) -> float:
        """
        Công thức EMA trên thang đo tỷ lệ 0.00 đến 1.00 (theo mô tả Project_LearnMate_AI.xlsx).
        Giới hạn nghiêm ngặt [0.0000, 1.0000], làm tròn 4 chữ số thập phân.
        """
        alpha_clamped = min(1.0, max(0.0, float(alpha)))
        new_ratio = (float(current_ratio) * (1.0 - alpha_clamped)) + (float(quiz_ratio) * alpha_clamped)
        return min(1.0, max(0.0, round(new_ratio, 4)))

    @classmethod
    def normalize_score_to_percent(cls, score: float) -> float:
        """
        Chuẩn hóa điểm kiểm tra trắc nghiệm về thang đo 100%:
        - Nếu score thuộc thang 10 (ví dụ từ QuizSubmissionService: 0.0 - 10.0) -> nhân 10.
        - Nếu score thuộc thang tỷ lệ [0.0, 1.0] và khác 0 -> nhân 100.
        - Nếu score đã ở thang 100 -> giữ nguyên trong [0.0, 100.0].
        """
        score_val = float(score)
        if score_val < 0.0:
            return 0.0
        if 0.0 < score_val <= 1.0:
            return min(100.0, round(score_val * 100.0, 2))
        if score_val <= 10.0:
            return min(100.0, round(score_val * 10.0, 2))
        return min(100.0, round(score_val, 2))

    @classmethod
    def classify_status(cls, score: float) -> MasteryStatus:
        """
        Phân loại xếp hạng năng lực theo ngưỡng BR-03 và BR-08:
        - >= 80% (hoặc >= 0.80): MASTER (Giỏi)
        - 60% - 79% (hoặc 0.60 - 0.79): FAIR (Khá)
        - < 60% (hoặc < 0.60): WEAK (Yếu)
        """
        score_val = float(score)
        # Hỗ trợ nhận diện tự động thang đo tỷ lệ [0.0, 1.0]
        threshold_master = 0.8 if score_val <= 1.0 and score_val > 0.0 else cls.MASTER_THRESHOLD
        threshold_weak = 0.6 if score_val <= 1.0 and score_val > 0.0 else cls.WEAK_THRESHOLD

        if score_val >= threshold_master:
            return MasteryStatus.MASTER
        if score_val >= threshold_weak:
            return MasteryStatus.FAIR
        return MasteryStatus.WEAK

    @classmethod
    def classify_label_vi(cls, score: float) -> str:
        """Trả về nhãn tiếng Việt tương ứng: 'Giỏi', 'Khá', 'Yếu'."""
        status = cls.classify_status(score)
        if status == MasteryStatus.MASTER:
            return "Giỏi"
        if status == MasteryStatus.FAIR:
            return "Khá"
        return "Yếu"

    @classmethod
    def determine_difficulty(cls, score: float) -> str:
        """
        Quy tắc BR-03: Điều chỉnh độ khó thích ứng cho lượt sinh câu hỏi tiếp theo:
        - Mastery >= 80%: Sinh câu hỏi Khó (HARD)
        - 60% <= Mastery < 80%: Sinh câu hỏi Trung bình (MEDIUM)
        - Mastery < 60%: Sinh câu hỏi Dễ (EASY)
        """
        score_val = float(score)
        threshold_master = 0.8 if score_val <= 1.0 and score_val > 0.0 else cls.MASTER_THRESHOLD
        threshold_weak = 0.6 if score_val <= 1.0 and score_val > 0.0 else cls.WEAK_THRESHOLD

        if score_val >= threshold_master:
            return QuizDifficulty.HARD.value
        if score_val >= threshold_weak:
            return QuizDifficulty.MEDIUM.value
        return QuizDifficulty.EASY.value


class MasteryService:
    """
    Dịch vụ điều phối CSDL cho Lõi thích ứng Mastery (Phân hệ 6).
    Triển khai chính xác theo bản thiết kế mẫu tại Bảng 7 của tài liệu SDD.
    """

    ALPHA: float = MasteryEngine.ALPHA

    def __init__(
        self,
        db: Session,
        recommendation_service: Optional[RecommendationService] = None,
        alpha: float = ALPHA,
    ):
        self.db = db
        self.recommendation_service = recommendation_service or RecommendationService(db)
        self.alpha = alpha

    def get_or_create_mastery(self, user_id: int, topic_id: int) -> TopicMastery:
        """Tìm hoặc khởi tạo bản ghi độ thành thạo của sinh viên cho một chủ đề."""
        mastery = self.db.scalar(
            select(TopicMastery).where(
                TopicMastery.user_id == user_id,
                TopicMastery.topic_id == topic_id,
            )
        )
        if not mastery:
            mastery = TopicMastery(
                user_id=user_id,
                topic_id=topic_id,
                mastery_score=Decimal("0.00"),
                status=MasteryStatus.WEAK.value,
                last_practiced_at=datetime.now(timezone.utc),
            )
            self.db.add(mastery)
            self.db.flush()
        return mastery

    def update_mastery_after_quiz(
        self,
        user_id: int,
        topic_id: int,
        quiz_score: float,
        duration_sec: int = 0,
    ) -> TopicMastery:
        """
        Cập nhật điểm thành thạo Mastery theo công thức Exponential Moving Average (EMA)
        sau mỗi lượt nộp bài trắc nghiệm (BR-01).

        Quy trình:
        1. Lấy hoặc tạo bản ghi TopicMastery (user_topic_mastery).
        2. Chuẩn hóa điểm bài thi về thang 100%.
        3. Tính điểm mới: S_new = S_old * (1 - α) + S_quiz * α (làm tròn 2 chữ số, [0, 100]).
        4. Gán phân hạng năng lực mới: 'WEAK' (<60), 'FAIR' (60-79), 'MASTER' (>=80).
        5. Nếu điểm mới < 60%: Tự động kích hoạt nhiệm vụ ôn tập lý thuyết (BR-08).
           Nếu điểm mới >= 60%: Hoàn tất các nhiệm vụ ôn tập đang chờ của chủ đề này.
        6. Ghi nhật ký hành vi học tập vào bảng learning_events (student_activity_logs).
        7. Lưu giao dịch CSDL và trả về TopicMastery.
        """
        mastery = self.get_or_create_mastery(user_id, topic_id)
        current_score = float(mastery.mastery_score or 0.0)

        # 2. Chuẩn hóa điểm quiz
        normalized_quiz_score = MasteryEngine.normalize_score_to_percent(quiz_score)

        # 3. Tính điểm mới bằng EMA (xử lý Cold-Start giải thuật)
        # Khi sinh viên làm bài trắc nghiệm của một chủ đề lần đầu tiên (current_score == 0.0):
        # Điểm Mastery ban đầu được thiết lập bằng chính kết quả bài thi đầu tiên.
        # Từ các lượt làm bài tiếp theo (current_score > 0.0), áp dụng chuẩn công thức EMA:
        # S_new = S_old * 0.7 + S_quiz * 0.3 (BR-01)
        if current_score == 0.0:
            new_score = normalized_quiz_score
        else:
            new_score = MasteryEngine.calculate_ema(current_score, normalized_quiz_score, self.alpha)

        # 4. Phân hạng năng lực
        new_status = MasteryEngine.classify_status(new_score)
        label_vi = MasteryEngine.classify_label_vi(new_score)

        mastery.mastery_score = Decimal(str(new_score))
        mastery.status = new_status.value
        mastery.last_practiced_at = datetime.now(timezone.utc)

        # 5. Kích hoạt quy tắc cảnh báo chủ đề yếu BR-08
        if new_score < MasteryEngine.WEAK_THRESHOLD:
            self.recommendation_service.create_review_task(
                user_id=user_id,
                topic_id=topic_id,
                action_type=RecommendationAction.REVIEW_THEORY.value,
                priority=1,
            )
        else:
            # Khi sinh viên đã cải thiện điểm lên >= 60%, tự động đóng các nhiệm vụ ôn tập cũ
            self.recommendation_service.complete_review_tasks_for_topic(user_id, topic_id)

        # 6. Ghi nhật ký sự kiện vào learning_events (student_activity_logs)
        try:
            event = LearningEvent(
                user_id=user_id,
                topic_id=topic_id,
                event_type=LearningEventType.SUBMIT_QUIZ.value,
                event_data={
                    "quiz_score_raw": quiz_score,
                    "quiz_score_normalized": normalized_quiz_score,
                    "old_mastery": current_score,
                    "new_mastery": new_score,
                    "status": new_status.value,
                    "label_vi": label_vi,
                    "duration_sec": duration_sec,
                },
                created_at=datetime.now(timezone.utc),
            )
            self.db.add(event)
        except Exception as exc:
            logger.warning(f"Không thể ghi nhật ký learning_events: {exc}")

        self.db.commit()
        self.db.refresh(mastery)
        return mastery

    def get_adaptive_difficulty(self, user_id: int, topic_id: int) -> str:
        """
        Truy vấn độ khó thích ứng cho sinh viên khi sinh đề kiểm tra mới (BR-03).
        Nếu sinh viên chưa làm bài lần nào (chưa có điểm), trả về mặc định MEDIUM hoặc EASY.
        """
        mastery = self.db.scalar(
            select(TopicMastery).where(
                TopicMastery.user_id == user_id,
                TopicMastery.topic_id == topic_id,
            )
        )
        if not mastery or float(mastery.mastery_score or 0.0) == 0.0:
            return QuizDifficulty.MEDIUM.value
        return MasteryEngine.determine_difficulty(float(mastery.mastery_score))

    def calculate_course_progress(self, user_id: int, course_id: int) -> float:
        """
        Tính toán tỷ lệ hoàn thành môn học (progress_pct) dựa trên trung bình điểm
        Mastery của toàn bộ các chủ đề trong môn học.
        """
        topics = list(
            self.db.scalars(
                select(Topic)
                .join(Lesson, Lesson.id == Topic.lesson_id)
                .where(Lesson.course_id == course_id)
            ).all()
        )
        if not topics:
            return 0.0

        topic_ids = [t.id for t in topics]
        masteries = list(
            self.db.scalars(
                select(TopicMastery).where(
                    TopicMastery.user_id == user_id,
                    TopicMastery.topic_id.in_(topic_ids),
                )
            ).all()
        )
        mastery_map = {m.topic_id: float(m.mastery_score or 0.0) for m in masteries}
        total_score = sum(mastery_map.get(tid, 0.0) for tid in topic_ids)
        avg_score = total_score / len(topic_ids)
        return min(100.0, max(0.0, round(avg_score, 2)))

    def get_course_topics_mastery_map(
        self, user_id: int, course_id: int
    ) -> dict[int, float]:
        """Lấy bảng ánh xạ {topic_id: mastery_score} cho các chủ đề thuộc một môn học."""
        rows = self.db.execute(
            select(TopicMastery.topic_id, TopicMastery.mastery_score)
            .join(Topic, Topic.id == TopicMastery.topic_id)
            .join(Lesson, Lesson.id == Topic.lesson_id)
            .where(
                TopicMastery.user_id == user_id,
                Lesson.course_id == course_id,
            )
        ).all()
        return {tid: float(score or 0.0) for tid, score in rows}
