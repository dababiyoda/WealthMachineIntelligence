"""Prototype services for market analysis and heuristic risk assessment.

This module implements the algorithms that power the platform's
intelligence features. The current implementations contain randomized and
heuristic components; their scores are not calibrated probabilities or
execution authority. Async APIs allow integration with FastAPI endpoints or
background workers.
"""
import asyncio
import random
from typing import Dict, List, Optional, Any
from datetime import datetime
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
    """Synthetic market-analysis prototype requiring external validation."""
    
    def __init__(self):
        self.agent_type = AgentType.MARKET_INTELLIGENCE
        self.model_version = "1.0.0"
        self.confidence_threshold = 0.7
        
    async def analyze_market_opportunity(self, venture_id: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze market opportunity using AI models"""
        try:
            # Simulate LSTM prediction (in production, use real trained model)
            trend_score = random.uniform(0.3, 0.9)
            market_size = market_data.get('market_size', 1000000)
            competition_level = market_data.get('competition_level', 'medium')
            
            # Calculate opportunity score
            opportunity_score = self._calculate_opportunity_score(
                trend_score, market_size, competition_level
            )
            
            # Generate demo insights. These are hypotheses, not observed trends.
            insights = {
                'opportunity_score': opportunity_score,
                'trend_prediction': trend_score,
                'market_timing': 'favorable' if opportunity_score > 0.6 else 'challenging',
                'key_trends': [
                    'AI automation adoption increasing',
                    'Digital transformation accelerating',
                    'SaaS market expanding'
                ],
                'recommendations': self._generate_recommendations(opportunity_score),
                'analysis_mode': 'synthetic_demo',
                'requires_external_validation': True,
                'execution_authority': False,
            }
            
            # Store analysis in database
            with get_db() as session:
                analysis = MarketAnalysis(
                    venture_id=venture_id,
                    market_size=market_size,
                    opportunity_score=opportunity_score,
                    key_trends=insights['key_trends'],
                    lstm_prediction={
                        'trend_score': trend_score,
                        'analysis_mode': 'synthetic_demo',
                    },
                    analyzed_at=datetime.utcnow()
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
        """Generate bounded evidence-gathering recommendations."""
        if opportunity_score > 0.8:
            return [
                "Prioritize an externally measured validation test",
                "Draft a bounded pilot for human review",
                "Set capital and kill limits before execution",
            ]
        elif opportunity_score > 0.6:
            return [
                "Collect paid-demand or retained-usage evidence",
                "Test the highest-impact assumption before building",
                "Monitor substitutes and adoption friction",
            ]
        else:
            return [
                "Keep the opportunity in research mode",
                "Test an alternative segment or problem wedge",
                "Do not allocate material capital without new evidence",
            ]

class RiskAssessmentService:
    """Uncalibrated heuristic risk service for development use."""

    def __init__(self):
        self.agent_type = AgentType.RISK_ASSESSMENT
        self.model_version = "1.0.0"
        self.legacy_score_threshold = 0.0001
        # Pre-compute weights without requiring a numerical runtime dependency.
        self._weight_vector = (0.35, 0.25, 0.3, 0.1)
        
    async def assess_venture_risk(self, venture_id: str) -> Dict[str, Any]:
        """Comprehensive risk assessment using hybrid models"""
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
                
                # Heuristic prototype; not a trained or calibrated failure model.
                risk_score = self._calculate_hybrid_risk_score(
                    market_risk, operational_risk, financial_risk, technical_risk
                )
                
                failure_probability = self._convert_risk_to_probability(risk_score)
                risk_level = self._determine_risk_level(failure_probability)
                
                # Generate recommendations
                recommendations = self._generate_risk_recommendations(
                    risk_score, failure_probability
                )
                
                # Store assessment
                assessment = RiskAssessment(
                    venture_id=venture_id,
                    agent_id=self._get_agent_id(session),
                    risk_score=risk_score,
                    failure_probability=failure_probability,
                    market_risk=market_risk,
                    operational_risk=operational_risk,
                    financial_risk=financial_risk,
                    technical_risk=technical_risk,
                    risk_level=risk_level,
                    recommendations=recommendations,
                    model_version=self.model_version,
                    confidence_level=0.85,
                    assessed_at=datetime.utcnow()
                )
                session.add(assessment)
                
                # Update venture risk metrics
                venture.risk_score = risk_score
                venture.failure_probability = failure_probability
                venture.risk_level = risk_level
                
                session.commit()
                
                logger.info("Risk assessment completed",
                           venture_id=venture_id,
                           risk_score=risk_score,
                           failure_probability=failure_probability,
                           meets_internal_threshold=(
                               failure_probability <= self.legacy_score_threshold
                           ),
                           probability_calibrated=False)
                
                return {
                    'risk_score': risk_score,
                    'failure_probability': failure_probability,
                    'risk_level': risk_level.value,
                    'risk_factors': {
                        'market': market_risk,
                        'operational': operational_risk,
                        'financial': financial_risk,
                        'technical': technical_risk
                    },
                    'recommendations': recommendations,
                    'meets_internal_threshold': (
                        failure_probability <= self.legacy_score_threshold
                    ),
                    'probability_calibrated': False,
                    'score_semantics': (
                        'heuristic proxy stored in a legacy probability field; '
                        'not an empirical venture failure probability'
                    ),
                    'execution_authority': False,
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
        
        # Legacy heuristic only; automation does not inherently prove safety.
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
        
        # AI integration does not inherently reduce technical risk. A validated
        # model-risk term should replace this neutral placeholder.
        
        return base_risk
    
    def _calculate_hybrid_risk_score(self, market: float, operational: float,
                                   financial: float, technical: float) -> float:
        """Calculate the weighted heuristic risk score."""
        scores = (market, operational, financial, technical)
        weighted_score = sum(
            score * weight for score, weight in zip(scores, self._weight_vector)
        )
        return min(weighted_score, 1.0)
    
    def _convert_risk_to_probability(self, risk_score: float) -> float:
        """Map a heuristic score into a legacy probability-shaped field.

        This transform is not empirically calibrated and must not be presented
        as a real-world probability or used to unlock capital or authority.
        """
        return min(risk_score ** 2 * 0.1, 0.5)
    
    def _determine_risk_level(self, failure_probability: float) -> RiskLevel:
        """Determine risk level based on failure probability"""
        if failure_probability <= 0.0001:  # ≤ 0.01%
            return RiskLevel.ULTRA_LOW
        elif failure_probability <= 0.001:  # ≤ 0.1%
            return RiskLevel.LOW
        elif failure_probability <= 0.01:   # ≤ 1%
            return RiskLevel.MODERATE
        elif failure_probability <= 0.05:   # ≤ 5%
            return RiskLevel.HIGH
        else:
            return RiskLevel.VERY_HIGH
    
    def _generate_risk_recommendations(self, risk_score: float, 
                                     failure_probability: float) -> List[str]:
        """Generate risk mitigation recommendations"""
        recommendations = []
        
        if failure_probability > self.legacy_score_threshold:
            recommendations.extend([
                "Collect representative external outcome data",
                "Validate the risk model before relying on its scale",
                "Use a bounded rollout with explicit rollback criteria",
            ])
        
        if risk_score > 0.5:
            recommendations.extend([
                "Conduct thorough competitive analysis",
                "Establish contingency plans",
                "Monitor key risk indicators closely"
            ])
        
        if failure_probability <= self.legacy_score_threshold:
            recommendations.append(
                "Low heuristic output; calibration evidence is still required"
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
                model_type="Heuristic prototype (uncalibrated)",
                is_active=True
            )
            session.add(agent)
            session.commit()
        
        return agent.id

class DecisionOrchestrator:
    """Orchestrate recommendation-only venture analysis."""
    
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
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except SQLAlchemyError as e:
            logger.error("Venture evaluation failed", venture_id=venture_id, error=str(e))
            raise
        except Exception:
            logger.exception("Unexpected error during venture evaluation")
            raise
    
    def _generate_final_decision(self, market_analysis: Dict[str, Any], 
                               risk_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a bounded validation recommendation, never an execution order."""
        opportunity_score = market_analysis['opportunity_score']
        risk_score = risk_analysis['risk_score']
        
        # Decision matrix
        if opportunity_score > 0.7 and risk_score <= 0.35:
            action = "PROPOSE_BOUNDED_PILOT"
            rationale = "Promising heuristic signal; seek external proof inside strict caps"
        elif opportunity_score > 0.5:
            action = "REQUEST_EXTERNAL_VALIDATION"
            rationale = "Evidence is insufficient for a launch or capital decision"
        else:
            action = "HOLD_FOR_EVIDENCE"
            rationale = "The current hypothesis does not justify further commitment"
        
        return {
            'action': action,
            'rationale': rationale,
            'opportunity_score': opportunity_score,
            'heuristic_risk_score': risk_score,
            'requires_human_approval': True,
            'execution_authority': False,
            'probability_calibrated': False,
        }
