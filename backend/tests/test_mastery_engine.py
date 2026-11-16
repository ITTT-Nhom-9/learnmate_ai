"""Bộ kiểm thử đơn vị & tích hợp cho Lõi thích ứng Mastery Engine (TK-20).

Phạm vi kiểm thử:
1. Giải thuật Exponential Moving Average (EMA) thang 100 và thang 1.0.
2. Quy tắc phân loại năng lực MasteryStatus (WEAK, FAIR, MASTER) và nhãn tiếng Việt (Yếu, Khá, Giỏi).
3. Quy tắc thích ứng độ khó BR-03 (EASY, MEDIUM, HARD).
4. Quy tắc cảnh báo chủ đề yếu BR-08 (tạo khuyến nghị REVIEW_THEORY khi < 60%).
5. Lưu trữ và cập nhật CSDL bảng topic_mastery (user_topic_mastery).
6. Ghi nhận nhật ký hành vi vào bảng learning_events (student_activity_logs).
7. Tự động hoàn thành nhiệm vụ ôn tập khi học viên cải thiện điểm lên >= 60%.
8. Tính toán tỷ lệ hoàn thành môn học (progress_pct) dựa trên trung bình Mastery các chủ đề.
9. Tích hợp trực tiếp với luồng nộp bài QuizSubmissionService.
"""
from decimal import Decimal
import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.course import Course, CourseStatus, Lesson, Topic
from app.models.mastery import (
    LearningEvent,
    LearningEventType,
    MasteryStatus,
    Recommendation,
    RecommendationAction,
    RecommendationStatus,
    TopicMastery,
)
from app.models.quiz import (
    Question,
    QuestionOption,
    Quiz,
    QuizDifficulty,
)
from app.models.user import User
from app.schemas.quiz import AnswerSubmitIn, QuizSubmitRequest
from app.services.mastery_service import MasteryEngine, MasteryService
from app.services.quiz_submission_service import QuizSubmissionService
from app.services.recommendation_service import RecommendationService


# ------------------------------------------------------------------------------
# 1. Kiểm thử thuần thuật toán MasteryEngine (Pure Functions)
# ------------------------------------------------------------------------------

def test_mastery_engine_ema_calculation_standard():
    """Kiểm tra công thức EMA với alpha mặc định 0.3 (BR-01)."""
    # Lần 1: Điểm cũ 0.0, điểm mới 80.0 -> 0.0 * 0.7 + 80.0 * 0.3 = 24.0
    res1 = MasteryEngine.calculate_ema(current_score=0.0, quiz_score=80.0)
    assert res1 == 24.0

    # Lần 2: Điểm cũ 24.0, điểm mới 90.0 -> 24.0 * 0.7 + 90.0 * 0.3 = 16.8 + 27.0 = 43.8
    res2 = MasteryEngine.calculate_ema(current_score=res1, quiz_score=90.0)
    assert res2 == 43.8

    # Lần 3: Điểm cũ 43.8, điểm mới 100.0 -> 43.8 * 0.7 + 100.0 * 0.3 = 30.66 + 30.0 = 60.66
    res3 = MasteryEngine.calculate_ema(current_score=res2, quiz_score=100.0)
    assert res3 == 60.66


def test_mastery_engine_ema_bounds_and_custom_alpha():
    """Kiểm tra giới hạn [0.0, 100.0] và thay đổi tham số alpha."""
    # Điểm quiz vượt trần bị clamp về 100.0
    assert MasteryEngine.calculate_ema(0.0, 150.0) == 45.0
    # Điểm âm bị clamp
    assert MasteryEngine.calculate_ema(0.0, -20.0) == 0.0

    # Alpha = 0.5
    assert MasteryEngine.calculate_ema(50.0, 100.0, alpha=0.5) == 75.0
    # Alpha = 1.0 (toàn bộ theo điểm mới)
    assert MasteryEngine.calculate_ema(50.0, 90.0, alpha=1.0) == 90.0
    # Alpha = 0.0 (toàn bộ theo lịch sử cũ)
    assert MasteryEngine.calculate_ema(50.0, 90.0, alpha=0.0) == 50.0


