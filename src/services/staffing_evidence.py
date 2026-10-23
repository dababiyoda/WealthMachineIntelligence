"""Read the staffing result already carried by the DALEOBANKS bridge.

This checks a report's internal arithmetic, not the original staffing problem,
the producer's identity, its certificate, or the world. Even ``certified: true``
is unverified wire data here. Results can tighten a recommendation, never grant
authority or manufacture demand, revenue, capacity, or proof of optimality.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

LABEL = "Evidence from GREG's certified staffing plan"
MAX_REPORT_CHARS = 8192
MAX_REPORTS = 16
MAX_ASSIGNMENTS = 256
MAX_UNITS = 10**12


@dataclass(frozen=True)
class StaffingReview:
    evidence_index: int
    staffed: int | None = None
    demand: int | None = None
    shortage: int | None = None
    unfilled: tuple[tuple[str, int], ...] = ()
    error: str | None = None

    @property
    def prevents_go(self) -> bool:
        return self.error is not None or bool(self.shortage)

    @property
    def reason(self) -> str:
        prefix = f"staffing evidence[{self.evidence_index}] (unverified report): "
        if self.error:
            return prefix + self.error + "; obtain the complete original plan"
        return (
            prefix + f"staffed={self.staffed}, total_demand={self.demand}, shortage={self.shortage}, "
            f"unfilled={json.dumps(dict(self.unfilled), sort_keys=True)}; "
            "internal arithmetic agrees only; original demand, capacity and optimality are not verified"
        )

    @property
    def next_action(self) -> str:
        if self.error:
            return f"Resolve staffing evidence[{self.evidence_index}]: {self.error}; obtain the original plan and inputs"
        if self.shortage:
            return (
                f"Validate the reported staffing shortage of {self.shortage} units against original demand and "
                f"capacity; resolve unfilled orders {json.dumps(dict(self.unfilled), sort_keys=True)} before proceeding"
            )
        return (
            f"Validate the reported staffing result of {self.staffed}/{self.demand} units against original demand "
            "and capacity; obtain independent acceptance before relying on it"
        )


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON keys make the staffing report ambiguous")
        result[key] = value
    return result


def _constant(_value):
    raise ValueError("nonfinite JSON numbers are not staffing quantities")


def _units(value, name, *, positive=False):
    if type(value) is not int or not (int(positive) <= value <= MAX_UNITS):
        raise ValueError(f"{name} must be a bounded {'positive' if positive else 'nonnegative'} integer")
    return value


def _name(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 128:
        raise ValueError("assignment and order identifiers must be nonempty strings of at most 128 characters")
    return value


def _read(item: str, index: int) -> StaffingReview:
    if len(item) > MAX_REPORT_CHARS:
        raise ValueError("staffing report exceeds the supported size")
    _, separator, raw = item.partition(":")
    if not separator:
        raise ValueError("staffing report has no JSON body")
    value = json.loads(raw.strip(), object_pairs_hook=_object, parse_constant=_constant)
    if not isinstance(value, dict):
        raise TypeError("staffing report must be a JSON object")
    staffed = _units(value.get("staffed"), "staffed")
    demand = _units(value.get("total_demand"), "total_demand")
    shortage = _units(value.get("shortage"), "shortage")
    if staffed + shortage != demand:
        raise ValueError("staffed plus shortage does not equal total_demand")

    assignment = value.get("assignment")
    if not isinstance(assignment, list) or len(assignment) > MAX_ASSIGNMENTS:
        raise ValueError("assignment must be a bounded list")
    pairs, total = set(), 0
    for row in assignment:
        if not isinstance(row, list) or len(row) != 3:
            raise ValueError("assignment rows must be [worker, order, units]")
        pair = (_name(row[0]), _name(row[1]))
        if pair in pairs:
            raise ValueError("assignment repeats a worker/order pair")
        pairs.add(pair)
        total += _units(row[2], "assignment units", positive=True)
    if total != staffed:
        raise ValueError("assignment units do not equal staffed")

    unfilled = value.get("unfilled")
    if not isinstance(unfilled, dict) or len(unfilled) > MAX_ASSIGNMENTS:
        raise ValueError("unfilled must be a bounded object, even when empty")
    unfilled = tuple(sorted((_name(order), _units(units, "unfilled units", positive=True))
                            for order, units in unfilled.items()))
    if sum(units for _, units in unfilled) != shortage:
        raise ValueError("unfilled units do not equal shortage")
    return StaffingReview(index, staffed, demand, shortage, unfilled)


def review_staffing_evidence(evidence: list[str]) -> list[StaffingReview]:
    """Interpret only the existing producer's explicitly labeled staffing data.

    Ordinary prose stays on the existing route. A malformed/truncated recognized
    report remains an explicit unresolved observation, rather than disappearing.
    """
    reviews = []
    for index, item in enumerate(evidence):
        text = item.lstrip()
        if not text.startswith(LABEL):
            continue
        if len(reviews) == MAX_REPORTS:
            reviews.append(StaffingReview(index, error="too many staffing reports; review limit reached"))
            break
        try:
            reviews.append(_read(text, index))
        except json.JSONDecodeError:
            reviews.append(StaffingReview(index, error="staffing JSON is malformed or incomplete"))
        except RecursionError:
            reviews.append(StaffingReview(index, error="staffing JSON exceeds the supported nesting depth"))
        except (TypeError, ValueError) as exc:
            reviews.append(StaffingReview(index, error=str(exc)))
    return reviews
