"""UAT mission control record — the enforced half of the group-chat design.

The founder's UAT design runs thirteen named bots in five mission groups
(Direction & Capital, Opportunity Foundry, Revenue & Partnerships,
Delivery & Automation, Compounding & Continuity). Its own text admits the
chat surface cannot enforce the rules it depends on: "never pretend
textual claims are locks", "do not rely on task leases as enforced
controls unless verified in tooling". This module is that tooling — the
canonical record the groups point to, with the rules made checkable:

    roster      : five groups, <=6 bots each, all thirteen roles covered
    open        : no mission without owner, reviewer, bottleneck,
                  acceptance criteria and outcome (missing fields named)
    claim       : one owner per mission; a second claim refuses; a stale
                  artifact version refuses
    grants      : every external effect needs an unexpired grant naming
                  that action, within its cash cap — or it refuses
    handoff     : packet must name an artifact at the current version and
                  a rostered receiver; ownership moves only on written
                  acceptance; rejection must say what is missing
    review      : reviewer is never the producer; a commercial claim
                  without evidence is rejected with its repair path
    effects     : an uncertain external result blocks the mission for
                  reconciliation — never an automatic retry
    collections : need evidence; synthetic amounts never count as real

execution_authority is hardcoded False: the record says what may happen,
it never makes anything happen.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

ROSTER = {
    "Hegemony": "Strategic Architecture and Portfolio Direction",
    "Strategos": "Mission Operations and Production Coordination",
    "Aurelius": "Economic Truth and Capital Continuity",
    "Veritas": "Evidence, Falsification and Acceptance",
    "Aegis": "Permissions, Risk and Resilience",
    "Prometheus": "Opportunity and Emerging Technology Discovery",
    "Logos": "Market Diligence and Decision Analysis",
    "Daedalus": "Business Architecture and Mechanism Invention",
    "Vulcan": "Product Engineering and Automation",
    "Mythos": "Positioning, Brand and Owned Distribution",
    "Concord": "Customer Access, Sales and Partnerships",
    "Continuum": "Customer Delivery, Retention and Venture Maturity",
    "Mnemosyne": "Institutional Memory and Capability Compounding",
}

GROUPS = {
    "Direction & Capital": ("Strategos", ["Hegemony", "Strategos", "Aurelius", "Veritas", "Aegis", "Mnemosyne"]),
    "Opportunity Foundry": ("Logos", ["Prometheus", "Logos", "Daedalus", "Hegemony", "Aurelius", "Veritas"]),
    "Revenue & Partnerships": ("Concord", ["Concord", "Mythos", "Daedalus", "Logos", "Aurelius", "Aegis"]),
    "Delivery & Automation": ("Continuum", ["Continuum", "Vulcan", "Daedalus", "Veritas", "Aegis", "Strategos"]),
    "Compounding & Continuity": ("Mnemosyne", ["Mnemosyne", "Aurelius", "Continuum", "Concord", "Hegemony", "Logos"]),
}
MAX_GROUP_SIZE = 6                       # documented Grok group limit: two to six bots

STATES = ("PROPOSED", "SCOPED", "AUTHORIZED", "READY", "RUNNING", "REVIEW", "ACCEPTED",
          "DELIVERED", "PARTIALLY_COLLECTED", "COLLECTED", "BLOCKED", "REJECTED",
          "INCIDENT", "CLOSED")
TRANSITIONS = {
    "PROPOSED": {"SCOPED", "CLOSED"},
    "SCOPED": {"AUTHORIZED", "BLOCKED", "CLOSED"},
    "AUTHORIZED": {"READY", "BLOCKED", "CLOSED"},
    "READY": {"RUNNING", "BLOCKED"},
    "RUNNING": {"REVIEW", "BLOCKED", "INCIDENT"},
    "REVIEW": {"ACCEPTED", "REJECTED"},
    "REJECTED": {"RUNNING", "CLOSED"},
    "ACCEPTED": {"DELIVERED", "CLOSED"},
    "DELIVERED": {"PARTIALLY_COLLECTED", "COLLECTED", "INCIDENT"},
    "PARTIALLY_COLLECTED": {"COLLECTED", "INCIDENT"},
    "COLLECTED": {"CLOSED"},
    "BLOCKED": {"SCOPED", "AUTHORIZED", "READY", "RUNNING", "CLOSED"},
    "INCIDENT": {"BLOCKED", "CLOSED"},
    "CLOSED": set(),
}
DECISIONS = ("VALIDATE", "COMMIT", "RECONFIGURE", "STAGE-GATE", "PARK", "KILL")
EXTERNAL_ACTIONS = frozenset({"contact", "send", "publish", "spend", "sign", "deploy",
                              "delete", "collect_payment", "refund", "change_permissions"})
REQUIRED_FIELDS = ("mission_id", "venture_id", "owner", "reviewer", "bounded_outcome",
                   "active_bottleneck", "acceptance_criteria", "deadline")
HANDOFF_FIELDS = ("mission_id", "artifact_ref", "artifact_version", "from_bot", "to_bot",
                  "outcome", "requested_action", "acceptance_criterion")


class MissionRefusal(ValueError):
    """The record refuses the operation and says why. Fails closed."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Grant:
    grant_id: str
    actions: frozenset
    expires_at: datetime
    cash_cap_usd: float = 0.0


