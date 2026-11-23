import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import inspect, text
from app.core.config import settings
from app.core.database import Base, engine, ensure_database_exists
import app.models  # Dang ky toan bo 7 bang ORM vao Base.metadata
from app.api.api_v1 import api_router

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tu dong kiem tra, tao database va dong bo CSDL khi khoi dong backend
    try:
        ensure_database_exists()
        Base.metadata.create_all(bind=engine)

        # Tu dong kiem tra va bo sung cot moi vao bang da ton tai (vi create_all khong tu ALTER TABLE)
        with engine.begin() as conn:
            inspector = inspect(conn)
            all_tables = inspector.get_table_names()
            if "attempt_answers" in all_tables:
                existing_cols = [c["name"] for c in inspector.get_columns("attempt_answers")]
                if "is_correct" not in existing_cols:
                    conn.execute(text("ALTER TABLE attempt_answers ADD COLUMN is_correct BOOLEAN DEFAULT 0 NOT NULL;"))
                    logger.info("[Database] Da tu dong bo sung cot is_correct vao bang attempt_answers.")

            # Ho tro view alias cho Excel (user_topic_mastery, student_activity_logs) va SDD
            if "topic_mastery" in all_tables and "user_topic_mastery" not in all_tables:
                conn.execute(text("CREATE OR REPLACE VIEW user_topic_mastery AS SELECT * FROM topic_mastery;"))
            if "learning_events" in all_tables and "student_activity_logs" not in all_tables:
                conn.execute(text("CREATE OR REPLACE VIEW student_activity_logs AS SELECT * FROM learning_events;"))

        tables = list(Base.metadata.tables.keys())
        logger.info(f"[Database] Ket noi CSDL thanh cong tai port {settings.MYSQL_HOST_PORT}.")
        logger.info(f"[Database] Da kiem tra va dong bo {len(tables)} bang: {', '.join(tables)}")
    except Exception as exc:
        logger.error("[Database] Khoi tao CSDL that bai (%s)", type(exc).__name__)
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

@app.exception_handler(RequestValidationError)
async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": [
            {"loc": error["loc"], "type": error["type"], "msg": "Invalid request field"}
            for error in exc.errors()
        ]},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["Retry-After"],
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
