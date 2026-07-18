"""
Analytics and reporting API endpoints
Business intelligence and performance metrics
"""
from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from sqlalchemy.exc import SQLAlchemyError
from src.logging_config import logger

from ...database.connection import get_db
from ...core.epistemic import evidence_disclosure
from ...database.models import (
    DigitalVenture,
    VentureStatus,
    RiskLevel,
)
from ..auth import get_current_user


router = APIRouter()


class EvidenceDisclosure(BaseModel):
    operating_mode: str
    evidence_status: str
    source: str
    risk_semantics: str
    authority: str
    limitations: List[str]


def disclosure(source: str) -> EvidenceDisclosure:
    return EvidenceDisclosure(**evidence_disclosure(source))


class DashboardMetrics(BaseModel):
    total_ventures: int
    active_ventures: int
    total_revenue: float
    average_roi: float
    low_risk_ventures: int
    modeled_low_risk_coverage: float
    evidence: EvidenceDisclosure
    
class VentureMetrics(BaseModel):
    venture_id: str
    name: str
    monthly_revenue: float
    growth_rate: float
    risk_score: float
    heuristic_risk_index: float
    automation_level: float
    evidence: EvidenceDisclosure

class PortfolioPerformance(BaseModel):
    total_valuation: float
    monthly_revenue: float
    monthly_expenses: float
    profit_margin: float
    venture_count: int
    average_risk_score: float
    roi_by_type: Dict[str, float]
    evidence: EvidenceDisclosure

class RiskAnalysis(BaseModel):
    ultra_low_risk_count: int
    low_risk_count: int
    moderate_risk_count: int
    high_risk_count: int
    average_heuristic_risk_index: float
    ventures_below_review_threshold: int
    evidence: EvidenceDisclosure

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
        
        # This is an uncalibrated review index, not a failure probability.
        ventures_below_review_threshold = db.query(DigitalVenture).filter(
            DigitalVenture.risk_score <= 0.2
        ).count()
        
        modeled_low_risk_coverage = (
            ventures_below_review_threshold / total_ventures * 100
            if total_ventures > 0
            else 0
        )
        
        return DashboardMetrics(
            total_ventures=total_ventures,
            active_ventures=active_ventures,
            total_revenue=revenue_sum,
            average_roi=average_roi,
            low_risk_ventures=low_risk_ventures,
            modeled_low_risk_coverage=modeled_low_risk_coverage,
            evidence=disclosure("local DigitalVenture records; records may be simulation fixtures"),
        )
        
    except SQLAlchemyError as e:
        logger.error("Failed to get dashboard metrics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error"
        )
    except Exception:
        logger.exception("Unexpected error getting dashboard metrics")
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
        metrics = db.query(
            func.sum(DigitalVenture.current_valuation),
            func.sum(DigitalVenture.monthly_revenue),
            func.sum(DigitalVenture.monthly_expenses),
            func.avg(DigitalVenture.risk_score),
            func.count(DigitalVenture.id),
        ).filter(
            DigitalVenture.status != VentureStatus.DISCONTINUED
        ).one()

        (
            total_valuation,
            monthly_revenue,
            monthly_expenses,
            average_risk_score,
            venture_count,
        ) = metrics

        profit_margin = (
            (monthly_revenue - monthly_expenses) / monthly_revenue
            if monthly_revenue and monthly_revenue > 0
            else 0
        )

        roi_query = (
            db.query(
                DigitalVenture.venture_type,
                func.avg(DigitalVenture.profit_margin),
            )
            .filter(DigitalVenture.status != VentureStatus.DISCONTINUED)
            .group_by(DigitalVenture.venture_type)
            .all()
        )
        roi_by_type = {vt.value: roi for vt, roi in roi_query}

        return PortfolioPerformance(
            total_valuation=total_valuation or 0,
            monthly_revenue=monthly_revenue or 0,
            monthly_expenses=monthly_expenses or 0,
            profit_margin=profit_margin,
            venture_count=venture_count,
            average_risk_score=average_risk_score or 0,
            roi_by_type=roi_by_type,
            evidence=disclosure("local DigitalVenture records; financial fields are not independently audited"),
        )
        
    except SQLAlchemyError as e:
        logger.error("Failed to get portfolio performance", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error"
        )
    except Exception:
        logger.exception("Unexpected error getting portfolio performance")
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
        
        # Average uncalibrated heuristic index.
        average_heuristic_risk_index = db.query(
            func.avg(DigitalVenture.risk_score)
        ).scalar() or 0
        
        ventures_below_review_threshold = db.query(DigitalVenture).filter(
            DigitalVenture.risk_score <= 0.2
        ).count()
        
        return RiskAnalysis(
            ultra_low_risk_count=ultra_low_risk,
            low_risk_count=low_risk,
            moderate_risk_count=moderate_risk,
            high_risk_count=high_risk,
            average_heuristic_risk_index=average_heuristic_risk_index,
            ventures_below_review_threshold=ventures_below_review_threshold,
            evidence=disclosure("local DigitalVenture heuristic risk fields; no outcome calibration"),
        )
        
    except SQLAlchemyError as e:
        logger.error("Failed to get risk analysis", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error"
        )
    except Exception:
        logger.exception("Unexpected error getting risk analysis")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve risk analysis"
        )

@router.get("/top-performers", response_model=List[VentureMetrics])
async def get_top_performers(
    limit: int = Query(10, ge=1, le=50),
    metric: str = Query("revenue", pattern="^(revenue|growth|roi|automation)$"),
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
                heuristic_risk_index=v.risk_score,
                automation_level=v.automation_level,
                evidence=disclosure("local DigitalVenture record; values are not independently audited"),
            ) for v in ventures
        ]
        
    except SQLAlchemyError as e:
        logger.error("Failed to get top performers", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error"
        )
    except Exception:
        logger.exception("Unexpected error getting top performers")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve top performers"
        )
