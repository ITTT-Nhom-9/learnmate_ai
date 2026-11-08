from datetime import datetime

from pydantic import BaseModel, ConfigDict


# ------------------------------------------------------------------------------
# GET /courses
# ------------------------------------------------------------------------------

class CourseSummary(BaseModel):
    id: int
    code: str
    title: str
    description: str | None = None
    status: str
    lesson_count: int
    topic_count: int
    is_enrolled: bool
    enrolled_at: datetime | None = None


class CourseListResponse(BaseModel):
    total: int
    items: list[CourseSummary]


# ------------------------------------------------------------------------------
# GET /courses/{id}
# ------------------------------------------------------------------------------

class TopicItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None


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
    lesson_count: int
    topic_count: int
    is_enrolled: bool
    enrolled_at: datetime | None = None
    lessons: list[LessonDetail]


# ------------------------------------------------------------------------------
# POST /courses/{id}/enroll
# ------------------------------------------------------------------------------

class EnrollmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    enrollment_id: int
    user_id: int
    course_id: int
    enrolled_at: datetime
    message: str = "Ghi danh môn học thành công"
