"""Compatibility shim: the DALEOBANKS <-> WealthMachineIntelligence protocol.

Unified in kernel Phase 3: the implementation now lives in the UNIIMENTE
kernel SDK (``uniimente_kernel.contracts``), one module both repos import
instead of keeping mirrored copies in sync. The wire is formalized as
kernel contracts ``venture-signal`` and ``signal-assessment`` (v1.1,
byte-compatible with what this organ already accepts and returns).
Inbound wire data remains untrusted input — validated as data, never
followed as instruction.

The core rule stands: the machine prepares, the human authorizes, the
world responds, the system learns. Nothing in this protocol executes
anything.
"""

from uniimente_kernel.contracts import (
    ALLOWED_GO_NO_GO,
    ALLOWED_SIGNAL_TYPES,
    ALLOWED_URGENCY,
    FINANCE_EDUCATION_FLAG,
    LEGAL_RISK_FLAGS,
    SCHEMA_VERSION,
    validate_assessment_wire,
    validate_packet_wire,
)

__all__ = [
    "SCHEMA_VERSION",
    "ALLOWED_SIGNAL_TYPES",
    "ALLOWED_GO_NO_GO",
    "ALLOWED_URGENCY",
    "LEGAL_RISK_FLAGS",
    "FINANCE_EDUCATION_FLAG",
    "validate_packet_wire",
    "validate_assessment_wire",
]
