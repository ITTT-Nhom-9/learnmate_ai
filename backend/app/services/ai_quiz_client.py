"""Client gọi AI Microservice nội bộ (POST /ai/quiz/generate) để sinh đề trắc nghiệm."""
import httpx

from app.core.config import settings


class AIQuizServiceError(Exception):
    def __init__(self, error_code: str, message: str, status_code: int = 502):
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.status_code = status_code


class AIQuizClient:
    GENERATE_PATH = "/ai/quiz/generate"

    def __init__(self, base_url: str, api_key: str, timeout: float = 45.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    async def generate_quiz(self, payload: dict) -> dict:
        """Gửi yêu cầu sinh đề thi trắc nghiệm sang AI Microservice và nhận kết quả."""
        timeout = httpx.Timeout(self.timeout, connect=5.0)
        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=timeout) as client:
                response = await client.post(
                    self.GENERATE_PATH,
                    json=payload,
                    headers={"X-API-Key": self.api_key, "Content-Type": "application/json"},
                )
                if response.status_code != 200:
                    try:
                        err_body = response.json()
                        detail = err_body.get("detail") or "Dịch vụ AI gặp lỗi khi sinh đề"
                    except Exception:
                        detail = response.text or f"Mã lỗi HTTP {response.status_code}"
                    raise AIQuizServiceError("AI_QUIZ_ERROR", detail, status_code=response.status_code)

                return response.json()
        except httpx.HTTPError:
            raise AIQuizServiceError(
                "AI_SERVICE_UNAVAILABLE",
                "Không kết nối được tới dịch vụ AI Microservice để sinh câu hỏi",
                status_code=503,
            )


def get_ai_quiz_client() -> AIQuizClient:
    """Dependency cung cấp AIQuizClient (dễ override khi viết unit test)."""
    return AIQuizClient(
        base_url=settings.AI_SERVICE_URL,
        api_key=settings.INTERNAL_API_KEY,
        timeout=settings.AI_SERVICE_TIMEOUT_SECONDS,
    )
