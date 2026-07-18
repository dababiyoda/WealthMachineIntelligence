"""
AI Agents API endpoints
Manage and monitor AI agents in the system
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from src.logging_config import logger

from ...database.connection import session_dependency as get_db
from ...database.models import AIAgent, AgentType
from ..auth import get_current_user


router = APIRouter()

class AgentResponse(BaseModel):
    id: str
    agent_type: AgentType
    name: str
    version: str
    reported_accuracy: float = Field(validation_alias="accuracy")
    decisions_made: int
    reported_success_rate: float = Field(validation_alias="success_rate")
    model_type: Optional[str]
    is_active: bool
    last_activity: Optional[datetime]
    created_at: datetime
    evidence_status: str = "unverified_seed_or_operator_input"
    limitations: List[str] = Field(
        default_factory=lambda: [
            "Reported performance fields have no linked evaluation or outcome evidence."
        ]
    )

    model_config = ConfigDict(from_attributes=True)

class AgentStatus(BaseModel):
    id: str
    agent_type: AgentType
    name: str
    is_active: bool
    last_activity: Optional[datetime]
    reported_accuracy: float
    reported_success_rate: float
    decisions_made: int
    evidence_status: str = "unverified_seed_or_operator_input"

@router.get("/", response_model=List[AgentResponse])
async def list_agents(
    active_only: bool = True,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all AI agents"""
    try:
        query = db.query(AIAgent)
        
        if active_only:
            query = query.filter(AIAgent.is_active)
        
        agents = query.all()
        return agents
        
    except SQLAlchemyError as e:
        logger.error("Failed to list agents", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error"
        )
    except Exception:
        logger.exception("Unexpected error listing agents")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agents"
        )

@router.get("/status", response_model=List[AgentStatus])
async def get_agents_status(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get quick status of all agents"""
    try:
        agents = db.query(AIAgent).all()
        return [AgentStatus(
            id=agent.id,
            agent_type=agent.agent_type,
            name=agent.name,
            is_active=agent.is_active,
            last_activity=agent.last_activity,
            reported_accuracy=agent.accuracy,
            reported_success_rate=agent.success_rate,
            decisions_made=agent.decisions_made
        ) for agent in agents]
        
    except SQLAlchemyError as e:
        logger.error("Failed to get agents status", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error"
        )
    except Exception:
        logger.exception("Unexpected error getting agents status")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agent status"
        )

@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific agent details"""
    agent = db.query(AIAgent).filter(AIAgent.id == agent_id).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    return agent

@router.post("/{agent_id}/activate", response_model=AgentResponse)
async def activate_agent(
    agent_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Legacy activation is held behind the governed action workflow."""
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Direct agent activation is disabled; a contract and capability grant are required.",
    )

@router.post("/{agent_id}/deactivate", response_model=AgentResponse)
async def deactivate_agent(
    agent_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Legacy deactivation is held behind the governed action workflow."""
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Direct agent state mutation is disabled; use governance or a kill switch.",
    )
