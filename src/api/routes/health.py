"""
System health and monitoring endpoints
"""
from typing import Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
import structlog

from ...database.connection import get_db, db
from ..auth import get_current_user

logger = structlog.get_logger()

router = APIRouter()

class SystemHealth(BaseModel):
    status: str
    timestamp: datetime
    database: Dict[str, Any]
    api: Dict[str, Any]
    
class DatabaseHealth(BaseModel):
    connected: bool
    pool_status: Dict[str, Any]
    response_time_ms: float

@router.get("/health", response_model=SystemHealth)
async def system_health():
    """Comprehensive system health check"""
    start_time = datetime.now()
    
    # Database health
    db_healthy = db.health_check()
    pool_status = db.get_pool_status()
    db_response_time = (datetime.now() - start_time).total_seconds() * 1000
    
    return SystemHealth(
        status="healthy" if db_healthy else "unhealthy",
        timestamp=datetime.now(),
        database={
            "connected": db_healthy,
            "pool": pool_status,
            "response_time_ms": db_response_time
        },
        api={
            "status": "operational",
            "uptime_ms": db_response_time
        }
    )

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
        
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return DatabaseHealth(
            connected=False,
            pool_status={},
            response_time_ms=-1
        )