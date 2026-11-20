"""API Endpoints dành riêng cho Quản trị viên (Phân hệ 7: Quản trị | TK-23 / SCR-08).

Các phân hệ chức năng:
1. Quản lý danh sách người dùng (Users):
   - GET /api/v1/admin/users: Danh sách người dùng, tìm kiếm, lọc vai trò/trạng thái, phân trang.
   - GET /api/v1/admin/users/{user_id}: Xem chi tiết thông tin và thống kê học tập/AI của người dùng.
   - PATCH /api/v1/admin/users/{user_id}/status: Khóa / mở khóa tài khoản (thu hồi refresh tokens khi khóa).
   - PATCH /api/v1/admin/users/{user_id}/role: Phân quyền vai trò (STUDENT / ADMIN).
   - PUT /api/v1/admin/users/{user_id}: Cập nhật thông tin tổng hợp người dùng.
   - POST /api/v1/admin/users/{user_id}/lock: Shortcut khóa tài khoản người dùng.
   - POST /api/v1/admin/users/{user_id}/unlock: Shortcut mở khóa tài khoản người dùng.

2. Cấu hình Prompt Templates (Prompts):
   - GET /api/v1/admin/prompts (và alias /api/v1/prompts): Lấy danh sách mẫu prompt.
   - GET /api/v1/admin/prompts/{id} (và alias /api/v1/prompts/{id}): Xem chi tiết mẫu prompt.
   - GET /api/v1/admin/prompts/code/{code}/active: Lấy mẫu prompt đang kích hoạt theo mã code.
   - POST /api/v1/admin/prompts (và alias /api/v1/prompts): Tạo mới mẫu prompt hoặc phiên bản mới (A/B testing).
   - PUT /api/v1/admin/prompts/{id} (và alias /api/v1/prompts/{id}): Chỉnh sửa nội dung / trạng thái kích hoạt mẫu prompt.
   - DELETE /api/v1/admin/prompts/{id} (và alias /api/v1/prompts/{id}): Xóa mẫu prompt.

3. Giám sát AI Logs & Thống kê Chi phí Token (Logs):
   - GET /api/v1/admin/logs (và alias /api/v1/logs): Danh sách nhật ký gọi AI chi tiết kèm chi phí USD/VND.
   - GET /api/v1/admin/logs/tokens (và alias /api/v1/logs/tokens): Báo cáo thống kê token và chi phí vận hành (SDD).
   - POST /api/v1/admin/logs (và alias /api/v1/logs): Ghi log cuộc gọi AI phục vụ kiểm thử và giám sát.
"""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.models.user import User, UserStatus
from app.schemas.admin import (
    UserAdminItem,
    UserAdminDetailResponse,
    UserListResponse,
    UserStatusUpdate,
    UserRoleUpdate,
    UserUpdate,
    PromptTemplateCreate,
    PromptTemplateUpdate,
    PromptTemplateResponse,
    AIRequestLogCreate,
    AIRequestLogItem,
    AIRequestLogListResponse,
    TokenStatsResponse,
)
from app.services.admin_service import AdminError, AdminService

# Router chính dưới tiền tố /admin
router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(require_admin)])

# Routers bí danh (alias) để hỗ trợ gọi trực tiếp /prompts và /logs (theo yêu cầu đề bài TK-23)
prompts_router = APIRouter(prefix="/prompts", tags=["Prompt Templates"])
logs_router = APIRouter(prefix="/logs", tags=["AI Request Logs"])


def _to_http(exc: AdminError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.message)


# ==============================================================================
# 1. QUẢN LÝ DANH SÁCH NGƯỜI DÙNG (/admin/users)
# ==============================================================================

@router.get(
    "/users",
    response_model=UserListResponse,
    summary="Xem danh sách người dùng, tìm kiếm và lọc theo trạng thái/vai trò",
)
def list_users(
    page: int = Query(1, ge=1, description="Số trang hiển thị"),
    page_size: int = Query(20, ge=1, le=100, description="Số lượng bản ghi mỗi trang"),
    search: Optional[str] = Query(None, description="Tìm kiếm theo email hoặc họ tên"),
    role: Optional[str] = Query(None, description="Lọc vai trò: STUDENT | ADMIN"),
    status: Optional[str] = Query(None, description="Lọc trạng thái: ACTIVE | LOCKED"),
    db: Session = Depends(get_db),
):
    try:
        return AdminService(db).list_users(
            page=page, page_size=page_size, search=search, role=role, status=status
        )
    except AdminError as exc:
        raise _to_http(exc)


