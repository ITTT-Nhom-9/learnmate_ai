from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(prefix="/ai", tags=["Health"])


@router.get(
    "/health",
    summary="Kiểm tra trạng thái hoạt động của AI Microservice",
    description=(
        "Cách hoạt động:\n"
        "1. Endpoint công khai phục vụ Docker healthcheck và giám sát dịch vụ.\n"
        "2. Đọc cấu hình `LLM_PROVIDER`, `LLM_MODEL` hiện hành và kiểm tra đã nạp API Key hay chưa (chỉ trả boolean, không lộ khóa bí mật)."
    ),
)
def health_check():
    provider = (settings.LLM_PROVIDER or "gemini").strip().lower()
    if provider == "openai":
        api_key_configured = bool((settings.OPENAI_API_KEY or "").strip())
    else:
        api_key_configured = bool((settings.GEMINI_API_KEY or "").strip())

    return {
        "status": "healthy",
        "service": "ai-microservice",
        "provider": provider,
        "model": settings.LLM_MODEL,
        "api_key_configured": api_key_configured,
    }
