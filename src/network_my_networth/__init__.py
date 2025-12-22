"""Network My Net Worth package.

Provides orchestration helpers that combine the Income Streams and
Team loops, risk management, decision rules, and SMART goal tracking
into a cohesive, locally runnable application.
"""

from .system import NetworkWealthEngine, PortfolioRunResult

__all__ = ["NetworkWealthEngine", "PortfolioRunResult"]
