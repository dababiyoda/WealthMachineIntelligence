# WealthMachineIntelligence – Enhanced Edition

This fork takes the original **WealthMachineIntelligence** repository and
transforms it into production‑grade, enterprise‑ready infrastructure.  It
introduces high‑performance caching, vector search, strong identity
management, supply‑chain security, and a robust CI/CD pipeline.  The goal
is to create unkillable replacement infrastructure that can handle AI‑driven
digital venture orchestration at scale.

## Key enhancements

- **Caching with Valkey/Redis** – A dedicated cache layer dramatically
  reduces latency for frequent queries and session data.  The cache is
  pluggable via environment variables and uses a connection pool.
- **Vector database integration** – We include an abstraction over
  [Milvus](https://milvus.io) that handles collection creation, embedding
  insertion and similarity search.  This enables retrieval‑augmented
  generation (RAG) and semantic search for venture data.
- **Enterprise identity management** – Authentication and authorisation are
  delegated to an external provider such as Keycloak or Ory Kratos.  The
  application verifies JWTs issued by the identity provider and extracts
  user information via OpenID Connect.
- **Observability** – Prometheus metrics and health/readiness endpoints
  expose internal state.  Optional OpenTelemetry tracing can be enabled
  via environment variables.
- **Secure supply chain** – Pre‑commit hooks enforce style and security
  checks.  Continuous integration scans the code and container images
  using Ruff, Bandit and Trivy.  Artifacts are signed with Sigstore’s
  cosign.
- **Modular micro‑services** – Code has been refactored into clear
  modules (`cache.py`, `vector_db.py`, `auth/`).  Future services can be
  split out without breaking contracts.

## Getting started

### Prerequisites

* Docker and Docker Compose
* Python 3.10+

### Installation

1. Clone the repository and change into the project directory:

   ```bash
   git clone https://github.com/your-org/WealthMachineIntelligence.git
   cd WealthMachineIntelligence
   ```

2. Copy `.env.example` to `.env` and set values for database credentials,
   cache host, vector store host and identity provider endpoints.

3. Start the stack using Docker Compose:

   ```bash
   docker compose up -d
   ```

4. Run the API:

   ```bash
   docker compose exec api python -m src.api.main
   ```

5. Visit `http://localhost:8000/docs` for the interactive Swagger UI.

### Development workflow

We use **pre‑commit** to run formatting (Black), linting (Ruff) and
security checks (Bandit).  Install the hooks locally:

```bash
pip install pre‑commit
pre‑commit install
```

On every commit the hooks will run; to manually trigger all hooks:

```bash
pre‑commit run --all-files
```

### Continuous integration

GitHub Actions is configured under `.github/workflows/ci.yml`.  The
workflow installs dependencies, runs tests, executes Ruff and Bandit,
performs container scanning with Trivy, runs OpenSSF Scorecard checks and
builds a signed Docker image.

## Directory layout

```
WealthMachineIntelligence/
├── docker-compose.yml     # Compose stack with database, cache, vector DB and IAM
├── pyproject.toml         # Configuration for Ruff, Black and dependencies
├── .pre‑commit‑config.yaml
├── .github/workflows/ci.yml
└── src/
    ├── api/
    │   ├── main.py        # FastAPI application with caching, vector search and identity integration
    │   └── routes/
    │       └── ventures.py# Example API routes
    ├── auth/
    │   └── keycloak.py    # Functions to verify tokens against Keycloak/Ory
    ├── cache.py           # Redis/Valkey connection pool and helper functions
    ├── config.py          # Application settings loaded from environment
    ├── database/
    │   └── connection.py  # SQLAlchemy database connection (unchanged from upstream)
    └── vector_db.py       # Milvus vector store abstraction
```
