from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.course import (
    CourseDetailResponse,
    CourseListResponse,
    CourseSummary,
    EnrollmentResponse,
    LessonDetail,
)
from app.services.course_service import CourseError, CourseService, enrolled_at_of

router = APIRouter(prefix="/courses", tags=["Courses"])


def _to_http(exc: CourseError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.message)


@router.get(
    "",
    response_model=CourseListResponse,
    summary="API-05: Lấy danh sách toàn bộ môn học (kèm số bài, số chủ đề, trạng thái ghi danh)",
)
def list_courses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = CourseService(db).list_courses(current_user)
    items = [
        CourseSummary(
            id=course.id,
            code=course.code,
            title=course.title,
            description=course.description,
            status=course.status,
            lesson_count=stats.lesson_count,
            topic_count=stats.topic_count,
            is_enrolled=enrollment is not None,
            enrolled_at=enrolled_at_of(enrollment),
        )
        for course, stats, enrollment in rows
    ]
    return CourseListResponse(total=len(items), items=items)


@router.get(
    "/{course_id}",
    response_model=CourseDetailResponse,
    summary="API-06: Xem chi tiết môn học, cây bài học và các chủ đề kiến thức",
)
def get_course_detail(
    course_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        course, stats, enrollment = CourseService(db).get_course_detail(course_id, current_user)
    except CourseError as exc:
        raise _to_http(exc)
    return CourseDetailResponse(
        id=course.id,
        code=course.code,
        title=course.title,
        description=course.description,
        status=course.status,
        lesson_count=stats.lesson_count,
        topic_count=stats.topic_count,
        is_enrolled=enrollment is not None,
        enrolled_at=enrolled_at_of(enrollment),
        lessons=[LessonDetail.model_validate(lesson) for lesson in course.lessons],
    )


@router.post(
    "/{course_id}/enroll",
    response_model=EnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="API-07: Sinh viên ghi danh tham gia môn học (UNIQUE user_id + course_id)",
)
def enroll_course(
    course_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        enrollment = CourseService(db).enroll(course_id, current_user)
    except CourseError as exc:
        raise _to_http(exc)
    return EnrollmentResponse(
        enrollment_id=enrollment.id,
        user_id=enrollment.user_id,
        course_id=enrollment.course_id,
        enrolled_at=enrollment.enrolled_at,
    )
