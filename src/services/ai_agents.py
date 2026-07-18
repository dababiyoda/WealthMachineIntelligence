"""Quarantined market and risk simulation services.

The formulas and random values in this module are deterministic or synthetic
test scaffolding. They are not trained, calibrated, or externally validated
models, and their outputs carry recommendation-only authority.
"""
import asyncio
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from src.logging_config import logger

from ..database.connection import get_db
from ..database.models import (
    DigitalVenture,
    AIAgent,
    RiskAssessment,
    MarketAnalysis,
    AgentType,
    RiskLevel,
    VentureStatus,
)


class MarketIntelligenceService:
    """Generate a synthetic market-analysis fixture for local simulations."""
    
    def __init__(self):
        self.agent_type = AgentType.MARKET_INTELLIGENCE
        self.model_version = "simulation-heuristic-1.0"
        
    async def analyze_market_opportunity(self, venture_id: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate an unvalidated market hypothesis from provided inputs."""
        try:
            # Synthetic value for simulation only; this is not an LSTM output.
            trend_score = np.random.uniform(0.3, 0.9)
            market_size = market_data.get('market_size', 1000000)
            competition_level = market_data.get('competition_level', 'medium')
            
            # Calculate opportunity score
            opportunity_score = self._calculate_opportunity_score(
                trend_score, market_size, competition_level
            )
            
            # Generate insights
            insights = {
                'opportunity_score': opportunity_score,
                'simulated_trend_index': trend_score,
                'market_timing_hypothesis': 'favorable' if opportunity_score > 0.6 else 'challenging',
                'key_trends': [
                    'AI automation adoption increasing',
                    'Digital transformation accelerating',
                    'SaaS market expanding'
                ],
                'recommendations': self._generate_recommendations(opportunity_score),
                'evidence_status': 'simulation_heuristic_unvalidated',
                'confidence_status': 'not_calibrated',
                'authority': 'recommendation_only',
            }
            
            # Store analysis in database
            with get_db() as session:
                analysis = MarketAnalysis(
                    venture_id=venture_id,
                    market_size=market_size,
                    opportunity_score=opportunity_score,
                    key_trends=insights['key_trends'],
                    lstm_prediction={
                        'simulated_trend_index': trend_score,
                        'evidence_status': 'simulation_heuristic_unvalidated',
                    },
                    analyzed_at=datetime.now(timezone.utc)
                )
                session.add(analysis)
                session.commit()
            
            logger.info("Market opportunity analyzed",
                       venture_id=venture_id,
                       opportunity_score=opportunity_score)
            
            return insights
            
        except SQLAlchemyError as e:
            logger.error("Market analysis failed", venture_id=venture_id, error=str(e))
            raise
        except Exception:
            logger.exception("Unexpected error during market analysis")
            raise
    
    def _calculate_opportunity_score(self, trend_score: float, market_size: float, competition: str) -> float:
        """Calculate weighted opportunity score"""
        competition_weights = {
            'low': 0.9,
            'medium': 0.6,
            'high': 0.3
        }
        
        market_weight = min(market_size / 10000000, 1.0)  # Normalize to max 10M
        competition_weight = competition_weights.get(competition, 0.5)
        
        return (trend_score * 0.5 + market_weight * 0.3 + competition_weight * 0.2)
    
    def _generate_recommendations(self, opportunity_score: float) -> List[str]:
        """Generate actionable recommendations"""
        if opportunity_score > 0.8:
            return [
                "Prioritize external buyer validation",
                "Design the smallest reversible test",
                "Do not release capital from this score alone"
            ]
        elif opportunity_score > 0.6:
            return [
                "Conduct additional market validation",
                "Monitor contradicting evidence",
                "Prepare a bounded experiment for human review"
            ]
        else:
            return [
                "Consider alternative markets",
                "Gather stronger problem and buyer evidence",
                "Recommend a hold until the active uncertainty is reduced"
            ]

class RiskAssessmentService:
    """Generate an uncalibrated heuristic risk index for simulation review."""

    def __init__(self):
        self.agent_type = AgentType.RISK_ASSESSMENT
        self.model_version = "simulation-heuristic-1.0"
        self.review_threshold = 0.2
        # Pre-compute weight vector for risk score calculation
        self._weight_vector = np.array([0.35, 0.25, 0.3, 0.1])
        
    async def assess_venture_risk(self, venture_id: str) -> Dict[str, Any]:
        """Calculate a non-probabilistic simulation index."""
        try:
            with get_db() as session:
                venture = session.query(DigitalVenture).filter(
                    DigitalVenture.id == venture_id
                ).first()
                
                if not venture:
                    raise ValueError(f"Venture {venture_id} not found")
                
                # Calculate risk factors
                market_risk = self._assess_market_risk(venture)
                operational_risk = self._assess_operational_risk(venture)
                financial_risk = self._assess_financial_risk(venture)
                technical_risk = self._assess_technical_risk(venture)
                
                # Weighted simulation heuristic; no trained hybrid model exists.
                risk_score = self._calculate_hybrid_risk_score(
                    market_risk, operational_risk, financial_risk, technical_risk
                )
                
                risk_level = self._determine_risk_level(risk_score)
                
                # Generate recommendations
                recommendations = self._generate_risk_recommendations(risk_score)
                
                # Store assessment
                assessment = RiskAssessment(
                    venture_id=venture_id,
                    agent_id=self._get_agent_id(session),
                    risk_score=risk_score,
                    heuristic_risk_index=risk_score,
                    market_risk=market_risk,
                    operational_risk=operational_risk,
                    financial_risk=financial_risk,
                    technical_risk=technical_risk,
                    risk_level=risk_level,
                    recommendations=recommendations,
                    model_version=self.model_version,
                    heuristic_confidence=0.0,
                    assessed_at=datetime.now(timezone.utc)
                )
                session.add(assessment)
                
                # Update venture risk metrics
                venture.risk_score = risk_score
                venture.heuristic_risk_index = risk_score
                venture.risk_level = risk_level
                
                session.commit()
                
                logger.info("Risk assessment completed",
                           venture_id=venture_id,
                           risk_score=risk_score,
                           evidence_status="simulation_heuristic_unvalidated")
                
                return {
                    'risk_score': risk_score,
                    'heuristic_risk_index': risk_score,
                    'risk_level': risk_level.value,
                    'risk_factors': {
                        'market': market_risk,
                        'operational': operational_risk,
                        'financial': financial_risk,
                        'technical': technical_risk
                    },
                    'recommendations': recommendations,
                    'below_review_threshold': risk_score <= self.review_threshold,
                    'evidence_status': 'simulation_heuristic_unvalidated',
                    'confidence_status': 'not_calibrated',
                    'authority': 'recommendation_only',
                }
                
        except SQLAlchemyError as e:
            logger.error("Risk assessment failed", venture_id=venture_id, error=str(e))
            raise
        except Exception:
            logger.exception("Unexpected error during risk assessment")
            raise
    
    def _assess_market_risk(self, venture: DigitalVenture) -> float:
        """Assess market-related risks"""
        base_risk = 0.3
        
        # Reduce risk for proven business models
        if venture.venture_type.value in ['saas', 'ecommerce']:
            base_risk *= 0.8
        
        # Adjust for market maturity (Phase-based)
        if venture.status in [VentureStatus.SCALING, VentureStatus.MATURE]:
            base_risk *= 0.6
        
        return min(base_risk, 1.0)
    
    def _assess_operational_risk(self, venture: DigitalVenture) -> float:
        """Assess operational risks"""
        base_risk = 0.25
        
        # Higher automation reduces operational risk
        automation_reduction = venture.automation_level * 0.5
        base_risk = max(base_risk - automation_reduction, 0.05)
        
        return base_risk
    
    def _assess_financial_risk(self, venture: DigitalVenture) -> float:
        """Assess financial risks"""
        if venture.monthly_revenue == 0:
            return 0.8  # High risk for no revenue
        
        if venture.monthly_expenses == 0:
            return 0.3  # Moderate risk
        
        # Calculate burn rate and runway
        burn_rate = venture.monthly_expenses / max(venture.monthly_revenue, 1)
        
        if burn_rate > 1.0:
            return 0.9  # Very high risk
        elif burn_rate > 0.8:
            return 0.6  # High risk
        else:
            return 0.2  # Low risk
    
    def _assess_technical_risk(self, venture: DigitalVenture) -> float:
        """Assess technical risks"""
        base_risk = 0.2
        
        # Digital ventures have lower technical risk with higher AI integration
        if venture.ai_enabled:
            base_risk *= 0.7
        
        return base_risk
    
    def _calculate_hybrid_risk_score(self, market: float, operational: float,
                                   financial: float, technical: float) -> float:
        """Calculate weighted risk score using a vectorized approach"""
        scores = np.array([market, operational, financial, technical])
        weighted_score = float(np.dot(scores, self._weight_vector))
        return min(weighted_score, 1.0)
    
    def _determine_risk_level(self, risk_score: float) -> RiskLevel:
        """Map an uncalibrated index into legacy ordered review bands."""
        if risk_score <= 0.2:
            return RiskLevel.ULTRA_LOW
        elif risk_score <= 0.35:
            return RiskLevel.LOW
        elif risk_score <= 0.5:
            return RiskLevel.MODERATE
        elif risk_score <= 0.7:
            return RiskLevel.HIGH
        else:
            return RiskLevel.VERY_HIGH
    
    def _generate_risk_recommendations(self, risk_score: float) -> List[str]:
        """Generate non-authorizing risk-review suggestions."""
        recommendations = []
        
        if risk_score > self.review_threshold:
            recommendations.extend([
                "Implement additional market validation",
                "Investigate the dominant modeled risk factor",
                "Use a reversible test before requesting more authority"
            ])
        
        if risk_score > 0.5:
            recommendations.extend([
                "Conduct thorough competitive analysis",
                "Establish contingency plans",
                "Monitor key risk indicators closely"
            ])
        
        if risk_score <= self.review_threshold:
            recommendations.append(
                "Heuristic is below the review threshold; external evidence is still required"
            )
        
        return recommendations
    
    def _get_agent_id(self, session: Session) -> str:
        """Get or create risk assessment agent"""
        agent = session.query(AIAgent).filter(
            AIAgent.agent_type == self.agent_type
        ).first()
        
        if not agent:
            agent = AIAgent(
                agent_type=self.agent_type,
                name="Risk Assessment Agent",
                version=self.model_version,
                model_type="Hybrid LSTM + Random Forest",
                is_active=True
            )
            session.add(agent)
            session.commit()
        
        return agent.id

class DecisionOrchestrator:
    """Orchestrates AI agent decisions for optimal venture management"""
    
    def __init__(self):
        self.market_service = MarketIntelligenceService()
        self.risk_service = RiskAssessmentService()
    
    async def evaluate_venture_opportunity(self, venture_id: str, 
                                         market_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Comprehensive venture evaluation using multiple AI agents"""
        try:
            # Default market data if not provided
            if not market_data:
                market_data = {
                    'market_size': 5000000,
                    'competition_level': 'medium',
                    'growth_rate': 0.15
                }
            
            # Run analyses in parallel
            market_analysis_task = self.market_service.analyze_market_opportunity(
                venture_id, market_data
            )
            risk_analysis_task = self.risk_service.assess_venture_risk(venture_id)
            
            market_analysis, risk_analysis = await asyncio.gather(
                market_analysis_task, risk_analysis_task
            )
            
            # Generate final recommendation
            final_decision = self._generate_final_decision(
                market_analysis, risk_analysis
            )
            
            logger.info("Venture evaluation completed",
                       venture_id=venture_id,
                       decision=final_decision['action'])
            
            return {
                'venture_id': venture_id,
                'market_analysis': market_analysis,
                'risk_analysis': risk_analysis,
                'final_decision': final_decision,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except SQLAlchemyError as e:
            logger.error("Venture evaluation failed", venture_id=venture_id, error=str(e))
            raise
        except Exception:
            logger.exception("Unexpected error during venture evaluation")
            raise
    
    def _generate_final_decision(self, market_analysis: Dict[str, Any], 
                               risk_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a non-authorizing simulation recommendation."""
        opportunity_score = market_analysis['opportunity_score']
        heuristic_risk_index = risk_analysis['heuristic_risk_index']
        below_review_threshold = risk_analysis['below_review_threshold']
        
        # Simulation recommendation matrix. No branch authorizes execution.
        if opportunity_score > 0.7 and below_review_threshold:
            action = "RECOMMEND_BOUNDED_VALIDATION"
            rationale = "Modeled priority is high; seek decisive external evidence"
        elif opportunity_score > 0.5 and heuristic_risk_index <= 0.5:
            action = "RECOMMEND_MORE_EVIDENCE"
            rationale = "The simulation is inconclusive; reduce the active uncertainty"
        else:
            action = "RECOMMEND_HOLD"
            rationale = "Do not advance from the current unvalidated inputs"
        
        return {
            'action': action,
            'action_authority': 'none',
            'confidence_status': 'not_calibrated',
            'rationale': rationale,
            'opportunity_score': opportunity_score,
            'heuristic_risk_index': heuristic_risk_index,
            'below_review_threshold': below_review_threshold,
            'evidence_status': 'simulation_heuristic_unvalidated',
        }
