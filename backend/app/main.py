import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import Base, engine, ensure_database_exists
import app.models  # Dang ky toan bo 7 bang ORM vao Base.metadata
from app.api.api_v1 import api_router

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tu dong kiem tra, tao database va 7 bang CSDL khi khoi dong backend
    try:
        ensure_database_exists()
        Base.metadata.create_all(bind=engine)
        tables = list(Base.metadata.tables.keys())
        logger.info(f"[Database] Ket noi CSDL thanh cong tai port {settings.MYSQL_HOST_PORT}.")
        logger.info(f"[Database] Da kiem tra va dong bo {len(tables)} bang: {', '.join(tables)}")
    except Exception as e:
        logger.error(f"[Database ERROR] Khong the khoi tao bang CSDL: {e}")
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="LearnMate AI - Backend Core Service API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Welcome to LearnMate AI Backend Core Service",
        "docs": f"{settings.API_V1_STR}/docs",
        "health": f"{settings.API_V1_STR}/health"
    }
