"""Dịch vụ nghiệp vụ Quản trị hệ thống (Phân hệ 7: Quản trị | TK-23 / SCR-08).

Chức năng:
1. Quản lý danh sách người dùng (User Management):
   - Phân trang, tìm kiếm theo email / họ tên, lọc theo vai trò (STUDENT/ADMIN) và trạng thái (ACTIVE/LOCKED).
   - Khóa / Mở khóa tài khoản: Thu hồi toàn bộ Refresh Token đang hoạt động nếu tài khoản bị khóa.
   - Chặn Admin tự khóa tài khoản hoặc tự giáng quyền của chính mình.
   - Thống kê chi tiết hoạt động của từng người dùng (khóa học, chat, quiz, ai requests).

2. Quản lý Prompt Templates (Prompt Configuration):
   - Quản trị tập trung các mẫu system prompt: TUTOR_EXPLAIN, TUTOR_SOCRATIC, QUIZ_GEN, RAG.
   - Hỗ trợ đánh phiên bản (versioning) phục vụ A/B Testing, chuyển đổi template kích hoạt an toàn.
   - Lấy template đang kích hoạt theo mã tính năng.

3. Giám sát AI Logs & Thống kê Chi phí Token (Token Monitoring & Cost Estimation):
   - Bảng nhật ký gọi API AI chi tiết: tokens prompt, tokens completion, độ trễ, quy đổi chi phí USD / VND.
   - Báo cáo tổng hợp lượng token tiêu thụ theo ngày, theo tính năng (TUTOR, SOCRATIC, QUIZ_GEN, RAG) và theo nhà cung cấp (Gemini, OpenAI).
"""
import math
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, func, update, delete, or_, desc, asc
from sqlalchemy.orm import Session