def test_mastery_engine_ema_ratio_scale():
    """Kiểm tra công thức EMA trên thang đo tỷ lệ 0.00 đến 1.00 (theo file Excel)."""
    # Lần 1: Cũ 0.0, Mới 0.8 -> 0.0 * 0.7 + 0.8 * 0.3 = 0.24
    r1 = MasteryEngine.calculate_ema_ratio(current_ratio=0.0, quiz_ratio=0.8, alpha=0.3)
    assert r1 == 0.24

    # Lần 2: Cũ 0.24, Mới 0.9 -> 0.24 * 0.7 + 0.9 * 0.3 = 0.168 + 0.27 = 0.438
    r2 = MasteryEngine.calculate_ema_ratio(current_ratio=r1, quiz_ratio=0.9, alpha=0.3)
    assert r2 == 0.438


def test_mastery_engine_normalize_score():
    """Kiểm tra hàm chuẩn hóa điểm thi trắc nghiệm về thang 100%."""
    # Thang 10 điểm (từ QuizSubmissionService)
    assert MasteryEngine.normalize_score_to_percent(8.5) == 85.0
    assert MasteryEngine.normalize_score_to_percent(10.0) == 100.0
    assert MasteryEngine.normalize_score_to_percent(0.0) == 0.0

    # Thang tỷ lệ [0.0, 1.0]
    assert MasteryEngine.normalize_score_to_percent(0.75) == 75.0

    # Thang 100 điểm
    assert MasteryEngine.normalize_score_to_percent(92.5) == 92.5


def test_mastery_engine_classification_and_labels():
    """Kiểm tra phân hạng năng lực WEAK, FAIR, MASTER và nhãn tiếng Việt."""
    # Thang 100
    assert MasteryEngine.classify_status(85.0) == MasteryStatus.MASTER
    assert MasteryEngine.classify_label_vi(85.0) == "Giỏi"

    assert MasteryEngine.classify_status(80.0) == MasteryStatus.MASTER
    assert MasteryEngine.classify_label_vi(80.0) == "Giỏi"

    assert MasteryEngine.classify_status(79.9) == MasteryStatus.FAIR
    assert MasteryEngine.classify_label_vi(79.9) == "Khá"

    assert MasteryEngine.classify_status(60.0) == MasteryStatus.FAIR
    assert MasteryEngine.classify_label_vi(60.0) == "Khá"

    assert MasteryEngine.classify_status(59.9) == MasteryStatus.WEAK
    assert MasteryEngine.classify_label_vi(59.9) == "Yếu"

    assert MasteryEngine.classify_status(0.0) == MasteryStatus.WEAK
    assert MasteryEngine.classify_label_vi(0.0) == "Yếu"

    # Thang tỷ lệ [0.0, 1.0]
    assert MasteryEngine.classify_status(0.85) == MasteryStatus.MASTER
    assert MasteryEngine.classify_status(0.75) == MasteryStatus.FAIR
    assert MasteryEngine.classify_status(0.55) == MasteryStatus.WEAK


def test_mastery_engine_adaptive_difficulty():
    """Kiểm tra quy tắc thích ứng độ khó BR-03."""
    assert MasteryEngine.determine_difficulty(85.0) == QuizDifficulty.HARD.value
    assert MasteryEngine.determine_difficulty(80.0) == QuizDifficulty.HARD.value
    assert MasteryEngine.determine_difficulty(75.0) == QuizDifficulty.MEDIUM.value
    assert MasteryEngine.determine_difficulty(60.0) == QuizDifficulty.MEDIUM.value
    assert MasteryEngine.determine_difficulty(59.9) == QuizDifficulty.EASY.value
    assert MasteryEngine.determine_difficulty(0.0) == QuizDifficulty.EASY.value


# ------------------------------------------------------------------------------
# 2. Kiểm thử dịch vụ CSDL MasteryService & RecommendationService
# ------------------------------------------------------------------------------

