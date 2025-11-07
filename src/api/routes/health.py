"""
System health and monitoring endpoints
"""
from typing import Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from src.logging_config import logger

from ...database.connection import get_db, db
from ..auth import get_current_user


router = APIRouter()


@router.get("/health")
async def system_health() -> Dict[str, str]:
    """Lightweight health endpoint compatible with legacy checks."""

    status = "ok" if db.health_check() else "degraded"
    return {"status": status}


class DatabaseHealth(BaseModel):
    connected: bool
    pool_status: Dict[str, Any]
    response_time_ms: float

@router.get("/database", response_model=DatabaseHealth)
async def database_health(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db)
):
    """Detailed database health check"""
    start_time = datetime.now()
    
    try:
        # Test database query
        from sqlalchemy import text
        session.execute(text("SELECT 1"))
        
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        pool_status = db.get_pool_status()
        
        return DatabaseHealth(
            connected=True,
            pool_status=pool_status,
            response_time_ms=response_time
        )
        
    except SQLAlchemyError as e:
        logger.error("Database health check failed", error=str(e))
        return DatabaseHealth(
            connected=False,
            pool_status={},
            response_time_ms=-1
        )
    except Exception as e:
        logger.exception("Unexpected error during database health check")
        return DatabaseHealth(
            connected=False,
            pool_status={},
            response_time_ms=-1
        )