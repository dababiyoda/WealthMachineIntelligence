# WealthMachineOntology_DigitalAI

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


## Future Development
- Expansion of ontology with domain-specific extensions
- Integration of advanced AI capabilities
- Development of automated validation systems
- Enhancement of multi-agent coordination
- Implementation of live knowledge graph queries
## Continuous Integration
This project includes a basic GitHub Actions workflow located in `.github/workflows/ci.yml`. The workflow installs dependencies, runs lint checks with `ruff`, and executes the unit tests with `pytest` on every push and pull request.
