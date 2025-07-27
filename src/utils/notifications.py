"""
Notification Utilities
----------------------

This module defines a simple notification interface used by the
knowledge graph connector and rule engine to alert human roles about
important events.  In a production deployment this layer would be
replaced with integrations to email, Slack, SMS, or other messaging
platforms.  For local development and testing it simply logs the
notification payload.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def notify_role(role: str, message: Dict[str, Any]) -> None:
    """Notify a role with a structured message.

    Parameters
    ----------
    role: str
        The name of the role to notify (e.g. ``"FinancialStrategist"``).
    message: Dict[str, Any]
        A freeform dictionary describing the notification.  Should
        include at minimum a ``"subject"`` or ``"body"`` key in a
        real implementation.
    """
    logger.info("Notification sent", extra={"role": role, "message": message})
