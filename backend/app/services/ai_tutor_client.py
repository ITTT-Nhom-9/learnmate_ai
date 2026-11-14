"""Client goi AI Microservice noi bo (POST /ai/tutor/stream) va doc luong SSE tra ve."""
import json
from dataclasses import dataclass
from typing import AsyncIterator

import httpx

from app.core.config import settings


class AIServiceError(Exception):
    def __init__(self, error_code: str, message: str):
        super().__init__(message)
        self.error_code = error_code
        self.message = message


@dataclass
class AIStreamChunk:
    delta: str = ""
    done: bool = False
    tokens_prompt: int = 0
    tokens_completion: int = 0
    total_tokens: int = 0


class AITutorClient:
    STREAM_PATH = "/ai/tutor/stream"

    def __init__(self, base_url: str, api_key: str, timeout: float):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    async def stream(self, payload: dict) -> AsyncIterator[AIStreamChunk]:
        timeout = httpx.Timeout(self.timeout, connect=5.0)
        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=timeout) as client:
                async with client.stream(
                    "POST",
                    self.STREAM_PATH,
                    json=payload,
                    headers={"X-API-Key": self.api_key, "Accept": "text/event-stream"},
                ) as response:
                    if response.status_code != 200:
                        await response.aread()
                        raise AIServiceError(
                            "AI_SERVICE_ERROR",
                            f"AI service trả về mã lỗi {response.status_code}",
                        )
                    async for chunk in self._parse_sse(response.aiter_lines()):
                        yield chunk
        except httpx.HTTPError:
            raise AIServiceError("AI_SERVICE_UNAVAILABLE", "Không kết nối được tới dịch vụ AI")

    @staticmethod
    async def _parse_sse(lines: AsyncIterator[str]) -> AsyncIterator[AIStreamChunk]:
        event = "message"
        async for line in lines:
            if not line:
                event = "message"
                continue
            if line.startswith("event:"):
                event = line[len("event:"):].strip()
                continue
            if not line.startswith("data:"):
                continue
            try:
                data = json.loads(line[len("data:"):].strip())
            except json.JSONDecodeError:
                continue
            if event == "error":
                raise AIServiceError(
                    data.get("error_code") or "AI_STREAM_ERROR",
                    data.get("detail") or "Dịch vụ AI gặp lỗi khi sinh câu trả lời",
                )
            yield AIStreamChunk(
                delta=data.get("delta") or "",
                done=bool(data.get("done")),
                tokens_prompt=int(data.get("tokens_prompt") or 0),
                tokens_completion=int(data.get("tokens_completion") or 0),
                total_tokens=int(data.get("total_tokens") or 0),
            )


def get_ai_tutor_client() -> AITutorClient:
    """Dependency (de override khi test)."""
    return AITutorClient(
        base_url=settings.AI_SERVICE_URL,
        api_key=settings.INTERNAL_API_KEY,
        timeout=settings.AI_SERVICE_TIMEOUT_SECONDS,
    )
