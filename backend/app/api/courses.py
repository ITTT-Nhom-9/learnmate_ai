from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.models.user import User
from app.schemas.course import (
    ContentCreate,
    ContentUpdate,
    CourseActionResponse,
    CourseCreate,
    CourseDetailResponse,
    CourseListResponse,
    CourseSummary,
    CourseUpdate,
    EnrollmentResponse,
    LessonCreate,
    LessonDetail,
    LessonDetailResponse,
    LessonUpdate,
    TopicCreate,
    TopicItem,
    TopicUpdate,
)
from app.services.course_service import CourseError, CourseService, enrolled_at_of
from app.services.mastery_service import MasteryService

router = APIRouter(prefix="/courses", tags=["Courses"])


def _to_http(exc: CourseError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.message)


@router.get(
    "",
    response_model=CourseListResponse,
    summary="API-05: Lấy danh sách môn học (phân trang, kèm số bài, tiến độ, trạng thái ghi danh)",
)
def list_courses(
    page: int = Query(1, ge=1, description="Trang hiện tại (bắt đầu từ 1)"),
    limit: int = Query(10, ge=1, le=100, description="Số môn học mỗi trang (tối đa 100)"),
    include_inactive: bool = Query(False, description="Chỉ dành cho Admin: bao gồm cả môn INACTIVE"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    is_admin = getattr(current_user, "role", None) == "ADMIN"
    allow_inactive = is_admin and include_inactive
    rows, total = CourseService(db).list_courses(
        current_user, page=page, limit=limit, include_inactive=allow_inactive
    )
    mastery_service = MasteryService(db)
    courses = [
        CourseSummary(
            id=course.id,
            code=course.code,
            title=course.title,
            description=course.description,
            status=course.status,
            total_lessons=stats.lesson_count,
            topic_count=stats.topic_count,
            progress_pct=mastery_service.calculate_course_progress(current_user.id, course.id) if enrollment else 0.0,
            is_enrolled=enrollment is not None,
            enrolled_at=enrolled_at_of(enrollment),
        )
        for course, stats, enrollment in rows
    ]
    return CourseListResponse(courses=courses, total=total, page=page, limit=limit)


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

    mastery_service = MasteryService(db)
    progress_pct = (
        mastery_service.calculate_course_progress(current_user.id, course.id)
        if enrollment
        else 0.0
    )
    mastery_map = (
        mastery_service.get_course_topics_mastery_map(current_user.id, course.id)
        if enrollment
        else {}
    )

    # Đính kèm điểm Mastery thực tế của từng chủ đề cho sinh viên
    for lesson in course.lessons:
        for topic in lesson.topics:
            setattr(topic, "mastery_score", mastery_map.get(topic.id, 0.0))

    return CourseDetailResponse(
        id=course.id,
        code=course.code,
        title=course.title,
        description=course.description,
        status=course.status,
        total_lessons=stats.lesson_count,
        topic_count=stats.topic_count,
        progress_pct=progress_pct,
        is_enrolled=enrollment is not None,
        enrolled_at=enrolled_at_of(enrollment),
        lessons=[LessonDetail.model_validate(lesson) for lesson in course.lessons],
    )


@router.get(
    "/{course_id}/lessons/{lesson_id}",
    response_model=LessonDetailResponse,
    summary="Xem chi tiết một bài học: các chủ đề và nội dung lý thuyết",
)
def get_lesson_detail(
    course_id: int = Path(..., ge=1),
    lesson_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        lesson = CourseService(db).get_lesson_detail(course_id, lesson_id, current_user)
    except CourseError as exc:
        raise _to_http(exc)
    return LessonDetailResponse.model_validate(lesson)


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


# ------------------------------------------------------------------------------
# API Quản trị viên: Thêm, sửa, xóa môn học (Admin Course CRUD)
# ------------------------------------------------------------------------------

@router.post(
    "",
    response_model=CourseDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Admin: Tạo môn học mới (tự động tạo bài 1 và chủ đề mở đầu)",
)
def create_course(
    payload: CourseCreate,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        course = CourseService(db).create_course(payload, current_admin)
        detail, stats, _ = CourseService(db).get_course_detail(course.id, current_admin)
    except CourseError as exc:
        raise _to_http(exc)

    return CourseDetailResponse(
        id=detail.id,
        code=detail.code,
        title=detail.title,
        description=detail.description,
        status=detail.status,
        total_lessons=stats.lesson_count,
        topic_count=stats.topic_count,
        progress_pct=0.0,
        is_enrolled=False,
        enrolled_at=None,
        lessons=[LessonDetail.model_validate(l) for l in detail.lessons],
    )


@router.put(
    "/{course_id}",
    response_model=CourseDetailResponse,
    summary="Admin: Cập nhật thông tin môn học (mã môn, tên môn, mô tả, trạng thái)",
)
def update_course(
    course_id: int = Path(..., ge=1),
    payload: CourseUpdate = ...,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        CourseService(db).update_course(course_id, payload, current_admin)
        detail, stats, _ = CourseService(db).get_course_detail(course_id, current_admin)
    except CourseError as exc:
        raise _to_http(exc)

    return CourseDetailResponse(
        id=detail.id,
        code=detail.code,
        title=detail.title,
        description=detail.description,
        status=detail.status,
        total_lessons=stats.lesson_count,
        topic_count=stats.topic_count,
        progress_pct=0.0,
        is_enrolled=False,
        enrolled_at=None,
        lessons=[LessonDetail.model_validate(l) for l in detail.lessons],
    )


@router.delete(
    "/{course_id}",
    response_model=CourseActionResponse,
    summary="Admin: Xóa hoặc chuyển lưu trữ an toàn môn học",
)
def delete_course(
    course_id: int = Path(..., ge=1),
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        res = CourseService(db).delete_course(course_id, current_admin)
    except CourseError as exc:
        raise _to_http(exc)
    return CourseActionResponse(
        success=True,
        message=res["message"],
        action=res["action"],
        data={"course_id": res["course_id"]},
    )


# ------------------------------------------------------------------------------
# API Quản trị viên: CRUD Bài học (Lessons)
# ------------------------------------------------------------------------------

@router.post(
    "/{course_id}/lessons",
    response_model=LessonDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Admin: Tạo bài học mới trong môn học",
)
def create_lesson(
    course_id: int = Path(..., ge=1),
    payload: LessonCreate = ...,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        lesson = CourseService(db).create_lesson(course_id, payload, current_admin)
        res = CourseService(db).get_lesson_detail(course_id, lesson.id, current_admin)
    except CourseError as exc:
        raise _to_http(exc)
    return LessonDetailResponse.model_validate(res)


@router.put(
    "/{course_id}/lessons/{lesson_id}",
    response_model=LessonDetailResponse,
    summary="Admin: Sửa thông tin bài học (tiêu đề, thứ tự)",
)
def update_lesson(
    course_id: int = Path(..., ge=1),
    lesson_id: int = Path(..., ge=1),
    payload: LessonUpdate = ...,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        lesson = CourseService(db).update_lesson(course_id, lesson_id, payload, current_admin)
        res = CourseService(db).get_lesson_detail(course_id, lesson.id, current_admin)
    except CourseError as exc:
        raise _to_http(exc)
    return LessonDetailResponse.model_validate(res)


@router.delete(
    "/{course_id}/lessons/{lesson_id}",
    response_model=CourseActionResponse,
    summary="Admin: Xóa bài học",
)
def delete_lesson(
    course_id: int = Path(..., ge=1),
    lesson_id: int = Path(..., ge=1),
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        res = CourseService(db).delete_lesson(course_id, lesson_id, current_admin)
    except CourseError as exc:
        raise _to_http(exc)
    return CourseActionResponse(success=True, message=res["message"], data={"lesson_id": res["lesson_id"]})


# ------------------------------------------------------------------------------
# API Quản trị viên: CRUD Chủ đề (Topics)
# ------------------------------------------------------------------------------

@router.post(
    "/{course_id}/lessons/{lesson_id}/topics",
    response_model=TopicItem,
    status_code=status.HTTP_201_CREATED,
    summary="Admin: Thêm chủ đề mới vào bài học",
)
def create_topic(
    course_id: int = Path(..., ge=1),
    lesson_id: int = Path(..., ge=1),
    payload: TopicCreate = ...,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        topic = CourseService(db).create_topic(course_id, lesson_id, payload, current_admin)
    except CourseError as exc:
        raise _to_http(exc)
    return TopicItem.model_validate(topic)


@router.put(
    "/{course_id}/topics/{topic_id}",
    response_model=TopicItem,
    summary="Admin: Cập nhật chủ đề kiến thức",
)
def update_topic(
    course_id: int = Path(..., ge=1),
    topic_id: int = Path(..., ge=1),
    payload: TopicUpdate = ...,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        topic = CourseService(db).update_topic(course_id, topic_id, payload, current_admin)
    except CourseError as exc:
        raise _to_http(exc)
    return TopicItem.model_validate(topic)


@router.delete(
    "/{course_id}/topics/{topic_id}",
    response_model=CourseActionResponse,
    summary="Admin: Xóa chủ đề kiến thức",
)
def delete_topic(
    course_id: int = Path(..., ge=1),
    topic_id: int = Path(..., ge=1),
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        res = CourseService(db).delete_topic(course_id, topic_id, current_admin)
    except CourseError as exc:
        raise _to_http(exc)
    return CourseActionResponse(success=True, message=res["message"], data={"topic_id": res["topic_id"]})


# ------------------------------------------------------------------------------
# API Quản trị viên: Soạn / Chỉnh sửa nội dung lý thuyết bài học (Contents)
# ------------------------------------------------------------------------------

@router.post(
    "/{course_id}/lessons/{lesson_id}/contents",
    response_model=LessonDetailResponse,
    summary="Admin: Thêm hoặc cập nhật nội dung lý thuyết Markdown cho bài học",
)
def save_lesson_content(
    course_id: int = Path(..., ge=1),
    lesson_id: int = Path(..., ge=1),
    payload: ContentCreate = ...,
    content_id: int | None = Query(None, description="ID nội dung nếu sửa cụ thể"),
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        CourseService(db).save_lesson_content(
            course_id=course_id,
            lesson_id=lesson_id,
            payload=payload,
            content_id=content_id,
            admin=current_admin,
        )
        res = CourseService(db).get_lesson_detail(course_id, lesson_id, current_admin)
    except CourseError as exc:
        raise _to_http(exc)
    return LessonDetailResponse.model_validate(res)
