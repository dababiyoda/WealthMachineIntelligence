"""Issue #27 exit evidence: wire parity against kernel contracts v1.1.

The vendored schemas under contracts/kernel/ are pinned by SHA-256 — any
silent drift fails here. Canonical kernel packets/assessments validate
against the vendored schema (hand-rolled structural validator: the repo
CI runs dependency-light, so parity must not require new packages).
Translations through the adapter preserve the law on both directions.
"""
import hashlib
import json
import uuid
from pathlib import Path

import pytest

from src.services import kernel_contracts as kc
from src.services.venture_protocol import validate_assessment_wire, validate_packet_wire

ROOT = Path(__file__).resolve().parent.parent
SCHEMAS = ROOT / "contracts" / "kernel"


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TestPinnedSchemas:
    def test_vendored_schemas_match_pins(self):
        assert _sha(SCHEMAS / "opportunity-packet.schema.json") == \
            kc.PINNED_SCHEMA_HASHES["opportunity-packet"]
        assert _sha(SCHEMAS / "venture-assessment.schema.json") == \
            kc.PINNED_SCHEMA_HASHES["venture-assessment"]

    def test_vendored_schemas_are_kernel_v11(self):
        packet = json.loads((SCHEMAS / "opportunity-packet.schema.json").read_text())
        assert packet["properties"]["schema_version"]["enum"] == ["1.0", "1.1"]
        assert "packet_id" in packet["required"]
        assess = json.loads((SCHEMAS / "venture-assessment.schema.json").read_text())
        assert assess["properties"]["requires_human_approval"] == {"type": "boolean",
                                                                   "const": True}
        assert assess["properties"]["execution_authority"] == {"type": "boolean",
                                                               "const": False}


def _structural_validate(instance: dict, schema: dict) -> list[str]:
    """Minimal validator for these two contracts: required, additionalProperties,
    enums, consts. (Dependency-light by design; jsonschema stays optional.)"""
    problems = []
    for req in schema.get("required", []):
        if req not in instance:
            problems.append(f"missing required: {req}")
    if schema.get("additionalProperties") is False:
        extra = set(instance) - set(schema.get("properties", {}))
        if extra:
            problems.append(f"additional properties: {sorted(extra)}")
    for key, spec in schema.get("properties", {}).items():
        if key not in instance:
            continue
        if "enum" in spec and instance[key] not in spec["enum"]:
            problems.append(f"{key} not in enum {spec['enum']}")
        if "const" in spec and instance[key] != spec["const"]:
            problems.append(f"{key} must be const {spec['const']}")
    return problems


def _kernel_packet(**kw):
    base = {
        "packet_id": str(uuid.uuid4()),
        "schema_version": "1.1",
        "created_by": "spiffe://uniimente.internal/organ/daleobanks",
        "created_at": "2026-07-20T00:00:00Z",
        "observed_failure": "founders cannot prove governance to enterprise buyers",
        "pain_owner": "founder",
        "budget_owner": "cto",
        "governing_bottleneck": "no verifiable governance evidence",
        "cheapest_decisive_test": "sell one governance-audit pilot",
        "key_risks": ["market timing"],
        "evidence_refs": ["sha256:" + "a" * 64],
    }
    base.update(kw)
    return base


def _kernel_assessment(**kw):
    base = {
        "assessment_id": str(uuid.uuid4()),
        "packet_id": str(uuid.uuid4()),
        "schema_version": "1.1",
        "assessed_by": "spiffe://uniimente.internal/organ/wealthmachine",
        "assessed_at": "2026-07-20T00:00:00Z",
        "verdict": "go",
        "adversarial_cases": {"bull": "real pain", "bear": "thin market",
                              "do_nothing": "competitors standardize"},
        "requires_human_approval": True,
        "execution_authority": False,
    }
    base.update(kw)
    return base


class TestCanonicalInstancesValidate:
    def test_kernel_packet_validates_against_vendored_schema(self):
        schema = json.loads((SCHEMAS / "opportunity-packet.schema.json").read_text())
        assert _structural_validate(_kernel_packet(), schema) == []

    def test_kernel_assessment_validates_against_vendored_schema(self):
        schema = json.loads((SCHEMAS / "venture-assessment.schema.json").read_text())
        assert _structural_validate(_kernel_assessment(), schema) == []

    def test_constitutional_constants_enforced(self):
        schema = json.loads((SCHEMAS / "venture-assessment.schema.json").read_text())
        bad = _kernel_assessment(requires_human_approval=False)
        problems = _structural_validate(bad, schema)
        assert any("requires_human_approval" in p for p in problems)


class TestAdapter:
    def test_kernel_packet_to_wire_passes_dialect_validator(self):
        wire = kc.kernel_packet_to_wire(_kernel_packet())
        normalized = validate_packet_wire(wire)          # the dialect's own law
        assert normalized["id"] == wire["id"]
        assert normalized["observed_pain"] == wire["observed_pain"]

    def test_wire_to_kernel_refuses_without_enrichment(self):
        wire = {"id": str(uuid.uuid4()), "observed_pain": "x", "core_thesis": "y"}
        with pytest.raises(kc.ContractRefusal, match="enrichment"):
            kc.wire_packet_to_kernel(wire, enrichment={})

    def test_wire_to_kernel_roundtrip_preserves_semantics(self):
        wire = {"id": str(uuid.uuid4()), "observed_pain": "buyers distrust AI claims",
                "core_thesis": "governance evidence sells", "risk_flags": ["legal_risk"],
                "evidence": ["sha256:" + "b" * 64, "not-a-hash"],
                "smallest_validation_action": "one pilot"}
        enrichment = {"pain_owner": "founder", "budget_owner": "cto",
                      "governing_bottleneck": "trust", "cheapest_decisive_test": "one pilot"}
        kernel = kc.wire_packet_to_kernel(wire, enrichment=enrichment)
        schema = json.loads((SCHEMAS / "opportunity-packet.schema.json").read_text())
        assert _structural_validate(kernel, schema) == []
        assert kernel["observed_failure"] == wire["observed_pain"]
        assert kernel["key_risks"] == ["legal_risk"]
        # only hash-formatted evidence survives into kernel law
        assert kernel["evidence_refs"] == ["sha256:" + "b" * 64]

    def test_assessment_translation_preserves_constitution(self):
        wire = kc.kernel_assessment_to_wire(_kernel_assessment(verdict="go"))
        normalized = validate_assessment_wire(wire)
        assert normalized["requires_human_approval"] is True
        # an assessment that broke the constitution cannot be translated
        with pytest.raises(kc.ContractRefusal, match="constitution"):
            kc.kernel_assessment_to_wire(_kernel_assessment(execution_authority=True))
