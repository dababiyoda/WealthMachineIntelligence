"""Lightweight JWT stub for test environments."""

from typing import Any, Dict


def encode(payload: Dict[str, Any], key: str, algorithm: str = "HS256") -> str:  # pragma: no cover - simple stub
    return "stub-token"


def decode(token: str, key: str, algorithms: Any | None = None) -> Dict[str, Any]:  # pragma: no cover - simple stub
    return {"sub": "test-user"}
