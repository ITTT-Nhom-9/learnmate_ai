from fastapi import APIRouter

from app.api import auth, courses

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(courses.router)


@api_router.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": "backend-core",
        "version": "1.0.0"
    }
