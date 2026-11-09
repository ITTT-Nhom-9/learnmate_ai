from datetime import datetime

from pydantic import BaseModel, ConfigDict

# Ten truong bam sat sheet "Dac ta API & Figma UI UX" (Project_LearnMate_AI.xlsx).
# progress_pct / mastery_score: chua co bang mastery (Phan he hoc tap thich ung),
# tam thoi tra 0.0 de Frontend hien thi thanh tien do / mau node chu de.


# ------------------------------------------------------------------------------
# API-05: GET /courses?page=&limit=
# ------------------------------------------------------------------------------

class CourseSummary(BaseModel):
    id: int
    code: str
    title: str
    description: str | None = None
    status: str
    total_lessons: int
    topic_count: int
    progress_pct: float = 0.0
    is_enrolled: bool
    enrolled_at: datetime | None = None


class CourseListResponse(BaseModel):
    courses: list[CourseSummary]
    total: int
    page: int
    limit: int


# ------------------------------------------------------------------------------
# API-06: GET /courses/{id}
# ------------------------------------------------------------------------------

class TopicItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    mastery_score: float = 0.0


class LessonContentItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    content_type: str
    body: str


class LessonDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    order_index: int
    topics: list[TopicItem]
    contents: list[LessonContentItem]


class CourseDetailResponse(BaseModel):
    id: int
    code: str
    title: str
    description: str | None = None
    status: str
    total_lessons: int
    topic_count: int
    progress_pct: float = 0.0
    is_enrolled: bool
    enrolled_at: datetime | None = None
    lessons: list[LessonDetail]


# ------------------------------------------------------------------------------
# GET /courses/{id}/lessons/{lesson_id}
# ------------------------------------------------------------------------------

class LessonDetailResponse(LessonDetail):
    course_id: int


# ------------------------------------------------------------------------------
# API-07: POST /courses/{id}/enroll
# ------------------------------------------------------------------------------

class EnrollmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    enrollment_id: int
    user_id: int
    course_id: int
    status: str = "ACTIVE"
    enrolled_at: datetime
    message: str = "Ghi danh môn học thành công"
