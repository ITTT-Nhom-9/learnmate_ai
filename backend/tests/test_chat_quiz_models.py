import pytest
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from app.core.database import Base
from app.models import (
    User,
    Course,
    Lesson,
    Topic,
    ChatSession,
    ChatMessage,
    ChatMode,
    ChatRole,
    ChatSessionStatus,
    Quiz,
    Question,
    QuestionOption,
    QuizAttempt,
    AttemptAnswer,
    QuizDifficulty,
    QuizAttemptStatus,
)


@pytest.fixture(scope="function")
def db_session():
    """
    Tạo in-memory SQLite database riêng biệt cho mỗi unit test để đảm bảo tính cô lập 100%.
    Bật PRAGMA foreign_keys=ON để kiểm tra toàn vẹn khóa ngoại và cascade delete.
    """
    engine = create_engine("sqlite:///:memory:", echo=False)

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def base_data(db_session):
    """Fixture tạo sẵn User, Course, Lesson, Topic cơ bản cho các bài test."""
    user = User(
        email="student_test@learnmate.edu.vn",
        password_hash="fakehash123",
        full_name="Nguyễn Văn Test",
    )
    course = Course(
        code="CS101",
        title="Lập trình Python cơ bản",
        description="Môn học nền tảng"
    )
    db_session.add_all([user, course])
    db_session.commit()

    lesson = Lesson(
        course_id=course.id,
        title="Bài 1: Cú pháp biến và kiểu dữ liệu",
        order_index=1
    )
    db_session.add(lesson)
    db_session.commit()

    topic = Topic(
        lesson_id=lesson.id,
        name="Biến và Kiểu dữ liệu",
        description="Lý thuyết về int, float, string"
    )
    db_session.add(topic)
    db_session.commit()

    return {
        "user": user,
        "course": course,
        "lesson": lesson,
        "topic": topic
    }


# ==============================================================================
# 1. Tests cho Phân hệ Chat AI: chat_sessions & chat_messages
# ==============================================================================

