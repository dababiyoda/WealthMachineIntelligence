"""
Market Monitor Service
---------------------

This module defines a background service that periodically collects
market and operational metrics for each venture and feeds them into
the decision engine.  It demonstrates how the rule engine, knowledge
graph connector and simulated data collection can work together to
provide real-time insights.

The monitor relies on an external JSON rules file to define the
conditions and actions.  In production the metrics should be
collected from live data streams or third-party APIs.  Here we use
randomised simulations for demonstration purposes.
"""

from __future__ import annotations

import asyncio
import random
import logging
from typing import Dict, List

from ..core.knowledge_graph_connector import KnowledgeGraphConnector
from .decision_engine import DecisionEngine

try:
    from ..database.connection import db
    from ..database.models import DigitalVenture
except Exception:
    db = None  # type: ignore
    DigitalVenture = None  # type: ignore

logger = logging.getLogger(__name__)


class MarketMonitor:
    """Background service that evaluates ventures on a schedule."""

    def __init__(self, rules_path: str, interval_seconds: int = 60) -> None:
        self.connector = KnowledgeGraphConnector()
        self.engine = DecisionEngine.from_json_file(rules_path, connector=self.connector)
        self.interval_seconds = interval_seconds

    async def _collect_metrics(self, venture_id: str, venture_type: str) -> Dict[str, float]:
        """Simulate metric collection for a venture.

        In a real implementation this would call APIs, query data
        warehouses or read from monitoring systems.  The selected
        metrics match those referenced in the sample rules file.
        """
        # Randomised values for demonstration – adjust ranges as needed
        return {
            'market_volatility': random.uniform(0.0, 1.0),
            'risk_profile': random.choice(['Low', 'Medium', 'High']),
            'monthly_churn_rate': random.uniform(0.0, 0.2),
            'mrr_growth_rate': random.uniform(-0.1, 0.3),
            'cart_abandonment_rate': random.uniform(0.0, 1.0),
            'customer_acquisition_cost': random.uniform(10.0, 100.0),
            'regulatory_compliance_score': random.uniform(0.8, 1.0),
            'data_protection_score': random.uniform(0.8, 1.0),
        }

    async def _list_ventures(self) -> List[Dict[str, str]]:
        """Retrieve a list of ventures with their types.

        Returns a list of dicts containing ``id`` and ``type``.  If a
        database is available it will query that, otherwise it falls
        back to the knowledge graph.
        """
        ventures: List[Dict[str, str]] = []
        if db and DigitalVenture:
            with db.get_session() as session:
                for v in session.query(DigitalVenture).all():
                    ventures.append({'id': v.id, 'type': v.venture_type.value})
        else:
            # Fallback: inspect nodes in the knowledge graph
            from ..core.knowledge_graph import knowledge_graph
            for node in knowledge_graph.get_nodes_by_type('DigitalVenture'):
                v_type = node.properties.get('venture_type', 'DigitalVenture')
                ventures.append({'id': node.node_id, 'type': v_type})
        return ventures

    async def run_once(self) -> None:
        """Perform a single monitoring cycle across all ventures."""
        ventures = await self._list_ventures()
        for venture in ventures:
            metrics = await self._collect_metrics(venture['id'], venture['type'])
            # Persist collected metrics to the knowledge graph
            self.connector.update_venture_metrics(venture['id'], metrics)
            outcomes = self.engine.evaluate(venture['id'], venture['type'], metrics)
            if outcomes:
                logger.info("Actions executed", extra={"venture_id": venture['id'], "outcomes": outcomes})

    async def start(self) -> None:
        """Continuously run monitoring cycles with a fixed interval."""
        while True:
            try:
                await self.run_once()
            except Exception as e:
                logger.exception("Error during monitoring cycle: %s", e)
            await asyncio.sleep(self.interval_seconds)


async def main(rules_path: str, interval_seconds: int = 60) -> None:
    """Entry point for standalone execution."""
    monitor = MarketMonitor(rules_path=rules_path, interval_seconds=interval_seconds)
    await monitor.start()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Run market monitor service')
    parser.add_argument('--rules', type=str, default='automation/sample-rules.json', help='Path to rules file')
    parser.add_argument('--interval', type=int, default=60, help='Interval between monitoring cycles in seconds')
    args = parser.parse_args()
    asyncio.run(main(args.rules, args.interval))
