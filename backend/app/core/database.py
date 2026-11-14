import logging
from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

logger = logging.getLogger("uvicorn.error")

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def ensure_database_exists():
    """Tu dong kiem tra va tao database neu chua ton tai (ho tro MySQL)."""
    try:
        url = make_url(settings.DATABASE_URL)
        if url.drivername.startswith("mysql"):
            # Ket noi den MySQL server khong kem ten DB de thuc thi lenh tao CSDL
            server_url = url.set(database="")
            temp_engine = create_engine(server_url, isolation_level="AUTOCOMMIT")
            with temp_engine.connect() as conn:
                conn.execute(
                    text(f"CREATE DATABASE IF NOT EXISTS `{url.database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
                )
            temp_engine.dispose()
    except Exception as e:
        logger.warning(f"[DB Auto-Create] Khong the tu dong tao database: {e}")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_session_factory() -> sessionmaker:
    """Factory tao Session moi, dung cho tac vu chay sau khi request da tra ve (vd: SSE stream)."""
    return SessionLocal
