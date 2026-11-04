from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(prefix="/ai", tags=["Health"])


@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "ai-microservice",
        "provider": settings.LLM_PROVIDER,
        "model": settings.LLM_MODEL
    }

