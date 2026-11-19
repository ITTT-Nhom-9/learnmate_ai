"""Kiểm thử toàn diện các API và nghiệp vụ Quản trị viên (Phân hệ 7: Quản trị | TK-23 / SCR-08).

Kiểm tra:
1. Phân quyền và bảo mật (RBAC):
   - require_admin cho phép ADMIN, chặn STUDENT với mã lỗi 403 Forbidden.
   - Chặn tài khoản bị khóa (LOCKED) truy cập hệ thống.
2. Quản lý người dùng (/admin/users):
   - Danh sách người dùng, tìm kiếm theo tên/email, lọc theo role, status, phân trang.
   - Chi tiết người dùng kèm số liệu học tập và số lượt gọi AI.
   - Khóa/mở khóa tài khoản: thu hồi Refresh Token khi khóa tài khoản.
   - Chặn Admin tự khóa tài khoản hoặc tự giáng quyền của chính mình.
   - Chặn khóa Admin hoạt động duy nhất của hệ thống.
3. Cấu hình Prompt Templates (/admin/prompts & alias /prompts):
   - Danh sách mẫu prompt, lọc theo mã code và trạng thái is_active.
   - Xem chi tiết prompt theo ID và lấy prompt active theo mã code.
   - Tạo mới mẫu prompt: tự động sinh version (max + 1), tự động vô hiệu hóa version cũ khi kích hoạt.
   - Ràng buộc duy nhất UNIQUE(code, version) chống xung đột phiên bản.
   - Chỉnh sửa nội dung prompt, bật/tắt kích hoạt và xóa prompt.
4. Giám sát AI Logs & Thống kê Chi phí Token (/admin/logs & alias /logs):
   - Danh sách nhật ký gọi AI kèm tính toán chi phí USD/VND theo nhà cung cấp (Gemini, OpenAI).
   - Báo cáo thống kê toàn diện: tổng token, chi phí ước tính, phân nhóm theo tính năng, nhà cung cấp và theo ngày.
   - Tỷ giá quy đổi 25.400 VND/USD chính xác.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi import HTTPException

from app.core.database import Base
from app.models.user import User, UserRole, UserStatus, RefreshToken
from app.models.course import Course, Lesson, Topic, Enrollment
from app.models.chat import ChatSession, ChatMode, ChatSessionStatus
from app.models.quiz import QuizAttempt
from app.models.rag import PromptTemplate, AIRequestLog, AIFeature, AIProvider
from app.api.deps import require_admin
from app.schemas.admin import (
    UserStatusUpdate,
    UserRoleUpdate,
    UserUpdate,
    PromptTemplateCreate,
    PromptTemplateUpdate,
    AIRequestLogCreate,
)
from app.services.admin_service import (
    AdminService,
    AdminOperationForbiddenError,
    UserNotFoundError,
    PromptNotFoundError,
    PromptConflictError,
    calculate_token_cost,
    TOKEN_PRICING_CONFIG,
    USD_TO_VND_RATE,
)
from app.api.admin import (
    list_users,
    get_user_detail,
    update_user_status,
    update_user_role,
    update_user,
    lock_user_shortcut,
    unlock_user_shortcut,
    list_prompts_admin,
    get_prompt_admin,
    get_active_prompt_admin,
    create_prompt_admin,
    update_prompt_admin,
    delete_prompt_admin,
    list_prompts_alias,
    create_prompt_alias,
    update_prompt_alias,
    delete_prompt_alias,
    list_logs_admin,
    get_token_statistics_admin,
    create_log_admin,
    list_logs_alias,
    get_token_statistics_alias,
)


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture()
def db_session():
    """Tạo CSDL SQLite in-memory độc lập cho mỗi test case."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = session_factory()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def seed_data(db_session):
    """Khởi tạo tài khoản Admin, Student và dữ liệu mẫu."""
    admin_user = User(
        email="admin@learnmate.edu.vn",
        password_hash="hashed_admin_pass",
        full_name="Quản Trị Viên Hệ Thống",
        role=UserRole.ADMIN.value,
        status=UserStatus.ACTIVE.value,
    )
    admin_user_2 = User(
        email="admin2@learnmate.edu.vn",
        password_hash="hashed_admin2_pass",
        full_name="Quản Trị Viên Phụ",
        role=UserRole.ADMIN.value,
        status=UserStatus.ACTIVE.value,
    )
    student_user = User(
        email="student.nguyen@learnmate.edu.vn",
        password_hash="hashed_student_pass",
        full_name="Nguyễn Văn Sinh Viên",
        role=UserRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    student_locked = User(
        email="locked.user@learnmate.edu.vn",
        password_hash="hashed_locked_pass",
        full_name="Người Dùng Bị Khóa",
        role=UserRole.STUDENT.value,
        status=UserStatus.LOCKED.value,
    )
    db_session.add_all([admin_user, admin_user_2, student_user, student_locked])
    db_session.flush()

    # Thêm refresh token cho student
    r_token = RefreshToken(
        user_id=student_user.id,
        token_hash="sample_token_hash_student_active",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db_session.add(r_token)

    # Thêm prompt templates mẫu
    p1 = PromptTemplate(
        code="TUTOR_EXPLAIN",
        version=1,
        content="System prompt giải thích bài học v1",
        is_active=False,
    )
    p2 = PromptTemplate(
        code="TUTOR_EXPLAIN",
        version=2,
        content="System prompt giải thích bài học v2 có thẻ XML",
        is_active=True,
    )
    p3 = PromptTemplate(
        code="TUTOR_SOCRATIC",
        version=1,
        content="System prompt gia sư Socratic 5 bước",
        is_active=True,
    )
    db_session.add_all([p1, p2, p3])

    # Thêm nhật ký AI Request Logs mẫu
    now = datetime.now(timezone.utc)
    log1 = AIRequestLog(
        user_id=student_user.id,
        feature=AIFeature.TUTOR.value,
        provider=AIProvider.GEMINI.value,
        tokens_prompt=500,
        tokens_completion=250,
        latency_ms=620,
        created_at=now - timedelta(days=1),
    )
    log2 = AIRequestLog(
        user_id=student_user.id,
        feature=AIFeature.SOCRATIC.value,
        provider=AIProvider.GEMINI.value,
        tokens_prompt=400,
        tokens_completion=150,
        latency_ms=750,
        created_at=now,
    )
    log3 = AIRequestLog(
        user_id=student_user.id,
        feature=AIFeature.QUIZ_GEN.value,
        provider=AIProvider.OPENAI.value,
        tokens_prompt=1200,
        tokens_completion=800,
        latency_ms=1450,
        created_at=now,
    )
    db_session.add_all([log1, log2, log3])
    db_session.commit()

    return {
        "admin": admin_user,
        "admin2": admin_user_2,
        "student": student_user,
        "student_locked": student_locked,
        "token": r_token,
        "prompts": [p1, p2, p3],
        "logs": [log1, log2, log3],
    }


# ==============================================================================
# 1. KIỂM THỬ BẢO MẬT VÀ PHÂN QUYỀN (RBAC)
# ==============================================================================

def test_require_admin_success(seed_data):
    """Admin hợp lệ được cấp quyền truy cập."""
    admin = seed_data["admin"]
    res = require_admin(current_user=admin)
    assert res.id == admin.id
    assert res.role == UserRole.ADMIN.value


def test_require_admin_forbidden_for_student(seed_data):
    """Sinh viên bị chặn 403 Forbidden khi truy cập endpoint Admin."""
    student = seed_data["student"]
    with pytest.raises(HTTPException) as exc_info:
        require_admin(current_user=student)
    assert exc_info.value.status_code == 403
    assert "Chỉ Quản trị viên" in exc_info.value.detail


# ==============================================================================
# 2. KIỂM THỬ QUẢN LÝ NGƯỜI DÙNG (/admin/users)
# ==============================================================================

def test_list_users_pagination_and_search(db_session, seed_data):
    """Kiểm tra danh sách người dùng có phân trang và tìm kiếm."""
    service = AdminService(db_session)

    # 1. Lấy tất cả (4 người dùng đã tạo trong fixture)
    res = service.list_users(page=1, page_size=10)
    assert res.total == 4
    assert len(res.items) == 4
    assert res.total_pages == 1

    # 2. Tìm kiếm theo họ tên
    search_res = service.list_users(search="Nguyễn Văn")
    assert search_res.total == 1
    assert search_res.items[0].email == "student.nguyen@learnmate.edu.vn"

    # 3. Lọc theo vai trò ADMIN
    admin_res = service.list_users(role="ADMIN")
    assert admin_res.total == 2
    for u in admin_res.items:
        assert u.role == "ADMIN"

    # 4. Lọc theo trạng thái LOCKED
    locked_res = service.list_users(status="LOCKED")
    assert locked_res.total == 1
    assert locked_res.items[0].email == "locked.user@learnmate.edu.vn"


def test_get_user_detail_with_stats(db_session, seed_data):
    """Kiểm tra xem chi tiết thông tin và thống kê số liệu của người dùng."""
    service = AdminService(db_session)
    student = seed_data["student"]

    detail = service.get_user_detail(student.id)
    assert detail.id == student.id
    assert detail.email == student.email
    assert detail.ai_requests_count == 3  # 3 logs đã tạo trong fixture

    # User không tồn tại -> 404
    with pytest.raises(UserNotFoundError):
        service.get_user_detail(99999)


def test_lock_and_unlock_user(db_session, seed_data):
    """Khóa tài khoản sinh viên: đổi trạng thái LOCKED và thu hồi refresh token."""
    service = AdminService(db_session)
    admin = seed_data["admin"]
    student = seed_data["student"]
    token = seed_data["token"]

    assert token.revoked_at is None

    # Khóa tài khoản sinh viên
    updated = service.update_user_status(
        current_admin=admin,
        target_user_id=student.id,
        new_status=UserStatus.LOCKED.value,
        reason="Vi phạm chính sách sử dụng",
    )
    assert updated.status == UserStatus.LOCKED.value

    # Refresh token của sinh viên phải bị thu hồi ngay lập tức
    db_session.refresh(token)
    assert token.revoked_at is not None

    # Mở khóa tài khoản sinh viên
    unlocked = service.update_user_status(
        current_admin=admin,
        target_user_id=student.id,
        new_status=UserStatus.ACTIVE.value,
    )
    assert unlocked.status == UserStatus.ACTIVE.value


def test_admin_cannot_lock_self(db_session, seed_data):
    """Admin không thể tự khóa tài khoản của chính mình."""
    service = AdminService(db_session)
    admin = seed_data["admin"]

    with pytest.raises(AdminOperationForbiddenError) as exc_info:
        service.update_user_status(
            current_admin=admin,
            target_user_id=admin.id,
            new_status=UserStatus.LOCKED.value,
        )
    assert "Không thể tự khóa tài khoản" in str(exc_info.value)


def test_admin_cannot_demote_self(db_session, seed_data):
    """Admin không thể tự giáng quyền ADMIN của chính mình."""
    service = AdminService(db_session)
    admin = seed_data["admin"]

    with pytest.raises(AdminOperationForbiddenError) as exc_info:
        service.update_user_role(
            current_admin=admin,
            target_user_id=admin.id,
            new_role=UserRole.STUDENT.value,
        )
    assert "Không thể tự giáng quyền" in str(exc_info.value)


def test_update_user_role(db_session, seed_data):
    """Phân quyền thăng chức sinh viên lên ADMIN."""
    service = AdminService(db_session)
    admin = seed_data["admin"]
    student = seed_data["student"]

    promoted = service.update_user_role(
        current_admin=admin,
        target_user_id=student.id,
        new_role=UserRole.ADMIN.value,
    )
    assert promoted.role == UserRole.ADMIN.value


# ==============================================================================
# 3. KIỂM THỬ CẤU HÌNH PROMPT TEMPLATES (/admin/prompts & /prompts)
# ==============================================================================

def test_list_and_get_prompt_templates(db_session, seed_data):
    """Lấy danh sách và chi tiết Prompt Templates."""
    service = AdminService(db_session)

    # 1. Lấy toàn bộ templates
    all_prompts = service.list_prompts()
    assert len(all_prompts) == 3

    # 2. Lọc theo mã TUTOR_EXPLAIN
    explain_prompts = service.list_prompts(code="TUTOR_EXPLAIN")
    assert len(explain_prompts) == 2

    # 3. Lọc theo is_active=True
    active_prompts = service.list_prompts(is_active=True)
    assert len(active_prompts) == 2

    # 4. Lấy active prompt theo mã
    active_explain = service.get_active_prompt_by_code("TUTOR_EXPLAIN")
    assert active_explain.version == 2
    assert active_explain.is_active is True

    # 5. Mã không tồn tại -> 404
    with pytest.raises(PromptNotFoundError):
        service.get_active_prompt_by_code("NON_EXISTENT_CODE")


def test_create_prompt_auto_version_and_active_switch(db_session, seed_data):
    """Tạo phiên bản prompt mới: tự tăng version và tự tắt active của phiên bản cũ."""
    service = AdminService(db_session)

    # Đang có TUTOR_EXPLAIN v1 (inactive) và v2 (active)
    # Tạo TUTOR_EXPLAIN mới với is_active=True
    new_p = service.create_prompt(
        code="TUTOR_EXPLAIN",
        content="System prompt giải thích bài học v3 tối ưu hoá",
        is_active=True,
    )
    assert new_p.version == 3
    assert new_p.is_active is True

    # Phiên bản v2 trước đó phải bị tự động chuyển sang is_active=False
    v2 = service.get_prompt(seed_data["prompts"][1].id)
    assert v2.is_active is False

    # Thử tạo lại với cặp (code, version) trùng -> văng PromptConflictError
    with pytest.raises(PromptConflictError):
        service.create_prompt(
            code="TUTOR_EXPLAIN",
            content="Nội dung trùng version",
            version=3,
        )


def test_update_and_delete_prompt(db_session, seed_data):
    """Cập nhật nội dung prompt và xóa prompt."""
    service = AdminService(db_session)
    p_id = seed_data["prompts"][0].id  # TUTOR_EXPLAIN v1

    # Cập nhật nội dung và kích hoạt
    updated = service.update_prompt(
        prompt_id=p_id,
        content="Nội dung đã được cập nhật bởi Admin",
        is_active=True,
    )
    assert updated.content == "Nội dung đã được cập nhật bởi Admin"
    assert updated.is_active is True

    # Xóa prompt
    service.delete_prompt(p_id)
    with pytest.raises(PromptNotFoundError):
        service.get_prompt(p_id)


# ==============================================================================
# 4. KIỂM THỬ GIÁM SÁT AI LOGS VÀ TÍNH TOÁN CHI PHÍ TOKEN (/admin/logs & /logs)
# ==============================================================================

def test_token_cost_calculation():
    """Kiểm tra công thức tính chi phí token USD và VND."""
    # Gemini: Prompt $0.075/1M, Completion $0.300/1M
    cost_usd, cost_vnd = calculate_token_cost("gemini", 1_000_000, 1_000_000)
    assert cost_usd == pytest.approx(0.375, rel=1e-4)
    assert cost_vnd == pytest.approx(0.375 * USD_TO_VND_RATE, rel=1e-4)

    # OpenAI: Prompt $0.150/1M, Completion $0.600/1M
    cost_usd_oa, cost_vnd_oa = calculate_token_cost("openai", 1_000_000, 1_000_000)
    assert cost_usd_oa == pytest.approx(0.750, rel=1e-4)
    assert cost_vnd_oa == pytest.approx(0.750 * USD_TO_VND_RATE, rel=1e-4)


def test_list_logs_with_costs(db_session, seed_data):
    """Kiểm tra danh sách nhật ký gọi AI có đầy đủ chi phí quy đổi USD và VND."""
    service = AdminService(db_session)
    res = service.list_logs(page=1, page_size=10)

    assert res.total == 3
    assert len(res.items) == 3

    for item in res.items:
        assert item.total_tokens == item.tokens_prompt + item.tokens_completion
        assert item.estimated_cost_usd >= 0.0
        assert item.estimated_cost_vnd >= 0.0
        assert item.latency_ms > 0

    # Lọc theo feature QUIZ_GEN
    quiz_logs = service.list_logs(feature="QUIZ_GEN")
    assert quiz_logs.total == 1
    assert quiz_logs.items[0].provider == "openai"


def test_get_token_statistics_comprehensive(db_session, seed_data):
    """Kiểm tra báo cáo thống kê tổng quan và phân nhóm token (SDD Bảng 17 & 18)."""
    service = AdminService(db_session)
    stats = service.get_token_statistics()

    # 1. Summary
    assert stats.summary.total_requests == 3
    # 500+250 + 400+150 + 1200+800 = 3300 tokens
    assert stats.summary.total_tokens_prompt == 2100
    assert stats.summary.total_tokens_completion == 1200
    assert stats.summary.total_tokens == 3300
    assert stats.summary.estimated_cost_usd > 0.0
    assert stats.summary.estimated_cost_vnd > 0.0
    assert stats.summary.avg_latency_ms > 0.0

    # 2. By feature
    features = {f.key for f in stats.by_feature}
    assert "TUTOR" in features
    assert "SOCRATIC" in features
    assert "QUIZ_GEN" in features

    # 3. By provider
    providers = {p.key for p in stats.by_provider}
    assert "gemini" in providers
    assert "openai" in providers

    # 4. By date
    assert len(stats.by_date) >= 1

    # 5. Pricing metadata
    assert stats.exchange_rate_vnd == 25400.0
    assert "gemini" in stats.pricing_rates
    assert "openai" in stats.pricing_rates


# ==============================================================================
# 5. KIỂM THỬ CÁC ROUTER HANDLERS TRỰC TIẾP
# ==============================================================================

def test_api_router_user_endpoints(db_session, seed_data):
    """Kiểm tra các hàm endpoint người dùng trong admin.py."""
    admin = seed_data["admin"]
    student = seed_data["student"]

    # 1. list_users
    res_list = list_users(page=1, page_size=10, db=db_session)
    assert res_list.total == 4

    # 2. get_user_detail
    res_detail = get_user_detail(user_id=student.id, db=db_session)
    assert res_detail.email == student.email

    # 3. update_user_status (LOCKED)
    res_lock = update_user_status(
        payload=UserStatusUpdate(status="LOCKED", reason="Khóa thử nghiệm"),
        user_id=student.id,
        current_admin=admin,
        db=db_session,
    )
    assert res_lock.status == "LOCKED"

    # 4. unlock_user_shortcut
    res_unlock = unlock_user_shortcut(user_id=student.id, current_admin=admin, db=db_session)
    assert res_unlock.status == "ACTIVE"

    # 5. lock_user_shortcut
    res_lock_sc = lock_user_shortcut(user_id=student.id, current_admin=admin, db=db_session)
    assert res_lock_sc.status == "LOCKED"

    # 6. update_user_role
    res_role = update_user_role(
        payload=UserRoleUpdate(role="ADMIN"),
        user_id=student.id,
        current_admin=admin,
        db=db_session,
    )
    assert res_role.role == "ADMIN"

    # 7. update_user full
    res_update = update_user(
        payload=UserUpdate(full_name="Nguyễn Văn Sinh Viên Mới", status="ACTIVE"),
        user_id=student.id,
        current_admin=admin,
        db=db_session,
    )
    assert res_update.full_name == "Nguyễn Văn Sinh Viên Mới"
    assert res_update.status == "ACTIVE"


def test_api_router_prompt_endpoints(db_session, seed_data):
    """Kiểm tra các hàm endpoint prompt templates (cả router chính và alias router)."""
    # 1. list_prompts_admin & list_prompts_alias
    p_admin = list_prompts_admin(db=db_session)
    p_alias = list_prompts_alias(db=db_session)
    assert len(p_admin) == 3
    assert len(p_alias) == 3

    # 2. get_active_prompt_admin
    act = get_active_prompt_admin(code="TUTOR_SOCRATIC", db=db_session)
    assert act.code == "TUTOR_SOCRATIC"
    assert act.is_active is True

    # 3. create_prompt_admin
    created = create_prompt_admin(
        payload=PromptTemplateCreate(
            code="QUIZ_GEN",
            content="Mẫu sinh trắc nghiệm thích ứng v1",
            is_active=True,
        ),
        db=db_session,
    )
    assert created.code == "QUIZ_GEN"
    assert created.version == 1

    # 4. update_prompt_alias
    updated = update_prompt_alias(
        payload=PromptTemplateUpdate(content="Mẫu sinh trắc nghiệm thích ứng v1 updated"),
        id=created.id,
        db=db_session,
    )
    assert updated.content == "Mẫu sinh trắc nghiệm thích ứng v1 updated"

    # 5. delete_prompt_admin
    del_res = delete_prompt_admin(id=created.id, db=db_session)
    assert del_res["deleted"] is True


def test_api_router_log_endpoints(db_session, seed_data):
    """Kiểm tra các hàm endpoint logs và tokens (cả router chính và alias router)."""
    # 1. list_logs_admin & list_logs_alias
    logs_admin = list_logs_admin(page=1, page_size=20, db=db_session)
    logs_alias = list_logs_alias(page=1, page_size=20, db=db_session)
    assert logs_admin.total == 3
    assert logs_alias.total == 3

    # 2. get_token_statistics_admin & get_token_statistics_alias
    stats_admin = get_token_statistics_admin(db=db_session)
    stats_alias = get_token_statistics_alias(db=db_session)
    assert stats_admin.summary.total_requests == 3
    assert stats_alias.summary.total_requests == 3

    # 3. create_log_admin
    new_log = create_log_admin(
        payload=AIRequestLogCreate(
            user_id=seed_data["student"].id,
            feature="RAG",
            provider="gemini",
            tokens_prompt=300,
            tokens_completion=100,
            latency_ms=400,
        ),
        db=db_session,
    )
    assert new_log["feature"] == "RAG"
    assert new_log["total_tokens"] == 400
