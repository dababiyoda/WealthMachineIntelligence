"""Canonical web application for the UAT governed preview release candidate."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from src.api.auth import authenticate_user, configured_users, create_access_token
from src.api.middleware import LoggingMiddleware, RateLimitMiddleware, SecurityHeadersMiddleware
from src.api.routes import agents, analytics, governance, health, opportunities, ventures
from src.core.epistemic import current_capability_record
from src.database.connection import db
from src.governance.bootstrap import bootstrap_preview
from src.governance.service import GovernanceError, GovernanceService
from src.logging_config import configure_logging, logger


ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "static"
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
VERSION = "0.2.0-rc1"

configure_logging()


def bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def csv_env(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name)
    return [item.strip() for item in value.split(",") if item.strip()] if value else default


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Starting UAT governed preview", version=VERSION, environment=ENVIRONMENT)
    db.create_tables()
    bootstrap_enabled = bool_env("UAT_BOOTSTRAP_PREVIEW", ENVIRONMENT != "production")
    if bootstrap_enabled:
        with db.get_session() as session:
            bootstrap_preview(session, users=configured_users())
    yield
    logger.info("Stopping UAT governed preview", version=VERSION)


docs_enabled = bool_env("UAT_ENABLE_DOCS", ENVIRONMENT != "production")
app = FastAPI(
    title="UAT Governed Preview",
    description=(
        "Evidence-labeled venture simulation with a deterministic AG1/AG2 "
        "control-plane candidate and no autonomous external authority"
    ),
    version=VERSION,
    lifespan=lifespan,
    docs_url="/docs" if docs_enabled else None,
    redoc_url="/redoc" if docs_enabled else None,
)

trusted_hosts = csv_env(
    "UAT_TRUSTED_HOSTS",
    ["localhost", "127.0.0.1", "testserver"]
    if ENVIRONMENT != "production"
    else ["localhost"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)

allowed_origins = csv_env(
    "UAT_ALLOWED_ORIGINS", ["*"] if ENVIRONMENT != "production" else []
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials="*" not in allowed_origins,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(
    RateLimitMiddleware,
    calls=int(os.getenv("UAT_RATE_LIMIT_CALLS", "180")),
    period=int(os.getenv("UAT_RATE_LIMIT_PERIOD_SECONDS", "60")),
)


@app.exception_handler(GovernanceError)
async def governance_error_handler(_request: Request, exc: GovernanceError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "Unhandled request exception",
        path=request.url.path,
        method=request.method,
        request_id=getattr(request.state, "request_id", "unknown"),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "request_id": getattr(request.state, "request_id", "unknown"),
        },
    )


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok" if db.health_check() else "degraded"}


@app.get("/health/live")
def liveness() -> dict[str, str]:
    return {"status": "live", "version": VERSION}


@app.get("/health/ready")
def readiness() -> JSONResponse:
    database_ok = db.health_check()
    audit_ok = False
    if database_ok:
        with db.get_session() as session:
            audit_ok = GovernanceService(session).verify_audit_chain()
    ready = database_ok and audit_ok
    return JSONResponse(
        status_code=200 if ready else 503,
        content={
            "status": "ready" if ready else "not_ready",
            "database": database_ok,
            "audit_chain": audit_ok,
            "external_autonomy": "none",
        },
    )


@app.get("/metrics")
def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/auth/login")
async def login(request: Request) -> dict:
    form = await request.form()
    username = str(form.get("username", ""))
    password = str(form.get("password", ""))
    user = authenticate_user(username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    token = create_access_token(
        {
            "sub": user["user_id"],
            "username": user["username"],
            "role": user["role"],
            "permissions": user["permissions"],
        }
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user,
        "expires_in_seconds": int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")) * 60,
    }


app.include_router(ventures.router, prefix="/api/v1/ventures", tags=["ventures"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
app.include_router(health.router, prefix="/api/v1/system", tags=["system"])
app.include_router(governance.router, prefix="/api/v1/governance", tags=["governance"])
app.include_router(opportunities.router, prefix="/api", tags=["opportunities"])


@app.get("/api")
def api_root() -> dict:
    return {
        "name": "UAT Governed Preview",
        "version": VERSION,
        "capability": current_capability_record(),
        "published_at": datetime.now(timezone.utc).isoformat(),
        "endpoints": {
            "capabilities": "/api/v1/system/capabilities",
            "governance_status": "/api/v1/governance/status",
            "health": "/health",
            "readiness": "/health/ready",
        },
    }


@app.get("/api/v1/system/capabilities")
def capabilities() -> dict:
    return current_capability_record()


app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/", include_in_schema=False)
def operator_console() -> FileResponse:
    return FileResponse(STATIC / "index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.api.main:app", host="0.0.0.0", port=5000, reload=False)