@dataclass
class Mission:
    mission_id: str
    venture_id: str
    owner: str
    reviewer: str
    bounded_outcome: str
    active_bottleneck: str
    acceptance_criteria: str
    deadline: str
    origin_group: str = ""
    synthetic: bool = False
    grant: Grant | None = None
    state: str = "PROPOSED"
    claimed_by: str | None = None
    artifact_ref: str = ""
    artifact_version: int = 0
    spent_usd: float = 0.0
    decision: str | None = None
    pending_handoff: dict | None = None
    history: list = field(default_factory=list)


def validate_roster(groups: dict = GROUPS, roster: dict = ROSTER) -> list[str]:
    """Return every way the group design breaks its own rules."""
    problems, covered = [], set()
    for name, (coordinator, members) in groups.items():
        if len(members) > MAX_GROUP_SIZE:
            problems.append(f"{name}: {len(members)} bots exceeds {MAX_GROUP_SIZE}")
        if len(set(members)) != len(members):
            problems.append(f"{name}: duplicate member")
        if coordinator not in members:
            problems.append(f"{name}: coordinator {coordinator} is not a member")
        unknown = [m for m in members if m not in roster]
        if unknown:
            problems.append(f"{name}: unknown bots {unknown}")
        covered.update(members)
    missing = set(roster) - covered
    if missing:
        problems.append(f"roles in no group: {sorted(missing)}")
    return problems


