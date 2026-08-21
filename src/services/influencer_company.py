"""Phase 6 — the first AI Influencer Company.

Doctrine: an AI influencer is a media organ, not a person. It operates
under a charter, discloses its nature on every artifact, stays inside
declared topic bounds, and NEVER publishes autonomously — every artifact
leaves as a publish-ready package with ``requires_human_approval: True``,
routed to the kernel Consequence Gate by the caller.

Compliance is structural, not tonal:
  - AI disclosure is mandatory on every artifact (no disclosure -> refuse)
  - finance topics are hardened to educational-only (no income promises,
    no personalized advice) — mirrors the venture_protocol finance flag
  - legal/regulated topics force escalation, never publication
  - prohibited patterns (deception, artificial scarcity, false urgency)
    refuse the draft
  - every persona carries kill criteria; breaching one pauses the persona

The company prepares. The human authorizes. Reality responds. The system
learns.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

FINANCE_TOPICS = {"investing", "trading", "crypto", "personal_finance", "wealth"}
LEGAL_ESCALATION_TOPICS = {"legal_advice", "medical_advice", "regulated_product"}
PROHIBITED_PATTERNS = (
    "artificial scarcity", "false urgency", "hidden cost", "guaranteed income",
    "risk-free", "act now or miss out", "secret method",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class ComplianceRefusal(ValueError):
    """A draft violates persona bounds or content law. Fails closed."""


@dataclass
class KillCriteria:
    min_engagement_quality: float = 0.3      # below this, pause and review
    max_complaint_rate: float = 0.02         # above this, pause immediately
    max_offbrand_incidents: int = 3          # cumulative


@dataclass
class PersonaProfile:
    """One AI persona: voice, bounds, disclosure, kill criteria."""
    name: str
    niche: str
    voice: str
    allowed_topics: list[str]
    kill_criteria: KillCriteria = field(default_factory=KillCriteria)
    disclosure: str = "AI-generated persona operated under human charter"
    persona_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    active: bool = True
    offbrand_incidents: int = 0

    def validate(self) -> list[str]:
        problems = []
        if not self.name or not self.niche:
            problems.append("persona requires name and niche")
        if not self.disclosure:
            problems.append("AI disclosure is mandatory")
        if not self.allowed_topics:
            problems.append("persona must declare allowed topics")
        return problems


@dataclass
class ContentDraft:
    persona_id: str
    topic: str
    body: str
    channel: str
    depth_level: int = 0                  # position in a rabbit-hole sequence
    draft_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=_now)


@dataclass
class PublishPackage:
    """What leaves the company: a gated, human-ratifiable unit."""
    draft: ContentDraft
    compliance_notes: list[str]
    requires_human_approval: bool = True  # hardcoded; assessments never self-execute
    execution_authority: bool = False     # this company never holds execution authority


class InfluencerCompany:
    """The first AI influencer company: chartered personas, compliant pipeline."""

    def __init__(self, *, charter: str, legal_operator: str = "alfonso_lopez"):
        if legal_operator == "UNIIMENTE":
            raise ValueError("UNIIMENTE is never a legal operator")
        self.charter = charter
        self.legal_operator = legal_operator
        self.personas: dict[str, PersonaProfile] = {}
        self.drafts: list[dict] = []      # every draft and its verdict, kept forever

    # ------------------------------------------------------------ personas
    def register_persona(self, persona: PersonaProfile) -> PersonaProfile:
        problems = persona.validate()
        if problems:
            raise ComplianceRefusal(f"persona invalid: {problems}")
        self.personas[persona.persona_id] = persona
        return persona

    def record_engagement(self, persona_id: str, *, quality: float,
                          complaint_rate: float) -> str:
        """Feed reality back in. Kill criteria are enforced, not advisory."""
        p = self.personas[persona_id]
        if complaint_rate > p.kill_criteria.max_complaint_rate:
            p.active = False
            verdict = "paused: complaint rate breached kill criterion"
        elif quality < p.kill_criteria.min_engagement_quality:
            p.active = False
            verdict = "paused: engagement quality below floor"
        else:
            verdict = "active"
        self.drafts.append({"type": "engagement", "persona_id": persona_id,
                            "quality": quality, "complaint_rate": complaint_rate,
                            "verdict": verdict, "at": _now()})
        return verdict

    # ------------------------------------------------------------ pipeline
    def compliance_check(self, persona: PersonaProfile, draft: ContentDraft) -> list[str]:
        """Return compliance notes; raise ComplianceRefusal on any violation."""
        notes = []
        if not persona.active:
            raise ComplianceRefusal(f"persona {persona.name} is paused by kill criteria")
        if draft.topic not in persona.allowed_topics:
            persona.offbrand_incidents += 1
            if persona.offbrand_incidents >= persona.kill_criteria.max_offbrand_incidents:
                persona.active = False
            raise ComplianceRefusal(
                f"topic {draft.topic!r} outside persona bounds {persona.allowed_topics}")
        if persona.disclosure not in draft.body and "AI" not in draft.body:
            raise ComplianceRefusal("draft lacks AI disclosure; disclosure is mandatory")
        lowered = draft.body.lower()
        for pattern in PROHIBITED_PATTERNS:
            if pattern in lowered:
                raise ComplianceRefusal(f"prohibited pattern in draft: {pattern!r}")
        if draft.topic in LEGAL_ESCALATION_TOPICS:
            raise ComplianceRefusal(
                f"topic {draft.topic!r} forces legal escalation; never publishes")
        if draft.topic in FINANCE_TOPICS:
            notes.append("finance_education_only: educational framing; no income promises; "
                         "no personalized advice")
        notes.append(f"disclosure present: {persona.disclosure!r}")
        return notes

    def prepare(self, persona_id: str, *, topic: str, body: str,
                channel: str, depth_level: int = 0) -> PublishPackage:
        """Draft -> compliance -> publish-ready package. Nothing executes."""
        persona = self.personas[persona_id]
        draft = ContentDraft(persona_id=persona_id, topic=topic, body=body,
                             channel=channel, depth_level=depth_level)
        try:
            notes = self.compliance_check(persona, draft)
            verdict = "ready"
        except ComplianceRefusal as e:
            self.drafts.append({"type": "draft", "draft_id": draft.draft_id,
                                "verdict": "refused", "reason": str(e), "at": _now()})
            raise
        self.drafts.append({"type": "draft", "draft_id": draft.draft_id,
                            "verdict": verdict, "notes": notes, "at": _now()})
        return PublishPackage(draft=draft, compliance_notes=notes)