def test_create_chat_session_success(db_session, base_data):
    user = base_data["user"]
    lesson = base_data["lesson"]

    session = ChatSession(
        user_id=user.id,
        lesson_id=lesson.id,
        mode=ChatMode.SOCRATIC.value,
        hint_level=1,
        wrong_streak=0,
        status=ChatSessionStatus.ACTIVE.value
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    assert session.id is not None
    assert session.user_id == user.id
    assert session.lesson_id == lesson.id
    assert session.mode == "SOCRATIC"
    assert session.hint_level == 1
    assert session.wrong_streak == 0
    assert session.status == "ACTIVE"
    assert session.user.email == user.email
    assert session.lesson.title == lesson.title


def test_create_chat_messages_and_ordering(db_session, base_data):
    user = base_data["user"]
    lesson = base_data["lesson"]

    session = ChatSession(
        user_id=user.id,
        lesson_id=lesson.id,
        mode=ChatMode.EXPLAIN.value
    )
    db_session.add(session)
    db_session.commit()

    msg1 = ChatMessage(
        session_id=session.id,
        role=ChatRole.USER.value,
        content="Cho em hỏi kiểu dữ liệu float trong Python là gì?",
        tokens_used=15
    )
    msg2 = ChatMessage(
        session_id=session.id,
        role=ChatRole.ASSISTANT.value,
        content="Kiểu dữ liệu float đại diện cho các số thực có dấu phẩy động.",
        tokens_used=25
    )
    db_session.add_all([msg1, msg2])
    db_session.commit()

    db_session.refresh(session)
    assert len(session.messages) == 2
    assert session.messages[0].role == "USER"
    assert session.messages[1].role == "ASSISTANT"
    assert session.messages[0].tokens_used == 15
    assert session.messages[1].tokens_used == 25


def test_chat_session_cascade_delete(db_session, base_data):
    user = base_data["user"]
    lesson = base_data["lesson"]

    session = ChatSession(
        user_id=user.id,
        lesson_id=lesson.id,
        mode=ChatMode.EXPLAIN.value
    )
    db_session.add(session)
    db_session.commit()

    msg = ChatMessage(
        session_id=session.id,
        role=ChatRole.USER.value,
        content="Tin nhắn thử nghiệm"
    )
    db_session.add(msg)
    db_session.commit()

    msg_id = msg.id
    db_session.delete(session)
    db_session.commit()

    # ChatMessage liên quan phải bị xóa theo (Cascade)
    assert db_session.query(ChatMessage).filter_by(id=msg_id).first() is None


def test_chat_session_cascade_delete_on_user(db_session, base_data):
    user = base_data["user"]
    lesson = base_data["lesson"]

    session = ChatSession(
        user_id=user.id,
        lesson_id=lesson.id
    )
    db_session.add(session)
    db_session.commit()

    session_id = session.id
    db_session.delete(user)
    db_session.commit()

    assert db_session.query(ChatSession).filter_by(id=session_id).first() is None


# ==============================================================================
# 2. Tests cho Phân hệ Quiz & Làm bài: quizzes, questions, question_options
# ==============================================================================

def test_create_quiz_with_questions_and_options(db_session, base_data):
    topic = base_data["topic"]

    quiz = Quiz(
        topic_id=topic.id,
        title="Trắc nghiệm Kiểm tra Biến và Kiểu dữ liệu",
        difficulty=QuizDifficulty.MEDIUM.value,
        total_questions=1
    )
    db_session.add(quiz)
    db_session.commit()

    question = Question(
        quiz_id=quiz.id,
        content="Kết quả của hàm type(3.14) trong Python là gì?",
        explanation="3.14 là số thực dấu phẩy động nên có kiểu là <class 'float'>."
    )
    db_session.add(question)
    db_session.commit()

    options = [
        QuestionOption(question_id=question.id, opt_label="A", content="<class 'int'>", is_correct=False),
        QuestionOption(question_id=question.id, opt_label="B", content="<class 'float'>", is_correct=True),
        QuestionOption(question_id=question.id, opt_label="C", content="<class 'str'>", is_correct=False),
        QuestionOption(question_id=question.id, opt_label="D", content="<class 'bool'>", is_correct=False),
    ]
    db_session.add_all(options)
    db_session.commit()

    db_session.refresh(quiz)
    assert len(quiz.questions) == 1
    q = quiz.questions[0]
    assert len(q.options) == 4
    correct_opts = [opt for opt in q.options if opt.is_correct]
    assert len(correct_opts) == 1
    assert correct_opts[0].opt_label == "B"


def test_quiz_cascade_delete(db_session, base_data):
    topic = base_data["topic"]

    quiz = Quiz(
        topic_id=topic.id,
        title="Quiz test cascade",
        difficulty=QuizDifficulty.EASY.value,
        total_questions=1
    )
    db_session.add(quiz)
    db_session.commit()

    question = Question(
        quiz_id=quiz.id,
        content="Câu hỏi mẫu",
        explanation="Giải thích"
    )
    db_session.add(question)
    db_session.commit()

    option = QuestionOption(
        question_id=question.id,
        opt_label="A",
        content="Phương án A",
        is_correct=True
    )
    db_session.add(option)
    db_session.commit()

    q_id = question.id
    opt_id = option.id

    db_session.delete(quiz)
    db_session.commit()

    assert db_session.query(Question).filter_by(id=q_id).first() is None
    assert db_session.query(QuestionOption).filter_by(id=opt_id).first() is None


# ==============================================================================
# 3. Tests cho Lượt làm bài thi: quiz_attempts & attempt_answers
# ==============================================================================

def test_quiz_attempt_and_attempt_answers_success(db_session, base_data):
    user = base_data["user"]
    topic = base_data["topic"]

    # 1. Tạo Quiz + Question + Option
    quiz = Quiz(
        topic_id=topic.id,
        title="Mini Quiz",
        difficulty=QuizDifficulty.EASY.value,
        total_questions=1
    )
    db_session.add(quiz)
    db_session.commit()

    question = Question(
        quiz_id=quiz.id,
        content="1 + 1 = ?",
        explanation="1 + 1 = 2"
    )
    db_session.add(question)
    db_session.commit()

    option = QuestionOption(
        question_id=question.id,
        opt_label="A",
        content="2",
        is_correct=True
    )
    db_session.add(option)
    db_session.commit()

    # 2. Tạo QuizAttempt
    attempt = QuizAttempt(
        quiz_id=quiz.id,
        user_id=user.id,
        score=Decimal("100.00"),
        duration_sec=35,
        status=QuizAttemptStatus.SUBMITTED.value
    )
    db_session.add(attempt)
    db_session.commit()

    # 3. Tạo AttemptAnswer
    answer = AttemptAnswer(
        attempt_id=attempt.id,
        question_id=question.id,
        selected_option_id=option.id
    )
    db_session.add(answer)
    db_session.commit()

    db_session.refresh(attempt)
    assert attempt.id is not None
    assert attempt.score == Decimal("100.00")
    assert attempt.duration_sec == 35
    assert len(attempt.answers) == 1
    assert attempt.answers[0].selected_option_id == option.id
    assert attempt.answers[0].selected_option.content == "2"


def test_attempt_cascade_delete(db_session, base_data):
    user = base_data["user"]
    topic = base_data["topic"]

    quiz = Quiz(
        topic_id=topic.id,
        title="Quiz test cascade attempt",
        difficulty=QuizDifficulty.EASY.value,
        total_questions=1
    )
    db_session.add(quiz)
    db_session.commit()

    question = Question(quiz_id=quiz.id, content="Q", explanation="E")
    db_session.add(question)
    db_session.commit()

    attempt = QuizAttempt(
        quiz_id=quiz.id,
        user_id=user.id,
        score=Decimal("80.00"),
        duration_sec=40
    )
    db_session.add(attempt)
    db_session.commit()

    answer = AttemptAnswer(
        attempt_id=attempt.id,
        question_id=question.id,
        selected_option_id=None
    )
    db_session.add(answer)
    db_session.commit()

    ans_id = answer.id
    db_session.delete(attempt)
    db_session.commit()

    assert db_session.query(AttemptAnswer).filter_by(id=ans_id).first() is None

