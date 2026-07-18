"""Local UAT simulation API.

This entrypoint is an architectural skeleton, not a production or autonomous
venture operator. Its current limits are exposed through the capability API.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from src.logging_config import configure_logging
from datetime import datetime

from src.core.epistemic import current_capability_record, evidence_disclosure
from src.database.connection import db
from src.api.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
)

# Configure logging
configure_logging()

app = FastAPI(
    title="UAT Simulation API",
    description="Evidence-labeled architecture skeleton for governed venture experiments",
    version="0.1.0"
)

# Static files will be served by our custom handler

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Health check
@app.get("/health")
async def health_check():
    """System health check"""
    db_healthy = db.health_check()
    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "timestamp": datetime.now().isoformat(),
        "database": {"healthy": db_healthy},
        "version": "0.1.0",
        "operating_mode": current_capability_record()["operating_mode"]
    }

# Authentication endpoint
@app.post("/auth/login")
async def login(request: Request):
    """Login endpoint"""
    form = await request.form()
    username = form.get("username", "demo")
    password = form.get("password", "demo")
    
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
                        "heuristic_risk_index": v.risk_score,
                        "evidence_status": "unverified_local_record"
                    } for v in ventures
                ],
                "count": len(ventures),
                "evidence": evidence_disclosure("local DigitalVenture records; records may be simulation fixtures")
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
                        "reported_accuracy": a.accuracy,
                        "evidence_status": "unverified_seed_or_operator_input"
                    } for a in agents
                ],
                "evidence": evidence_disclosure("local AIAgent records; performance fields are not independently evaluated")
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
            
            below_review_threshold = session.query(DigitalVenture).filter(
                DigitalVenture.risk_score <= 0.2
            ).count()
            
            modeled_coverage = (
                below_review_threshold / total_ventures * 100
                if total_ventures > 0
                else 0
            )
            
            return {
                "total_ventures": total_ventures,
                "total_monthly_revenue": total_revenue,
                "modeled_risk_threshold_count": below_review_threshold,
                "modeled_risk_threshold_coverage": modeled_coverage,
                "threshold": {
                    "metric": "uncalibrated_heuristic_risk_index",
                    "operator": "less_than_or_equal",
                    "value": 0.2,
                    "decision_authority": "none"
                },
                "evidence": evidence_disclosure("local DigitalVenture records; values may be simulation fixtures")
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/ventures/{venture_id}/evaluate")
async def evaluate_venture(venture_id: str, current_user=Depends(get_current_user)):
    """Evaluate venture using AI agents"""
    try:
        from src.services.ai_agents import DecisionOrchestrator

        orchestrator = DecisionOrchestrator()
        evaluation = await orchestrator.evaluate_venture_opportunity(venture_id)
        evaluation["evidence"] = evidence_disclosure("simulation DecisionOrchestrator")
        return evaluation
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    """Serve the main UI"""
    from fastapi.responses import FileResponse
    return FileResponse('static/index.html')

@app.get("/static/{file_path:path}")
async def serve_static(file_path: str):
    """Serve static files"""
    from fastapi.responses import FileResponse
    import os
    file_location = f"static/{file_path}"
    if os.path.exists(file_location):
        return FileResponse(file_location)
    raise HTTPException(status_code=404, detail="File not found")

@app.get("/api")
async def api_root():
    """API root"""
    return {
        "name": "UAT Simulation API",
        "version": "0.1.0",
        "description": "Evidence-labeled architecture skeleton for governed venture experiments",
        "capability": current_capability_record(),
        "endpoints": {
            "health": "/health",
            "login": "/auth/login",
            "ventures": "/api/v1/ventures",
            "agents": "/api/v1/agents", 
            "dashboard": "/api/v1/analytics/dashboard"
        }
    }


@app.get("/api/v1/system/capabilities")
async def capabilities():
    """Return the versioned, fail-closed current-capability record."""

    return current_capability_record()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5000,
        reload=False,
        log_level="info"
    )
