import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "spec" / "uat" / "v1" / "repository-truth-audit.json"
AUDIT_DOC_PATH = ROOT / "docs" / "REPOSITORY_TRUTH_AUDIT.md"


def load_audit() -> dict:
    return json.loads(AUDIT_PATH.read_text(encoding="utf-8"))


def test_repository_truth_audit_preserves_runtime_boundary() -> None:
    audit = load_audit()

    assert audit["canonical_release_path"] == [
        "main.py",
        "src.api.main",
        "src.governance",
    ]
    assert audit["overall_classification"] == (
        "governed_preview_with_durable_owner_beta_site"
    )
    assert audit["components"]["governance_record_api"].endswith(
        "no_external_execution"
    )
    assert audit["components"]["commercial_multi_tenant_saas"].startswith(
        "blocked"
    )


def test_daleobanks_is_service_and_live_player_is_context() -> None:
    audit = load_audit()

    assert audit["daleobanks"]["classification"] == "separate_github_service"
    assert audit["daleobanks"]["opportunity_contract"] == "schema_1_0_compatible"
    assert audit["daleobanks"]["runtime_connection"] == "not_configured"
    assert audit["daleobanks"]["execution_authority"] == "none"
    assert audit["library_sources"]["/LIVE PLAYER"]["purpose"] == (
        "ai_agent_context_source"
    )
    assert audit["library_sources"]["/LIVE PLAYER"]["authority"] == "none"


def test_repository_audit_documents_unresolved_sources_and_truth_rule() -> None:
    audit_doc = AUDIT_DOC_PATH.read_text(encoding="utf-8")

    for required in (
        "## DALEOBANKS sibling-service boundary",
        "## LIVE PLAYER context boundary",
        "not absent",
        "Context may influence a bounded recommendation",
        "## Truth rule",
    ):
        assert required in audit_doc