@router.get(
    "/users/{user_id}",
    response_model=UserAdminDetailResponse,
    summary="Xem thông tin chi tiết một người dùng kèm số liệu học tập/AI",
)
def get_user_detail(
    user_id: int = Path(..., ge=1, description="ID người dùng"),
    db: Session = Depends(get_db),
):
    try:
        return AdminService(db).get_user_detail(user_id)
    except AdminError as exc:
        raise _to_http(exc)


@router.patch(
    "/users/{user_id}/status",
    response_model=UserAdminItem,
    summary="Khóa hoặc mở khóa tài khoản người dùng (thu hồi token nếu khóa)",
)
def update_user_status(
    payload: UserStatusUpdate,
    user_id: int = Path(..., ge=1, description="ID người dùng cần đổi trạng thái"),
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        return AdminService(db).update_user_status(
            current_admin=current_admin,
            target_user_id=user_id,
            new_status=payload.status,
            reason=payload.reason,
        )
    except AdminError as exc:
        raise _to_http(exc)


@router.patch(
    "/users/{user_id}/role",
    response_model=UserAdminItem,
    summary="Phân quyền vai trò người dùng (STUDENT <-> ADMIN)",
)
def update_user_role(
    payload: UserRoleUpdate,
    user_id: int = Path(..., ge=1, description="ID người dùng cần phân quyền"),
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        return AdminService(db).update_user_role(
            current_admin=current_admin,
            target_user_id=user_id,
            new_role=payload.role,
        )
    except AdminError as exc:
        raise _to_http(exc)


@router.put(
    "/users/{user_id}",
    response_model=UserAdminItem,
    summary="Cập nhật thông tin tổng hợp người dùng",
)
def update_user(
    payload: UserUpdate,
    user_id: int = Path(..., ge=1, description="ID người dùng"),
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        return AdminService(db).update_user(
            current_admin=current_admin,
            target_user_id=user_id,
            full_name=payload.full_name,
            role=payload.role,
            status=payload.status,
        )
    except AdminError as exc:
        raise _to_http(exc)


@router.post(
    "/users/{user_id}/lock",
    response_model=UserAdminItem,
    summary="Khóa tài khoản người dùng ngay lập tức",
)
def lock_user_shortcut(
    user_id: int = Path(..., ge=1, description="ID người dùng cần khóa"),
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        return AdminService(db).update_user_status(
            current_admin=current_admin,
            target_user_id=user_id,
            new_status=UserStatus.LOCKED.value,
        )
    except AdminError as exc:
        raise _to_http(exc)


@router.post(
    "/users/{user_id}/unlock",
    response_model=UserAdminItem,
    summary="Mở khóa tài khoản người dùng",
)
def unlock_user_shortcut(
    user_id: int = Path(..., ge=1, description="ID người dùng cần mở khóa"),
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        return AdminService(db).update_user_status(
            current_admin=current_admin,
            target_user_id=user_id,
            new_status=UserStatus.ACTIVE.value,
        )
    except AdminError as exc:
        raise _to_http(exc)


# ==============================================================================
# 2. CẤU HÌNH PROMPT TEMPLATES TRÊN WEB (/admin/prompts & /prompts)
# ==============================================================================

def _list_prompts_impl(
    code: Optional[str],
    is_active: Optional[bool],
    db: Session,
):
    try:
        return AdminService(db).list_prompts(code=code, is_active=is_active)
    except AdminError as exc:
        raise _to_http(exc)


def _get_prompt_impl(prompt_id: int, db: Session):
    try:
        return AdminService(db).get_prompt(prompt_id)
    except AdminError as exc:
        raise _to_http(exc)


def _get_active_prompt_impl(code: str, db: Session):
    try:
        return AdminService(db).get_active_prompt_by_code(code)
    except AdminError as exc:
        raise _to_http(exc)


def _create_prompt_impl(payload: PromptTemplateCreate, db: Session):
    try:
        return AdminService(db).create_prompt(
            code=payload.code,
            content=payload.content,
            version=payload.version,
            is_active=payload.is_active,
        )
    except AdminError as exc:
        raise _to_http(exc)


def _update_prompt_impl(prompt_id: int, payload: PromptTemplateUpdate, db: Session):
    try:
        return AdminService(db).update_prompt(
            prompt_id=prompt_id,
            content=payload.content,
            is_active=payload.is_active,
            version=payload.version,
        )
    except AdminError as exc:
        raise _to_http(exc)


def _delete_prompt_impl(prompt_id: int, db: Session):
    try:
        AdminService(db).delete_prompt(prompt_id)
        return {"deleted": True, "prompt_id": prompt_id, "message": "Đã xóa mẫu prompt thành công"}
    except AdminError as exc:
        raise _to_http(exc)


# Đăng ký routes cho /admin/prompts
@router.get(
    "/prompts",
    response_model=List[PromptTemplateResponse],
    summary="Lấy danh sách tất cả mẫu Prompt Templates",
)
def list_prompts_admin(
    code: Optional[str] = Query(None, description="Lọc theo mã: TUTOR_EXPLAIN, TUTOR_SOCRATIC, QUIZ_GEN, RAG"),
    is_active: Optional[bool] = Query(None, description="Lọc theo trạng thái kích hoạt"),
    db: Session = Depends(get_db),
):
    return _list_prompts_impl(code, is_active, db)


@router.get(
    "/prompts/code/{code}/active",
    response_model=PromptTemplateResponse,
    summary="Lấy mẫu Prompt Template đang kích hoạt theo mã tính năng",
)
def get_active_prompt_admin(
    code: str = Path(..., description="Mã template: TUTOR_EXPLAIN, TUTOR_SOCRATIC, QUIZ_GEN, RAG"),
    db: Session = Depends(get_db),
):
    return _get_active_prompt_impl(code, db)


@router.get(
    "/prompts/{id}",
    response_model=PromptTemplateResponse,
    summary="Xem chi tiết một mẫu Prompt Template theo ID",
)
def get_prompt_admin(
    id: int = Path(..., ge=1, description="ID mẫu prompt"),
    db: Session = Depends(get_db),
):
    return _get_prompt_impl(id, db)


@router.post(
    "/prompts",
    response_model=PromptTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo mẫu Prompt mới hoặc tạo phiên bản mới (A/B testing)",
)
def create_prompt_admin(
    payload: PromptTemplateCreate,
    db: Session = Depends(get_db),
):
    return _create_prompt_impl(payload, db)


@router.put(
    "/prompts/{id}",
    response_model=PromptTemplateResponse,
    summary="Chỉnh sửa nội dung hoặc kích hoạt Prompt Template (SDD Bảng 17 / TK-23)",
)
def update_prompt_admin(
    payload: PromptTemplateUpdate,
    id: int = Path(..., ge=1, description="ID mẫu prompt"),
    db: Session = Depends(get_db),
):
    return _update_prompt_impl(id, payload, db)


@router.delete(
    "/prompts/{id}",
    summary="Xóa mẫu Prompt Template",
)
def delete_prompt_admin(
    id: int = Path(..., ge=1, description="ID mẫu prompt"),
    db: Session = Depends(get_db),
):
    return _delete_prompt_impl(id, db)


# Đăng ký routes bí danh cho /prompts (yêu cầu quyền Admin)
@prompts_router.get(
    "",
    response_model=List[PromptTemplateResponse],
    dependencies=[Depends(require_admin)],
    summary="[Alias] Lấy danh sách tất cả mẫu Prompt Templates",
)
def list_prompts_alias(
    code: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    return _list_prompts_impl(code, is_active, db)


@prompts_router.get(
    "/code/{code}/active",
    response_model=PromptTemplateResponse,
    dependencies=[Depends(get_current_user)],
    summary="[Alias] Lấy mẫu Prompt Template đang kích hoạt theo mã tính năng",
)
def get_active_prompt_alias(
    code: str = Path(..., description="Mã template"),
    db: Session = Depends(get_db),
):
    return _get_active_prompt_impl(code, db)


@prompts_router.get(
    "/{id}",
    response_model=PromptTemplateResponse,
    dependencies=[Depends(require_admin)],
    summary="[Alias] Xem chi tiết một mẫu Prompt Template theo ID",
)
def get_prompt_alias(
    id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    return _get_prompt_impl(id, db)


@prompts_router.post(
    "",
    response_model=PromptTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
    summary="[Alias] Tạo mẫu Prompt mới hoặc phiên bản mới",
)
def create_prompt_alias(
    payload: PromptTemplateCreate,
    db: Session = Depends(get_db),
):
    return _create_prompt_impl(payload, db)


@prompts_router.put(
    "/{id}",
    response_model=PromptTemplateResponse,
    dependencies=[Depends(require_admin)],
    summary="[Alias] Chỉnh sửa nội dung hoặc kích hoạt Prompt Template",
)
def update_prompt_alias(
    payload: PromptTemplateUpdate,
    id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    return _update_prompt_impl(id, payload, db)


@prompts_router.delete(
    "/{id}",
    dependencies=[Depends(require_admin)],
    summary="[Alias] Xóa mẫu Prompt Template",
)
def delete_prompt_alias(
    id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    return _delete_prompt_impl(id, db)


# ==============================================================================
# 3. GIÁM SÁT AI LOGS & THỐNG KÊ CHI PHÍ TOKEN (/admin/logs & /logs)
# ==============================================================================

def _list_logs_impl(
    page: int,
    page_size: int,
    user_id: Optional[int],
    feature: Optional[str],
    provider: Optional[str],
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    db: Session,
):
    try:
        return AdminService(db).list_logs(
            page=page,
            page_size=page_size,
            user_id=user_id,
            feature=feature,
            provider=provider,
            start_date=start_date,
            end_date=end_date,
        )
    except AdminError as exc:
        raise _to_http(exc)


def _get_token_stats_impl(
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    db: Session,
):
    try:
        return AdminService(db).get_token_statistics(start_date=start_date, end_date=end_date)
    except AdminError as exc:
        raise _to_http(exc)


def _create_log_impl(payload: AIRequestLogCreate, db: Session):
    try:
        log = AdminService(db).log_ai_request(
            user_id=payload.user_id,
            feature=payload.feature,
            provider=payload.provider,
            tokens_prompt=payload.tokens_prompt,
            tokens_completion=payload.tokens_completion,
            latency_ms=payload.latency_ms,
        )
        return {
            "id": log.id,
            "feature": log.feature,
            "provider": log.provider,
            "tokens_prompt": log.tokens_prompt,
            "tokens_completion": log.tokens_completion,
            "total_tokens": log.tokens_prompt + log.tokens_completion,
            "latency_ms": log.latency_ms,
            "created_at": log.created_at,
        }
    except AdminError as exc:
        raise _to_http(exc)


# Đăng ký routes cho /admin/logs
@router.get(
    "/logs",
    response_model=AIRequestLogListResponse,
    summary="Xem danh sách nhật ký gọi API AI chi tiết kèm chi phí quy đổi USD/VND",
)
def list_logs_admin(
    page: int = Query(1, ge=1, description="Số trang hiển thị"),
    page_size: int = Query(20, ge=1, le=100, description="Số lượng bản ghi mỗi trang"),
    user_id: Optional[int] = Query(None, description="Lọc theo ID người dùng"),
    feature: Optional[str] = Query(None, description="Lọc theo tính năng: TUTOR, SOCRATIC, QUIZ_GEN, RAG"),
    provider: Optional[str] = Query(None, description="Lọc theo nhà cung cấp: gemini, openai"),
    start_date: Optional[datetime] = Query(None, description="Từ thời điểm (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="Đến thời điểm (ISO format)"),
    db: Session = Depends(get_db),
):
    return _list_logs_impl(page, page_size, user_id, feature, provider, start_date, end_date, db)


@router.get(
    "/logs/tokens",
    response_model=TokenStatsResponse,
    summary="Xem báo cáo thống kê lượng token AI tiêu thụ và chi phí vận hành (SDD / SCR-08)",
)
def get_token_statistics_admin(
    start_date: Optional[datetime] = Query(None, description="Thời điểm bắt đầu"),
    end_date: Optional[datetime] = Query(None, description="Thời điểm kết thúc"),
    db: Session = Depends(get_db),
):
    return _get_token_stats_impl(start_date, end_date, db)


@router.post(
    "/logs",
    status_code=status.HTTP_201_CREATED,
    summary="Ghi nhận nhật ký gọi AI mới (dành cho kiểm thử hoặc ghi log thủ công)",
)
def create_log_admin(
    payload: AIRequestLogCreate,
    db: Session = Depends(get_db),
):
    return _create_log_impl(payload, db)


# Đăng ký routes bí danh cho /logs (yêu cầu quyền Admin)
@logs_router.get(
    "",
    response_model=AIRequestLogListResponse,
    dependencies=[Depends(require_admin)],
    summary="[Alias] Xem danh sách nhật ký gọi API AI chi tiết",
)
def list_logs_alias(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: Optional[int] = Query(None),
    feature: Optional[str] = Query(None),
    provider: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
):
    return _list_logs_impl(page, page_size, user_id, feature, provider, start_date, end_date, db)


@logs_router.get(
    "/tokens",
    response_model=TokenStatsResponse,
    dependencies=[Depends(require_admin)],
    summary="[Alias] Xem báo cáo thống kê lượng token AI tiêu thụ và chi phí vận hành",
)
def get_token_statistics_alias(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
):
    return _get_token_stats_impl(start_date, end_date, db)


@logs_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
    summary="[Alias] Ghi nhận nhật ký gọi AI mới",
)
def create_log_alias(
    payload: AIRequestLogCreate,
    db: Session = Depends(get_db),
):
    return _create_log_impl(payload, db)
