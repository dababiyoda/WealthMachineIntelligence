import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
READINESS_PATH = ROOT / "spec" / "uat" / "v1" / "commercial-platform-readiness.json"
BACKCAST_PATH = ROOT / "docs" / "COMMERCIAL_PLATFORM_BACKCAST.md"


def load_readiness() -> dict:
    return json.loads(READINESS_PATH.read_text(encoding="utf-8"))


def test_commercial_readiness_fails_closed() -> None:
    readiness = load_readiness()

    assert readiness["external_side_effects"] == "none"
    assert readiness["access"]["current_mode"] == "custom_owner_only"
    assert readiness["access"]["public_mode_available"] is False
    assert readiness["access"]["commercial_multi_user_ready"] is False
    assert readiness["billing"]["charges_authorized"] is False
    assert readiness["billing"]["webhook_entitlement"] == "not_implemented"
    assert readiness["connectors"]["external_oauth"] == "not_implemented"
    assert readiness["connectors"]["production_tokens_stored"] is False
    assert readiness["connectors"]["daleobanks"]["classification"] == (
        "separate_github_service"
    )
    assert readiness["connectors"]["daleobanks"]["protocol"] == {
        "intake_endpoint": "/api/opportunities/intake",
        "request_type": "OpportunityPacket",
        "response_type": "VentureAssessment",
        "requires_human_approval": True,
    }
    assert readiness["connectors"]["daleobanks"]["runtime"] == "not_configured"
    assert readiness["agent_contexts"]["live_player"]["classification"] == (
        "ai_agent_context_source_not_connector"
    )
    assert readiness["agent_contexts"]["live_player"]["authority"] == "none"


def test_owner_beta_workflows_and_activation_gates_are_explicit() -> None:
    readiness = load_readiness()

    assert set(readiness["node_1_required_workflows"]) == {
        "provision_account",
        "create_owned_egregore",
        "retrieve_owned_egregore",
        "request_plan_activation",
        "request_connector_activation",
        "request_agent_context_activation",
    }
    assert len(readiness["commercial_activation_gates"]) >= 8
    assert {"requested", "verified", "active", "revoked"}.issubset(
        readiness["status_vocabulary"]
    )


def test_backcast_preserves_truth_and_required_nodes() -> None:
    backcast = BACKCAST_PATH.read_text(encoding="utf-8")
    normalized_backcast = " ".join(backcast.split())

    for required in (
        "## GPS lock",
        "## Critical assumption register",
        "## Route tournament",
        "### Node 1 — Durable owner beta",
        "### Node 3 — Subscription activation",
        "### Node 5 — DALEOBANKS sandbox bridge",
        "## Adversarial defense",
    ):
        assert required in backcast

    assert "owner-only" in backcast
    assert "not a probability" in backcast
    assert "External completion remains blocked" in normalized_backcast
