"""Router API Thống kê tiến độ học tập & Điểm Radar (TK-21 / Phân hệ 6, UC-07).

Endpoints:
- GET /api/v1/progress/summary?course_id=: % hoàn thành môn, thẻ chỉ số, cảnh báo đỏ, lịch sử làm bài.
- GET /api/v1/progress/radar?course_id=&max_axes=6: Điểm năng lực theo chủ đề để vẽ biểu đồ Radar.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.progress import ProgressSummaryResponse, RadarResponse
from app.services.course_service import CourseError
from app.services.progress_service import DEFAULT_RADAR_AXES, ProgressService

router = APIRouter(prefix="/progress", tags=["Progress"])


def _to_http(exc: CourseError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.message)


@router.get(
    "/summary",
    response_model=ProgressSummaryResponse,
    summary="Tổng quan tiến độ môn học: % hoàn thành, thẻ chỉ số, chủ đề yếu (Alert Red)",
    description=(
        "- `overall_progress_pct`: trung bình Mastery của mọi chủ đề trong môn (chủ đề chưa học = 0%).\n"
        "- `weak_topics`: chủ đề đã luyện tập có Mastery < 60% (BR-08), xếp từ yếu nhất.\n"
        "- `recent_attempts`: 10 lượt nộp bài gần nhất trong môn.\n\n"
        "Lỗi: 404 nếu môn không tồn tại/đã ẩn, 403 nếu sinh viên chưa ghi danh."
    ),
)
def get_progress_summary(
    course_id: int = Query(..., ge=1, description="ID môn học cần xem tiến độ"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return ProgressService(db).get_summary(current_user, course_id)
    except CourseError as exc:
        raise _to_http(exc)


@router.get(
    "/radar",
    response_model=RadarResponse,
    summary="Điểm năng lực Radar (mặc định 6 trục, mỗi trục là một chủ đề)",
    description=(
        "Nếu môn có nhiều chủ đề hơn `max_axes`, ưu tiên chủ đề luyện tập gần nhất rồi lấp bằng "
        "chủ đề chưa học theo thứ tự giáo trình (`truncated = true`). Các trục luôn theo thứ tự "
        "giáo trình. `labels`/`scores` có thể truyền thẳng vào Chart.js."
    ),
)
def get_progress_radar(
    course_id: int = Query(..., ge=1, description="ID môn học"),
    max_axes: int = Query(DEFAULT_RADAR_AXES, ge=3, le=12, description="Số trục tối đa (3-12)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return ProgressService(db).get_radar(current_user, course_id, max_axes=max_axes)
    except CourseError as exc:
        raise _to_http(exc)
