"""Tests for the Constitutional Control Layer.

The load-bearing claims under test: default-deny, no contract means no
authority, globally prohibited actions cannot be contracted around,
irreversible and high-consequence work always escalates, autonomy rises
only with evidence and falls without it, and the ledger is append-only.
"""

import pytest

from src.control import (
    ActionRequest,
    AgentContract,
    ContractRegistry,
    EvidenceLedger,
    PolicyEngine,
)


@pytest.fixture()
def registry():
    return ContractRegistry()


@pytest.fixture()
def engine(registry):
    return PolicyEngine(registry)


def cell_contract(**overrides):
    kwargs = {
        "agent_id": "cell-alpha",
        "mission": "Validate the checklist offer with a small audience",
        "autonomy_level": 1,
        "permitted_actions": frozenset({"draft_copy", "run_experiment"}),
        "limits": {"max_spend_usd": 100.0},
        "prohibited_actions": frozenset({"commit_capital"}),
        "escalation_triggers": [],
    }
    kwargs.update(overrides)
    return AgentContract(**kwargs)


# ---------------------------------------------------------------------- #
# Agent Contracts
# ---------------------------------------------------------------------- #
def test_contract_requires_mission_and_valid_level():
    with pytest.raises(ValueError):
        AgentContract(agent_id="a", mission="")
    with pytest.raises(ValueError):
        AgentContract(agent_id="", mission="m")
    with pytest.raises(ValueError):
        AgentContract(agent_id="a", mission="m", autonomy_level=9)


def test_contract_rejects_action_both_permitted_and_prohibited():
    with pytest.raises(ValueError):
        AgentContract(
            agent_id="a", mission="m",
            permitted_actions={"x"}, prohibited_actions={"x"},
        )


def test_new_contracts_cannot_start_above_level_one(registry):
    with pytest.raises(ValueError):
        registry.register(cell_contract(autonomy_level=3))
    registry.register(cell_contract(autonomy_level=1))
    assert registry.get("cell-alpha").autonomy_level == 1


def test_duplicate_registration_rejected(registry):
    registry.register(cell_contract())
    with pytest.raises(ValueError):
        registry.register(cell_contract())


# ---------------------------------------------------------------------- #
# Autonomy: earned up, free down
# ---------------------------------------------------------------------- #
def test_promotion_requires_evidence_and_reason(registry):
    registry.register(cell_contract())
    with pytest.raises(ValueError):
        registry.set_autonomy_level("cell-alpha", 2, reason="feels ready")
    with pytest.raises(ValueError):
        registry.set_autonomy_level("cell-alpha", 2, reason="", evidence_refs=["ev-1"])

    contract = registry.set_autonomy_level(
        "cell-alpha", 2, reason="10 paying pilots", evidence_refs=["ev-1"]
    )
    assert contract.autonomy_level == 2


def test_demotion_needs_no_evidence(registry):
    registry.register(cell_contract())
    registry.set_autonomy_level("cell-alpha", 2, reason="evidence", evidence_refs=["ev-1"])
    contract = registry.set_autonomy_level("cell-alpha", 0, reason="churn spiked")
    assert contract.autonomy_level == 0


def test_every_level_change_is_logged_with_evidence(registry):
    registry.register(cell_contract())
    registry.set_autonomy_level("cell-alpha", 2, reason="pilots", evidence_refs=["ev-1"])
    registry.set_autonomy_level("cell-alpha", 1, reason="regression")

    history = registry.level_history
    assert [h["new_level"] for h in history] == [1, 2, 1]
    assert history[1]["evidence_refs"] == ["ev-1"]
    assert history[2]["reason"] == "regression"


def test_revoked_contract_cannot_be_promoted(registry):
    registry.register(cell_contract())
    registry.revoke("cell-alpha", "kill switch")
    with pytest.raises(ValueError):
        registry.set_autonomy_level("cell-alpha", 2, reason="r", evidence_refs=["ev"])


# ---------------------------------------------------------------------- #
# Policy engine: deny
# ---------------------------------------------------------------------- #
def test_no_contract_means_no_authority(engine):
    decision = engine.evaluate(ActionRequest(agent_id="ghost", action_type="draft_copy"))
    assert decision.verdict == "deny"
    assert not decision.allowed


def test_globally_prohibited_actions_are_denied_for_everyone(registry, engine):
    # Even a contract that tries to permit them cannot grant them.
    registry.register(cell_contract(
        permitted_actions=frozenset({"draft_copy", "disable_guardrails"}),
    ))
    decision = engine.evaluate(ActionRequest(
        agent_id="cell-alpha", action_type="disable_guardrails",
    ))
    assert decision.verdict == "deny"
    assert "globally prohibited" in decision.reasons[0]


@pytest.mark.parametrize("action", [
    "self_authorize", "modify_own_contract", "raise_own_autonomy",
    "bypass_policy_engine", "delete_evidence", "promise_returns",
    "personalized_financial_advice",
])
def test_control_layer_attacks_are_denied(engine, registry, action):
    registry.register(cell_contract())
    assert engine.evaluate(
        ActionRequest(agent_id="cell-alpha", action_type=action)
    ).verdict == "deny"