@pytest.fixture()
def db_session():
    """Tạo CSDL SQLite in-memory độc lập cho mỗi ca kiểm thử."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def mock_learning_data(db_session: Session):
    """Fixture tạo dữ liệu cơ bản: sinh viên, môn học, bài học và chủ đề."""
    user = User(
        email="student.mastery@test.edu.vn",
        full_name="Nguyễn Văn Test Mastery",
        password_hash="fake_hash",
        role="STUDENT",
    )
    db_session.add(user)

    course = Course(
        code="CS101",
        title="Nhập môn lập trình thích ứng",
        status=CourseStatus.ACTIVE.value,
    )
    db_session.add(course)
    db_session.flush()

    lesson = Lesson(
        course_id=course.id,
        title="Cấu trúc dữ liệu và giải thuật",
        order_index=1,
    )
    db_session.add(lesson)
    db_session.flush()

    topic1 = Topic(lesson_id=lesson.id, name="Độ phức tạp thuật toán Big-O")
    topic2 = Topic(lesson_id=lesson.id, name="Cây nhị phân tìm kiếm")
    db_session.add_all([topic1, topic2])
    db_session.commit()

    return user, course, lesson, [topic1, topic2]


def test_mastery_service_get_or_create(db_session: Session, mock_learning_data):
    user, course, lesson, topics = mock_learning_data
    topic1 = topics[0]

    service = MasteryService(db_session)
    mastery = service.get_or_create_mastery(user.id, topic1.id)

    assert mastery.id is not None
    assert mastery.user_id == user.id
    assert mastery.topic_id == topic1.id
    assert float(mastery.mastery_score) == 0.0
    assert mastery.status == MasteryStatus.WEAK.value

    # Gọi lần 2 không tạo thêm bản ghi mới (Idempotent)
    mastery2 = service.get_or_create_mastery(user.id, topic1.id)
    assert mastery2.id == mastery.id


def test_mastery_service_update_after_quiz_and_weak_recommendation(
    db_session: Session, mock_learning_data
):
    """Kiểm tra cập nhật Mastery EMA và kích hoạt BR-08 (tạo khuyến nghị khi < 60%)."""
    user, course, lesson, topics = mock_learning_data
    topic1 = topics[0]

    service = MasteryService(db_session)

    # Sinh viên làm bài đạt 5/10 (50%) -> EMA = 0.0 * 0.7 + 50.0 * 0.3 = 15.0%
    mastery = service.update_mastery_after_quiz(
        user_id=user.id,
        topic_id=topic1.id,
        quiz_score=5.0,
        duration_sec=120,
    )
    assert float(mastery.mastery_score) == 15.0
    assert mastery.status == MasteryStatus.WEAK.value

    # Kiểm tra kích hoạt nhiệm vụ khuyến nghị ôn tập BR-08
    rec_service = RecommendationService(db_session)
    pending_tasks = rec_service.get_pending_recommendations(user.id)
    assert len(pending_tasks) == 1
    assert pending_tasks[0].topic_id == topic1.id
    assert pending_tasks[0].action_type == RecommendationAction.REVIEW_THEORY.value
    assert pending_tasks[0].status == RecommendationStatus.PENDING.value

    # Kiểm tra nhật ký hành vi learning_events (student_activity_logs)
    events = list(
        db_session.scalars(
            select(LearningEvent).where(
                LearningEvent.user_id == user.id,
                LearningEvent.event_type == LearningEventType.SUBMIT_QUIZ.value,
            )
        ).all()
    )
    assert len(events) == 1
    assert events[0].event_data["new_mastery"] == 15.0
    assert events[0].event_data["status"] == "WEAK"
    assert events[0].event_data["label_vi"] == "Yếu"


def test_mastery_service_improves_and_completes_recommendation(
    db_session: Session, mock_learning_data
):
    """Kiểm tra khi sinh viên tiến bộ (>= 60%), hệ thống tự động hoàn thành nhiệm vụ ôn tập."""
    user, course, lesson, topics = mock_learning_data
    topic1 = topics[0]

    service = MasteryService(db_session)

    # Đặt sẵn điểm cũ là 55.0% (vùng Yếu, có 1 nhiệm vụ ôn tập PENDING)
    mastery = service.get_or_create_mastery(user.id, topic1.id)
    mastery.mastery_score = Decimal("55.00")
    mastery.status = MasteryStatus.WEAK.value
    db_session.commit()

    rec_service = RecommendationService(db_session)
    rec_service.create_review_task(user.id, topic1.id)
    assert len(rec_service.get_pending_recommendations(user.id)) == 1

    # Sinh viên làm bài tiếp theo được 10/10 (100%)
    # New score = 55.0 * 0.7 + 100.0 * 0.3 = 38.5 + 30.0 = 68.5% (Khá)
    updated = service.update_mastery_after_quiz(user.id, topic1.id, quiz_score=10.0)
    assert float(updated.mastery_score) == 68.5
    assert updated.status == MasteryStatus.FAIR.value

    # Khuyến nghị cũ đã được tự động hoàn tất
    pending_after = rec_service.get_pending_recommendations(user.id)
    assert len(pending_after) == 0

    all_tasks = list(
        db_session.scalars(
            select(Recommendation).where(
                Recommendation.user_id == user.id,
                Recommendation.topic_id == topic1.id,
            )
        ).all()
    )
    assert len(all_tasks) == 1
    assert all_tasks[0].status == RecommendationStatus.COMPLETED.value


def test_mastery_service_calculate_course_progress(
    db_session: Session, mock_learning_data
):
    """Kiểm tra hàm tính tỷ lệ hoàn thành môn học dựa trên trung bình Mastery các chủ đề."""
    user, course, lesson, topics = mock_learning_data
    topic1, topic2 = topics[0], topics[1]

    service = MasteryService(db_session)

    # Ban đầu chưa học chủ đề nào -> tiến độ 0.0%
    assert service.calculate_course_progress(user.id, course.id) == 0.0

    # Học topic1 đạt 80% (Mastery = 24.0% sau lượt 1)
    service.update_mastery_after_quiz(user.id, topic1.id, quiz_score=8.0)
    # Trung bình: (24.0 + 0.0) / 2 = 12.0%
    assert service.calculate_course_progress(user.id, course.id) == 12.0

    # Học topic2 đạt 100% (Mastery = 30.0% sau lượt 1)
    service.update_mastery_after_quiz(user.id, topic2.id, quiz_score=10.0)
    # Trung bình: (24.0 + 30.0) / 2 = 27.0%
    assert service.calculate_course_progress(user.id, course.id) == 27.0


def test_mastery_service_adaptive_difficulty_query(
    db_session: Session, mock_learning_data
):
    """Kiểm tra truy vấn độ khó thích ứng khi sinh đề BR-03."""
    user, course, lesson, topics = mock_learning_data
    topic1 = topics[0]

    service = MasteryService(db_session)

    # Chưa học -> mặc định MEDIUM
    assert service.get_adaptive_difficulty(user.id, topic1.id) == QuizDifficulty.MEDIUM.value

    # Đạt mức MASTER (>= 80%)
    m = service.get_or_create_mastery(user.id, topic1.id)
    m.mastery_score = Decimal("85.00")
    m.status = MasteryStatus.MASTER.value
    db_session.commit()
    assert service.get_adaptive_difficulty(user.id, topic1.id) == QuizDifficulty.HARD.value


def test_quiz_submission_triggers_mastery_update(
    db_session: Session, mock_learning_data
):
    """Kiểm thử tích hợp: Khi nộp bài thi bằng QuizSubmissionService, điểm Mastery được cập nhật tự động."""
    user, course, lesson, topics = mock_learning_data
    topic1 = topics[0]

    # Tạo 1 đề thi gồm 2 câu hỏi
    quiz = Quiz(
        topic_id=topic1.id,
        title="Kiểm tra Big-O",
        difficulty=QuizDifficulty.MEDIUM.value,
        total_questions=2,
    )
    db_session.add(quiz)
    db_session.flush()

    q1 = Question(quiz_id=quiz.id, content="Câu 1", explanation="Giải thích 1")
    q2 = Question(quiz_id=quiz.id, content="Câu 2", explanation="Giải thích 2")
    db_session.add_all([q1, q2])
    db_session.flush()

    opt1_correct = QuestionOption(question_id=q1.id, opt_label="A", content="Đúng", is_correct=True)
    opt1_wrong = QuestionOption(question_id=q1.id, opt_label="B", content="Sai", is_correct=False)
    opt2_correct = QuestionOption(question_id=q2.id, opt_label="A", content="Đúng", is_correct=True)
    opt2_wrong = QuestionOption(question_id=q2.id, opt_label="B", content="Sai", is_correct=False)
    db_session.add_all([opt1_correct, opt1_wrong, opt2_correct, opt2_wrong])
    db_session.commit()

    # Sinh viên nộp bài: đúng 2/2 câu -> 10.0/10.0
    payload = QuizSubmitRequest(
        quiz_id=quiz.id,
        duration_sec=60,
        answers=[
            AnswerSubmitIn(question_id=q1.id, selected_option_id=opt1_correct.id),
            AnswerSubmitIn(question_id=q2.id, selected_option_id=opt2_correct.id),
        ],
    )

    submission_service = QuizSubmissionService(db_session)
    response = submission_service.submit(user, payload)

    assert response.score == 10.0
    assert response.correct_count == 2

    # Kiểm tra tự động cập nhật TopicMastery: 0.0 * 0.7 + 100.0 * 0.3 = 30.0%
    mastery = db_session.scalar(
        select(TopicMastery).where(
            TopicMastery.user_id == user.id,
            TopicMastery.topic_id == topic1.id,
        )
    )
    assert mastery is not None
    assert float(mastery.mastery_score) == 30.0
    assert mastery.status == MasteryStatus.WEAK.value  # 30% vẫn < 60%


def test_mastery_service_edge_cases_and_model_aliases(
    db_session: Session, mock_learning_data
):
    """Kiểm tra các trường hợp biên và bí danh mô hình UserTopicMastery, StudentActivityLog."""
    from app.models.mastery import StudentActivityLog, UserTopicMastery

    user, course, lesson, topics = mock_learning_data
    topic1 = topics[0]

    service = MasteryService(db_session)

    # 1. Làm bài được 0 điểm
    m_zero = service.update_mastery_after_quiz(user.id, topic1.id, quiz_score=0.0)
    assert float(m_zero.mastery_score) == 0.0
    assert m_zero.status == MasteryStatus.WEAK.value

    # 2. Kiểm tra truy vấn qua bí danh UserTopicMastery (Project_LearnMate_AI.xlsx)
    queried_alias = db_session.scalar(
        select(UserTopicMastery).where(
            UserTopicMastery.user_id == user.id,
            UserTopicMastery.topic_id == topic1.id,
        )
    )
    assert queried_alias is not None
    assert queried_alias.id == m_zero.id

    # 3. Kiểm tra truy vấn qua bí danh StudentActivityLog (Project_LearnMate_AI.xlsx)
    log_alias = db_session.scalar(
        select(StudentActivityLog).where(
            StudentActivityLog.user_id == user.id,
            StudentActivityLog.topic_id == topic1.id,
        )
    )
    assert log_alias is not None
    assert log_alias.event_type == LearningEventType.SUBMIT_QUIZ.value


def test_mastery_engine_boundary_conditions():
    """Kiểm tra giá trị sát ranh giới 59.99, 60.00, 79.99, 80.00."""
    assert MasteryEngine.classify_status(59.99) == MasteryStatus.WEAK
    assert MasteryEngine.classify_label_vi(59.99) == "Yếu"
    assert MasteryEngine.determine_difficulty(59.99) == QuizDifficulty.EASY.value

    assert MasteryEngine.classify_status(60.00) == MasteryStatus.FAIR
    assert MasteryEngine.classify_label_vi(60.00) == "Khá"
    assert MasteryEngine.determine_difficulty(60.00) == QuizDifficulty.MEDIUM.value

    assert MasteryEngine.classify_status(79.99) == MasteryStatus.FAIR
    assert MasteryEngine.classify_label_vi(79.99) == "Khá"
    assert MasteryEngine.determine_difficulty(79.99) == QuizDifficulty.MEDIUM.value

    assert MasteryEngine.classify_status(80.00) == MasteryStatus.MASTER
    assert MasteryEngine.classify_label_vi(80.00) == "Giỏi"
    assert MasteryEngine.determine_difficulty(80.00) == QuizDifficulty.HARD.value

