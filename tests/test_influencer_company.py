"""Phase 6 tests: the AI influencer company's structural compliance.

Disclosure is mandatory. Finance is educational-only. Legal topics
escalate. Dark patterns refuse. Kill criteria pause personas. Nothing
self-executes.
"""
import pytest

from src.services.influencer_company import (ComplianceRefusal, InfluencerCompany,
                                             KillCriteria, PersonaProfile)


def _company():
    return InfluencerCompany(charter="build public trust through honest education")


def _persona(**kw):
    base = dict(name="Atlas", niche="ai_governance", voice="precise, warm",
                allowed_topics=["ai_governance", "building_in_public", "investing"])
    base.update(kw)
    return PersonaProfile(**base)


class TestPersonaContract:
    def test_persona_requires_disclosure_and_topics(self):
        c = _company()
        with pytest.raises(ComplianceRefusal):
            c.register_persona(_persona(disclosure=""))
        with pytest.raises(ComplianceRefusal):
            c.register_persona(_persona(allowed_topics=[]))

    def test_uniimente_never_operator(self):
        with pytest.raises(ValueError, match="UNIIMENTE"):
            InfluencerCompany(charter="x", legal_operator="UNIIMENTE")


class TestCompliance:
    def test_missing_disclosure_refused(self):
        c = _company()
        p = c.register_persona(_persona())
        with pytest.raises(ComplianceRefusal, match="disclosure"):
            c.prepare(p.persona_id, topic="ai_governance", channel="x",
                      body="here is what I learned about gates")   # no AI disclosure

    def test_dark_patterns_refused(self):
        c = _company()
        p = c.register_persona(_persona())
        for body in ("Act now or miss out! AI inside", "A risk-free path — AI disclosure"):
            with pytest.raises(ComplianceRefusal, match="prohibited pattern"):
                c.prepare(p.persona_id, topic="ai_governance", channel="x", body=body)

    def test_finance_hardened_educational(self):
        c = _company()
        p = c.register_persona(_persona())
        pkg = c.prepare(p.persona_id, topic="investing", channel="x",
                        body="AI-generated: how index funds work, conceptually")
        assert any("finance_education_only" in n for n in pkg.compliance_notes)

    def test_legal_topic_escalates_never_publishes(self):
        c = _company()
        p = c.register_persona(_persona(allowed_topics=["legal_advice"]))
        with pytest.raises(ComplianceRefusal, match="legal escalation"):
            c.prepare(p.persona_id, topic="legal_advice", channel="x",
                      body="AI-generated: contract basics")

    def test_ready_package_never_self_executes(self):
        c = _company()
        p = c.register_persona(_persona())
        pkg = c.prepare(p.persona_id, topic="ai_governance", channel="x",
                        body="AI-generated: what a consequence gate is")
        assert pkg.requires_human_approval is True
        assert pkg.execution_authority is False

    def test_offbrand_refusals_accumulate_to_pause(self):
        c = _company()
        p = c.register_persona(_persona(kill_criteria=KillCriteria(max_offbrand_incidents=2)))
        for _ in range(2):
            with pytest.raises(ComplianceRefusal, match="outside persona bounds"):
                c.prepare(p.persona_id, topic="cooking", channel="x", body="AI recipe")
        assert not p.active                              # paused by kill criteria
        with pytest.raises(ComplianceRefusal, match="paused"):
            c.prepare(p.persona_id, topic="ai_governance", channel="x", body="AI post")


class TestKillCriteria:
    def test_complaint_rate_pauses_immediately(self):
        c = _company()
        p = c.register_persona(_persona())
        verdict = c.record_engagement(p.persona_id, quality=0.9, complaint_rate=0.5)
        assert verdict.startswith("paused") and not p.active

    def test_low_quality_pauses_for_review(self):
        c = _company()
        p = c.register_persona(_persona())
        verdict = c.record_engagement(p.persona_id, quality=0.1, complaint_rate=0.0)
        assert "paused" in verdict

    def test_healthy_engagement_keeps_active(self):
        c = _company()
        p = c.register_persona(_persona())
        assert c.record_engagement(p.persona_id, quality=0.8, complaint_rate=0.001) == "active"
        assert p.active
