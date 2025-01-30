from datetime import datetime
from typing import Dict, Any
import numpy as np

class RiskAssessmentAgent:
    def __init__(self):
        self.weights = {
            'market': 0.4,      # Market risk weight
            'compliance': 0.3,  # Compliance risk weight
            'operational': 0.3  # Operational risk weight
        }

    async def evaluate_risk(self, venture_data: Dict[str, Any]) -> Dict[str, Any]:
        # Simulate risk evaluation for testing
        market_risk = float(venture_data.get('market_risk', 'medium') == 'high')
        compliance_risk = float(venture_data.get('compliance_status', 'pending') == 'non_compliant')
        operational_risk = 1 - np.mean([
            venture_data.get('operational_metrics', {}).get('efficiency', 0.5),
            venture_data.get('operational_metrics', {}).get('reliability', 0.5)
        ])

        # Calculate weighted total risk
        total_risk = np.average(
            [market_risk, compliance_risk, operational_risk],
            weights=[
                self.weights['market'],
                self.weights['compliance'],
                self.weights['operational']
            ]
        )

        return {
            'total_risk': float(total_risk),
            'components': {
                'market': float(market_risk),
                'compliance': float(compliance_risk),
                'operational': float(operational_risk)
            },
            'weights': self.weights,
            'timestamp': datetime.now()
        }
