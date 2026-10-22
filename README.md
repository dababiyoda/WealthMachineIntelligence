# WealthMachineOntology_DigitalAI

## Current integration boundary

Draft development candidate, not production authorization. Canonical ASGI owner:
`src.api.main:app`; `main:app` is only a compatibility re-export.
See [Instructions.md](Instructions.md) for ownership, inspected PRs, negative
evidence, rollback and handoff. Kernel alone owns institutional authority and
external consequences. These tests establish no founder authentication or CMC.

## Purpose
A unified ontological backbone for digital business ventures that emphasizes AI integration and multi-agent orchestration. This framework provides a structured approach to identifying, launching, and scaling digital business opportunities through AI-driven processes and human expertise.

## Core Principles

### Digital-First Approach
- Systematic identification of low-risk, high-reward digital opportunities
- Focus on scalable digital business models (SaaS, e-commerce, subscription services)
- Integration of automation at every level of operations

### AI-Driven Synergy
- Multi-agent architecture for automated decision-making
- Data-driven validation of business opportunities
- Continuous learning and optimization through AI feedback loops

### Iterative Growth Strategy
- Phased approach to business development
- Risk-managed expansion through data analytics
- Automated market validation and testing

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
uvicorn src.api.main:app --host 0.0.0.0 --port 5000
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

Hardcoded guardrails: every assessment carries
`requires_human_approval: true`; packets with legal risk flags are killed
and escalated to the operator; finance-flagged packets always require legal
review and stay educational (no revenue promises, no personalized advice).
Every bridge route requires a JWT verified with explicit `JWT_SECRET_KEY`
(32+ characters), `JWT_ISSUER`, and `JWT_AUDIENCE`. POST also requires existing
HMAC body headers and `WEALTHMACHINE_SIGNING_KEY`. Missing configuration prevents
startup; flags cannot enable unsigned or demo HTTP admission.
`WEALTHMACHINE_INTAKE_TOKEN` no longer substitutes for JWT authentication.
This intentionally breaks permissive callers: DALEOBANKS migration must pass the
shared-interface gate before activation. No real credentials, login endpoint or
token issuer are provided. Synthetic fixtures are excluded from the image.
Symmetric signatures prove key possession, not isolated workload identity,
founder authentication, or permission to produce consequences.

## Future Development
- Expansion of ontology with domain-specific extensions
- Integration of advanced AI capabilities
- Development of automated validation systems
- Enhancement of multi-agent coordination
- Implementation of live knowledge graph queries
## Continuous Integration
This project includes a basic GitHub Actions workflow located in `.github/workflows/ci.yml`. The workflow installs dependencies, runs lint checks with `ruff`, and executes the unit tests with `pytest` on every push and pull request.
