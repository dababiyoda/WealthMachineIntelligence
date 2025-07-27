"""
AI Agents API endpoints
Manage and monitor AI agents in the system
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from src.logging_config import logger

from ...database.connection import get_db
from ...database.models import AIAgent, AgentType
from ..auth import get_current_user


router = APIRouter()

class AgentResponse(BaseModel):
    id: str
    agent_type: AgentType
    name: str
    version: str
    accuracy: float
    decisions_made: int
    success_rate: float
    model_type: Optional[str]
    is_active: bool
    last_activity: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

class AgentStatus(BaseModel):
    id: str
    agent_type: AgentType
    name: str
    is_active: bool
    last_activity: Optional[datetime]
    accuracy: float
    success_rate: float
    decisions_made: int

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
    except Exception as e:
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
            accuracy=agent.accuracy,
            success_rate=agent.success_rate,
            decisions_made=agent.decisions_made
        ) for agent in agents]
        
    except SQLAlchemyError as e:
        logger.error("Failed to get agents status", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error"
        )
    except Exception as e:
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
    """Activate an AI agent"""
    agent = db.query(AIAgent).filter(AIAgent.id == agent_id).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    try:
        agent.is_active = True
        agent.last_activity = datetime.utcnow()
        
        db.commit()
        db.refresh(agent)
        
        logger.info("Agent activated",
                   agent_id=agent_id,
                   agent_type=agent.agent_type.value,
                   activated_by=current_user.get("user_id"))
        
        return agent
        
    except SQLAlchemyError as e:
        logger.error("Failed to activate agent", agent_id=agent_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error"
        )
    except Exception as e:
        logger.exception("Unexpected error activating agent")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate agent"
        )

@router.post("/{agent_id}/deactivate", response_model=AgentResponse)
async def deactivate_agent(
    agent_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deactivate an AI agent"""
    agent = db.query(AIAgent).filter(AIAgent.id == agent_id).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    try:
        agent.is_active = False
        
        db.commit()
        db.refresh(agent)
        
        logger.info("Agent deactivated",
                   agent_id=agent_id,
                   agent_type=agent.agent_type.value,
                   deactivated_by=current_user.get("user_id"))
        
        return agent
        
    except SQLAlchemyError as e:
        logger.error("Failed to deactivate agent", agent_id=agent_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error"
        )
    except Exception as e:
        logger.exception("Unexpected error deactivating agent")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate agent"
        )