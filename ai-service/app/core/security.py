import hmac
from fastapi import HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from app.core.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_internal_api_key(api_key: str = Security(api_key_header)) -> str:
    """Xác thực Header X-API-Key cho các yêu cầu nội bộ từ Backend Core."""
    expected_key = (settings.INTERNAL_API_KEY or "").strip()
    if not expected_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="INTERNAL_API_KEY is not configured on AI service",
        )

    if not api_key or not hmac.compare_digest(api_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key for internal AI service",
        )
    return api_key
