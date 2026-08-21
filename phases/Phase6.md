# Phase 6 — First AI Influencer Company + Rabbit Hole Engine

Status: **executable and verified (2026-07-20)** — `src/services/influencer_company.py`,
`src/services/rabbit_hole.py`, `tests/test_influencer_company.py`,
`tests/test_rabbit_hole.py` (18 tests green).

## The company

An AI influencer is a media organ, not a person. It operates under a charter,
discloses its nature on every artifact, stays inside declared topic bounds, and
never publishes autonomously — every artifact leaves as a publish-ready package
with `requires_human_approval: True` and `execution_authority: False`, routed
to the kernel Consequence Gate by the caller.

Structural compliance (not tonal):

- AI disclosure mandatory on every artifact; missing disclosure refuses the draft
- Finance topics hardened to educational-only (no income promises, no
  personalized advice) — mirrors the `finance_education_only` wire flag
- Legal/regulated topics force escalation, never publication
- Dark patterns refuse the draft (artificial scarcity, false urgency, hidden
  cost, guaranteed income, risk-free claims, "act now or miss out", "secret method")
- Every persona carries kill criteria (engagement-quality floor, complaint-rate
  ceiling, off-brand incident budget); breaches pause the persona immediately

## The Rabbit Hole Engine

A rabbit hole is a content sequence that rewards curiosity with depth. The
engine's job is progression; its law is ethics:

- every node declares what it is (no disguised ads)
- dark-pattern nodes never enter the graph
- depth is bounded per session (ceiling 5); past it, the only honest
  recommendation is the exit ramp
- every recommendation carries an exit ramp — leaving is one step, never punished
- progression is earned: deeper nodes unlock only through actual consumption

The engine never optimizes for time-on-site. It optimizes for value delivered
per step, with depth as the proof of value.

## Integration

The influencer company is a signal source: its audience learnings flow into the
existing intake bridge (`POST /api/opportunities/intake`) as OpportunityPackets
— never around the VentureAssessment guardrails. Publication flows the other
way: packages route to the kernel Consequence Gate for authorization.
