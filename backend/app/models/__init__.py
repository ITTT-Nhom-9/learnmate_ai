from app.core.database import Base
from app.models.user import User, RefreshToken, UserRole, UserStatus
from app.models.course import (
    Course,
    Enrollment,
    Lesson,
    Topic,
    LessonContent,
    CourseStatus,
    ContentType,
)
from app.models.chat import (
    ChatSession,
    ChatMessage,
    ChatMode,
    ChatRole,
    ChatSessionStatus,
)
from app.models.quiz import (
    Quiz,
    Question,
    QuestionOption,
    QuizAttempt,
    AttemptAnswer,
    QuizDifficulty,
    QuizAttemptStatus,
)
from app.models.mastery import (
    TopicMastery,
    UserTopicMastery,
    MasteryStatus,
    Recommendation,
    RecommendationAction,
    RecommendationStatus,
    LearningEvent,
    StudentActivityLog,
    LearningEventType,
)
from app.models.rag import (
    Document,
    DocumentChunk,
    AIRequestLog,
    AIFeature,
    AIProvider,
    PromptTemplate,
    SystemSetting,
)

__all__ = [
    "Base",
    # User models
    "User",
    "RefreshToken",
    "UserRole",
    "UserStatus",
    # Course models
    "Course",
    "Enrollment",
    "Lesson",
    "Topic",
    "LessonContent",
    "CourseStatus",
    "ContentType",
    # Chat models
    "ChatSession",
    "ChatMessage",
    "ChatMode",
    "ChatRole",
    "ChatSessionStatus",
    # Quiz models
    "Quiz",
    "Question",
    "QuestionOption",
    "QuizAttempt",
    "AttemptAnswer",
    "QuizDifficulty",
    "QuizAttemptStatus",
    # Mastery models (TK-19 / Phân hệ 6)
    "TopicMastery",
    "UserTopicMastery",
    "MasteryStatus",
    "Recommendation",
    "RecommendationAction",
    "RecommendationStatus",
    "LearningEvent",
    "StudentActivityLog",
    "LearningEventType",
    # RAG & Admin models (TK-19 / Phân hệ 7 & 8)
    "Document",
    "DocumentChunk",
    "AIRequestLog",
    "AIFeature",
    "AIProvider",
    "PromptTemplate",
    "SystemSetting",
]
