import json
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, sessionmaker
from starlette.concurrency import run_in_threadpool

from app.api.deps import get_current_user
from app.core.database import get_db, get_session_factory
from app.models.user import User
from app.schemas.tutor import ChatMessageItem, TutorChatRequest, TutorHistoryResponse
from app.services.ai_tutor_client import AIServiceError, AITutorClient, get_ai_tutor_client
from app.services.quota_guard import QuotaExceededError
from app.services.tutor_service import PreparedTurn, TutorError, TutorService

router = APIRouter(prefix="/tutor", tags=["AI Tutor"])

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post(
    "/chat",
    summary="API-09: Chat với gia sư AI (Streaming SSE), lưu lịch sử và QuotaGuard 50 câu/ngày (BR-05)",
    description=(
        "Trả về `text/event-stream`:\n"
        "- `event: message` → `{token, hint_level, is_concluded}` cho từng mảnh chữ\n"
        "- `event: done` → `{message_id, session_id, tokens_used, quota_remaining}`\n"
        "- `event: error` → `{error_code, detail}` khi dịch vụ AI gặp lỗi (lượt hỏi được hoàn lại)\n\n"
        "Lỗi trước khi stream: 401/403 xác thực, 404 bài học không tồn tại, "
        "422 dữ liệu không hợp lệ, 429 hết hạn ngạch 50 câu/ngày."
    ),
    responses={
        200: {"content": {"text/event-stream": {}}},
        404: {"description": "Bài học không tồn tại"},
        429: {"description": "Hết hạn ngạch 50 câu hỏi/ngày (BR-05)"},
    },
)
def chat(
    payload: TutorChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    session_factory: sessionmaker = Depends(get_session_factory),
    ai_client: AITutorClient = Depends(get_ai_tutor_client),
):
    try:
        turn = TutorService(db).prepare_turn(current_user, payload.lesson_id, payload.message, payload.mode)
    except QuotaExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=exc.message,
            headers={"Retry-After": str(exc.retry_after_seconds())},
        )
    except TutorError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    return StreamingResponse(
        _stream_reply(turn, ai_client, session_factory),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


async def _stream_reply(
    turn: PreparedTurn, ai_client: AITutorClient, session_factory: sessionmaker
) -> AsyncIterator[str]:
    # Session cua request (get_db) co the da dong khi body dang stream -> mo session rieng.
    def _save(content: str, tokens: int) -> int:
        with session_factory() as db:
            return TutorService(db).save_reply(turn, content, tokens)

    def _cancel() -> None:
        with session_factory() as db:
            TutorService(db).cancel_turn(turn)

    parts: list[str] = []
    tokens_used = 0
    finished = False
    try:
        try:
            async for chunk in ai_client.stream(turn.ai_payload):
                if chunk.delta:
                    parts.append(chunk.delta)
                    yield sse("message", {
                        "token": chunk.delta,
                        "hint_level": turn.hint_level,
                        "is_concluded": turn.is_concluded,
                    })
                if chunk.done:
                    tokens_used = chunk.total_tokens
        except AIServiceError as exc:
            finished = True
            if parts:
                # Da co mot phan cau tra loi: van luu lai de lich su khop voi nhung gi SV da thay
                await run_in_threadpool(_save, "".join(parts), tokens_used)
            else:
                await run_in_threadpool(_cancel)
            yield sse("error", {"error_code": exc.error_code, "detail": exc.message})
            return

        content = "".join(parts).strip()
        finished = True
        if not content:
            await run_in_threadpool(_cancel)
            yield sse("error", {"error_code": "EMPTY_RESPONSE", "detail": "AI không trả về nội dung"})
            return

        message_id = await run_in_threadpool(_save, content, tokens_used)
        yield sse("done", {
            "message_id": message_id,
            "session_id": turn.session_id,
            "tokens_used": tokens_used,
            "quota_remaining": turn.quota_remaining,
            "hint_level": turn.hint_level,
            "is_concluded": turn.is_concluded,
        })
    finally:
        # Client ngat ket noi giua chung: luu phan da nhan, hoac hoan quota neu chua co gi
        if not finished:
            if parts:
                _save("".join(parts), tokens_used)
            else:
                _cancel()


@router.get(
    "/history/{lesson_id}",
    response_model=TutorHistoryResponse,
    summary="API-10: Lấy lịch sử tin nhắn của phiên chat gần nhất trong bài học",
)
def get_history(
    lesson_id: int = Path(..., ge=1),
    limit: int = Query(20, ge=1, le=100, description="Số tin nhắn gần nhất (tối đa 100)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        session, messages, quota_remaining = TutorService(db).get_history(current_user, lesson_id, limit)
    except TutorError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    return TutorHistoryResponse(
        session_id=session.id if session else None,
        lesson_id=lesson_id,
        mode=session.mode if session else None,
        hint_level=session.hint_level if session else 0,
        status=session.status if session else None,
        quota_remaining=quota_remaining,
        messages=[ChatMessageItem.model_validate(m) for m in messages],
    )
