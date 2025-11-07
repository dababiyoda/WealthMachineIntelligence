"""
Knowledge Graph Connector
========================

This module exposes a high‑level interface to interact with both the
in‑memory knowledge graph (provided by ``knowledge_graph.py``) and
the persistent SQLAlchemy models defined in the original
``WealthMachineIntelligence`` repository.  Its responsibilities include
updating venture statuses and metrics, persisting sentiment and
forecast data, recording risk assessments, and retrieving competitor
information.  The connector acts as a central gateway for the rule
engine and AI agents, encapsulating both graph and database operations.

The implementation deliberately logs actions for auditing and
debugging purposes.  In a production environment this layer could be
extended to emit events to message queues or external monitoring
services.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional

from .knowledge_graph import knowledge_graph, Node, Edge

try:
    # Try to import database models and session manager.  These imports
    # will fail in pure unit‑test environments where SQLAlchemy isn't
    # available or configured.  When unavailable, the connector falls
    # back to graph‑only behaviour.
    from ..database.connection import db
    from ..database.models import DigitalVenture, MarketAnalysis, RiskAssessment
except Exception as e:  # broad catch to handle missing dependencies
    db = None  # type: ignore
    DigitalVenture = None  # type: ignore
    MarketAnalysis = None  # type: ignore
    RiskAssessment = None  # type: ignore
    logging.warning("Database modules not available: %s", e)


logger = logging.getLogger(__name__)


class KnowledgeGraphConnector:
    """Facade for synchronising the knowledge graph and the database.

    All public methods perform their work in both the graph and the
    database (when available).  If no database connection is
    configured the operations will still be reflected in the in‑memory
    graph, allowing the rule engine to function in isolation.
    """

    def update_venture_status(self, venture_id: str, new_status: str) -> None:
        """Update the status of a venture.

        Parameters
        ----------
        venture_id: str
            Unique identifier of the venture.
        new_status: str
            New status (e.g. ``'On Hold'`` or ``'Needs Review'``).
        """
        logger.info("Updating venture status", extra={"venture_id": venture_id, "new_status": new_status})

        # Update database record if available
        if db and DigitalVenture:
            try:
                with db.get_session() as session:
                    venture = session.query(DigitalVenture).filter(DigitalVenture.id == venture_id).first()
                    if venture:
                        venture.status = new_status  # type: ignore[attr-defined]
                    else:
                        logger.warning("Venture not found in DB when updating status", extra={"venture_id": venture_id})
            except Exception as exc:  # pragma: no cover - defensive fallback for tests
                logger.warning("Skipping database status update", exc_info=exc)

        # Update or create node in knowledge graph
        node = knowledge_graph.get_node(venture_id)
        if node:
            node.update({"status": new_status})
        else:
            # If node does not exist, create a basic node with minimal properties
            knowledge_graph.add_node(Node(venture_id, "DigitalVenture", {"status": new_status}))

    def update_venture_metrics(self, venture_id: str, metrics: Dict[str, Any]) -> None:
        """Update numerical metrics for a venture.

        Both the database and the knowledge graph will be updated.
        """
        logger.info("Updating venture metrics", extra={"venture_id": venture_id, "metrics": metrics})

        # Persist metrics to the database where possible
        if db and DigitalVenture:
            try:
                with db.get_session() as session:
                    venture = session.query(DigitalVenture).filter(DigitalVenture.id == venture_id).first()
                    if venture:
                        for key, value in metrics.items():
                            if hasattr(venture, key):
                                setattr(venture, key, value)
                    else:
                        logger.warning("Venture not found in DB when updating metrics", extra={"venture_id": venture_id})
            except Exception as exc:  # pragma: no cover
                logger.warning("Skipping database metric update", exc_info=exc)

        # Update the knowledge graph node
        node = knowledge_graph.get_node(venture_id)
        if node:
            node.update(metrics)
        else:
            knowledge_graph.add_node(Node(venture_id, "DigitalVenture", metrics))

    def store_sentiment(self, venture_id: str, sentiment_data: Dict[str, Any]) -> None:
        """Persist sentiment analysis results for a venture.

        Sentiment data is stored in the ``MarketAnalysis`` table under
        the ``sentiment_analysis`` column.  It is also attached to the
        knowledge graph node for quick lookups.
        """
        logger.info("Storing sentiment", extra={"venture_id": venture_id, "sentiment": sentiment_data})

        if db and MarketAnalysis:
            try:
                with db.get_session() as session:
                    analysis = session.query(MarketAnalysis).filter(MarketAnalysis.venture_id == venture_id).order_by(
                        MarketAnalysis.analyzed_at.desc()
                    ).first()
                    if analysis:
                        analysis.sentiment_analysis = sentiment_data
                    else:
                        analysis = MarketAnalysis(
                            venture_id=venture_id,
                            market_size=0.0,
                            growth_rate=0.0,
                            competition_level="unknown",
                            opportunity_score=0.0,
                            lstm_prediction={},
                            sentiment_analysis=sentiment_data
                        )
                        session.add(analysis)
            except Exception as exc:  # pragma: no cover
                logger.warning("Skipping sentiment DB persistence", exc_info=exc)

        # Update knowledge graph
        node = knowledge_graph.get_node(venture_id)
        if node:
            node.update({"sentiment_analysis": sentiment_data})
        else:
            knowledge_graph.add_node(Node(venture_id, "DigitalVenture", {"sentiment_analysis": sentiment_data}))

    def store_predictions(self, venture_id: str, prediction_data: Dict[str, Any]) -> None:
        """Persist AI model predictions for a venture.

        Predictions are saved into the ``lstm_prediction`` column of
        ``MarketAnalysis`` and attached to the knowledge graph.
        """
        logger.info("Storing predictions", extra={"venture_id": venture_id, "predictions": prediction_data})

        if db and MarketAnalysis:
            try:
                with db.get_session() as session:
                    analysis = session.query(MarketAnalysis).filter(MarketAnalysis.venture_id == venture_id).order_by(
                        MarketAnalysis.analyzed_at.desc()
                    ).first()
                    if analysis:
                        analysis.lstm_prediction = prediction_data
                    else:
                        analysis = MarketAnalysis(
                            venture_id=venture_id,
                            market_size=0.0,
                            growth_rate=0.0,
                            competition_level="unknown",
                            opportunity_score=0.0,
                            lstm_prediction=prediction_data
                        )
                        session.add(analysis)
            except Exception as exc:  # pragma: no cover
                logger.warning("Skipping prediction DB persistence", exc_info=exc)

        node = knowledge_graph.get_node(venture_id)
        if node:
            node.update({"predictions": prediction_data})
        else:
            knowledge_graph.add_node(Node(venture_id, "DigitalVenture", {"predictions": prediction_data}))

    def store_forecast(self, venture_id: str, forecast_data: Dict[str, Any]) -> None:
        """Attach forecast data to the knowledge graph node.

        Forecasts are not currently persisted in the database because
        there is no dedicated column defined.  In a full
        implementation this method would write to a dedicated table.
        """
        logger.info("Storing forecast", extra={"venture_id": venture_id, "forecast": forecast_data})
        node = knowledge_graph.get_node(venture_id)
        if node:
            node.update({"forecast": forecast_data})
        else:
            knowledge_graph.add_node(Node(venture_id, "DigitalVenture", {"forecast": forecast_data}))

    def store_risk_assessment(self, venture_id: str, risk_data: Dict[str, Any]) -> None:
        """Persist a risk assessment into the database and graph.

        The ``risk_data`` should include keys like ``risk_score``,
        ``failure_probability``, ``risk_level`` and ``recommendations``.  A
        new ``RiskAssessment`` record is created and linked to the
        venture.  Additionally, the latest risk information is stored on
        the venture node.
        """
        logger.info("Storing risk assessment", extra={"venture_id": venture_id, "risk_data": risk_data})

        if db and RiskAssessment:
            try:
                with db.get_session() as session:
                    assessment = RiskAssessment(
                        venture_id=venture_id,
                        agent_id=risk_data.get("agent_id", "unknown"),
                        risk_score=risk_data.get("risk_score", 0.0),
                        failure_probability=risk_data.get("failure_probability", 0.0),
                        market_risk=risk_data.get("market_risk", 0.0),
                        operational_risk=risk_data.get("operational_risk", 0.0),
                        financial_risk=risk_data.get("financial_risk", 0.0),
                        technical_risk=risk_data.get("technical_risk", 0.0),
                        risk_level=risk_data.get("risk_level"),
                        recommendations=risk_data.get("recommendations", []),
                        confidence_level=risk_data.get("confidence_level", 0.0),
                        model_version=risk_data.get("model_version", "unknown"),
                        features_used=risk_data.get("features_used", []),
                    )
                    session.add(assessment)
                    venture = session.query(DigitalVenture).filter(DigitalVenture.id == venture_id).first()
                    if venture:
                        venture.risk_score = risk_data.get("risk_score", venture.risk_score)
                        venture.failure_probability = risk_data.get("failure_probability", venture.failure_probability)
                        venture.risk_level = risk_data.get("risk_level", venture.risk_level)
            except Exception as exc:  # pragma: no cover
                logger.warning("Skipping risk assessment DB persistence", exc_info=exc)

        # Update knowledge graph node
        node = knowledge_graph.get_node(venture_id)
        if node:
            node.update({
                "risk_score": risk_data.get("risk_score"),
                "failure_probability": risk_data.get("failure_probability"),
                "risk_level": risk_data.get("risk_level").value if hasattr(risk_data.get("risk_level"), 'value') else risk_data.get("risk_level"),
            })
        else:
            knowledge_graph.add_node(Node(venture_id, "DigitalVenture", {
                "risk_score": risk_data.get("risk_score"),
                "failure_probability": risk_data.get("failure_probability"),
                "risk_level": risk_data.get("risk_level"),
            }))

    def get_competitor_data(self, sector: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve competitor entities from the graph.

        Currently this method simply returns all knowledge graph
        entities of type ``Competitor``.  A future implementation
        could incorporate external API calls or database queries.
        """
        competitors: List[Dict[str, Any]] = []
        for node in knowledge_graph.get_nodes_by_type("Competitor"):
            if sector and node.properties.get("sector") != sector:
                continue
            competitors.append(node.properties)
        return competitors

    def update_opportunities(self, venture_id: str, opportunities: List[Dict[str, Any]]) -> None:
        """Attach newly identified opportunities to a venture node.

        Opportunities are stored under a ``opportunities`` property in
        the node.  Each entry in the list should include fields such as
        ``description``, ``expected_value`` and ``confidence``.
        """
        logger.info("Updating opportunities", extra={"venture_id": venture_id, "opportunities": opportunities})
        node = knowledge_graph.get_node(venture_id)
        if node:
            existing = node.properties.get("opportunities", [])
            existing.extend(opportunities)
            node.update({"opportunities": existing})
        else:
            knowledge_graph.add_node(Node(venture_id, "DigitalVenture", {"opportunities": opportunities}))

    def notify_role(self, role: str, message: Dict[str, Any]) -> None:
        """Send a notification to a designated role.

        Notifications are routed through the ``notify_role`` function in
        ``src.utils.notifications`` if available.  Otherwise they are
        logged.  This abstraction decouples the rule engine from
        specific messaging implementations (email, Slack, etc.).
        """
        try:
            from ..utils.notifications import notify_role as real_notify
            real_notify(role, message)
        except Exception:
            logger.info("Notify %s: %s", role, message)
