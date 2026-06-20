"""
database.py — Database engine, session factory, and initialization.
"""

from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from backend.config import settings

# Construct absolute path for SQLite to avoid CWD issues
if settings.DATABASE_URL.startswith("sqlite:///./"):
    db_name = settings.DATABASE_URL.replace("sqlite:///./", "")
    BASE_DIR = Path(__file__).resolve().parent.parent
    # Convert Windows Path to standard URI format for SQLAlchemy
    db_path = (BASE_DIR / db_name).as_posix()
    DATABASE_URL = f"sqlite:///{db_path}"
else:
    DATABASE_URL = settings.DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


def get_db():
    """FastAPI dependency that provides a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables defined on Base metadata."""
    # Import models here to ensure they are registered on Base before create_all
    from backend import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
