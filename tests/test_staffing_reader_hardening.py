"""Hardening of the staffing reader after independent review of #45 (2026-10-28).

Each test fails on #45's head (b2c7f234) and passes here. The answers are the Kernel's own certified staffing
answers (tests/fixtures/staffing/kernel_certified_answers.json, captured from certify_staffing at Kernel 4e970f2d),
not a hand-made shape. A report still confers no verification: these tests only make the reader refuse what the
report's own arithmetic contradicts, keep staffing data out of the demand evidence, and keep the result a
function of the report alone.
"""

import json
import sys
from pathlib import Path

import pytest

from src.services import opportunity_intake as intake
from src.services import staffing_evidence as reader
from src.services.opportunity_intake import OpportunityIntakeService
from src.services.staffing_evidence import review_staffing_evidence
from src.services.venture_protocol import validate_assessment_wire
from tests.test_opportunity_intake import fire_packet

ANSWERS = json.loads((Path(__file__).parent / "fixtures/staffing/kernel_certified_answers.json").read_text())
FULL = ANSWERS["full_8_of_8"]["answer"]
SHORT = ANSWERS["short_4_of_8"]["answer"]
LOOP15 = ANSWERS["loop15_8_of_9"]["answer"]
# The fifteen-step mission's binding, as DALEOBANKS carries it: the report sentence after the thought's own.
LABEL = "Evidence from GREG's certified staffing plan for the docks and the line: "


def report(answer, label=LABEL, **dumps):
    """The report sentence as the Kernel binds it: render "json" is json.dumps(sort_keys=True, indent=1,
    ensure_ascii=False) (greg/missions.py bound_value), so the JSON spans lines."""
    return label + json.dumps(answer, **(dumps or {"sort_keys": True, "indent": 1, "ensure_ascii": False}))


def assess(*evidence, urgency="medium", confidence=0.55, **packet):
    """The DALEOBANKS-shaped packet (fire_packet: medium urgency, finance_education_only) with these reports."""
    result = OpportunityIntakeService().evaluate_packet(
        fire_packet(urgency=urgency, confidence=confidence, evidence=["operator thought x", *evidence], **packet))
    validate_assessment_wire(result)
    return result


def errors(*evidence):
    return [r.error for r in review_staffing_evidence(list(evidence))]


# ---------------------------------------------------------------------------- the Kernel's real answers
@pytest.mark.parametrize("answer", [FULL, SHORT, LOOP15], ids=["8of8", "4of8", "8of9"])
def test_the_kernels_certified_answers_read_as_consistent(answer):
    [review] = review_staffing_evidence([report(answer)])
    assert review.error is None
    assert (review.staffed, review.demand, review.shortage) == (answer["staffed"], answer["total_demand"],
                                                              answer["shortage"])


def test_the_fifteen_step_missions_shortage_of_one_caps_the_verdict():
    result = assess(report(LOOP15))
    assert result["go_no_go"] == "needs_more_evidence"
    assert result["recommended_next_action"].startswith("Validate the reported staffing shortage of 1 units")
    assert '"Dock2": 1' in result["recommended_next_action"]


def test_the_report_is_read_whatever_the_packets_risk_flags():
    """A finance-flagged packet (the real DALEOBANKS packet) and a legal-flagged one both carry the reading;
    legal risk still kills."""
    finance = assess(report(LOOP15), risk_flags=["finance_education_only"])
    legal = assess(report(LOOP15), risk_flags=["legal_risk"])
    for result in (finance, legal):
        assert any(r.startswith("staffing evidence[1]") and "shortage=1" in r for r in result["reasons"])
        assert result["validation_plan"][0].startswith("Validate the reported staffing shortage of 1 units")
    assert legal["go_no_go"] == "kill" and finance["go_no_go"] == "needs_more_evidence"


# ---------------------------------------------------------------------------- capacity is not demand
@pytest.mark.parametrize("urgency", ["low", "medium", "high"])
@pytest.mark.parametrize("confidence", [0.3, 0.55, 0.9])
def test_a_report_never_raises_the_score_or_the_verdict(urgency, confidence):
    """Review: an 8/8 report turned defer into go at low urgency (0.638 -> 0.667) by counting as a demand signal."""
    without = assess(urgency=urgency, confidence=confidence)
    for answer in (FULL, SHORT):
        withit = assess(report(answer), urgency=urgency, confidence=confidence)
        for field in ("opportunity_score", "market_alignment", "risk_level", "cases"):
            assert withit[field] == without[field], (field, urgency, confidence)
        if without["go_no_go"] != "go":
            assert withit["go_no_go"] == without["go_no_go"] or withit["go_no_go"] == "needs_more_evidence"
            assert withit["go_no_go"] != "go"


