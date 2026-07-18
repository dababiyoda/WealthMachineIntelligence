"""Append-only, hash-chained evidence ledger.

The chain makes modification detectable. It is not a substitute for an
independently anchored WORM store in production.
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Optional

from .models import canonical_json, digest, utc_now


GENESIS_HASH = "0" * 64


@dataclass(frozen=True)
class LedgerEntry:
    sequence: int
    event_type: str
    actor_id: str
    cell_id: str
    action_id: str
    timestamp: datetime
    metadata: Mapping[str, Any]
    previous_hash: str
    entry_hash: str

    def hash_payload(self) -> Mapping[str, Any]:
        return {
            "sequence": self.sequence,
            "event_type": self.event_type,
            "actor_id": self.actor_id,
            "cell_id": self.cell_id,
            "action_id": self.action_id,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "previous_hash": self.previous_hash,
        }


class EvidenceLedger:
    """Thread-safe ledger with an optional durable JSONL append target."""

    def __init__(self, path: Optional[Path | str] = None) -> None:
        self.path = Path(path) if path else None
        self._entries: list[LedgerEntry] = []
        self._lock = threading.RLock()
        if self.path and self.path.exists():
            self._load()

    @property
    def entries(self) -> tuple[LedgerEntry, ...]:
        with self._lock:
            return tuple(self._entries)

    def append(
        self,
        event_type: str,
        actor_id: str,
        metadata: Mapping[str, Any],
        *,
        cell_id: str = "",
        action_id: str = "",
        timestamp: Optional[datetime] = None,
    ) -> LedgerEntry:
        with self._lock:
            previous_hash = self._entries[-1].entry_hash if self._entries else GENESIS_HASH
            payload = {
                "sequence": len(self._entries) + 1,
                "event_type": event_type,
                "actor_id": actor_id,
                "cell_id": cell_id,
                "action_id": action_id,
                "timestamp": timestamp or utc_now(),
                "metadata": metadata,
                "previous_hash": previous_hash,
            }
            entry = LedgerEntry(entry_hash=digest(payload), **payload)
            self._entries.append(entry)
            if self.path:
                self._append_to_disk(entry)
            return entry

    def verify_chain(self) -> bool:
        with self._lock:
            previous_hash = GENESIS_HASH
            for expected_sequence, entry in enumerate(self._entries, start=1):
                if entry.sequence != expected_sequence or entry.previous_hash != previous_hash:
                    return False
                if digest(entry.hash_payload()) != entry.entry_hash:
                    return False
                previous_hash = entry.entry_hash
            return True

    def _append_to_disk(self, entry: LedgerEntry) -> None:
        assert self.path is not None
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(canonical_json(entry) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def _load(self) -> None:
        assert self.path is not None
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                raw = json.loads(line)
                try:
                    entry = LedgerEntry(
                        sequence=int(raw["sequence"]),
                        event_type=str(raw["event_type"]),
                        actor_id=str(raw["actor_id"]),
                        cell_id=str(raw["cell_id"]),
                        action_id=str(raw["action_id"]),
                        timestamp=datetime.fromisoformat(raw["timestamp"]),
                        metadata=raw["metadata"],
                        previous_hash=str(raw["previous_hash"]),
                        entry_hash=str(raw["entry_hash"]),
                    )
                except (KeyError, TypeError, ValueError) as exc:
                    raise ValueError(f"Invalid ledger entry at line {line_number}") from exc
                self._entries.append(entry)
        if not self.verify_chain():
            raise ValueError("Evidence ledger integrity check failed")


__all__ = ["EvidenceLedger", "GENESIS_HASH", "LedgerEntry"]
