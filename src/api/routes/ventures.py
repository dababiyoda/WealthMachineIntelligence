"""
Digital ventures API endpoints
CRUD operations and business logic for digital business opportunities
"""
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from src.logging_config import logger

from ...database.connection import get_db
from ...database.models import DigitalVenture, VentureType, VentureStatus, RiskLevel
from ..admin_audit import record_admin_intent, record_admin_outcome
from ..auth import get_current_user, require_admin_user


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
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: VentureStatus
    current_valuation: float
    monthly_revenue: float
    monthly_expenses: float
    profit_margin: float
    risk_level: RiskLevel
    risk_score: float
    failure_probability: float
    customer_count: int
    churn_rate: float
    growth_rate: float
    ai_enabled: bool
    automation_level: float
    created_at: datetime
    updated_at: Optional[datetime]
    
class VentureList(BaseModel):
    ventures: List[VentureResponse]
    total: int
    page: int
    size: int

@router.post("/", response_model=VentureResponse, status_code=status.HTTP_201_CREATED)
async def create_venture(
    venture: VentureCreate,
    current_user: dict = Depends(require_admin_user),
    db: Session = Depends(get_db)
):
    """Create a venture through the authenticated human-admin plane."""
    action_id = record_admin_intent(
        current_user,
        action_type="admin.venture.create",
        resource="venture:new",
        changed_fields=venture.model_dump().keys(),
    )
    try:
        # Create venture with initial risk assessment
        db_venture = DigitalVenture(
            name=venture.name,
            description=venture.description,
            venture_type=venture.venture_type,
            initial_investment=venture.initial_investment,
            status=VentureStatus.IDEATION,
            risk_level=RiskLevel.MODERATE,
            ai_enabled=True,
            automation_level=0.1  # Start with basic automation
        )
        
        db.add(db_venture)
        db.commit()
        db.refresh(db_venture)
        
        logger.info("Venture created", 
                   venture_id=db_venture.id,
                   name=db_venture.name,
                   type=db_venture.venture_type.value,
                   created_by=current_user.get("user_id"))
        record_admin_outcome(
            current_user,
            action_id=action_id,
            action_type="admin.venture.create",
            resource=f"venture:{db_venture.id}",
            status="succeeded",
        )
        
        return db_venture
        
    except SQLAlchemyError as e:
        record_admin_outcome(
            current_user,
            action_id=action_id,
            action_type="admin.venture.create",
            resource="venture:new",
            status="failed",
            error_type=type(e).__name__,
        )
        logger.error("Failed to create venture", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error"
        )
    except Exception as e:
        record_admin_outcome(
            current_user,
            action_id=action_id,
            action_type="admin.venture.create",
            resource="venture:new",
            status="failed",
            error_type=type(e).__name__,
        )
        logger.exception("Unexpected error creating venture")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create venture"
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
    current_user: dict = Depends(require_admin_user),
    db: Session = Depends(get_db)
):
    """Update a venture through the authenticated human-admin plane."""
    venture = db.query(DigitalVenture).filter(DigitalVenture.id == venture_id).first()
    
    if not venture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venture not found"
        )
    
    update_data = venture_update.model_dump(exclude_unset=True)
    action_id = record_admin_intent(
        current_user,
        action_type="admin.venture.update",
        resource=f"venture:{venture_id}",
        changed_fields=update_data.keys(),
    )
    try:
        # Update fields
        for field, value in update_data.items():
            setattr(venture, field, value)
        
        # Recalculate profit margin if revenue/expenses updated
        if venture.monthly_revenue and venture.monthly_expenses:
            venture.profit_margin = (venture.monthly_revenue - venture.monthly_expenses) / venture.monthly_revenue
        
        # Update growth rate based on customer metrics
        if venture.customer_count and venture.churn_rate:
            venture.growth_rate = max(0, 1 - venture.churn_rate)
        
        db.commit()
        db.refresh(venture)
        
        logger.info("Venture updated",
                   venture_id=venture_id,
                   updated_by=current_user.get("user_id"),
                   changes=list(update_data.keys()))
        record_admin_outcome(
            current_user,
            action_id=action_id,
            action_type="admin.venture.update",
            resource=f"venture:{venture_id}",
            status="succeeded",
        )
        
        return venture
        
    except SQLAlchemyError as e:
        record_admin_outcome(
            current_user,
            action_id=action_id,
            action_type="admin.venture.update",
            resource=f"venture:{venture_id}",
            status="failed",
            error_type=type(e).__name__,
        )
        logger.error("Failed to update venture", venture_id=venture_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error"
        )
    except Exception as e:
        record_admin_outcome(
            current_user,
            action_id=action_id,
            action_type="admin.venture.update",
            resource=f"venture:{venture_id}",
            status="failed",
            error_type=type(e).__name__,
        )
        logger.exception("Unexpected error updating venture")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update venture"
        )

