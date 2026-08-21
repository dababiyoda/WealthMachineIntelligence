# WealthMachineOntology_DigitalAI

## Purpose
A unified ontological backbone for digital business ventures that emphasizes evidence-gated AI integration, multi-agent orchestration, and bounded human authority. The framework supports identifying, testing, and operating digital opportunities without treating model confidence or commercial success as permission to take consequential actions.

## Core Principles

### Digital-First Approach
- Systematic identification of bounded, testable digital opportunities
- Focus on scalable digital business models (SaaS, e-commerce, subscription services)
- Integration of automation where scope, loss, and rollback are explicit

### AI-Driven Synergy
- Multi-agent architecture for analysis and policy-mediated execution
- Data-driven validation of business opportunities
- Continuous learning and optimization through AI feedback loops

### Iterative Growth Strategy
- Phased approach to business development
- Risk-managed expansion through data analytics
- Automated market validation and testing

## Constitutional Control Plane

Consequential execution is now separated from analysis and recommendation.
Autonomy is represented by an expiring grant for one agent, action, resource,
context, parameter set, and budget—not by a blanket cell rank.

- `DecisionEngine` is proposal-only unless an execution gateway is explicitly
  configured.
- Unknown, ungranted, expired, out-of-scope, over-budget, and stale-context
  actions fail closed.
- Material actions require approvals from two distinct registered humans bound
  to the exact intent.
- Major incidents regress the affected capability; critical incidents pause the
  cell.
- Commercial evidence controls venture investment. Separate reliability and
  red-team evidence controls authority promotion.

Start with:

1. [`docs/AUTONOMY_ARCHITECTURE_DECISION.md`](docs/AUTONOMY_ARCHITECTURE_DECISION.md)
2. [`docs/CONSTITUTIONAL_CONTROL_LAYER.md`](docs/CONSTITUTIONAL_CONTROL_LAYER.md)
3. [`docs/PROGRESSIVE_AUTONOMY_LEVELS.md`](docs/PROGRESSIVE_AUTONOMY_LEVELS.md)
4. [`docs/VENTURE_CELL_CHARTER_TEMPLATE.md`](docs/VENTURE_CELL_CHARTER_TEMPLATE.md)
5. [`docs/IMPLEMENTATION_ROADMAP.md`](docs/IMPLEMENTATION_ROADMAP.md)
6. [`docs/SIDE_EFFECT_INVENTORY.md`](docs/SIDE_EFFECT_INVENTORY.md)

The current control plane is a tested foundation, not a production compliance
claim. Production release still requires authenticated workload identities,
durable transactional state, independently anchored evidence, credential
brokering, egress enforcement, and a verified inventory of all side-effect
paths.

## Directory Structure

### /ontology
Contains the core ontological framework defining relationships between business entities, roles, and processes.

### /roles
Detailed specifications for each specialized role in the digital business ecosystem.

### /loops
Documentation of key operational cycles for income generation and team collaboration.

### /phases
Strategic roadmap divided into three progressive phases of business development.

### /automation
Rules and logic for automated decision-making processes.

### /ai_integration
Architecture and workflows for AI agent implementation. Documentation is located in `/ai_integration/docs` and includes:
- `agent-architecture.md`: Comprehensive agent system design, communication flows, and scalability
- `agent-flow.md`: Detailed step-by-step workflow for agent operations
- `agent-lifecycle.md`: Agent initialization, state management, and maintenance
- `multi-agent-workflow.md`: Inter-agent coordination and business process automation
- `AI-tools.md`: Integration guidelines for AI capabilities

For detailed understanding of the multi-agent system:
1. Start with `agent-architecture.md` for system overview
2. Review `agent-flow.md` for operational details
3. Study `agent-lifecycle.md` for implementation specifics
4. See `multi-agent-workflow.md` for orchestration patterns

### /knowledge-graph
Query patterns and examples for exploring relationships between ventures, roles, and processes. See:
- `queries.md` for comprehensive documentation of query types and patterns
- `query-examples.yaml` for practical implementation examples
- Integration guidelines with graph databases like Neo4j, Apache Jena, and Stardog

## Getting Started
1. Review the ontology schema in `/ontology/ontology-schema.yaml`
2. Understand role definitions in the `/roles` directory
3. Study the operational loops in `/loops`
4. Follow the phase progression in `/phases`
5. Implement automation rules from `/automation`
6. Deploy AI agents according to `/ai_integration` guidelines
7. Explore knowledge graph capabilities in `/knowledge-graph`

## Docker Setup
The repository now includes a `Dockerfile` and `.env.example` to simplify local development.

1. Copy `.env.example` to `.env` and update the values for your environment.
2. Build the container image:

   ```bash
   docker build -t wealthmachine .
   ```

3. Run the application with your environment file:

   ```bash
   docker run --env-file .env -p 5000:5000 wealthmachine
   ```

The API will be available at `http://localhost:5000`.

## Local Usage Examples

### Initialize the database

1. Ensure your `.env` file contains a valid `DATABASE_URL` for PostgreSQL.
2. Run one of the initialization scripts:

   ```bash
   python setup_database.py
   ```

   or

   ```bash
   python -m src.database.init_db
   ```

### Start the API server

Run the application directly with Python:

```bash
python main.py
```

Or start it with Uvicorn:

```bash
uvicorn main:app --host 0.0.0.0 --port 5000
```

### Run the test suite

Install the package in editable mode with the optional development
dependencies and execute the unit tests with `pytest`:

```bash
pip install -e .[dev]
pytest -q
```

Use `ruff` to run the linter locally:

```bash
ruff check .
```

## DALEOBANKS Bridge (OpportunityPacket intake)

DALEOBANKS (the media/signal engine) and WealthMachineIntelligence (this
venture-evaluation engine) stay separate systems connected only by a stable
wire protocol, mirrored in both repos as `venture_protocol`:

- `POST /api/opportunities/intake` — accept an `OpportunityPacket`, run it
  through the existing `NetworkWealthEngine` venture loop (opportunity
  scoring, market, product, business model, financial, legal, marketing,
  partnerships, risk), and return a `VentureAssessment`
  (`go | defer | kill | needs_more_evidence`).
- `POST /api/ventures/evaluate` — alias for the same evaluation.
- `GET /api/ventures/{id}/assessment` — fetch a stored assessment by
  assessment id or opportunity packet id.

Assessment guardrails: every assessment carries
`requires_human_approval: true`; packets with legal risk flags are killed
and escalated to the operator; finance-flagged packets always require legal
review and stay educational (no revenue promises, no personalized advice).
The endpoints run locally with zero credentials; set
`WEALTHMACHINE_INTAKE_TOKEN` to require a shared bearer token in
deployment. On the DALEOBANKS side, point `WEALTHMACHINE_URL` at this
server to switch its bridge from mock to HTTP mode.

An assessment is evidence for a venture decision, not an execution grant. Any
resulting side effect must independently pass the Constitutional Control Plane.

## Future Development
- Persist control state and idempotency transactionally
- Broker short-lived, resource-scoped adapter credentials
- Enforce cell-specific workload identity and network egress
- Anchor Evidence Ledger hashes outside the writer trust domain
- Inventory and mediate every remaining consequential side-effect path
- Add portfolio command, independent red-team, and human authority workflows
## Continuous Integration
This project includes a basic GitHub Actions workflow located in `.github/workflows/ci.yml`. The workflow installs dependencies, runs lint checks with `ruff`, and executes the unit tests with `pytest` on every push and pull request.
