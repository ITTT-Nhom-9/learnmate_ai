from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.course import ContentType, Course, CourseStatus, Enrollment, Lesson, LessonContent, Topic
from app.models.user import User
from app.schemas.course import (
    ContentCreate,
    ContentUpdate,
    CourseCreate,
    CourseUpdate,
    LessonCreate,
    LessonUpdate,
    TopicCreate,
    TopicUpdate,
)


class CourseError(Exception):
    """Loi nghiep vu mon hoc, router se anh xa sang HTTP status tuong ung."""

    status_code: int = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class CourseNotFoundError(CourseError):
    status_code = 404


class AlreadyEnrolledError(CourseError):
    status_code = 409


class DuplicateCourseError(CourseError):
    status_code = 409


@dataclass
class CourseStats:
    lesson_count: int = 0
    topic_count: int = 0


class CourseService:
    def __init__(self, db: Session):
        self.db = db

    # --------------------------------------------------------------------------
    # Danh sach mon hoc (FR-CM-01)
    # --------------------------------------------------------------------------
    def list_courses(
        self, user: User, page: int = 1, limit: int = 10, include_inactive: bool = False
    ) -> tuple[list[tuple[Course, CourseStats, Enrollment | None]], int]:
        """Tra ve danh sach mon hoc (phan trang).
        Mac dinh chi hien thi cac mon ACTIVE.
        Chi khi include_inactive=True (Admin) moi lay ca mon INACTIVE."""
        condition = True if include_inactive else (Course.status == CourseStatus.ACTIVE.value)
        total = self.db.scalar(select(func.count(Course.id)).where(condition)) or 0
        courses = self.db.scalars(
            select(Course)
            .where(condition)
            .order_by(Course.code, Course.id)
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
        if not courses:
            return [], total

        course_ids = [c.id for c in courses]
        stats = self._stats_for(course_ids)
        enrollments = {
            e.course_id: e
            for e in self.db.scalars(
                select(Enrollment).where(
                    Enrollment.user_id == user.id,
                    Enrollment.course_id.in_(course_ids),
                )
            )
        }
        return [(c, stats.get(c.id, CourseStats()), enrollments.get(c.id)) for c in courses], total

    # --------------------------------------------------------------------------
    # Chi tiet mon hoc: cay bai hoc + chu de + noi dung (FR-CM-03)
    # --------------------------------------------------------------------------
    def get_course_detail(self, course_id: int, user: User) -> tuple[Course, CourseStats, Enrollment | None]:
        is_admin = getattr(user, "role", None) == "ADMIN"
        stmt = (
            select(Course)
            .where(Course.id == course_id)
            .options(
                selectinload(Course.lessons).selectinload(Lesson.topics),
                selectinload(Course.lessons).selectinload(Lesson.contents),
            )
        )
        if not is_admin:
            stmt = stmt.where(Course.status == CourseStatus.ACTIVE.value)
        course = self.db.scalar(stmt)
        if course is None:
            raise CourseNotFoundError("Môn học không tồn tại")

        stats = CourseStats(
            lesson_count=len(course.lessons),
            topic_count=sum(len(lesson.topics) for lesson in course.lessons),
        )
        return course, stats, self._get_enrollment(user.id, course.id)

    # --------------------------------------------------------------------------
    # Chi tiet 1 bai hoc: chu de + noi dung ly thuyet
    # --------------------------------------------------------------------------
    def get_lesson_detail(self, course_id: int, lesson_id: int, user: User | None = None) -> Lesson:
        is_admin = getattr(user, "role", None) == "ADMIN" if user else False
        stmt = (
            select(Lesson)
            .join(Course, Course.id == Lesson.course_id)
            .where(
                Lesson.id == lesson_id,
                Lesson.course_id == course_id,
            )
            .options(selectinload(Lesson.topics), selectinload(Lesson.contents))
        )
        if not is_admin:
            stmt = stmt.where(Course.status == CourseStatus.ACTIVE.value)
        lesson = self.db.scalar(stmt)
        if lesson is None:
            raise CourseNotFoundError("Bài học không tồn tại")
        return lesson

    # --------------------------------------------------------------------------
    # Ghi danh mon hoc (FR-CM-02) - rang buoc UNIQUE(user_id, course_id)
    # --------------------------------------------------------------------------
    def enroll(self, course_id: int, user: User) -> Enrollment:
        course = self.db.scalar(
            select(Course).where(Course.id == course_id, Course.status == CourseStatus.ACTIVE.value)
        )
        if course is None:
            raise CourseNotFoundError("Môn học không tồn tại")

        # Kiem tra som de tra loi than thien, khong ton 1 lan INSERT that bai
        if self._get_enrollment(user.id, course.id) is not None:
            raise AlreadyEnrolledError("Bạn đã ghi danh môn học này")

        enrollment = Enrollment(user_id=user.id, course_id=course.id)
        self.db.add(enrollment)
        try:
            self.db.commit()
        except IntegrityError:
            # 2 request ghi danh dong thoi -> UNIQUE uq_user_course chan ban ghi trung
            self.db.rollback()
            raise AlreadyEnrolledError("Bạn đã ghi danh môn học này")
        self.db.refresh(enrollment)
        return enrollment

    # --------------------------------------------------------------------------
    # Helpers
    # --------------------------------------------------------------------------
    def _get_enrollment(self, user_id: int, course_id: int) -> Enrollment | None:
        return self.db.scalar(
            select(Enrollment).where(Enrollment.user_id == user_id, Enrollment.course_id == course_id)
        )

    def _stats_for(self, course_ids: list[int]) -> dict[int, CourseStats]:
        """Dem so bai hoc va so chu de cua nhieu mon trong 1 truy van (tranh N+1)."""
        rows = self.db.execute(
            select(
                Lesson.course_id,
                func.count(func.distinct(Lesson.id)),
                func.count(Topic.id),
            )
            .outerjoin(Topic, Topic.lesson_id == Lesson.id)
            .where(Lesson.course_id.in_(course_ids))
            .group_by(Lesson.course_id)
        ).all()
        return {cid: CourseStats(lesson_count=lc, topic_count=tc) for cid, lc, tc in rows}

    # --------------------------------------------------------------------------
    # CRUD Môn học dành cho Quản trị viên (Admin Course CRUD)
    # --------------------------------------------------------------------------
    def create_course(self, payload: CourseCreate, admin: User) -> Course:
        code_upper = payload.code.strip().upper()
        existing = self.db.scalar(select(Course).where(Course.code == code_upper))
        if existing:
            raise DuplicateCourseError(f"Mã môn học '{code_upper}' đã tồn tại trong hệ thống")

        course = Course(
            code=code_upper,
            title=payload.title.strip(),
            description=payload.description.strip() if payload.description else None,
            status=payload.status or CourseStatus.ACTIVE.value,
        )
        self.db.add(course)
        self.db.flush()

        # Tạo sẵn Bài 1 và 1 Chủ đề mở đầu để tiện cho Admin soạn nội dung ngay
        lesson = Lesson(
            course_id=course.id,
            title="Bài 1: Tổng quan môn học",
            order_index=1,
        )
        self.db.add(lesson)
        self.db.flush()

        topic = Topic(
            lesson_id=lesson.id,
            name="Chủ đề 1: Giới thiệu nội dung và mục tiêu",
            description=f"Giới thiệu tổng quan về chương trình học môn {course.title}",
        )
        self.db.add(topic)

        content = LessonContent(
            lesson_id=lesson.id,
            content_type=ContentType.MARKDOWN.value,
            body=f"# Chào mừng bạn đến với môn học {course.title} ({course.code})\n\nNội dung bài học đang được biên soạn.",
        )
        self.db.add(content)

        self.db.commit()
        self.db.refresh(course)
        return course

    def update_course(self, course_id: int, payload: CourseUpdate, admin: User) -> Course:
        course = self.db.get(Course, course_id)
        if not course:
            raise CourseNotFoundError("Môn học không tồn tại")

        if payload.code is not None:
            new_code = payload.code.strip().upper()
            if new_code != course.code:
                dup = self.db.scalar(select(Course).where(Course.code == new_code, Course.id != course_id))
                if dup:
                    raise DuplicateCourseError(f"Mã môn học '{new_code}' đã được sử dụng")
                course.code = new_code

        if payload.title is not None:
            course.title = payload.title.strip()
        if payload.description is not None:
            course.description = payload.description.strip() if payload.description else None
        if payload.status is not None:
            course.status = payload.status

        self.db.commit()
        self.db.refresh(course)
        return course

    def delete_course(self, course_id: int, admin: User) -> dict:
        course = self.db.get(Course, course_id)
        if not course:
            raise CourseNotFoundError("Môn học không tồn tại")

        enrollment_count = self.db.scalar(
            select(func.count(Enrollment.id)).where(Enrollment.course_id == course_id)
        ) or 0

        if enrollment_count > 0:
            course.status = CourseStatus.INACTIVE.value
            self.db.commit()
            return {
                "message": f"Môn học {course.code} đã có sinh viên ghi danh nên được chuyển sang trạng thái Lưu trữ (INACTIVE) để bảo toàn dữ liệu.",
                "action": "ARCHIVED",
                "course_id": course.id,
            }
        else:
            self.db.delete(course)
            self.db.commit()
            return {
                "message": f"Đã xóa hoàn toàn môn học {course.code} khỏi cơ sở dữ liệu.",
                "action": "DELETED",
                "course_id": course_id,
            }

    # --------------------------------------------------------------------------
    # CRUD Bài học (Lessons)
    # --------------------------------------------------------------------------
    def create_lesson(self, course_id: int, payload: LessonCreate, admin: User) -> Lesson:
        course = self.db.get(Course, course_id)
        if not course:
            raise CourseNotFoundError("Môn học không tồn tại")

        if not payload.order_index or payload.order_index <= 0:
            max_order = self.db.scalar(
                select(func.max(Lesson.order_index)).where(Lesson.course_id == course_id)
            ) or 0
            order_index = max_order + 1
        else:
            order_index = payload.order_index

        lesson = Lesson(
            course_id=course_id,
            title=payload.title.strip(),
            order_index=order_index,
        )
        self.db.add(lesson)
        self.db.commit()
        self.db.refresh(lesson)
        return lesson

    def update_lesson(self, course_id: int, lesson_id: int, payload: LessonUpdate, admin: User) -> Lesson:
        lesson = self.db.scalar(
            select(Lesson).where(Lesson.id == lesson_id, Lesson.course_id == course_id)
        )
        if not lesson:
            raise CourseNotFoundError("Bài học không tồn tại trong môn học này")

        if payload.title is not None:
            lesson.title = payload.title.strip()
        if payload.order_index is not None:
            lesson.order_index = payload.order_index

        self.db.commit()
        self.db.refresh(lesson)
        return lesson

    def delete_lesson(self, course_id: int, lesson_id: int, admin: User) -> dict:
        lesson = self.db.scalar(
            select(Lesson).where(Lesson.id == lesson_id, Lesson.course_id == course_id)
        )
        if not lesson:
            raise CourseNotFoundError("Bài học không tồn tại trong môn học này")

        self.db.delete(lesson)
        self.db.commit()
        return {"message": "Đã xóa bài học thành công", "lesson_id": lesson_id}

    # --------------------------------------------------------------------------
    # CRUD Chủ đề (Topics)
    # --------------------------------------------------------------------------
    def create_topic(self, course_id: int, lesson_id: int, payload: TopicCreate, admin: User) -> Topic:
        lesson = self.db.scalar(
            select(Lesson).where(Lesson.id == lesson_id, Lesson.course_id == course_id)
        )
        if not lesson:
            raise CourseNotFoundError("Bài học không tồn tại trong môn học này")

        topic = Topic(
            lesson_id=lesson_id,
            name=payload.name.strip(),
            description=payload.description.strip() if payload.description else None,
        )
        self.db.add(topic)
        self.db.commit()
        self.db.refresh(topic)
        return topic

    def update_topic(self, course_id: int, topic_id: int, payload: TopicUpdate, admin: User) -> Topic:
        topic = self.db.scalar(
            select(Topic)
            .join(Lesson, Lesson.id == Topic.lesson_id)
            .where(Topic.id == topic_id, Lesson.course_id == course_id)
        )
        if not topic:
            raise CourseNotFoundError("Chủ đề không tồn tại trong môn học này")

        if payload.name is not None:
            topic.name = payload.name.strip()
        if payload.description is not None:
            topic.description = payload.description.strip() if payload.description else None

        self.db.commit()
        self.db.refresh(topic)
        return topic

    def delete_topic(self, course_id: int, topic_id: int, admin: User) -> dict:
        topic = self.db.scalar(
            select(Topic)
            .join(Lesson, Lesson.id == Topic.lesson_id)
            .where(Topic.id == topic_id, Lesson.course_id == course_id)
        )
        if not topic:
            raise CourseNotFoundError("Chủ đề không tồn tại trong môn học này")

        self.db.delete(topic)
        self.db.commit()
        return {"message": "Đã xóa chủ đề thành công", "topic_id": topic_id}

    # --------------------------------------------------------------------------
    # CRUD Nội dung bài học (Lesson Contents)
    # --------------------------------------------------------------------------
    def save_lesson_content(
        self,
        course_id: int,
        lesson_id: int,
        payload: ContentCreate,
        content_id: int | None = None,
        admin: User = None,
    ) -> LessonContent:
        lesson = self.db.scalar(
            select(Lesson).where(Lesson.id == lesson_id, Lesson.course_id == course_id)
        )
        if not lesson:
            raise CourseNotFoundError("Bài học không tồn tại trong môn học này")

        if content_id:
            content = self.db.scalar(
                select(LessonContent).where(LessonContent.id == content_id, LessonContent.lesson_id == lesson_id)
            )
            if not content:
                raise CourseNotFoundError("Nội dung bài học không tồn tại")
            content.body = payload.body
            if payload.content_type:
                content.content_type = payload.content_type
        else:
            content = self.db.scalar(
                select(LessonContent).where(LessonContent.lesson_id == lesson_id).order_by(LessonContent.id)
            )
            if content:
                content.body = payload.body
                if payload.content_type:
                    content.content_type = payload.content_type
            else:
                content = LessonContent(
                    lesson_id=lesson_id,
                    content_type=payload.content_type or ContentType.MARKDOWN.value,
                    body=payload.body,
                )
                self.db.add(content)

        self.db.commit()
        self.db.refresh(content)
        return content


def enrolled_at_of(enrollment: Enrollment | None) -> datetime | None:
    return enrollment.enrolled_at if enrollment is not None else None
