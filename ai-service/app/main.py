from fastapi import FastAPI
from app.core.config import settings
from app.routers.health_router import router as health_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="LearnMate AI - Stateless AI Microservice"
)

app.include_router(health_router)


@app.get("/")
def root():
    return {
        "message": "Welcome to LearnMate AI - AI Microservice",
        "health": "/ai/health"
    }