@router.delete("/{venture_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_venture(
    venture_id: str,
    current_user: dict = Depends(require_admin_user),
    db: Session = Depends(get_db)
):
    """Discontinue a venture through the authenticated human-admin plane."""
    venture = db.query(DigitalVenture).filter(DigitalVenture.id == venture_id).first()
    
    if not venture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venture not found"
        )
    
    action_id = record_admin_intent(
        current_user,
        action_type="admin.venture.discontinue",
        resource=f"venture:{venture_id}",
        changed_fields=("status", "discontinued_at"),
    )
    try:
        # Instead of hard delete, mark as discontinued
        venture.status = VentureStatus.DISCONTINUED
        venture.discontinued_at = datetime.now(timezone.utc)
        
        db.commit()
        
        logger.info("Venture discontinued",
                   venture_id=venture_id,
                   discontinued_by=current_user.get("user_id"))
        record_admin_outcome(
            current_user,
            action_id=action_id,
            action_type="admin.venture.discontinue",
            resource=f"venture:{venture_id}",
            status="succeeded",
        )
        
    except SQLAlchemyError as e:
        record_admin_outcome(
            current_user,
            action_id=action_id,
            action_type="admin.venture.discontinue",
            resource=f"venture:{venture_id}",
            status="failed",
            error_type=type(e).__name__,
        )
        logger.error("Failed to discontinue venture", venture_id=venture_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error"
        )
    except Exception as e:
        record_admin_outcome(
            current_user,
            action_id=action_id,
            action_type="admin.venture.discontinue",
            resource=f"venture:{venture_id}",
            status="failed",
            error_type=type(e).__name__,
        )
        logger.exception("Unexpected error discontinuing venture")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to discontinue venture"
        )

@router.post("/{venture_id}/launch", response_model=VentureResponse)
async def launch_venture(
    venture_id: str,
    current_user: dict = Depends(require_admin_user),
    db: Session = Depends(get_db)
):
    """Launch a venture through the authenticated human-admin plane."""
    venture = db.query(DigitalVenture).filter(DigitalVenture.id == venture_id).first()
    
    if not venture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venture not found"
        )
    
    if venture.status != VentureStatus.IDEATION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Venture must be in ideation status to launch"
        )
    
    action_id = record_admin_intent(
        current_user,
        action_type="admin.venture.launch",
        resource=f"venture:{venture_id}",
        changed_fields=("status", "launched_at", "automation_level"),
    )
    try:
        venture.status = VentureStatus.MVP
        venture.launched_at = datetime.now(timezone.utc)
        venture.automation_level = 0.3  # Increase automation on launch
        
        db.commit()
        db.refresh(venture)
        
        logger.info("Venture launched",
                   venture_id=venture_id,
                   launched_by=current_user.get("user_id"))
        record_admin_outcome(
            current_user,
            action_id=action_id,
            action_type="admin.venture.launch",
            resource=f"venture:{venture_id}",
            status="succeeded",
        )
        
        return venture
        
    except SQLAlchemyError as e:
        record_admin_outcome(
            current_user,
            action_id=action_id,
            action_type="admin.venture.launch",
            resource=f"venture:{venture_id}",
            status="failed",
            error_type=type(e).__name__,
        )
        logger.error("Failed to launch venture", venture_id=venture_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error"
        )
    except Exception as e:
        record_admin_outcome(
            current_user,
            action_id=action_id,
            action_type="admin.venture.launch",
            resource=f"venture:{venture_id}",
            status="failed",
            error_type=type(e).__name__,
        )
        logger.exception("Unexpected error launching venture")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to launch venture"
        )
