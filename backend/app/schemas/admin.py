"""Schemas Pydantic cho Phân hệ 7: Quản trị hệ thống (TK-23 / SCR-08).

Bao gồm:
- Quản lý danh sách người dùng (khóa/mở khóa, phân quyền)
- Cấu hình Prompt Templates trên web (A/B testing, kích hoạt phiên bản)
- Thống kê chi tiết lượng token AI tiêu thụ và chi phí ước tính (USD / VND)
"""
from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, ConfigDict, Field, field_validator


# ==============================================================================
# 1. SCHEMAS QUẢN LÝ NGƯỜI DÙNG (USERS)
# ==============================================================================

class UserAdminItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: str
    status: str
    created_at: datetime


class UserAdminDetailResponse(UserAdminItem):
    enrollments_count: int = 0
    chat_sessions_count: int = 0
    quiz_attempts_count: int = 0
    ai_requests_count: int = 0


class UserStatusUpdate(BaseModel):
    status: str = Field(..., description="Trạng thái tài khoản: ACTIVE hoặc LOCKED")
    reason: Optional[str] = Field(default=None, max_length=255, description="Lý do khóa hoặc mở khóa tài khoản")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        v_upper = v.strip().upper()
        if v_upper not in ("ACTIVE", "LOCKED"):
            raise ValueError("Trạng thái chỉ có thể là ACTIVE hoặc LOCKED")
        return v_upper


class UserRoleUpdate(BaseModel):
    role: str = Field(..., description="Vai trò: STUDENT hoặc ADMIN")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        v_upper = v.strip().upper()
        if v_upper not in ("STUDENT", "ADMIN"):
            raise ValueError("Vai trò chỉ có thể là STUDENT hoặc ADMIN")
        return v_upper


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    role: Optional[str] = None
    status: Optional[str] = None

    @field_validator("role")
    @classmethod
    def validate_role_opt(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_upper = v.strip().upper()
            if v_upper not in ("STUDENT", "ADMIN"):
                raise ValueError("Vai trò chỉ có thể là STUDENT hoặc ADMIN")
            return v_upper
        return v

    @field_validator("status")
    @classmethod
    def validate_status_opt(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_upper = v.strip().upper()
            if v_upper not in ("ACTIVE", "LOCKED"):
                raise ValueError("Trạng thái chỉ có thể là ACTIVE hoặc LOCKED")
            return v_upper
        return v


class UserListResponse(BaseModel):
    items: List[UserAdminItem]
    total: int
    page: int
    page_size: int
    total_pages: int


# ==============================================================================
# 2. SCHEMAS PROMPT TEMPLATES
# ==============================================================================

class PromptTemplateBase(BaseModel):
    code: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Mã mẫu prompt: TUTOR_EXPLAIN, TUTOR_SOCRATIC, QUIZ_GEN, RAG",
    )
    version: int = Field(default=1, ge=1, description="Phiên bản mẫu phục vụ A/B Testing")
    content: str = Field(..., min_length=1, description="Nội dung system prompt chứa các tham số biến")
    is_active: bool = Field(default=True, description="Cờ đánh dấu template đang kích hoạt")


class PromptTemplateCreate(BaseModel):
    code: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Mã mẫu prompt: TUTOR_EXPLAIN, TUTOR_SOCRATIC, QUIZ_GEN, RAG",
    )
    content: str = Field(..., min_length=1, description="Nội dung system prompt")
    version: Optional[int] = Field(
        default=None,
        ge=1,
        description="Phiên bản số nguyên. Nếu bỏ trống, hệ thống sẽ tự động gán max(version) + 1",
    )
    is_active: bool = Field(default=True, description="Tự động kích hoạt phiên bản mới này")

    @field_validator("code")
    @classmethod
    def normalize_code(cls, v: str) -> str:
        return v.strip().upper()


class PromptTemplateUpdate(BaseModel):
    content: Optional[str] = Field(default=None, min_length=1, description="Nội dung prompt cập nhật")
    is_active: Optional[bool] = Field(default=None, description="Bật/tắt trạng thái kích hoạt")
    version: Optional[int] = Field(default=None, ge=1, description="Cập nhật phiên bản mới")


class PromptTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    version: int
    content: str
    is_active: bool
    created_at: datetime


class PromptTemplateListResponse(BaseModel):
    items: List[PromptTemplateResponse]
    total: int


# ==============================================================================
# 3. SCHEMAS AI REQUEST LOGS & THỐNG KÊ CHI PHÍ TOKEN
# ==============================================================================

class AIRequestLogItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: Optional[int] = None
    user_email: Optional[str] = None
    user_full_name: Optional[str] = None
    feature: str
    provider: str
    tokens_prompt: int
    tokens_completion: int
    total_tokens: int
    latency_ms: int
    estimated_cost_usd: float = Field(..., description="Chi phí ước tính quy đổi USD")
    estimated_cost_vnd: float = Field(..., description="Chi phí ước tính quy đổi VND (tỷ giá 25.400)")
    created_at: datetime


class AIRequestLogCreate(BaseModel):
    user_id: Optional[int] = None
    feature: str = Field(default="TUTOR", description="TUTOR | SOCRATIC | QUIZ_GEN | RAG")
    provider: str = Field(default="gemini", description="gemini | openai")
    tokens_prompt: int = Field(default=0, ge=0)
    tokens_completion: int = Field(default=0, ge=0)
    latency_ms: int = Field(default=500, ge=0)


class AIRequestLogListResponse(BaseModel):
    items: List[AIRequestLogItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class TokenStatGroup(BaseModel):
    key: str = Field(..., description="Khóa nhóm: Tên tính năng, Tên provider hoặc Ngày (YYYY-MM-DD)")
    request_count: int
    tokens_prompt: int
    tokens_completion: int
    total_tokens: int
    estimated_cost_usd: float
    estimated_cost_vnd: float
    avg_latency_ms: float


class TokenUsageSummary(BaseModel):
    total_requests: int
    total_tokens_prompt: int
    total_tokens_completion: int
    total_tokens: int
    estimated_cost_usd: float
    estimated_cost_vnd: float
    avg_latency_ms: float


class TokenStatsResponse(BaseModel):
    summary: TokenUsageSummary
    by_feature: List[TokenStatGroup]
    by_provider: List[TokenStatGroup]
    by_date: List[TokenStatGroup]
    pricing_rates: Dict[str, Dict[str, float]]
    exchange_rate_vnd: float
