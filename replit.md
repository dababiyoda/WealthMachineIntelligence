# WealthMachineOntology_DigitalAI Project Notes

## Overview

WealthMachine is a Python-based venture research, assessment, and orchestration
prototype. It combines domain models, a knowledge graph, specialized agent
roles, APIs, database models, and a progressive constitutional control plane.

## Current implementation

- Python multi-agent workflow and opportunity-assessment flow;
- ontology and knowledge-graph structures;
- rule evaluation that is proposal-only unless a policy gateway is configured;
- SQLAlchemy/PostgreSQL and FastAPI foundations;
- heuristic/demo market and risk services;
- Venture Cell charters, capability grants, policy evaluation, evidence,
  assumptions, promotion/regression, incident pause, and execution receipts; and
- automated tests and CI configuration.

## Status and limits

The repository is suitable for development and controlled-pilot preparation.
It is not production-ready by virtue of its architecture alone. Model outputs
are not calibrated evidence of business failure probability, and several direct
database/graph mutation paths remain to be mediated. Production also requires
workload identity, transactional control state, credential brokering, egress
controls, durable/anchored evidence, security review, and operational drills.

## Operating priorities

1. Follow `docs/IMPLEMENTATION_ROADMAP.md`.
2. Use `docs/SIDE_EFFECT_INVENTORY.md` as the gateway-coverage denominator.
3. Keep commercial evidence separate from control-assurance evidence.
4. Start each new capability at simulate/shadow.
5. Do not claim guaranteed returns, calibrated failure probabilities, or
   compliance without independent evidence.
