"""
Analytics and reporting API endpoints
Business intelligence and performance metrics
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import structlog

from ...database.connection import get_db
from ...database.models import (
    DigitalVenture, PerformanceMetric, RiskAssessment, 
    VentureType, VentureStatus, RiskLevel
)
from ..auth import get_current_user

logger = structlog.get_logger()

router = APIRouter()

class DashboardMetrics(BaseModel):
    total_ventures: int
    active_ventures: int
    total_revenue: float
    average_roi: float
    low_risk_ventures: int
    ultra_low_failure_rate: float
    
class VentureMetrics(BaseModel):
    venture_id: str
    name: str
    monthly_revenue: float
    growth_rate: float
    risk_score: float
    failure_probability: float
    automation_level: float

class PortfolioPerformance(BaseModel):
    total_valuation: float
    monthly_revenue: float
    monthly_expenses: float
    profit_margin: float
    venture_count: int
    average_risk_score: float
    roi_by_type: Dict[str, float]

class RiskAnalysis(BaseModel):
    ultra_low_risk_count: int
    low_risk_count: int
    moderate_risk_count: int
    high_risk_count: int
    average_failure_probability: float
    ventures_meeting_target: int  # P(failure) ≤ 0.01%

@router.get("/dashboard", response_model=DashboardMetrics)
async def get_dashboard_metrics(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get high-level dashboard metrics"""
    try:
        # Count ventures by status
        total_ventures = db.query(DigitalVenture).count()
        active_ventures = db.query(DigitalVenture).filter(
            and_(
                DigitalVenture.status != VentureStatus.DISCONTINUED,
                DigitalVenture.status != VentureStatus.ON_HOLD
            )
        ).count()
        
        # Financial metrics
        revenue_sum = db.query(func.sum(DigitalVenture.monthly_revenue)).scalar() or 0
        
        # Calculate average ROI
        ventures_with_investment = db.query(DigitalVenture).filter(
            DigitalVenture.initial_investment > 0
        ).all()
        
        total_roi = 0
        roi_count = 0
        for venture in ventures_with_investment:
            if venture.monthly_revenue and venture.initial_investment:
                annual_revenue = venture.monthly_revenue * 12
                roi = (annual_revenue - venture.initial_investment) / venture.initial_investment
                total_roi += roi
                roi_count += 1
        
        average_roi = total_roi / roi_count if roi_count > 0 else 0
        
        # Risk metrics
        low_risk_ventures = db.query(DigitalVenture).filter(
            DigitalVenture.risk_level.in_([RiskLevel.ULTRA_LOW, RiskLevel.LOW])
        ).count()
        
        # Ultra-low failure rate (target ≤ 0.01%)
        ultra_low_failure_ventures = db.query(DigitalVenture).filter(
            DigitalVenture.failure_probability <= 0.0001
        ).count()
        
        ultra_low_failure_rate = (ultra_low_failure_ventures / total_ventures * 100) if total_ventures > 0 else 0
        
        return DashboardMetrics(
            total_ventures=total_ventures,
            active_ventures=active_ventures,
            total_revenue=revenue_sum,
            average_roi=average_roi,
            low_risk_ventures=low_risk_ventures,
            ultra_low_failure_rate=ultra_low_failure_rate
        )
        
    except Exception as e:
        logger.error("Failed to get dashboard metrics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve dashboard metrics"
        )

@router.get("/portfolio", response_model=PortfolioPerformance)
async def get_portfolio_performance(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get overall portfolio performance"""
    try:
        ventures = db.query(DigitalVenture).filter(
            DigitalVenture.status != VentureStatus.DISCONTINUED
        ).all()
        
        total_valuation = sum(v.current_valuation for v in ventures)
        monthly_revenue = sum(v.monthly_revenue for v in ventures)
        monthly_expenses = sum(v.monthly_expenses for v in ventures)
        
        profit_margin = (monthly_revenue - monthly_expenses) / monthly_revenue if monthly_revenue > 0 else 0
        average_risk_score = sum(v.risk_score for v in ventures) / len(ventures) if ventures else 0
        
        # ROI by venture type
        roi_by_type = {}
        for venture_type in VentureType:
            type_ventures = [v for v in ventures if v.venture_type == venture_type]
            if type_ventures:
                type_roi = sum(v.profit_margin for v in type_ventures) / len(type_ventures)
                roi_by_type[venture_type.value] = type_roi
        
        return PortfolioPerformance(
            total_valuation=total_valuation,
            monthly_revenue=monthly_revenue,
            monthly_expenses=monthly_expenses,
            profit_margin=profit_margin,
            venture_count=len(ventures),
            average_risk_score=average_risk_score,
            roi_by_type=roi_by_type
        )
        
    except Exception as e:
        logger.error("Failed to get portfolio performance", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve portfolio performance"
        )

@router.get("/risk-analysis", response_model=RiskAnalysis)
async def get_risk_analysis(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive risk analysis"""
    try:
        # Count ventures by risk level
        ultra_low_risk = db.query(DigitalVenture).filter(
            DigitalVenture.risk_level == RiskLevel.ULTRA_LOW
        ).count()
        
        low_risk = db.query(DigitalVenture).filter(
            DigitalVenture.risk_level == RiskLevel.LOW
        ).count()
        
        moderate_risk = db.query(DigitalVenture).filter(
            DigitalVenture.risk_level == RiskLevel.MODERATE
        ).count()
        
        high_risk = db.query(DigitalVenture).filter(
            DigitalVenture.risk_level.in_([RiskLevel.HIGH, RiskLevel.VERY_HIGH])
        ).count()
        
        # Average failure probability
        avg_failure_prob = db.query(func.avg(DigitalVenture.failure_probability)).scalar() or 0
        
        # Ventures meeting target (P(failure) ≤ 0.01%)
        ventures_meeting_target = db.query(DigitalVenture).filter(
            DigitalVenture.failure_probability <= 0.0001
        ).count()
        
        return RiskAnalysis(
            ultra_low_risk_count=ultra_low_risk,
            low_risk_count=low_risk,
            moderate_risk_count=moderate_risk,
            high_risk_count=high_risk,
            average_failure_probability=avg_failure_prob,
            ventures_meeting_target=ventures_meeting_target
        )
        
    except Exception as e:
        logger.error("Failed to get risk analysis", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve risk analysis"
        )

@router.get("/top-performers", response_model=List[VentureMetrics])
async def get_top_performers(
    limit: int = Query(10, ge=1, le=50),
    metric: str = Query("revenue", regex="^(revenue|growth|roi|automation)$"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get top performing ventures by specified metric"""
    try:
        query = db.query(DigitalVenture).filter(
            DigitalVenture.status != VentureStatus.DISCONTINUED
        )
        
        # Sort by specified metric
        if metric == "revenue":
            query = query.order_by(DigitalVenture.monthly_revenue.desc())
        elif metric == "growth":
            query = query.order_by(DigitalVenture.growth_rate.desc())
        elif metric == "roi":
            query = query.order_by(DigitalVenture.profit_margin.desc())
        elif metric == "automation":
            query = query.order_by(DigitalVenture.automation_level.desc())
        
        ventures = query.limit(limit).all()
        
        return [
            VentureMetrics(
                venture_id=v.id,
                name=v.name,
                monthly_revenue=v.monthly_revenue,
                growth_rate=v.growth_rate,
                risk_score=v.risk_score,
                failure_probability=v.failure_probability,
                automation_level=v.automation_level
            ) for v in ventures
        ]
        
    except Exception as e:
        logger.error("Failed to get top performers", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve top performers"
        )