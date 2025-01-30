from typing import Dict, Any

class RiskAssessmentAgent:
    def __init__(self):
        self.risk_weights = {
            "market_risk": 0.4,
            "compliance": 0.3,
            "operational": 0.3
        }
        
    async def evaluate_risk(self, risk_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall risk score based on multiple factors"""
        
        # Convert market risk class to score
        market_risk_scores = {"low": 0.2, "medium": 0.5, "high": 0.8}
        market_risk_score = market_risk_scores.get(risk_data["market_risk"], 0.5)
        
        # Calculate compliance risk score
        compliance_score = 0.7 if risk_data["compliance_status"] == "pending" else 0.3
        
        # Calculate operational risk score
        op_metrics = risk_data["operational_metrics"]
        op_score = 1 - ((op_metrics["efficiency"] + op_metrics["reliability"]) / 2)
        
        # Calculate weighted total risk
        total_risk = (
            market_risk_score * self.risk_weights["market_risk"] +
            compliance_score * self.risk_weights["compliance"] +
            op_score * self.risk_weights["operational"]
        )
        
        return {
            "total_risk": total_risk,
            "risk_factors": {
                "market": market_risk_score,
                "compliance": compliance_score,
                "operational": op_score
            },
            "status": "high" if total_risk > 0.7 else "medium" if total_risk > 0.4 else "low"
        }
