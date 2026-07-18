"""Integrity tests for the normative UAT Enterprise System Specification.

These tests make the design contract reviewable and resistant to accidental
erosion. They do not claim that the corresponding controls exist at runtime.
Runtime enforcement is earned only through the acceptance gates declared in
``spec/uat/v1/production-acceptance-gates.json``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "spec" / "uat" / "v1"


def load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def test_manifest_is_explicit_about_current_non_enforcement() -> None:
    manifest = load(SPEC / "system-manifest.json")

    assert manifest["status"] == "normative-design-draft"
    assert manifest["runtime_enforced"] is False
    assert manifest["non_claims"]
    assert any("does not establish" in item for item in manifest["non_claims"])


def test_every_manifest_artifact_exists() -> None:
    manifest = load(SPEC / "system-manifest.json")

    for artifact in manifest["files"].values():
        path = ROOT / artifact
        assert path.is_file(), f"missing normative artifact: {artifact}"


def test_normative_document_contains_the_required_implementation_contracts() -> None:
    document = (ROOT / "docs" / "UAT_ENTERPRISE_SYSTEM_SPECIFICATION.md").read_text(encoding="utf-8")
    required_sections = {
        "## 6. Current repository disposition",
        "## 7. Seven-plane architecture",
        "## 8. Deployment strategy and service boundaries",
        "## 9. Authoritative data architecture",
        "## 10. Venture lifecycle and gates",
        "## 11. Agent system",
        "## 13. Action authorization and execution",
        "## 14. API contract",
        "## 16. Security architecture",
        "## 19. AI and model governance",
        "## 23. Testing and evaluation",
        "## 24. Backcasted implementation architecture",
        "## 27. Definition of completion",
    }

    assert required_sections <= set(document.splitlines())


def test_machine_readable_documents_share_the_manifest_version() -> None:
    manifest = load(SPEC / "system-manifest.json")
    version = manifest["version"]
    documents = [
        "venture-lifecycle.json",
        "agent-charters.json",
        "approval-matrix.json",
        "threat-model.json",
        "evaluation-suite.json",
        "production-acceptance-gates.json",
    ]

    for document in documents:
        assert load(SPEC / document)["spec_version"] == version


def test_parent_council_contains_the_twelve_required_independent_roles() -> None:
    charters = load(SPEC / "agent-charters.json")
    parent_council = charters["parent_council"]
    ids = {agent["id"] for agent in parent_council}
    required = {
        "venture_scout",
        "strategic_market_analyst",
        "product_business_planning_architect",
        "business_model_technology_architect",
        "financial_strategist_capital_allocator",
        "regulatory_legal_risk_analyst",
        "brand_distribution_growth_strategist",
        "network_coalition_strategist",
        "portfolio_governor",
        "adversarial_assurance_red_team",
        "data_evidence_knowledge_steward",
        "security_reliability_incident",
    }

    assert len(parent_council) == 12
    assert ids == required
    assert all(agent["required_outputs"] for agent in parent_council)
    assert all(agent["prohibited"] for agent in parent_council)
    assert all(agent["may_create_venture"] is False for agent in parent_council)
    assert next(agent for agent in parent_council if agent["id"] == "adversarial_assurance_red_team")["independence_required"] is True


def test_workers_cannot_inherit_sovereignty() -> None:
    constraints = load(SPEC / "agent-charters.json")["worker_constraints"]

    assert constraints["factory_or_policy_approval_required"] is True
    assert constraints["parent_accountable"] is True
    assert constraints["inherit_parent_authority"] is False
    assert constraints["may_create_venture"] is False
    assert constraints["may_modify_constitution"] is False
    assert constraints["may_grant_capabilities"] is False


def test_venture_lifecycle_has_no_skippable_core_gate() -> None:
    lifecycle = load(SPEC / "venture-lifecycle.json")
    states = {state["id"]: state for state in lifecycle["states"]}
    transitions = {tuple(transition) for transition in lifecycle["forward_transitions"]}
    core_path = [
        "signal",
        "opportunity",
        "problem_validated",
        "buyer_validated",
        "solution_validated",
        "economics_validated",
        "readiness_validated",
        "controlled_pilot",
        "paid_launch",
        "repeatable",
        "scale",
        "mature",
    ]

    assert lifecycle["initial_state"] == "signal"
    assert lifecycle["universal_transition_rules"]["no_skip"]
    assert lifecycle["cycle_outcomes"] == ["progress", "proof", "correction", "protection"]
    assert all(state in states for state in core_path)
    assert all((left, right) in transitions for left, right in zip(core_path, core_path[1:]))
    assert all(states[state]["minimum_evidence"] for state in core_path)
    assert all(states[state]["exit_evidence"] for state in core_path)
    assert all(states[state]["failure_actions"] for state in core_path)


def test_approval_matrix_is_deny_by_default_and_preserves_human_authority() -> None:
    matrix = load(SPEC / "approval-matrix.json")
    risk_classes = {risk["id"]: risk for risk in matrix["risk_classes"]}

    assert matrix["default"] == "deny"
    assert matrix["separation_of_duties"]["required"] is True
    assert set(risk_classes) == {"R0", "R1", "R2", "R3", "R4"}
    assert risk_classes["R3"]["human_approval_required"] is True
    assert risk_classes["R4"]["human_approval_required"] is True
    assert risk_classes["R4"]["autonomous_execution_permitted"] is False
    assert "self_approval" in matrix["mandatory_denials"]


def test_every_threat_maps_to_defined_controls_and_evaluations() -> None:
    threat_model = load(SPEC / "threat-model.json")
    evaluation_suite = load(SPEC / "evaluation-suite.json")
    controls = {control["id"] for control in threat_model["control_catalog"]}
    evaluations = {evaluation["id"] for evaluation in evaluation_suite["evaluations"]}
    threat_ids: set[str] = set()

    for threat in threat_model["threats"]:
        assert threat["id"] not in threat_ids
        threat_ids.add(threat["id"])
        assert threat["controls"]
        assert threat["evaluations"]
        assert set(threat["controls"]) <= controls
        assert set(threat["evaluations"]) <= evaluations


def test_evaluations_have_objective_pass_conditions() -> None:
    evaluations = load(SPEC / "evaluation-suite.json")["evaluations"]
    ids = [evaluation["id"] for evaluation in evaluations]

    assert len(ids) == len(set(ids))
    assert all(evaluation["category"] for evaluation in evaluations)
    assert all(evaluation["test"] for evaluation in evaluations)
    assert all(evaluation["pass"] for evaluation in evaluations)
    assert all(isinstance(evaluation["automated"], bool) for evaluation in evaluations)


def test_acceptance_gates_require_reviewable_evidence_and_existing_evaluations() -> None:
    gates = load(SPEC / "production-acceptance-gates.json")
    evaluations = {item["id"] for item in load(SPEC / "evaluation-suite.json")["evaluations"]}
    expected_gate_ids = {f"AG{number}" for number in range(8)}
    actual_gate_ids = {gate["id"] for gate in gates["gates"]}

    assert gates["current_declared_stage"] == "AG0_candidate_pending_independent_review"
    assert actual_gate_ids == expected_gate_ids
    for gate in gates["gates"]:
        assert gate["objective"]
        assert gate["required_artifacts"]
        assert gate["exit_evidence"]
        assert gate["required_evaluations"]
        assert set(gate["required_evaluations"]) <= evaluations
        assert gate["hold_rule"]


def test_contract_schemas_preserve_identity_evidence_and_action_controls() -> None:
    schemas = {
        name: load(SPEC / "schemas" / name)
        for name in (
            "agent-contract.schema.json",
            "evidence-record.schema.json",
            "action-request.schema.json",
        )
    }

    assert all(schema["$schema"].endswith("2020-12/schema") for schema in schemas.values())
    assert {"prohibited_actions", "approval_rules", "failure_policy", "expires_at"} <= set(schemas["agent-contract.schema.json"]["required"])
    assert {"evidence_grade", "source", "verification_status", "integrity", "review_at"} <= set(schemas["evidence-record.schema.json"]["required"])
    assert {"idempotency_key", "risk_class", "evidence_refs", "expected_postconditions", "rollback_or_compensation"} <= set(schemas["action-request.schema.json"]["required"])


def test_repository_points_to_one_normative_specification() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    legacy_plan = (ROOT / "ENTERPRISE_UPGRADE_PLAN.md").read_text(encoding="utf-8")
    legacy_analysis = (ROOT / "WEALTHMACHINE_ANALYSIS.md").read_text(encoding="utf-8")
    normative_path = "docs/UAT_ENTERPRISE_SYSTEM_SPECIFICATION.md"

    assert normative_path in readme
    assert "simulation and architectural skeleton" in readme
    assert "superseded and non-normative" in legacy_plan
    assert normative_path in legacy_plan
    assert "superseded and non-normative" in legacy_analysis
    assert normative_path in legacy_analysis
