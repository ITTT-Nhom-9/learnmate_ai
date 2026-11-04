from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import Base, engine
import app.models  # Đăng ký toàn bộ 7 bảng ORM vào Base.metadata
from app.api.api_v1 import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tự động tạo các bảng CSDL nếu chưa tồn tại khi khởi động backend
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"Lưu ý: Không thể tự động tạo bảng (có thể do CSDL chưa khởi động): {e}")
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

