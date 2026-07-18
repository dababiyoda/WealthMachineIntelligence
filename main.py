"""Legacy-compatible local server for the WealthMachine prototype."""
import sys
import os
from pathlib import Path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from src.logging_config import configure_logging
from datetime import datetime

from src.database.connection import db
try:
    from src.api.auth import (
        authenticate_user,
        create_access_token,
        validate_auth_configuration,
        verify_token,
    )
    from src.services.ai_agents import DecisionOrchestrator
except ImportError as e:
    print(f"Import warning: {e}")
    # Fail-closed fallbacks for incomplete local installations.
    def verify_token(token):
        return None
    
    def authenticate_user(username, password):
        return None
    
    def create_access_token(data):
        raise RuntimeError("authentication module unavailable")

    def validate_auth_configuration():
        raise RuntimeError("authentication module unavailable")
    
    class DecisionOrchestrator:
        async def evaluate_venture_opportunity(self, venture_id):
            return {"status": "evaluation_completed", "venture_id": venture_id}

# Configure logging
configure_logging()

IS_PRODUCTION = os.getenv("ENVIRONMENT", "development").lower() == "production"
if IS_PRODUCTION:
    validate_auth_configuration()

STATIC_ROOT = (Path(__file__).resolve().parent / "static").resolve()

app = FastAPI(
    title="WealthMachine Controlled-Pilot API",
    description="Evidence-gated venture analysis prototype",
    version="1.0.0"
)

# Static files will be served by our custom handler

# CORS middleware
allowed_origins = (
    [
        origin.strip()
        for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    ]
    if IS_PRODUCTION
    else ["*"]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Authentication
security = HTTPBearer()

def get_current_user(credentials=Depends(security)):
    """Verify JWT token"""
    token = credentials.credentials
    demo_enabled = (
        os.getenv("ENVIRONMENT", "development").lower() != "production"
        and os.getenv("ALLOW_DEMO_AUTH", "false").lower() == "true"
    )
    if demo_enabled and token in ["demo_token", "demo"]:
        return {"user_id": "demo", "username": "demo"}
    
    user = verify_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    return user

# Health check
@app.get("/health")
async def health_check():
    """System health check"""
    db_healthy = db.health_check()
    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "timestamp": datetime.now().isoformat(),
        "database": {"healthy": db_healthy},
        "version": "1.0.0"
    }

# Authentication endpoint
@app.post("/auth/login")
async def login(request: Request):
    """Login endpoint"""
    form = await request.form()
    username = form.get("username", "")
    password = form.get("password", "")
    
    user = authenticate_user(username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    token = create_access_token({"sub": user["user_id"], "username": user["username"]})
    return {"access_token": token, "token_type": "bearer", "user": user}

# Include API routes (simplified versions without complex dependencies)
@app.get("/api/v1/ventures")
async def list_ventures_simple(current_user=Depends(get_current_user)):
    """List ventures (simplified)"""
    try:
        with db.get_session() as session:
            from src.database.models import DigitalVenture
            ventures = session.query(DigitalVenture).limit(10).all()
            return {
                "ventures": [
                    {
                        "id": v.id,
                        "name": v.name,
                        "type": v.venture_type.value,
                        "status": v.status.value,
                        "revenue": v.monthly_revenue,
                        "risk_score": v.risk_score,
                        "failure_probability": v.failure_probability
                    } for v in ventures
                ],
                "count": len(ventures)
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/agents")
async def list_agents_simple(current_user=Depends(get_current_user)):
    """List AI agents (simplified)"""
    try:
        with db.get_session() as session:
            from src.database.models import AIAgent
            agents = session.query(AIAgent).all()
            return {
                "agents": [
                    {
                        "id": a.id,
                        "type": a.agent_type.value,
                        "name": a.name,
                        "active": a.is_active,
                        "accuracy": a.accuracy
                    } for a in agents
                ]
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/dashboard")
async def dashboard_simple(current_user=Depends(get_current_user)):
    """Dashboard metrics (simplified)"""
    try:
        with db.get_session() as session:
            from src.database.models import DigitalVenture
            from sqlalchemy import func
            
            total_ventures = session.query(DigitalVenture).count()
            total_revenue = session.query(func.sum(DigitalVenture.monthly_revenue)).scalar() or 0
            
            lowest_heuristic_bucket = session.query(DigitalVenture).filter(
                DigitalVenture.failure_probability <= 0.0001
            ).count()

            heuristic_bucket_rate = (
                lowest_heuristic_bucket / total_ventures * 100
                if total_ventures > 0
                else 0
            )
            
            return {
                "total_ventures": total_ventures,
                "total_monthly_revenue": total_revenue,
                "ventures_in_lowest_heuristic_bucket": lowest_heuristic_bucket,
                "lowest_heuristic_bucket_percentage": heuristic_bucket_rate,
                "model_validation_status": "UNVALIDATED",
                "metric_warning": (
                    "Legacy failure_probability values are uncalibrated heuristic "
                    "scores, not observed success or failure rates."
                ),
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/ventures/{venture_id}/evaluate")
async def evaluate_venture(venture_id: str, current_user=Depends(get_current_user)):
    """Evaluate venture using AI agents"""
    try:
        orchestrator = DecisionOrchestrator()
        evaluation = await orchestrator.evaluate_venture_opportunity(venture_id)
        return evaluation
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    """Serve the main UI"""
    from fastapi.responses import FileResponse
    return FileResponse(STATIC_ROOT / "index.html")

@app.get("/static/{file_path:path}")
async def serve_static(file_path: str):
    """Serve static files"""
    from fastapi.responses import FileResponse
    file_location = (STATIC_ROOT / file_path).resolve()
    if STATIC_ROOT in file_location.parents and file_location.is_file():
        return FileResponse(file_location)
    raise HTTPException(status_code=404, detail="File not found")

@app.get("/api")
async def api_root():
    """API root"""
    return {
        "name": "WealthMachine API",
        "version": "1.0.0",
        "description": "AI-driven digital business opportunity identification system",
        "operating_mode": "controlled-pilot preparation",
        "model_warning": "Heuristic scores are uncalibrated and recommendation-only.",
        "endpoints": {
            "health": "/health",
            "login": "/auth/login",
            "ventures": "/api/v1/ventures",
            "agents": "/api/v1/agents", 
            "dashboard": "/api/v1/analytics/dashboard"
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5000,
        reload=False,
        log_level="info"
    )
