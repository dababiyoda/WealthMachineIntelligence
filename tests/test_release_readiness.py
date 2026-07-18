"""Repository-level release gates for the governed preview candidate.

These tests prove bounded implementation claims. They do not replace
independent security, legal, recovery, or deployment review.
"""

from __future__ import annotations

from html.parser import HTMLParser
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib

from fastapi import HTTPException
from fastapi.testclient import TestClient

import main as compatibility_entrypoint
from src.api.main import app
from src.api.routes import opportunities
from src.api import main as canonical_entrypoint


ROOT = Path(__file__).resolve().parents[1]


def load_json(relative_path: str) -> dict:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def production_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "ENVIRONMENT": "production",
            "DATABASE_URL": "sqlite:////tmp/uat-release-test.db",
            "JWT_SECRET_KEY": "release-test-secret-that-is-longer-than-thirty-two-characters",
            "UAT_ALLOW_DEMO_USERS": "false",
            "UAT_BOOTSTRAP_PREVIEW": "false",
        }
    )
    environment.pop("UAT_OPERATOR_USERNAME", None)
    environment.pop("UAT_OPERATOR_PASSWORD", None)
    return environment


def run_python(source: str, environment: dict[str, str]) -> subprocess.CompletedProcess[str]:
    executable = sys.executable
    if not Path(executable).exists():
        executable = (
            getattr(sys, "_base_executable", None)
            or shutil.which("python3")
            or sys.executable
        )
    return subprocess.run(
        [executable, "-c", source],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def authenticated_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        data={"username": "admin", "password": "admin"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


class StaticDocumentInspector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.remote_assets: list[str] = []
        self.disabled_ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(str(values["id"]))
            if "disabled" in values:
                self.disabled_ids.add(str(values["id"]))
        for attribute in ("src", "href"):
            value = values.get(attribute)
            if value and value.startswith(("http://", "https://", "//")):
                self.remote_assets.append(value)


def test_root_module_reexports_the_canonical_application() -> None:
    assert compatibility_entrypoint.app is canonical_entrypoint.app
    assert compatibility_entrypoint.app is app


def test_production_authentication_fails_closed() -> None:
    environment = production_environment()
    environment.pop("JWT_SECRET_KEY")
    missing = run_python("import src.api.auth", environment)
    assert missing.returncode != 0
    assert "production JWT_SECRET_KEY" in missing.stderr

    environment["JWT_SECRET_KEY"] = "too-short"
    weak = run_python("import src.api.auth", environment)
    assert weak.returncode != 0
    assert "production JWT_SECRET_KEY" in weak.stderr


def test_production_identity_configuration_has_no_demo_users() -> None:
    environment = production_environment()
    result = run_python(
        "from src.api.auth import configured_users; "
        "assert configured_users() == {}, configured_users()",
        environment,
    )
    assert result.returncode == 0, result.stderr


def test_capability_record_denies_external_autonomy() -> None:
    capability = load_json("spec/uat/v1/current-capability.json")
    assert capability["declared_stage"] == "governed_preview_release_candidate"
    assert capability["authorized_external_autonomy"] == "none"
    assert capability["runtime_enforced"] is False
    assert capability["review_required"] is True
    assert capability["acceptance_status"]["AG3_to_AG7"] == "not_implemented"


def test_live_chatgpt_site_has_a_repository_enforced_truth_boundary() -> None:
    capability = load_json("spec/uat/v1/current-capability.json")
    site = capability["operator_surfaces"]["chatgpt_site"]
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    site_doc = (ROOT / "docs/CHATGPT_SITE.md").read_text(encoding="utf-8")

    assert site["url"].startswith("https://")
    assert site["url"] in readme
    assert site["url"] in site_doc
    assert site["integration_status"] == (
        "published_truthful_frontend_not_connected_to_production_control_plane"
    )
    assert "External side effect: Not executed." in site_doc
    assert any(
        "does not read or mutate" in limitation
        for limitation in capability["limitations"]
    )


def test_governance_routes_expose_records_not_external_execution() -> None:
    paths = {
        path
        for path in app.openapi()["paths"]
        if path.startswith("/api/v1/governance")
    }
    prohibited_surfaces = ("/tools", "/publish", "/deploy", "/payments", "/sign")
    assert paths
    assert not any(fragment in path for path in paths for fragment in prohibited_surfaces)
    route_source = (ROOT / "src/api/routes/governance.py").read_text(encoding="utf-8")
    assert "do not execute external tools" in route_source
    assert "def record_execution" in route_source


def test_release_control_inventory_is_complete_and_resolvable() -> None:
    inventory = load_json("spec/uat/v1/governed-preview-controls.json")
    controls = inventory["controls"]
    ids = [control["id"] for control in controls]
    assert len(controls) == 15
    assert len(ids) == len(set(ids))
    assert inventory["external_assurance"] == "pending"

    for control in controls:
        assert control["status"] == "implemented_candidate_pending_independent_review"
        assert control["scope"]
        assert control["limitation"]
        assert control["implementation"]
        assert control["tests"]
        for location in control["implementation"]:
            assert (ROOT / location).exists(), f"missing implementation: {location}"
        for test_reference in control["tests"]:
            test_path, test_name = test_reference.split("::", 1)
            test_source = (ROOT / test_path).read_text(encoding="utf-8")
            assert f"def {test_name}(" in test_source, f"missing test: {test_reference}"


def test_static_console_is_self_contained_and_holds_unimplemented_actions() -> None:
    html = (ROOT / "static/index.html").read_text(encoding="utf-8")
    inspector = StaticDocumentInspector()
    inspector.feed(html)

    assert len(inspector.ids) == len(set(inspector.ids))
    assert inspector.remote_assets == []
    assert {"runOpportunityAnalysis", "refreshMarketData", "createAutomation"} <= (
        inspector.disabled_ids
    )
    assert "UAT Governed Preview" in html
    assert "External action authority: none" in html
    assert "admin / admin" not in html


def test_security_headers_and_anonymous_governance_hold() -> None:
    with TestClient(app) as client:
        root = client.get("/")
        assert root.status_code == 200
        policy = root.headers["content-security-policy"]
        assert "default-src 'self'" in policy
        assert "script-src 'self'" in policy
        assert "object-src 'none'" in policy
        assert "frame-ancestors 'none'" in policy
        assert root.headers["x-content-type-options"] == "nosniff"
        assert root.headers["x-frame-options"] == "DENY"
        assert client.get("/api/v1/governance/status").status_code == 401


def test_request_logging_does_not_capture_query_values() -> None:
    middleware = (ROOT / "src/api/middleware.py").read_text(encoding="utf-8")
    assert "query_parameter_names=sorted(request.query_params.keys())" in middleware
    assert "query_params=dict(request.query_params)" not in middleware


def test_all_legacy_mutation_routes_are_held() -> None:
    with TestClient(app) as client:
        headers = authenticated_headers(client)
        requests = [
            client.post(
                "/api/v1/ventures/",
                headers=headers,
                json={
                    "name": "held",
                    "venture_type": "saas",
                    "initial_investment": 0,
                },
            ),
            client.put("/api/v1/ventures/venture-x", headers=headers, json={}),
            client.delete("/api/v1/ventures/venture-x", headers=headers),
            client.post("/api/v1/ventures/venture-x/launch", headers=headers),
            client.post("/api/v1/agents/agent-x/activate", headers=headers),
            client.post("/api/v1/agents/agent-x/deactivate", headers=headers),
        ]
        assert [response.status_code for response in requests] == [409] * len(requests)


def test_production_intake_without_token_fails_closed(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("WEALTHMACHINE_INTAKE_TOKEN", raising=False)
    try:
        opportunities._check_token(None)
    except HTTPException as exc:
        assert exc.status_code == 503
    else:
        raise AssertionError("production intake accepted a request without a token")


def test_container_contract_is_bounded_and_non_root() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    runtime_requirements = (ROOT / "requirements-runtime.txt").read_text(
        encoding="utf-8"
    ).lower()
    assert "USER uat" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert '"src.api.main:app"' in dockerfile
    assert "uv sync --frozen" in dockerfile
    assert "COPY pyproject.toml uv.lock" in dockerfile
    for excluded in ("tensorflow", "transformers", "celery", "redis"):
        assert excluded not in runtime_requirements


def test_runtime_dependencies_and_lock_are_bounded_and_in_sync() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    runtime_lines = {
        line.strip()
        for line in (ROOT / "requirements-runtime.txt").read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip() and not line.startswith("#")
    }
    lock = (ROOT / "uv.lock").read_text(encoding="utf-8")

    assert runtime_lines == set(project["project"]["dependencies"])
    assert 'name = "uat-governed-preview"' in lock
    for excluded in (
        'name = "tensorflow"',
        'name = "transformers"',
        'name = "celery"',
        'name = "redis"',
        'name = "python-jose"',
        'name = "ecdsa"',
        'name = "wealthmachine-enterprise"',
    ):
        assert excluded not in lock


def test_production_example_disables_demo_users_and_marks_secrets() -> None:
    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "ENVIRONMENT=production" in example
    assert "UAT_ALLOW_DEMO_USERS=false" in example
    assert "UAT_BOOTSTRAP_PREVIEW=false" in example
    assert "UAT_ENABLE_DOCS=false" in example
    assert "JWT_SECRET_KEY=replace-" in example
    assert "UAT_OPERATOR_PASSWORD=replace-" in example
    assert "WEALTHMACHINE_INTAKE_TOKEN=replace-" in example


def test_release_workflow_requires_explicit_manual_confirmation() -> None:
    workflow = (ROOT / ".github/workflows/release-preview.yml").read_text(
        encoding="utf-8"
    )
    assert "workflow_dispatch:" in workflow
    assert "PUBLISH_GOVERNED_PREVIEW" in workflow
    assert "inputs.confirmation == 'PUBLISH_GOVERNED_PREVIEW'" in workflow
    assert "needs: verify" in workflow
    assert "uv sync --frozen --extra dev" in workflow
    assert "pip-audit --local --skip-editable" in workflow
    assert "pytest -q" in workflow
    assert "docker build --tag uat-governed-preview:release-verification" in workflow
    trigger_block = workflow.partition("\npermissions:")[0]
    assert "push:" not in trigger_block
    assert "pull_request:" not in trigger_block
    assert "sha-${{ github.sha }}" in workflow
    assert "0.2.0-rc1-${{ github.sha }}" in workflow
    assert "provenance: mode=max" in workflow
    assert "sbom: true" in workflow


def test_ci_uses_the_lock_and_runs_dependency_audit() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "uv sync --frozen --extra dev" in workflow
    assert "pip-audit --local --skip-editable" in workflow
    assert "uv pip check" in workflow