def test_default_deny_for_unlisted_actions(registry, engine):
    registry.register(cell_contract())
    decision = engine.evaluate(ActionRequest(
        agent_id="cell-alpha", action_type="send_invoice", category="propose",
    ))
    assert decision.verdict == "deny"


def test_contract_prohibited_list_beats_whitelist(registry, engine):
    registry.register(cell_contract())
    decision = engine.evaluate(ActionRequest(
        agent_id="cell-alpha", action_type="commit_capital",
    ))
    assert decision.verdict == "deny"


def test_revoked_contract_denies_everything(registry, engine):
    registry.register(cell_contract())
    registry.revoke("cell-alpha", "paused by operator")
    decision = engine.evaluate(ActionRequest(
        agent_id="cell-alpha", action_type="draft_copy", category="propose",
    ))
    assert decision.verdict == "deny"
    assert "revoked" in decision.reasons[0]


# ---------------------------------------------------------------------- #
# Policy engine: escalate
# ---------------------------------------------------------------------- #
def test_level_one_may_propose_but_not_execute(registry, engine):
    registry.register(cell_contract())
    proposal = engine.evaluate(ActionRequest(
        agent_id="cell-alpha", action_type="draft_copy",
        category="propose", consequence="low",
    ))
    assert proposal.verdict == "allow"

    execution = engine.evaluate(ActionRequest(
        agent_id="cell-alpha", action_type="draft_copy",
        category="execute", consequence="low",
    ))
    assert execution.verdict == "escalate"
    assert execution.requires_human_approval


def test_level_zero_may_not_even_propose(registry, engine):
    registry.register(cell_contract(autonomy_level=0))
    decision = engine.evaluate(ActionRequest(
        agent_id="cell-alpha", action_type="draft_copy", category="propose",
    ))
    assert decision.verdict == "escalate"


def test_irreversible_actions_escalate_at_every_level(registry, engine):
    registry.register(cell_contract())
    registry.set_autonomy_level("cell-alpha", 4, reason="max", evidence_refs=["ev-1"])
    decision = engine.evaluate(ActionRequest(
        agent_id="cell-alpha", action_type="draft_copy", category="execute",
        consequence="low", reversibility="irreversible",
    ))
    assert decision.verdict == "escalate"
    assert decision.requires_human_approval


def test_high_consequence_escalates_at_max_level(registry, engine):
    registry.register(cell_contract())
    registry.set_autonomy_level("cell-alpha", 4, reason="max", evidence_refs=["ev-1"])
    decision = engine.evaluate(ActionRequest(
        agent_id="cell-alpha", action_type="draft_copy",
        category="execute", consequence="high",
    ))
    assert decision.verdict == "escalate"


def test_over_limit_spend_escalates(registry, engine):
    registry.register(cell_contract())
    registry.set_autonomy_level("cell-alpha", 2, reason="ev", evidence_refs=["ev-1"])
    decision = engine.evaluate(ActionRequest(
        agent_id="cell-alpha", action_type="draft_copy", category="execute",
        consequence="low", spend_usd=101.0,
    ))
    assert decision.verdict == "escalate"
    assert "exceeds the contract limit" in decision.reasons[0]


def test_spend_with_no_limit_set_escalates(registry, engine):
    registry.register(cell_contract(limits={}))
    registry.set_autonomy_level("cell-alpha", 2, reason="ev", evidence_refs=["ev-1"])
    decision = engine.evaluate(ActionRequest(
        agent_id="cell-alpha", action_type="draft_copy", category="execute",
        consequence="low", spend_usd=1.0,
    ))
    assert decision.verdict == "escalate"


def test_hard_to_reverse_requires_level_three(registry, engine):
    registry.register(cell_contract())
    registry.set_autonomy_level("cell-alpha", 2, reason="ev", evidence_refs=["ev-1"])
    request = ActionRequest(
        agent_id="cell-alpha", action_type="draft_copy", category="execute",
        consequence="low", reversibility="hard_to_reverse",
    )
    assert engine.evaluate(request).verdict == "escalate"

    registry.set_autonomy_level("cell-alpha", 3, reason="more ev", evidence_refs=["ev-2"])
    assert engine.evaluate(request).verdict == "allow"


def test_contract_escalation_triggers_are_honored(registry, engine):
    registry.register(cell_contract(
        permitted_actions=frozenset({"run_experiment_with_capital"}),
        escalation_triggers=["capital"],
    ))
    registry.set_autonomy_level("cell-alpha", 2, reason="ev", evidence_refs=["ev-1"])
    decision = engine.evaluate(ActionRequest(
        agent_id="cell-alpha", action_type="run_experiment_with_capital",
        category="execute", consequence="low",
    ))
    assert decision.verdict == "escalate"


def test_consequence_cap_rises_with_autonomy(registry, engine):
    registry.register(cell_contract())
    registry.set_autonomy_level("cell-alpha", 2, reason="ev", evidence_refs=["ev-1"])
    medium = ActionRequest(
        agent_id="cell-alpha", action_type="draft_copy",
        category="execute", consequence="medium",
    )
    assert engine.evaluate(medium).verdict == "escalate"

    registry.set_autonomy_level("cell-alpha", 3, reason="more ev", evidence_refs=["ev-2"])
    assert engine.evaluate(medium).verdict == "allow"


