"""Read the staffing result already carried by the DALEOBANKS bridge.

This checks a report's internal arithmetic, not the original staffing problem,
the producer's identity, its certificate, or the world. Even ``certified: true``
is unverified wire data here. Results can tighten a recommendation, never grant
authority or manufacture demand, revenue, capacity, or proof of optimality.

A recognised report describes capacity, not market demand. ``staffing_indices``
names the evidence items that carry one so the intake keeps them out of the
demand signals and the adversarial evidence count: adding a report can change
reasons, the validation plan and the go cap, never the opportunity score.

The arithmetic checked is what the Kernel's ``certify_staffing`` guarantees of
every answer it emits: staffed plus shortage is total demand; the assignment
sums to staffed and unfilled to shortage; ``certified`` is true and a
certificate object is present; the bottleneck is null exactly when nothing is
short, and otherwise its demand minus capacity is the shortage, every unfilled
order is one of its orders, its orders are served only by its eligible workers,
and the units on them equal its capacity. A report that breaks any of these is
an explicit unresolved observation, never "arithmetic agrees".

Classification depends on the report only: nesting depth and number length are
bounded by a scan before parsing, so neither the interpreter's recursion limit
nor its integer-digit limit can change a reason or the validation plan.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

LABEL = "Evidence from GREG's certified staffing plan"
# The producer's label, matched anywhere in an item, in any case, with a straight or typographic apostrophe.
_LABEL = re.compile(r"evidence from greg[’'‘]s certified staffing plan", re.IGNORECASE)
# Staffing-shaped JSON under some other label: read nothing from it, but never let it pass as prose.
_SHAPE = re.compile(r'"(?:staffed|total_demand|shortage)"\s*:')
_TERMINATOR = re.compile(r"\s*[.!?]?\s*")
MAX_REPORT_CHARS = 8192
MAX_REPORTS = 16
MAX_ASSIGNMENTS = 256
MAX_UNITS = 10**12
MAX_DEPTH = 8                       # the producer's report nests three deep
MAX_DIGITS = len(str(MAX_UNITS))
MAX_DESCRIPTION = 200               # label to colon, e.g. " for the docks and the line"


@dataclass(frozen=True)
class StaffingReview:
    evidence_index: int
    staffed: int | None = None
    demand: int | None = None
    shortage: int | None = None
    unfilled: tuple[tuple[str, int], ...] = ()
    error: str | None = None
    part: int = 1
    assignment: tuple[tuple[str, str, int], ...] = ()

    @property
    def where(self) -> str:
        return f"{self.evidence_index}" if self.part == 1 else f"{self.evidence_index}.{self.part}"

    @property
    def prevents_go(self) -> bool:
        return self.error is not None or bool(self.shortage)

    @property
    def priority(self) -> tuple:
        """Unresolved reports first, then shortages, then complete reports; wire order within each."""
        return (self.error is None, not self.shortage, self.evidence_index, self.part)

    @property
    def reason(self) -> str:
        prefix = f"staffing evidence[{self.where}] (unverified report): "
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
            return f"Resolve staffing evidence[{self.where}]: {self.error}; obtain the original plan and inputs"
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


def _names(value, what):
    if not isinstance(value, list) or len(value) > MAX_ASSIGNMENTS:
        raise ValueError(f"bottleneck {what} must be a bounded list")
    names = [_name(v) for v in value]
    if len(set(names)) != len(names):
        raise ValueError(f"bottleneck {what} repeat")
    return set(names)


def _extent(text: str) -> int:
    """End of the first top-level JSON object in ``text`` (which starts with '{'), scanning outside strings.

    Raises on structure deeper than MAX_DEPTH or a number longer than MAX_DIGITS, before any parser runs, and
    ``json.JSONDecodeError`` when the object never closes (a cut report)."""
    depth, digits, in_string, escaped = 0, 0, False, False
    for i, ch in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch.isdigit():
            digits += 1
            if digits > MAX_DIGITS:
                raise ValueError("a number in the staffing report exceeds the supported size")
            continue
        digits = 0
        if ch == '"':
            in_string = True
        elif ch in "{[":
            depth += 1
            if depth > MAX_DEPTH:
                raise ValueError("staffing JSON exceeds the supported nesting depth")
        elif ch in "}]":
            depth -= 1
            if depth == 0:
                return i + 1
    raise json.JSONDecodeError("unterminated", text, len(text))


def _check(value) -> tuple:
    """The certify_staffing guarantees, from the report alone. Returns the reading's fields."""
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
    rows, total = [], 0
    for row in assignment:
        if not isinstance(row, list) or len(row) != 3:
            raise ValueError("assignment rows must be [worker, order, units]")
        rows.append((_name(row[0]), _name(row[1]), _units(row[2], "assignment units", positive=True)))
        total += rows[-1][2]
    if len({(w, o) for w, o, _ in rows}) != len(rows):
        raise ValueError("assignment repeats a worker/order pair")
    if total != staffed:
        raise ValueError("assignment units do not equal staffed")

    unfilled = value.get("unfilled")
    if not isinstance(unfilled, dict) or len(unfilled) > MAX_ASSIGNMENTS:
        raise ValueError("unfilled must be a bounded object, even when empty")
    unfilled = tuple(sorted((_name(order), _units(units, "unfilled units", positive=True))
                            for order, units in unfilled.items()))
    if sum(units for _, units in unfilled) != shortage:
        raise ValueError("unfilled units do not equal shortage")

    if value.get("certified") is not True:
        raise ValueError("the producer does not mark this plan certified")
    if not isinstance(value.get("certificate"), dict):
        raise TypeError("the report carries no certificate object")
    if "bottleneck" not in value:
        raise ValueError("the report states no bottleneck (null when nothing is short)")
    bottleneck = value["bottleneck"]
    if shortage == 0:
        if bottleneck is not None:
            raise ValueError("a report with no shortage names a bottleneck")
    else:
        if not isinstance(bottleneck, dict):
            raise ValueError("a report with a shortage names no bottleneck")
        orders = _names(bottleneck.get("orders"), "orders")
        workers = _names(bottleneck.get("eligible_workers"), "eligible_workers")
        need = _units(bottleneck.get("demand"), "bottleneck demand")
        capacity = _units(bottleneck.get("capacity"), "bottleneck capacity")
        if not orders:
            raise ValueError("a report with a shortage names no bottleneck orders")
        if need - capacity != shortage:
            raise ValueError("the bottleneck's demand minus capacity is not the shortage")
        if not {order for order, _ in unfilled} <= orders:
            raise ValueError("an unfilled order lies outside the bottleneck")
        on_bottleneck = [(w, o, x) for w, o, x in rows if o in orders]
        if any(w not in workers for w, _, _ in on_bottleneck):
            raise ValueError("a bottleneck order is served by a worker outside the bottleneck")
        if sum(x for *_, x in on_bottleneck) != capacity:
            raise ValueError("units on the bottleneck orders do not equal its capacity")
    return staffed, demand, shortage, unfilled, tuple(sorted(rows))


