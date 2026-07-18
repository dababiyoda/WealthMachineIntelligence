"""Deterministic governance and evidence services for the UAT preview.

Language models may propose work.  This package owns the authoritative,
deny-by-default records that determine whether a proposed action may proceed.
"""

from .service import GovernanceService

__all__ = ["GovernanceService"]
