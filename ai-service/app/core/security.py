import hmac
from fastapi import HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from app.core.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_internal_api_key(api_key: str = Security(api_key_header)) -> str:
    """Xác thực Header X-API-Key cho các yêu cầu nội bộ từ Backend Core."""
    expected_key = (settings.INTERNAL_API_KEY or "").strip()
    if not expected_key or expected_key in {
        "LM_Internal_Key_987654",
        "your_internal_api_key_for_microservice_calls",
    }:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Internal authentication is unavailable",
        )

    if not api_key or not hmac.compare_digest(api_key.encode("utf-8"), expected_key.encode("utf-8")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key for internal AI service",
        )
    return api_key
