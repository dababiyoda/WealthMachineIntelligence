"""
Digital ventures API endpoints
CRUD operations and business logic for digital business opportunities
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from src.logging_config import logger

from ...database.connection import session_dependency as get_db
from ...database.models import DigitalVenture, VentureType, VentureStatus, RiskLevel
from ..auth import get_current_user


router = APIRouter()

# Pydantic models for API
class VentureBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    venture_type: VentureType
    initial_investment: Optional[float] = Field(default=0.0, ge=0)

class VentureCreate(VentureBase):
    pass

class VentureUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[VentureStatus] = None
    monthly_revenue: Optional[float] = Field(None, ge=0)
    monthly_expenses: Optional[float] = Field(None, ge=0)
    customer_count: Optional[int] = Field(None, ge=0)
    churn_rate: Optional[float] = Field(None, ge=0, le=1)

class VentureResponse(VentureBase):
    id: str
    status: VentureStatus
    current_valuation: float
    monthly_revenue: float
    monthly_expenses: float
    profit_margin: float
    risk_level: RiskLevel
    risk_score: float
    risk_semantics: str = "uncalibrated_heuristic_index"
    evidence_status: str = "unverified_local_record"
    customer_count: int
    churn_rate: float
    growth_rate: float
    ai_enabled: bool
    automation_level: float
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)

class VentureList(BaseModel):
    ventures: List[VentureResponse]
    total: int
    page: int
    size: int

@router.post("/", response_model=VentureResponse, status_code=status.HTTP_201_CREATED)
async def create_venture(
    venture: VentureCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Legacy mutation is held behind the governed action workflow."""
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Direct venture creation is disabled; submit an evidence-linked governance action.",
    )

@router.get("/", response_model=VentureList)
async def list_ventures(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status_filter: Optional[VentureStatus] = None,
    type_filter: Optional[VentureType] = None,
    risk_filter: Optional[RiskLevel] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List digital ventures with filtering and pagination"""
    try:
        query = db.query(DigitalVenture)
        
        # Apply filters
        if status_filter:
            query = query.filter(DigitalVenture.status == status_filter)
        if type_filter:
            query = query.filter(DigitalVenture.venture_type == type_filter)
        if risk_filter:
            query = query.filter(DigitalVenture.risk_level == risk_filter)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * size
        ventures = query.offset(offset).limit(size).all()
        
        return VentureList(
            ventures=ventures,
            total=total,
            page=page,
            size=size
        )
        
    except SQLAlchemyError as e:
        logger.error("Failed to list ventures", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error"
        )
    except Exception:
        logger.exception("Unexpected error listing ventures")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve ventures"
        )

@router.get("/{venture_id}", response_model=VentureResponse)
async def get_venture(
    venture_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific venture by ID"""
    venture = db.query(DigitalVenture).filter(DigitalVenture.id == venture_id).first()
    
    if not venture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venture not found"
        )
    
    return venture

@router.put("/{venture_id}", response_model=VentureResponse)
async def update_venture(
    venture_id: str,
    venture_update: VentureUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Legacy mutation is held behind the governed action workflow."""
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Direct venture mutation is disabled; submit an evidence-linked governance action.",
    )

@router.delete("/{venture_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_venture(
    venture_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Legacy retirement is held behind the governed action workflow."""
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Direct venture retirement is disabled; submit a governed R4 action.",
    )

@router.post("/{venture_id}/launch", response_model=VentureResponse)
async def launch_venture(
    venture_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Legacy launch is held behind the governed action workflow."""
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Direct venture launch is disabled; readiness evidence and human authority are required.",
    )
