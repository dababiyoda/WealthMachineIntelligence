"""Adversarial underwriting: every assessment argues with itself.
Disagreement is preserved, a severe unresolved case caps the verdict,
and the do-nothing comparison is always present."""

import pytest

from src.services.adversarial import build_cases, severe_unresolved
from src.services.opportunity_intake import OpportunityIntakeService, set_intake_service
from tests.test_opportunity_intake import fire_packet


@pytest.fixture()
def service():
    svc = OpportunityIntakeService()
    set_intake_service(svc)
    yield svc
    set_intake_service(None)


def _cases_by_name(assessment):
    return {c["case"]: c for c in assessment["cases"]}


def test_strong_opportunity_still_receives_bear_analysis(service):
    strong = fire_packet(
        id="adv-strong", urgency="high", risk_flags=[],
        evidence=["five distinct replies", "two DMs describing the pain",
                  "a creator asking to collaborate"],
    )
    assessment = service.evaluate_packet(strong)
    cases = _cases_by_name(assessment)

    assert assessment["go_no_go"] == "go"  # strong stays strong...
    assert cases["bear"]["stance"] == "against"  # ...but the bear still speaks
    assert cases["bull"]["stance"] == "for"  # disagreement preserved, not averaged
    assert "do_nothing" in cases  # the mandatory comparison
    assert "incumbent_response" in cases
    assert "opportunity_cost" in cases


def test_sybil_shaped_evidence_gets_fraud_case_and_caps_verdict(service):
    suspicious = fire_packet(
        id="adv-sybil", urgency="high", risk_flags=[],
        evidence=["I would totally pay for this!", "i would totally pay for this!",
                  "I would totally pay for this! "],
    )
    assessment = service.evaluate_packet(suspicious)
    cases = _cases_by_name(assessment)

    assert cases["fraud_manipulation"]["severity"] == "high"
    assert assessment["go_no_go"] != "go"  # score cannot erase the risk
    assert any("adversarial case" in r for r in assessment["reasons"])


def test_severe_unresolved_helper():
    cases = build_cases(
        {"evidence": ["a", "a"], "monetization_paths": [], "urgency": "high",
         "possible_offer": "x", "buyer_type": "consumer"},
        0.9, 0.8,
    )
    assert "fraud_manipulation" in severe_unresolved(cases)


def test_assessment_remains_non_executable_with_cases(service):
    assessment = service.evaluate_packet(fire_packet(id="adv-nonexec"))
    assert assessment["requires_human_approval"] is True
    assert assessment["cases"]  # cases attached
    # Objections travel in structured reasons for the human, too.
    assert any(r.startswith("[") for r in assessment["reasons"])
