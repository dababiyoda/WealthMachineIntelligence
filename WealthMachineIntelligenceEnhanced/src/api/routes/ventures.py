from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session

from ..database.connection import get_db
from src.database.models import DigitalVenture  # Reuse existing model from original codebase


class VentureBase(BaseModel):
    name: str
    description: Optional[str] = None
    type: Optional[str] = None


class VentureCreate(VentureBase):
    pass


class VentureResponse(VentureBase):
    id: int

    class Config:
        orm_mode = True


router = APIRouter()


@router.post("/", response_model=VentureResponse, status_code=201)
def create_venture(
    venture: VentureCreate,
    db: Session = Depends(get_db),
) -> VentureResponse:
    """Create a new venture in the database."""
    db_venture = DigitalVenture(
        name=venture.name,
        description=venture.description,
        venture_type=venture.type,
    )
    db.add(db_venture)
    db.commit()
    db.refresh(db_venture)
    return db_venture


@router.get("/", response_model=List[VentureResponse])
def list_ventures(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
) -> List[VentureResponse]:
    """List ventures with pagination."""
    ventures = db.query(DigitalVenture).offset(skip).limit(limit).all()
    return ventures


@router.get("/{venture_id}", response_model=VentureResponse)
def get_venture(
    venture_id: int,
    db: Session = Depends(get_db),
) -> VentureResponse:
    """Retrieve a venture by its ID."""
    venture = db.get(DigitalVenture, venture_id)
    if venture is None:
        raise HTTPException(status_code=404, detail="Venture not found")
    return venture