def test_a_replayed_report_adds_no_score_and_is_named():
    once = assess(report(FULL))
    twice = assess(report(FULL), report(FULL, separators=(",", ":"), sort_keys=True))
    assert twice["opportunity_score"] == once["opportunity_score"]
    assert twice["go_no_go"] != "go"
    assert any("a replayed copy" in r for r in twice["reasons"])
    assert len(twice["validation_plan"]) == len(set(twice["validation_plan"])), "a step repeats"


def test_only_staffing_reports_is_not_demand_evidence():
    result = OpportunityIntakeService().evaluate_packet(fire_packet(evidence=[report(FULL)]))
    assert result["go_no_go"] == "needs_more_evidence"
    assert "only staffing reports attached; they describe capacity, not demand" in result["reasons"]


def test_the_demand_view_drops_exactly_the_staffing_items():
    item = "GREG staffing figures: " + json.dumps(SHORT)
    assert reader.staffing_indices([report(FULL), "a buyer asked", item]) == {0, 2}
    assert intake.demand_evidence([report(FULL), "a buyer asked twice"]) == ["a buyer asked twice"]


# ---------------------------------------------------------------------------- the report's own arithmetic
def bad(answer=None, **change):
    value = dict(answer or SHORT)
    for key, v in change.items():
        if v is KeyError:
            value.pop(key)
        else:
            value[key] = v
    return value


@pytest.mark.parametrize("value, why", [
    (bad(FULL, certified=False), "the producer does not mark this plan certified"),
    (bad(FULL, certified=KeyError), "the producer does not mark this plan certified"),
    (bad(FULL, certificate=KeyError), "the report carries no certificate object"),
    (bad(FULL, bottleneck=KeyError), "the report states no bottleneck"),
    (bad(FULL, bottleneck=LOOP15["bottleneck"]), "a report with no shortage names a bottleneck"),
    (bad(SHORT, bottleneck=None), "a report with a shortage names no bottleneck"),
    (bad(SHORT, bottleneck={**SHORT["bottleneck"], "capacity": 2}), "demand minus capacity is not the shortage"),
    (bad(SHORT, bottleneck={**SHORT["bottleneck"], "orders": ["Dock"]}), "an unfilled order lies outside"),
    (bad(SHORT, bottleneck={**SHORT["bottleneck"], "eligible_workers": ["Ana"]}),
     "served by a worker outside the bottleneck"),
    (bad(LOOP15, bottleneck={**LOOP15["bottleneck"], "demand": 8, "capacity": 7}),
     "units on the bottleneck orders do not equal its capacity"),
])
def test_a_report_its_own_fields_contradict_is_unresolved(value, why):
    [error] = errors(report(value))
    assert error and why in error, error
    result = assess(report(value))
    assert result["go_no_go"] != "go" and result["recommended_next_action"].startswith("Resolve staffing")
    assert not any("internal arithmetic agrees" in r for r in result["reasons"])


# ---------------------------------------------------------------------------- recognition on the real path
@pytest.mark.parametrize("item", [
    "Maybe a workshop could help people start " + report(SHORT),          # no terminator before the label
    "Note - " + report(SHORT),
    report(SHORT, label="evidence from GREG’s certified staffing plan: "),  # case and typographic apostrophe
])
def test_a_label_that_is_not_first_is_still_read(item):
    [review] = review_staffing_evidence([item])
    assert review.error is None and review.shortage == 4
    assert assess(item)["go_no_go"] != "go"


def test_staffing_shaped_data_under_another_label_is_unresolved_not_prose():
    item = "GREG staffing figures: " + json.dumps(SHORT)
    assert errors(item) == ["staffing-shaped data without the recognised label; not read"]
    result = assess(item)
    assert result["go_no_go"] != "go" and result["opportunity_score"] == assess()["opportunity_score"]


def test_two_reports_that_reach_wmi_as_one_sentence_are_both_read():
    """DALEOBANKS splits only after '.', '!' or '?', so two reports in one thought arrive as one item."""
    item = report(FULL) + " " + report(SHORT)
    reviews = review_staffing_evidence([item])
    assert [(r.where, r.error, r.shortage) for r in reviews] == [("0", None, 0), ("0.2", None, 4)]
    result = assess(item)
    assert result["go_no_go"] != "go"
    assert result["validation_plan"][0].startswith("Reconcile differing staffing reports")


def test_the_same_report_twice_in_one_sentence_is_a_named_replay():
    reviews = review_staffing_evidence([report(FULL) + " " + report(FULL)])
    assert reviews[0].error is None and "repeats staffing evidence[0]" in reviews[1].error


def test_a_sentence_terminator_after_the_report_is_allowed_and_other_text_is_not():
    assert errors(report(FULL) + ".") == [None]
    assert errors(report(FULL) + " and the line is fine") == [None, "text follows the staffing report"]


def test_the_same_figures_with_a_different_plan_are_two_plans():
    other = {**FULL, "assignment": [["Ana", "Dock", 3], ["Ben", "Line", 4], ["Ana", "Line", 1]]}
    result = assess(report(FULL), report(other))
    assert result["validation_plan"][0].startswith("Reconcile differing staffing reports")
    assert result["go_no_go"] != "go"
    # both plans ask for the same validation of 8/8; the plan states it once
    assert len(result["validation_plan"]) == len(set(result["validation_plan"])), result["validation_plan"]


