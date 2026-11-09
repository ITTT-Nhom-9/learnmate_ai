from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.course import Course, CourseStatus, Enrollment, Lesson, Topic
from app.models.user import User


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
        self, user: User, page: int = 1, limit: int = 10
    ) -> tuple[list[tuple[Course, CourseStats, Enrollment | None]], int]:
        """Tra ve (cac mon cua trang hien tai, tong so mon ACTIVE)."""
        active = Course.status == CourseStatus.ACTIVE.value
        total = self.db.scalar(select(func.count(Course.id)).where(active)) or 0
        courses = self.db.scalars(
            select(Course)
            .where(active)
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
        course = self.db.scalar(
            select(Course)
            .where(Course.id == course_id, Course.status == CourseStatus.ACTIVE.value)
            .options(
                selectinload(Course.lessons).selectinload(Lesson.topics),
                selectinload(Course.lessons).selectinload(Lesson.contents),
            )
        )
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
    def get_lesson_detail(self, course_id: int, lesson_id: int) -> Lesson:
        lesson = self.db.scalar(
            select(Lesson)
            .join(Course, Course.id == Lesson.course_id)
            .where(
                Lesson.id == lesson_id,
                Lesson.course_id == course_id,
                Course.status == CourseStatus.ACTIVE.value,
            )
            .options(selectinload(Lesson.topics), selectinload(Lesson.contents))
        )
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


def enrolled_at_of(enrollment: Enrollment | None) -> datetime | None:
    return enrollment.enrolled_at if enrollment is not None else None