# ---------------------------------------------------------------------- #
# Decision log
# ---------------------------------------------------------------------- #
def test_every_evaluation_is_logged(registry, engine):
    registry.register(cell_contract())
    engine.evaluate(ActionRequest(agent_id="cell-alpha", action_type="draft_copy",
                                  category="propose", consequence="low"))
    engine.evaluate(ActionRequest(agent_id="cell-alpha", action_type="nope"))
    engine.evaluate(ActionRequest(agent_id="other", action_type="draft_copy"))

    assert len(engine.decision_log) == 3
    assert [d.verdict for d in engine.decisions_for("cell-alpha")] == ["allow", "deny"]


def test_decision_serializes_for_audit(registry, engine):
    registry.register(cell_contract())
    decision = engine.evaluate(ActionRequest(
        agent_id="cell-alpha", action_type="draft_copy",
        category="propose", consequence="low", venture_id="v-1",
    ))
    payload = decision.to_dict()
    assert payload["verdict"] == "allow"
    assert payload["agent_id"] == "cell-alpha"
    assert payload["venture_id"] == "v-1"


def test_action_request_validates_its_own_fields():
    with pytest.raises(ValueError):
        ActionRequest(agent_id="a", action_type="x", consequence="catastrophic")
    with pytest.raises(ValueError):
        ActionRequest(agent_id="a", action_type="x", reversibility="maybe")
    with pytest.raises(ValueError):
        ActionRequest(agent_id="a", action_type="x", category="improvise")
    with pytest.raises(ValueError):
        ActionRequest(agent_id="a", action_type="x", spend_usd=-1)


# ---------------------------------------------------------------------- #
# Evidence Ledger and Assumption Register
# ---------------------------------------------------------------------- #
@pytest.fixture()
def ledger():
    return EvidenceLedger()


def test_assumptions_start_untested(ledger):
    assumption = ledger.add_assumption("Buyers will pay $29", venture_id="v-1")
    assert assumption["status"] == "untested"
    assert ledger.get_assumption(assumption["id"])["statement"] == "Buyers will pay $29"


def test_belief_changes_require_evidence(ledger):
    assumption = ledger.add_assumption("Buyers will pay $29", venture_id="v-1")
    with pytest.raises(ValueError):
        ledger.set_assumption_status(assumption["id"], "supported")

    evidence = ledger.record_evidence(
        "3 of 5 interviewees pre-paid", venture_id="v-1",
        assumption_id=assumption["id"], kind="external", strength="moderate",
    )
    updated = ledger.set_assumption_status(
        assumption["id"], "supported", evidence_ids=[evidence["id"]]
    )
    assert updated["status"] == "supported"


def test_status_history_is_preserved(ledger):
    assumption = ledger.add_assumption("Buyers will pay", venture_id="v-1")
    ledger.set_assumption_status(assumption["id"], "testing")
    evidence = ledger.record_evidence("nobody paid", venture_id="v-1",
                                      assumption_id=assumption["id"])
    ledger.set_assumption_status(assumption["id"], "refuted",
                                evidence_ids=[evidence["id"]])

    changes = [e for e in ledger.events if e["event_type"] == "assumption_status_changed"]
    assert [c["payload"]["new_status"] for c in changes] == ["testing", "refuted"]
    assert changes[0]["payload"]["old_status"] == "untested"


def test_ledger_is_append_only_and_ordered(ledger):
    ledger.add_assumption("a1", venture_id="v-1")
    ledger.record_experiment("h", "landing page test", venture_id="v-1")
    ledger.record_decision("defer", venture_id="v-1")

    events = ledger.events
    assert [e["sequence"] for e in events] == [0, 1, 2]
    # Mutating the returned copies cannot corrupt the ledger.
    events[0]["event_type"] = "tampered"
    assert ledger.events[0]["event_type"] == "assumption_added"


def test_ledger_rejects_malformed_records(ledger):
    with pytest.raises(ValueError):
        ledger.add_assumption("")
    with pytest.raises(ValueError):
        ledger.add_assumption("a", criticality="apocalyptic")
    with pytest.raises(ValueError):
        ledger.record_evidence("e", kind="hearsay")
    with pytest.raises(ValueError):
        ledger.record_evidence("e", assumption_id="does-not-exist")
    with pytest.raises(ValueError):
        ledger.record_experiment("h", "")
    with pytest.raises(ValueError):
        ledger.record_decision("")


def test_events_and_assumptions_scope_by_venture(ledger):
    a1 = ledger.add_assumption("a1", venture_id="v-1")
    ledger.add_assumption("a2", venture_id="v-2")
    ledger.record_evidence("e1", venture_id="v-1", assumption_id=a1["id"])

    assert len(ledger.assumptions_for("v-1")) == 1
    assert len(ledger.events_for("v-1")) == 2
    assert len(ledger.events_for("v-2")) == 1
