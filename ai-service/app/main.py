from fastapi import FastAPI
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.routers.health_router import router as health_router
from app.routers.tutor_router import router as tutor_router
from app.routers.quiz_router import router as quiz_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="LearnMate AI - Stateless AI Microservice",
)

register_exception_handlers(app)

app.include_router(health_router)
app.include_router(tutor_router)
app.include_router(quiz_router)


@app.get("/")
def root():
    return {
        "message": "Welcome to LearnMate AI - AI Microservice",
        "health": "/ai/health",
    }