def test_equal_totals_with_different_short_orders_differ():
    other = {**LOOP15, "unfilled": {"Dock1": 1},
             "assignment": [["Ana", "Dock1", 2], ["Ben", "Dock1", 1], ["Ben", "Dock2", 3], ["Cy", "Line", 2]]}
    assert errors(report(other)) == [None]
    result = assess(report(LOOP15), report(other))
    assert result["validation_plan"][0].startswith("Reconcile differing staffing reports")


def test_the_same_plan_with_different_short_orders_differs():
    """Two reports assign identically and agree on 8 of 9, but disagree on which order is short."""
    plan = [["Ana", "Dock", 4], ["Ben", "Line", 4]]
    dock_short = {**FULL, "total_demand": 9, "shortage": 1, "assignment": plan, "unfilled": {"Dock": 1},
                  "bottleneck": {"orders": ["Dock"], "eligible_workers": ["Ana"], "demand": 5, "capacity": 4,
                                 "why": "x"}}
    line_short = {**dock_short, "unfilled": {"Line": 1},
                  "bottleneck": {**dock_short["bottleneck"], "orders": ["Line"], "eligible_workers": ["Ben"]}}
    assert errors(report(dock_short), report(line_short)) == [None, None]
    result = assess(report(dock_short), report(line_short))
    assert result["validation_plan"][0].startswith("Reconcile differing staffing reports")


def test_equal_staffed_with_a_different_shortage_differs():
    result = assess(report(FULL), report({**SHORT, "staffed": 8, "total_demand": 12,
                                          "assignment": [["Ana", "Dock", 4], ["Ben", "Line", 4]],
                                          "unfilled": {"Dock": 2, "Line": 2},
                                          "bottleneck": {**SHORT["bottleneck"], "demand": 12, "capacity": 8}}))
    assert result["validation_plan"][0].startswith("Reconcile differing staffing reports")


# ---------------------------------------------------------------------------- each guard on its own
def test_a_duplicate_key_is_ambiguous_even_when_its_last_value_agrees():
    text = report(FULL)
    item = text.replace('"shortage": 0', '"shortage": 4,\n "shortage": 0', 1)
    assert errors(item) == ["duplicate JSON keys make the staffing report ambiguous"]


def test_a_zero_unit_assignment_row_is_refused():
    value = {**FULL, "assignment": [*FULL["assignment"], ["Cy", "Line", 0]]}
    assert errors(report(value)) == ["assignment units must be a bounded positive integer"]


def test_quantities_beyond_the_bound_are_refused_even_when_consistent():
    big = 10**12 + 4
    value = {**FULL, "staffed": 2 * big, "total_demand": 2 * big,
             "assignment": [["Ana", "Dock", big], ["Ben", "Line", big]]}
    assert errors(report(value)) == ["staffed must be a bounded nonnegative integer"]


def test_prose_that_names_the_label_without_a_report_is_unresolved_not_dropped():
    """A deliberate choice (review dissent recorded): the label anywhere is read, so a sentence that names GREG's
    staffing plan without carrying it asks for the plan instead of passing as demand prose."""
    item = "Note: Evidence from GREG's certified staffing plan is pending."
    assert errors(item) == ["staffing report has no JSON body"]
    assert assess(item)["go_no_go"] != "go"


# ---------------------------------------------------------------------------- priority and determinism
def test_an_unreadable_report_ranks_before_a_shortage_whatever_the_wire_order():
    for evidence in ([report(SHORT), LABEL + '{"staffed":'], [LABEL + '{"staffed":', report(SHORT)]):
        assert assess(*evidence)["recommended_next_action"].startswith("Resolve staffing evidence")


def deep(depth):
    return {**FULL, "certificate": {"kind": json.loads("[" * depth + "]" * depth)}}


@pytest.mark.parametrize("make, message", [
    (lambda: deep(7), "staffing JSON exceeds the supported nesting depth"),
    (lambda: deep(900), "staffing JSON exceeds the supported nesting depth"),
    (lambda: {**FULL, "certificate": {"n": int("9" * 5000)}},
     "a number in the staffing report exceeds the supported size"),
], ids=["depth-9", "depth-902", "5000-digits"])
def test_classification_depends_on_the_report_not_the_interpreter(make, message):
    old = sys.get_int_max_str_digits()
    sys.set_int_max_str_digits(0)          # build the report with no digit limit; reading it must not need one
    try:
        item = report(make(), separators=(",", ":"))      # compact, so the size bound does not answer first
    finally:
        sys.set_int_max_str_digits(old)

    def from_depth(n):
        return errors(item) if n == 0 else from_depth(n - 1)
    assert errors(item) == from_depth(300) == [message]
