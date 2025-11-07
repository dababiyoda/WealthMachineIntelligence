"""
Enterprise FastAPI application for WealthMachine
Production-ready API with authentication, monitoring, and comprehensive endpoints
"""
from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
import time
from src.logging_config import configure_logging, logger
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client import start_http_server
import os
from contextlib import asynccontextmanager

from ..database.connection import db
from .routes import ventures, agents, analytics, health
from .auth import verify_token
from .middleware import SecurityHeadersMiddleware, LoggingMiddleware

# Configure structured logging
configure_logging()

# Prometheus metrics
REQUEST_COUNT = Counter('wealthmachine_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('wealthmachine_request_duration_seconds', 'Request duration')

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting WealthMachine Enterprise API")
    
    # Initialize database
    try:
        db.create_tables()
        logger.info("Database tables initialized")
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise
    
    # Start Prometheus metrics server
    metrics_port = int(os.getenv('METRICS_PORT', '9090'))
    start_http_server(metrics_port)
    logger.info("Prometheus metrics server started", port=metrics_port)
    
    yield
    
    # Shutdown
    logger.info("Shutting down WealthMachine Enterprise API")

app = FastAPI(
    title="WealthMachine Enterprise API",
    description="AI-driven digital business opportunity identification and scaling system",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if os.getenv("ENVIRONMENT") != "production" else None,
    redoc_url="/redoc" if os.getenv("ENVIRONMENT") != "production" else None
)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["*"] if os.getenv("ENVIRONMENT") != "production" else ["localhost", "*.replit.app"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if os.getenv("ENVIRONMENT") != "production" else ["https://*.replit.app"],
    allow_credentials=True,
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

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "name": "WealthMachine Enterprise API",
        "version": "1.0.0",
        "description": "AI-driven digital business opportunity identification and scaling system",
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