def _reports(item: str):
    """Each (canonical JSON, fields) or error for the labelled reports in one evidence item, in order.

    DALEOBANKS splits a thought into sentences only after '.', '!' or '?', so two reports, or prose before a label,
    can arrive in one item. Each labelled report is read from its label; a sentence terminator after one is allowed,
    and anything else after it is an explicit error rather than a silently ignored tail."""
    if len(item) > MAX_REPORT_CHARS:
        yield ValueError("staffing report exceeds the supported size")
        return
    match = _LABEL.search(item)
    while match is not None:
        colon = item.find(":", match.end())
        if colon < 0 or colon - match.end() > MAX_DESCRIPTION or "{" in item[match.end():colon]:
            yield ValueError("staffing report has no JSON body")
            return
        start = len(item) - len(item[colon + 1:].lstrip())
        if not item.startswith("{", start):
            yield ValueError("staffing report must be a JSON object")
            return
        try:
            end = start + _extent(item[start:])
            value = json.loads(item[start:end], object_pairs_hook=_object, parse_constant=_constant)
        except json.JSONDecodeError:
            yield json.JSONDecodeError("malformed", item, start)
            return
        except ValueError as exc:
            yield exc
            return
        try:
            yield json.dumps(value, sort_keys=True, separators=(",", ":")), _check(value)
        except (TypeError, ValueError) as exc:
            yield exc
        tail = _TERMINATOR.match(item, end).end()
        match = _LABEL.match(item, tail)
        if match is None and tail < len(item):
            yield ValueError("text follows the staffing report")
            return


def staffing_indices(evidence: list[str]) -> set[int]:
    """Indices of the evidence items that carry a staffing report (recognised, or staffing-shaped under another
    label). They describe capacity, not demand."""
    return {i for i, item in enumerate(evidence)
            if isinstance(item, str) and (_LABEL.search(item) or _SHAPE.search(item))}


def review_staffing_evidence(evidence: list[str]) -> list[StaffingReview]:
    """Interpret only the existing producer's explicitly labeled staffing data.

    Ordinary prose stays on the existing route. A malformed, truncated, inconsistent,
    replayed or unlabeled staffing report remains an explicit unresolved observation,
    rather than disappearing.
    """
    reviews, seen = [], {}
    for index, item in enumerate(evidence):
        if not isinstance(item, str):
            continue
        if not _LABEL.search(item):
            if _SHAPE.search(item):
                reviews.append(StaffingReview(index, error="staffing-shaped data without the recognised label; "
                                                           "not read"))
            continue
        for part, result in enumerate(_reports(item), start=1):
            if len(reviews) == MAX_REPORTS:
                reviews.append(StaffingReview(index, part=part, error="too many staffing reports; review limit reached"))
                return reviews
            if isinstance(result, json.JSONDecodeError):
                reviews.append(StaffingReview(index, part=part, error="staffing JSON is malformed or incomplete"))
            elif isinstance(result, Exception):
                reviews.append(StaffingReview(index, part=part, error=str(result)))
            else:
                canonical, (staffed, demand, shortage, unfilled, assignment) = result
                first = seen.setdefault(canonical, f"{index}" if part == 1 else f"{index}.{part}")
                here = f"{index}" if part == 1 else f"{index}.{part}"
                if first != here:
                    reviews.append(StaffingReview(index, part=part, error=f"repeats staffing evidence[{first}] "
                                                                          "(a replayed copy); counted once"))
                else:
                    reviews.append(StaffingReview(index, staffed, demand, shortage, unfilled, part=part,
                                                  assignment=assignment))
    return reviews
