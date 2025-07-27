from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from typing import Generator
from pydantic import BaseSettings


class Settings(BaseSettings):
    """Configuration settings for the database connection."""
    database_url: str = "postgresql+psycopg2://postgres:postgres@postgres:5432/wealth"
    pool_size: int = 20
    max_overflow: int = 40
    pool_timeout: int = 30
    pool_recycle: int = 1800

    class Config:
        env_prefix = "DB_"


settings = Settings()

# Create the SQLAlchemy engine with connection pooling.
engine = create_engine(
    settings.database_url,
    pool_size=settings.pool_size,
    max_overflow=settings.max_overflow,
    pool_timeout=settings.pool_timeout,
    pool_recycle=settings.pool_recycle,
)

# Create a configured "Session" class.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db() -> Generator:
    """
    Yield a database session to be used within a request scope.
    Ensures that each session is committed or rolled back appropriately.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def create_tables() -> None:
    """Create database tables based on SQLAlchemy models."""
    from .models import Base

    Base.metadata.create_all(bind=engine)
