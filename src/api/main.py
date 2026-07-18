"""FastAPI prototype for doctrine-governed WealthMachine workflows."""
from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from src.logging_config import configure_logging, logger
from prometheus_client import Counter, Histogram, generate_latest
from prometheus_client import start_http_server
import os
from contextlib import asynccontextmanager

from ..database.connection import db
from .routes import agents, analytics, control, health, opportunities, ventures
from .auth import validate_auth_configuration, verify_token
from .control_runtime import initialize_production_control_plane
from .middleware import SecurityHeadersMiddleware, LoggingMiddleware


def _configured_trusted_hosts(environment: str) -> list[str]:
    hosts = [
        host.strip()
        for host in os.getenv("ALLOWED_HOSTS", "").split(",")
        if host.strip()
    ]
    if environment == "production":
        if not hosts:
            raise RuntimeError(
                "ALLOWED_HOSTS must name at least one explicit host in production"
            )
        if "*" in hosts:
            raise RuntimeError(
                "ALLOWED_HOSTS cannot contain '*' in production"
            )
        return hosts
    return hosts or ["*"]

# Configure structured logging
configure_logging()

# Prometheus metrics
REQUEST_COUNT = Counter('wealthmachine_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('wealthmachine_request_duration_seconds', 'Request duration')

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting WealthMachine controlled-pilot API")
    validate_auth_configuration()
    initialize_production_control_plane()

    environment = os.getenv("ENVIRONMENT", "development").lower()
    auto_create_schema = os.getenv("AUTO_CREATE_SCHEMA", "false").lower() == "true"
    if environment == "production" and auto_create_schema:
        raise RuntimeError("AUTO_CREATE_SCHEMA must be disabled in production")
    if auto_create_schema:
        try:
            db.create_tables()
            logger.info("Development database tables initialized")
        except Exception as e:
            logger.error("Failed to initialize development database", error=str(e))
            raise
    else:
        logger.info("Automatic schema creation disabled; migrations are operator-managed")
    
    # Start Prometheus metrics server
    metrics_port = int(os.getenv('METRICS_PORT', '9090'))
    start_http_server(metrics_port)
    logger.info("Prometheus metrics server started", port=metrics_port)
    
    yield
    
    # Shutdown
    logger.info("Shutting down WealthMachine Enterprise API")

app = FastAPI(
    title="WealthMachine Controlled-Pilot API",
    description="Evidence-gated venture analysis and policy-mediated execution prototype",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if os.getenv("ENVIRONMENT") != "production" else None,
    redoc_url="/redoc" if os.getenv("ENVIRONMENT") != "production" else None
)

# Security middleware
environment = os.getenv("ENVIRONMENT", "development").lower()
is_production = environment == "production"
allowed_hosts = _configured_trusted_hosts(environment)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=allowed_hosts,
)

allowed_origins = (
    [
        origin.strip()
        for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    ]
    if is_production
    else ["*"]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Custom middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(LoggingMiddleware)

# Authentication
security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token and return user info"""
    token = credentials.credentials
    user = verify_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

# Global error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions"""
    logger.error("Unhandled exception", 
                error=str(exc), 
                path=request.url.path,
                method=request.method)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred",
            "request_id": getattr(request.state, 'request_id', 'unknown')
        }
    )

# Health check endpoint (no auth required)
@app.get("/health")
async def health_check():
    """System health check"""
    db_healthy = db.health_check()
    return {"status": "ok" if db_healthy else "degraded"}

# Metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest()

# Include API routes
app.include_router(ventures.router, prefix="/api/v1/ventures", tags=["ventures"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
app.include_router(health.router, prefix="/api/v1/system", tags=["system"])
app.include_router(control.router, prefix="/api/v1/control", tags=["control"])
# DALEOBANKS bridge: OpportunityPacket in, VentureAssessment back.
app.include_router(opportunities.router, prefix="/api", tags=["opportunities"])

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "name": "WealthMachine Controlled-Pilot API",
        "version": "1.0.0",
        "description": "Evidence-gated venture analysis and policy-mediated execution prototype",
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=5000,
        reload=os.getenv("ENVIRONMENT") != "production",
        access_log=True,
        log_config={
            "version": 1,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "level": "INFO",
                "handlers": ["default"],
            },
        }
    )
