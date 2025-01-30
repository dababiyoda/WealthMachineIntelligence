import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Import required agent classes
from ai_integration.agents.market_intelligence import MarketIntelligenceAgent
from ai_integration.agents.risk_assessment import RiskAssessmentAgent
from ai_integration.agents.legal_compliance import LegalComplianceAgent
from ai_integration.knowledge_graph import KnowledgeGraphConnector

class SystemValidator:
    def __init__(self):
        self.market_intelligence_agent = MarketIntelligenceAgent()
        self.risk_assessment_agent = RiskAssessmentAgent()
        self.legal_compliance_agent = LegalComplianceAgent()
        self.knowledge_graph = KnowledgeGraphConnector()

        # Test venture data
        self.test_venture = {
            "id": "TEST_DV_001",
            "name": "Test Digital Venture",
            "type": "SaaS",
            "phase": "Phase2",
            "market_segment": "Enterprise",
            "jurisdiction": "US"
        }

    async def validate_market_intelligence(self) -> Dict[str, Any]:
        """Test Market Intelligence Agent functionality"""
        logger.info("Starting Market Intelligence validation...")

        try:
            # Generate test market data
            market_data = {
                "price": [100, 102, 98, 103, 105],
                "volume": [1000, 1200, 800, 1100, 1300],
                "volatility": 0.15,
                "sentiment": 0.75,
                "market_cap": 1000000
            }

            # Test LSTM + Random Forest pipeline
            trends = await self.market_intelligence_agent.analyze_market_trends(market_data)
            risk_assessment = await self.market_intelligence_agent.assess_risk(market_data)

            logger.info(f"Market Intelligence Results: Trend confidence: {trends['confidence']}, Risk class: {risk_assessment['risk_class']}")
            return {"trends": trends, "risk_assessment": risk_assessment}

        except Exception as e:
            logger.error(f"Market Intelligence validation failed: {str(e)}")
            raise

    async def validate_risk_assessment(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test Risk Assessment Agent functionality"""
        logger.info("Starting Risk Assessment validation...")

        try:
            # Calculate overall risk score
            risk_evaluation = await self.risk_assessment_agent.evaluate_risk({
                "id": self.test_venture["id"],
                "market_risk": market_data["risk_assessment"]["risk_class"],
                "compliance_status": "pending",
                "operational_metrics": {"efficiency": 0.8, "reliability": 0.9}
            })

            logger.info(f"Risk Assessment Results: Total risk score: {risk_evaluation['total_risk']}")
            return risk_evaluation

        except Exception as e:
            logger.error(f"Risk Assessment validation failed: {str(e)}")
            raise

    async def validate_legal_compliance(self) -> Dict[str, Any]:
        """Test Legal Compliance Agent functionality"""
        logger.info("Starting Legal Compliance validation...")

        try:
            # Fetch and process relevant regulations
            regulations = await self.legal_compliance_agent.get_relevant_regulations(
                self.test_venture["id"]
            )

            # Process regulations and trigger notifications
            compliance_status = await self.legal_compliance_agent.process_regulations({
                "text": "Test regulation requiring data encryption",
                "metadata": {
                    "domain": "data_security",
                    "jurisdiction": self.test_venture["jurisdiction"]
                }
            })

            logger.info(f"Legal Compliance Results: Status: {compliance_status['status']}, Actions required: {len(compliance_status.get('required_actions', []))}")
            return compliance_status

        except Exception as e:
            logger.error(f"Legal Compliance validation failed: {str(e)}")
            raise

    async def validate_end_to_end(self):
        """Run complete end-to-end validation"""
        logger.info(f"Starting end-to-end validation for venture: {self.test_venture['id']}")

        try:
            # Step 1: Market Intelligence
            market_results = await self.validate_market_intelligence()
            logger.info("✓ Market Intelligence validation completed")

            # Step 2: Risk Assessment
            risk_results = await self.validate_risk_assessment(market_results)
            logger.info("✓ Risk Assessment validation completed")

            # Step 3: Legal Compliance
            compliance_results = await self.validate_legal_compliance()
            logger.info("✓ Legal Compliance validation completed")

            # Verify knowledge graph updates
            venture_status = await self.knowledge_graph.get_venture_risk_profile(
                self.test_venture["id"]
            )
            logger.info(f"Final venture status: {venture_status}")

            return {
                "market_intelligence": market_results,
                "risk_assessment": risk_results,
                "legal_compliance": compliance_results,
                "venture_status": venture_status
            }

        except Exception as e:
            logger.error(f"End-to-end validation failed: {str(e)}")
            raise

async def run_validation():
    validator = SystemValidator()
    results = await validator.validate_end_to_end()
    logger.info("End-to-end validation completed successfully")
    return results

if __name__ == "__main__":
    asyncio.run(run_validation())