def utcnow() -> datetime:
    """Thời điểm hiện tại theo UTC dạng naive (khớp cột DateTime MySQL/SQLite)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

from app.models.user import User, UserRole, UserStatus, RefreshToken
from app.models.rag import PromptTemplate, AIRequestLog, AIFeature, AIProvider
from app.models.course import Enrollment
from app.models.chat import ChatSession
from app.models.quiz import QuizAttempt
from app.schemas.admin import (
    UserAdminItem,
    UserAdminDetailResponse,
    UserListResponse,
    PromptTemplateResponse,
    AIRequestLogItem,
    AIRequestLogListResponse,
    TokenStatGroup,
    TokenUsageSummary,
    TokenStatsResponse,
)


# ==============================================================================
# ĐỊNH NGHĨA NGOẠI LỆ NGHIỆP VỤ (EXCEPTIONS)
# ==============================================================================

class AdminError(Exception):
    status_code: int = 400

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code


class UserNotFoundError(AdminError):
    status_code = 404

    def __init__(self, user_id: int):
        super().__init__(f"Không tìm thấy người dùng với ID {user_id}", status_code=404)


class PromptNotFoundError(AdminError):
    status_code = 404

    def __init__(self, prompt_id: Optional[int] = None, code: Optional[str] = None):
        if prompt_id is not None:
            super().__init__(f"Không tìm thấy Prompt Template với ID {prompt_id}", status_code=404)
        else:
            super().__init__(f"Không tìm thấy mẫu prompt kích hoạt cho mã '{code}'", status_code=404)


class AdminOperationForbiddenError(AdminError):
    status_code = 400


class PromptConflictError(AdminError):
    status_code = 409


# ==============================================================================
# BẢNG GIÁ TOKEN VÀ TỶ GIÁ QUY ĐỔI (PRICING CONFIGURATION)
# ==============================================================================

# Bảng giá chuẩn ước tính theo USD trên 1 triệu token (1M tokens)
TOKEN_PRICING_CONFIG: Dict[str, Dict[str, float]] = {
    "gemini": {
        "prompt_per_1m": 0.075,       # ~$0.075 / 1M input tokens (Gemini 1.5/2.5 Flash)
        "completion_per_1m": 0.300,   # ~$0.300 / 1M output tokens
    },
    "openai": {
        "prompt_per_1m": 0.150,       # ~$0.150 / 1M input tokens (GPT-4o-mini)
        "completion_per_1m": 0.600,   # ~$0.600 / 1M output tokens
    },
    "default": {
        "prompt_per_1m": 0.100,
        "completion_per_1m": 0.400,
    },
}

# Tỷ giá USD sang VND niêm yết
USD_TO_VND_RATE: float = 25400.0


def calculate_token_cost(provider: str, tokens_prompt: int, tokens_completion: int) -> Tuple[float, float]:
    """Tính toán chi phí token ước tính theo USD và VND."""
    prov_key = (provider or "").strip().lower()
    rates = TOKEN_PRICING_CONFIG.get(prov_key, TOKEN_PRICING_CONFIG["default"])
    cost_usd = (
        (tokens_prompt * rates["prompt_per_1m"] + tokens_completion * rates["completion_per_1m"])
        / 1_000_000.0
    )
    cost_vnd = cost_usd * USD_TO_VND_RATE
    return round(cost_usd, 6), round(cost_vnd, 2)


# ==============================================================================
# ADMIN SERVICE CLASS
# ==============================================================================

class AdminService:
    def __init__(self, db: Session):
        self.db = db

    # --------------------------------------------------------------------------
    # 1. QUẢN LÝ NGƯỜI DÙNG (USERS)
    # --------------------------------------------------------------------------

    def list_users(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        role: Optional[str] = None,
        status: Optional[str] = None,
    ) -> UserListResponse:
        """Lấy danh sách người dùng có phân trang, tìm kiếm và lọc."""
        page = max(1, page)
        page_size = max(1, min(100, page_size))

        stmt = select(User)

        # Lọc theo từ khóa tìm kiếm (email hoặc họ tên)
        if isinstance(search, str) and search.strip():
            kw = f"%{search.strip()}%"
            stmt = stmt.where(or_(User.email.ilike(kw), User.full_name.ilike(kw)))

        # Lọc theo vai trò
        if isinstance(role, str) and role.strip():
            stmt = stmt.where(User.role == role.strip().upper())

        # Lọc theo trạng thái
        if isinstance(status, str) and status.strip():
            stmt = stmt.where(User.status == status.strip().upper())


        # Tính tổng số bản ghi
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.scalar(count_stmt) or 0
        total_pages = math.ceil(total / page_size) if total > 0 else 0

        # Phân trang và sắp xếp mới nhất lên đầu
        stmt = stmt.order_by(desc(User.created_at), desc(User.id))
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        users = self.db.scalars(stmt).all()

        items = [UserAdminItem.model_validate(u) for u in users]
        return UserListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def get_user_detail(self, user_id: int) -> UserAdminDetailResponse:
        """Lấy thông tin chi tiết một người dùng kèm các số liệu thống kê hoạt động."""
        user = self.db.get(User, user_id)
        if not user:
            raise UserNotFoundError(user_id)

        enrollments_count = self.db.scalar(
            select(func.count(Enrollment.id)).where(Enrollment.user_id == user_id)
        ) or 0
        chat_sessions_count = self.db.scalar(
            select(func.count(ChatSession.id)).where(ChatSession.user_id == user_id)
        ) or 0
        quiz_attempts_count = self.db.scalar(
            select(func.count(QuizAttempt.id)).where(QuizAttempt.user_id == user_id)
        ) or 0
        ai_requests_count = self.db.scalar(
            select(func.count(AIRequestLog.id)).where(AIRequestLog.user_id == user_id)
        ) or 0

        return UserAdminDetailResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            status=user.status,
            created_at=user.created_at,
            enrollments_count=enrollments_count,
            chat_sessions_count=chat_sessions_count,
            quiz_attempts_count=quiz_attempts_count,
            ai_requests_count=ai_requests_count,
        )

    def update_user_status(
        self,
        current_admin: User,
        target_user_id: int,
        new_status: str,
        reason: Optional[str] = None,
    ) -> User:
        """Khóa hoặc mở khóa tài khoản người dùng."""
        new_status = new_status.strip().upper()
        if new_status not in (UserStatus.ACTIVE.value, UserStatus.LOCKED.value):
            raise AdminOperationForbiddenError("Trạng thái chỉ có thể là ACTIVE hoặc LOCKED")

        user = self.db.get(User, target_user_id)
        if not user:
            raise UserNotFoundError(target_user_id)

        # Chặn Admin tự khóa tài khoản của chính mình
        if current_admin.id == target_user_id and new_status == UserStatus.LOCKED.value:
            raise AdminOperationForbiddenError("Không thể tự khóa tài khoản của chính mình")

        # Đảm bảo hệ thống luôn còn ít nhất 1 Admin hoạt động
        if user.role == UserRole.ADMIN.value and new_status == UserStatus.LOCKED.value:
            active_admins = self.db.scalar(
                select(func.count(User.id)).where(
                    User.role == UserRole.ADMIN.value,
                    User.status == UserStatus.ACTIVE.value,
                    User.id != target_user_id,
                )
            ) or 0
            if active_admins == 0:
                raise AdminOperationForbiddenError("Không thể khóa Admin duy nhất còn hoạt động của hệ thống")

        user.status = new_status

        # Khi khóa tài khoản, lập tức thu hồi mọi Refresh Token đang hiệu lực của người dùng này
        if new_status == UserStatus.LOCKED.value:
            self.db.execute(
                update(RefreshToken)
                .where(
                    RefreshToken.user_id == target_user_id,
                    RefreshToken.revoked_at.is_(None),
                )
                .values(revoked_at=utcnow())
            )

        self.db.commit()
        self.db.refresh(user)
        return user

    def update_user_role(
        self,
        current_admin: User,
        target_user_id: int,
        new_role: str,
    ) -> User:
        """Cập nhật phân quyền người dùng (STUDENT <-> ADMIN)."""
        new_role = new_role.strip().upper()
        if new_role not in (UserRole.STUDENT.value, UserRole.ADMIN.value):
            raise AdminOperationForbiddenError("Vai trò chỉ có thể là STUDENT hoặc ADMIN")

        user = self.db.get(User, target_user_id)
        if not user:
            raise UserNotFoundError(target_user_id)

        # Chặn Admin tự giáng quyền của chính mình
        if current_admin.id == target_user_id and new_role != UserRole.ADMIN.value:
            raise AdminOperationForbiddenError("Không thể tự giáng quyền của chính mình")

        user.role = new_role
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_user(
        self,
        current_admin: User,
        target_user_id: int,
        full_name: Optional[str] = None,
        role: Optional[str] = None,
        status: Optional[str] = None,
    ) -> User:
        """Cập nhật thông tin tổng hợp của người dùng."""
        user = self.db.get(User, target_user_id)
        if not user:
            raise UserNotFoundError(target_user_id)

        if full_name is not None and full_name.strip():
            user.full_name = full_name.strip()

        if status is not None:
            self.update_user_status(current_admin, target_user_id, status)

        if role is not None:
            self.update_user_role(current_admin, target_user_id, role)

        self.db.commit()
        self.db.refresh(user)
        return user

    # --------------------------------------------------------------------------
    # 2. QUẢN LÝ PROMPT TEMPLATES
    # --------------------------------------------------------------------------

    def list_prompts(
        self,
        code: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> List[PromptTemplateResponse]:
        """Lấy danh sách tất cả các Prompt Templates kèm bộ lọc."""
        stmt = select(PromptTemplate)
        if isinstance(code, str) and code.strip():
            stmt = stmt.where(PromptTemplate.code == code.strip().upper())
        if isinstance(is_active, bool):
            stmt = stmt.where(PromptTemplate.is_active == is_active)


        stmt = stmt.order_by(asc(PromptTemplate.code), desc(PromptTemplate.version))
        prompts = self.db.scalars(stmt).all()
        return [PromptTemplateResponse.model_validate(p) for p in prompts]

    def get_prompt(self, prompt_id: int) -> PromptTemplateResponse:
        """Lấy thông tin chi tiết một Prompt Template theo ID."""
        prompt = self.db.get(PromptTemplate, prompt_id)
        if not prompt:
            raise PromptNotFoundError(prompt_id=prompt_id)
        return PromptTemplateResponse.model_validate(prompt)

    def get_active_prompt_by_code(self, code: str) -> PromptTemplateResponse:
        """Lấy phiên bản Prompt Template đang được kích hoạt cho mã chỉ định."""
        code_upper = code.strip().upper()
        stmt = (
            select(PromptTemplate)
            .where(
                PromptTemplate.code == code_upper,
                PromptTemplate.is_active.is_(True),
            )
            .order_by(desc(PromptTemplate.version))
            .limit(1)
        )
        prompt = self.db.scalar(stmt)
        if not prompt:
            raise PromptNotFoundError(code=code_upper)
        return PromptTemplateResponse.model_validate(prompt)

    def create_prompt(
        self,
        code: str,
        content: str,
        version: Optional[int] = None,
        is_active: bool = True,
    ) -> PromptTemplateResponse:
        """Tạo mới một Prompt Template hoặc tạo phiên bản mới cho mã đã có."""
        code_upper = code.strip().upper()
        content = content.strip()
        if not content:
            raise AdminOperationForbiddenError("Nội dung prompt không được để trống")

        # Tự động gán version = max(version) + 1 nếu người dùng không truyền
        if version is None:
            max_ver = self.db.scalar(
                select(func.max(PromptTemplate.version)).where(PromptTemplate.code == code_upper)
            ) or 0
            version = max_ver + 1

        # Kiểm tra trùng lặp cặp (code, version)
        existing = self.db.scalar(
            select(PromptTemplate).where(
                PromptTemplate.code == code_upper,
                PromptTemplate.version == version,
            )
        )
        if existing:
            raise PromptConflictError(
                f"Mẫu prompt '{code_upper}' phiên bản {version} đã tồn tại trong hệ thống"
            )

        # Nếu phiên bản mới được kích hoạt, vô hiệu hóa cờ is_active của các phiên bản cũ cùng mã
        if is_active:
            self.db.execute(
                update(PromptTemplate)
                .where(PromptTemplate.code == code_upper)
                .values(is_active=False)
            )

        new_prompt = PromptTemplate(
            code=code_upper,
            version=version,
            content=content,
            is_active=is_active,
            created_at=utcnow(),
        )
        self.db.add(new_prompt)
        self.db.commit()
        self.db.refresh(new_prompt)
        return PromptTemplateResponse.model_validate(new_prompt)

    def update_prompt(
        self,
        prompt_id: int,
        content: Optional[str] = None,
        is_active: Optional[bool] = None,
        version: Optional[int] = None,
    ) -> PromptTemplateResponse:
        """Chỉnh sửa nội dung hoặc trạng thái kích hoạt của Prompt Template."""
        prompt = self.db.get(PromptTemplate, prompt_id)
        if not prompt:
            raise PromptNotFoundError(prompt_id=prompt_id)

        if content is not None:
            content_str = content.strip()
            if not content_str:
                raise AdminOperationForbiddenError("Nội dung prompt không được để trống")
            prompt.content = content_str

        if version is not None and version != prompt.version:
            # Kiểm tra xem version mới có trùng lặp không
            existing = self.db.scalar(
                select(PromptTemplate).where(
                    PromptTemplate.code == prompt.code,
                    PromptTemplate.version == version,
                    PromptTemplate.id != prompt_id,
                )
            )
            if existing:
                raise PromptConflictError(
                    f"Phiên bản {version} của mẫu '{prompt.code}' đã tồn tại"
                )
            prompt.version = version

        if is_active is not None:
            if is_active and not prompt.is_active:
                # Bật kích hoạt phiên bản này -> tắt các phiên bản khác cùng code
                self.db.execute(
                    update(PromptTemplate)
                    .where(
                        PromptTemplate.code == prompt.code,
                        PromptTemplate.id != prompt_id,
                    )
                    .values(is_active=False)
                )
            prompt.is_active = is_active

        self.db.commit()
        self.db.refresh(prompt)
        return PromptTemplateResponse.model_validate(prompt)

    def delete_prompt(self, prompt_id: int) -> None:
        """Xóa một mẫu prompt template."""
        prompt = self.db.get(PromptTemplate, prompt_id)
        if not prompt:
            raise PromptNotFoundError(prompt_id=prompt_id)
        self.db.delete(prompt)
        self.db.commit()

    # --------------------------------------------------------------------------
    # 3. NHẬT KÝ GỌI AI & THỐNG KÊ CHI PHÍ TOKEN
    # --------------------------------------------------------------------------

    def list_logs(
        self,
        page: int = 1,
        page_size: int = 20,
        user_id: Optional[int] = None,
        feature: Optional[str] = None,
        provider: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> AIRequestLogListResponse:
        """Xem danh sách nhật ký gọi API AI chi tiết kèm chi phí quy đổi."""
        page = max(1, page)
        page_size = max(1, min(100, page_size))

        stmt = select(AIRequestLog, User).outerjoin(User, User.id == AIRequestLog.user_id)

        if isinstance(user_id, int):
            stmt = stmt.where(AIRequestLog.user_id == user_id)
        if isinstance(feature, str) and feature.strip():
            stmt = stmt.where(AIRequestLog.feature == feature.strip().upper())
        if isinstance(provider, str) and provider.strip():
            stmt = stmt.where(AIRequestLog.provider == provider.strip().lower())
        if isinstance(start_date, datetime):
            stmt = stmt.where(AIRequestLog.created_at >= start_date)
        if isinstance(end_date, datetime):
            stmt = stmt.where(AIRequestLog.created_at <= end_date)


        # Tính tổng số bản ghi
        count_stmt = select(func.count()).select_from(
            stmt.with_only_columns(AIRequestLog.id).subquery()
        )
        total = self.db.scalar(count_stmt) or 0
        total_pages = math.ceil(total / page_size) if total > 0 else 0

        # Phân trang và sắp xếp mới nhất
        stmt = stmt.order_by(desc(AIRequestLog.created_at), desc(AIRequestLog.id))
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        rows = self.db.execute(stmt).all()

        items = []
        for log, user in rows:
            cost_usd, cost_vnd = calculate_token_cost(
                log.provider, log.tokens_prompt, log.tokens_completion
            )
            items.append(
                AIRequestLogItem(
                    id=log.id,
                    user_id=log.user_id,
                    user_email=user.email if user else None,
                    user_full_name=user.full_name if user else None,
                    feature=log.feature,
                    provider=log.provider,
                    tokens_prompt=log.tokens_prompt,
                    tokens_completion=log.tokens_completion,
                    total_tokens=log.tokens_prompt + log.tokens_completion,
                    latency_ms=log.latency_ms,
                    estimated_cost_usd=cost_usd,
                    estimated_cost_vnd=cost_vnd,
                    created_at=log.created_at,
                )
            )

        return AIRequestLogListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def get_token_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> TokenStatsResponse:
        """Báo cáo thống kê toàn diện lượng token AI tiêu thụ và chi phí vận hành (SDD / SCR-08)."""
        base_where = []
        if isinstance(start_date, datetime):
            base_where.append(AIRequestLog.created_at >= start_date)
        if isinstance(end_date, datetime):
            base_where.append(AIRequestLog.created_at <= end_date)


        # 1. Thống kê tổng quan (Summary)
        summary_stmt = select(
            func.count(AIRequestLog.id).label("total_requests"),
            func.coalesce(func.sum(AIRequestLog.tokens_prompt), 0).label("total_tokens_prompt"),
            func.coalesce(func.sum(AIRequestLog.tokens_completion), 0).label("total_tokens_completion"),
            func.coalesce(func.avg(AIRequestLog.latency_ms), 0.0).label("avg_latency"),
        )
        if base_where:
            summary_stmt = summary_stmt.where(*base_where)

        total_reqs, total_prompt, total_comp, avg_lat = self.db.execute(summary_stmt).one()
        total_toks = int(total_prompt) + int(total_comp)

        # 2. Thống kê theo Tính năng (by_feature)
        feat_stmt = select(
            AIRequestLog.feature,
            func.count(AIRequestLog.id),
            func.coalesce(func.sum(AIRequestLog.tokens_prompt), 0),
            func.coalesce(func.sum(AIRequestLog.tokens_completion), 0),
            func.coalesce(func.avg(AIRequestLog.latency_ms), 0.0),
        )
        if base_where:
            feat_stmt = feat_stmt.where(*base_where)
        feat_stmt = feat_stmt.group_by(AIRequestLog.feature).order_by(desc(func.count(AIRequestLog.id)))
        feat_rows = self.db.execute(feat_stmt).all()

        by_feature: List[TokenStatGroup] = []
        for feat, req_count, p_tokens, c_tokens, lat in feat_rows:
            p_tokens, c_tokens = int(p_tokens), int(c_tokens)
            c_usd, c_vnd = calculate_token_cost("default", p_tokens, c_tokens)
            by_feature.append(
                TokenStatGroup(
                    key=feat,
                    request_count=req_count,
                    tokens_prompt=p_tokens,
                    tokens_completion=c_tokens,
                    total_tokens=p_tokens + c_tokens,
                    estimated_cost_usd=c_usd,
                    estimated_cost_vnd=c_vnd,
                    avg_latency_ms=round(float(lat), 1),
                )
            )

        # 3. Thống kê theo Nhà cung cấp LLM (by_provider)
        prov_stmt = select(
            AIRequestLog.provider,
            func.count(AIRequestLog.id),
            func.coalesce(func.sum(AIRequestLog.tokens_prompt), 0),
            func.coalesce(func.sum(AIRequestLog.tokens_completion), 0),
            func.coalesce(func.avg(AIRequestLog.latency_ms), 0.0),
        )
        if base_where:
            prov_stmt = prov_stmt.where(*base_where)
        prov_stmt = prov_stmt.group_by(AIRequestLog.provider).order_by(desc(func.count(AIRequestLog.id)))
        prov_rows = self.db.execute(prov_stmt).all()

        by_provider: List[TokenStatGroup] = []
        tot_cost_usd = 0.0
        tot_cost_vnd = 0.0
        for prov, req_count, p_tokens, c_tokens, lat in prov_rows:
            p_tokens, c_tokens = int(p_tokens), int(c_tokens)
            c_usd, c_vnd = calculate_token_cost(prov, p_tokens, c_tokens)
            tot_cost_usd += c_usd
            tot_cost_vnd += c_vnd
            by_provider.append(
                TokenStatGroup(
                    key=prov,
                    request_count=req_count,
                    tokens_prompt=p_tokens,
                    tokens_completion=c_tokens,
                    total_tokens=p_tokens + c_tokens,
                    estimated_cost_usd=c_usd,
                    estimated_cost_vnd=c_vnd,
                    avg_latency_ms=round(float(lat), 1),
                )
            )

        # 4. Thống kê theo Ngày (by_date - hỗ trợ cả SQLite DATE() và MySQL DATE())
        date_col = func.substr(func.cast(AIRequestLog.created_at, func.CHAR if hasattr(func, "CHAR") else None), 1, 10)
        # Sử dụng biểu thức chuẩn SQL để trích xuất YYYY-MM-DD
        date_expr = func.strftime("%Y-%m-%d", AIRequestLog.created_at) if "sqlite" in str(self.db.bind.dialect.name).lower() else func.date(AIRequestLog.created_at)

        date_stmt = select(
            date_expr.label("log_date"),
            func.count(AIRequestLog.id),
            func.coalesce(func.sum(AIRequestLog.tokens_prompt), 0),
            func.coalesce(func.sum(AIRequestLog.tokens_completion), 0),
            func.coalesce(func.avg(AIRequestLog.latency_ms), 0.0),
        )
        if base_where:
            date_stmt = date_stmt.where(*base_where)
        date_stmt = date_stmt.group_by(date_expr).order_by(asc(date_expr))
        date_rows = self.db.execute(date_stmt).all()

        by_date: List[TokenStatGroup] = []
        for d_str, req_count, p_tokens, c_tokens, lat in date_rows:
            p_tokens, c_tokens = int(p_tokens), int(c_tokens)
            c_usd, c_vnd = calculate_token_cost("default", p_tokens, c_tokens)
            by_date.append(
                TokenStatGroup(
                    key=str(d_str or "Unknown"),
                    request_count=req_count,
                    tokens_prompt=p_tokens,
                    tokens_completion=c_tokens,
                    total_tokens=p_tokens + c_tokens,
                    estimated_cost_usd=c_usd,
                    estimated_cost_vnd=c_vnd,
                    avg_latency_ms=round(float(lat), 1),
                )
            )

        # Nếu không có breakdown provider, tính tổng chi phí theo default
        if not by_provider and total_toks > 0:
            tot_cost_usd, tot_cost_vnd = calculate_token_cost("default", int(total_prompt), int(total_comp))

        summary = TokenUsageSummary(
            total_requests=int(total_reqs),
            total_tokens_prompt=int(total_prompt),
            total_tokens_completion=int(total_comp),
            total_tokens=total_toks,
            estimated_cost_usd=round(tot_cost_usd, 6),
            estimated_cost_vnd=round(tot_cost_vnd, 2),
            avg_latency_ms=round(float(avg_lat), 1),
        )

        return TokenStatsResponse(
            summary=summary,
            by_feature=by_feature,
            by_provider=by_provider,
            by_date=by_date,
            pricing_rates=TOKEN_PRICING_CONFIG,
            exchange_rate_vnd=USD_TO_VND_RATE,
        )

    def log_ai_request(
        self,
        user_id: Optional[int],
        feature: str,
        provider: str,
        tokens_prompt: int,
        tokens_completion: int,
        latency_ms: int,
    ) -> AIRequestLog:
        """Ghi nhận lịch sử một lần gọi AI vào CSDL."""
        log = AIRequestLog(
            user_id=user_id,
            feature=feature.strip().upper(),
            provider=provider.strip().lower(),
            tokens_prompt=max(0, tokens_prompt),
            tokens_completion=max(0, tokens_completion),
            latency_ms=max(0, latency_ms),
            created_at=utcnow(),
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log
