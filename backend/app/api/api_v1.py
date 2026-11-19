from fastapi import APIRouter

from app.api import auth, courses, progress, quizzes, rag, tutor

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(courses.router)
api_router.include_router(progress.router)
api_router.include_router(rag.router, prefix="/rag")
api_router.include_router(tutor.router)
api_router.include_router(quizzes.router)
api_router.include_router(quizzes.alias_router)


@api_router.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": "backend-core",
        "version": "1.0.0"
    }