class ControlRecord:
    """The canonical UAT record. Chat coordinates; this decides what is true."""

    execution_authority = False          # hardcoded: the record never acts

    def __init__(self) -> None:
        self.missions: dict[str, Mission] = {}
        self.collections: list[dict] = []

    # -- helpers ---------------------------------------------------------
    def _get(self, mission_id: str) -> Mission:
        if mission_id not in self.missions:
            raise MissionRefusal(f"unknown mission {mission_id}")
        return self.missions[mission_id]

    @staticmethod
    def _log(m: Mission, event: str, **data) -> None:
        m.history.append({"event": event, "at": _now().isoformat(), **data})

    def _move(self, m: Mission, new_state: str, by: str) -> None:
        if new_state not in TRANSITIONS[m.state]:
            raise MissionRefusal(f"{m.mission_id}: {m.state} -> {new_state} is not allowed")
        self._log(m, "state", frm=m.state, to=new_state, by=by)
        m.state = new_state

    # -- lifecycle -------------------------------------------------------
    def open(self, **fields) -> Mission:
        missing = [f for f in REQUIRED_FIELDS if not fields.get(f)]
        if missing:
            raise MissionRefusal(f"mission contract missing fields: {missing}")
        if fields["mission_id"] in self.missions:
            raise MissionRefusal(f"mission {fields['mission_id']} already exists")
        for bot in (fields["owner"], fields["reviewer"]):
            if bot not in ROSTER:
                raise MissionRefusal(f"{bot} is not on the roster")
        if fields["owner"] == fields["reviewer"]:
            raise MissionRefusal("owner cannot review its own mission")
        m = Mission(**fields)
        self.missions[m.mission_id] = m
        self._log(m, "opened", owner=m.owner)
        return m

    def transition(self, mission_id: str, new_state: str, by: str) -> Mission:
        m = self._get(mission_id)
        if by not in (m.owner, "Alfonso", "Strategos"):
            raise MissionRefusal(f"{by} does not own {mission_id}")
        if new_state in ("ACCEPTED", "REJECTED"):
            raise MissionRefusal("acceptance is the reviewer's verdict; use review()")
        self._move(m, new_state, by)
        return m

    def claim(self, mission_id: str, bot: str, artifact_version: int) -> Mission:
        m = self._get(mission_id)
        if m.claimed_by and m.claimed_by != bot:
            raise MissionRefusal(f"duplicate claim: {mission_id} is held by {m.claimed_by}")
        if artifact_version != m.artifact_version:
            raise MissionRefusal(f"stale version: claim v{artifact_version}, "
                                 f"record holds v{m.artifact_version}")
        m.claimed_by = bot
        self._log(m, "claimed", bot=bot, version=artifact_version)
        return m

    def save_artifact(self, mission_id: str, bot: str, artifact_ref: str) -> int:
        m = self._get(mission_id)
        if bot != m.claimed_by:
            raise MissionRefusal(f"{bot} must hold the claim to write {mission_id}")
        m.artifact_ref, m.artifact_version = artifact_ref, m.artifact_version + 1
        self._log(m, "artifact", ref=artifact_ref, version=m.artifact_version)
        return m.artifact_version

    # -- authority -------------------------------------------------------
    def authorize_effect(self, mission_id: str, action: str, *, amount_usd: float = 0.0,
                         now: datetime | None = None) -> dict:
        m, now = self._get(mission_id), now or _now()
        g = m.grant
        if action in EXTERNAL_ACTIONS or amount_usd > 0:
            if g is None:
                raise MissionRefusal(f"absent permission: no grant covers '{action}'; ask Alfonso")
            if now >= g.expires_at:
                raise MissionRefusal(f"expired grant {g.grant_id}; ask Alfonso to renew")
            if action not in g.actions:
                raise MissionRefusal(f"grant {g.grant_id} does not cover '{action}'")
            if m.spent_usd + amount_usd > g.cash_cap_usd:
                raise MissionRefusal(f"cash cap ${g.cash_cap_usd:,.2f} would be exceeded")
        m.spent_usd += amount_usd
        self._log(m, "authorized", action=action, amount_usd=amount_usd)
        return {"mission_id": mission_id, "action": action, "permitted": True,
                "execution_authority": False}

    def record_effect_result(self, mission_id: str, action: str, status: str) -> Mission:
        """status: confirmed | failed | unknown. Unknown is never retried blindly."""
        m = self._get(mission_id)
        if status not in ("confirmed", "failed", "unknown"):
            raise MissionRefusal(f"unknown effect status {status!r}")
        self._log(m, "effect", action=action, status=status)
        if status == "unknown":
            m.state = "BLOCKED"
            self._log(m, "reconcile_before_retry", action=action)
        return m

    # -- handoffs --------------------------------------------------------
    def handoff(self, packet: dict) -> dict:
        missing = [f for f in HANDOFF_FIELDS if packet.get(f) in (None, "")]
        if missing:
            raise MissionRefusal(f"handoff packet missing: {missing}")
        m = self._get(packet["mission_id"])
        if packet["from_bot"] != m.owner:
            raise MissionRefusal(f"{packet['from_bot']} cannot hand off a mission it does not own")
        if packet["to_bot"] not in ROSTER:
            raise MissionRefusal(f"{packet['to_bot']} is not on the roster")
        if not m.artifact_ref or packet["artifact_version"] != m.artifact_version:
            raise MissionRefusal(f"artifact v{packet['artifact_version']} is not the record's "
                                 f"current v{m.artifact_version}; send the actual file")
        m.pending_handoff = dict(packet)
        self._log(m, "handoff_sent", to=packet["to_bot"], version=m.artifact_version)
        return m.pending_handoff

    def respond_handoff(self, mission_id: str, bot: str, accept: bool, reason: str = "") -> Mission:
        m = self._get(mission_id)
        if not m.pending_handoff or m.pending_handoff["to_bot"] != bot:
            raise MissionRefusal(f"no handoff pending for {bot} on {mission_id}")
        if not accept and not reason:
            raise MissionRefusal("a rejection must name the exact missing requirement")
        if accept:
            if bot == m.reviewer:
                raise MissionRefusal("the reviewer cannot become the owner it reviews")
            m.owner, m.claimed_by = bot, None
        self._log(m, "handoff_" + ("accepted" if accept else "rejected"), by=bot, reason=reason)
        m.pending_handoff = None
        return m

    # -- review and decisions --------------------------------------------
    def review(self, mission_id: str, reviewer: str, *, claims: list[dict],
               criteria_met: bool, repair: str = "") -> Mission:
        """claims: [{"claim": str, "evidence": [refs]}]. Unsupported claims reject."""
        m = self._get(mission_id)
        if reviewer != m.reviewer:
            raise MissionRefusal(f"{reviewer} is not the assigned reviewer")
        if reviewer in (m.owner, m.claimed_by):
            raise MissionRefusal("producer cannot accept its own work")
        unsupported = [c["claim"] for c in claims if not c.get("evidence")]
        if unsupported or not criteria_met:
            if not repair:
                raise MissionRefusal("a rejection must carry an exact repair path")
            self._move(m, "REJECTED", reviewer)
            self._log(m, "rejected", unsupported=unsupported, repair=repair)
        else:
            self._move(m, "ACCEPTED", reviewer)
        return m

    def decide(self, mission_id: str, verb: str, by: str, rationale: str) -> Mission:
        m = self._get(mission_id)
        if verb not in DECISIONS:
            raise MissionRefusal(f"decision must be one of {DECISIONS}")
        if not rationale:
            raise MissionRefusal("a decision record needs its rationale")
        if verb == "COMMIT" and not any(h["event"] == "state" and h["to"] == "ACCEPTED"
                                        for h in m.history):
            raise MissionRefusal("COMMIT needs accepted evidence first; COMMIT is not encouragement")
        m.decision = verb
        self._log(m, "decision", verb=verb, by=by, rationale=rationale)
        return m

    # -- money -----------------------------------------------------------
    def record_collection(self, mission_id: str, amount_usd: float, evidence_ref: str,
                          *, synthetic: bool) -> dict:
        m = self._get(mission_id)
        if amount_usd <= 0:
            raise MissionRefusal("a collection must be a positive amount")
        if not evidence_ref:
            raise MissionRefusal("no evidence, no collection: a promise is not cash")
        if m.synthetic and not synthetic:
            raise MissionRefusal("a synthetic mission cannot record real cash")
        if not m.synthetic and synthetic:
            raise MissionRefusal("synthetic amounts never enter a real mission")
        entry = {"mission_id": mission_id, "amount_usd": amount_usd,
                 "evidence_ref": evidence_ref, "synthetic": synthetic}
        self.collections.append(entry)
        self._log(m, "collection", **entry)
        return entry

    def totals(self) -> dict:
        real = sum(c["amount_usd"] for c in self.collections if not c["synthetic"])
        fake = sum(c["amount_usd"] for c in self.collections if c["synthetic"])
        return {"real_collected_usd": round(real, 2), "synthetic_collected_usd": round(fake, 2),
                "execution_authority": False}
