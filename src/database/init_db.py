"""
Database initialization script.

Seed records are explicit simulation fixtures. They are not production
outcomes, audited financials, model evaluations, or compliance evidence.
"""
from datetime import datetime, timezone

from .connection import db, get_db
from .models import (
    Base, AIAgent, DigitalVenture, AgentType, VentureType, VentureStatus, RiskLevel
)

def create_all_tables():
    """Create all database tables"""
    try:
        Base.metadata.create_all(bind=db.engine)
        print("✅ Database tables created successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to create tables: {e}")
        return False

def populate_initial_data():
    """Populate database with initial AI agents and sample data"""
    try:
        with get_db() as session:
            # Check if agents already exist
            existing_agents = session.query(AIAgent).count()
            if existing_agents > 0:
                print("✅ Initial data already exists")
                return True
            
            # Create simulation component fixtures. Performance remains zero
            # until linked evaluation evidence exists.
            agents = [
                AIAgent(
                    agent_type=AgentType.MARKET_INTELLIGENCE,
                    name="Market Intelligence Agent",
                    version="simulation-1.0.0",
                    model_type="Unvalidated simulation placeholder",
                    is_active=True,
                    accuracy=0.0,
                    success_rate=0.0,
                    decisions_made=0,
                    last_activity=datetime.now(timezone.utc)
                ),
                AIAgent(
                    agent_type=AgentType.RISK_ASSESSMENT,
                    name="Risk Assessment Agent", 
                    version="simulation-1.0.0",
                    model_type="Unvalidated simulation placeholder",
                    is_active=True,
                    accuracy=0.0,
                    success_rate=0.0,
                    decisions_made=0,
                    last_activity=datetime.now(timezone.utc)
                ),
                AIAgent(
                    agent_type=AgentType.LEGAL_COMPLIANCE,
                    name="Legal Compliance Agent",
                    version="simulation-1.0.0",
                    model_type="Unvalidated simulation placeholder",
                    is_active=True,
                    accuracy=0.0,
                    success_rate=0.0,
                    decisions_made=0,
                    last_activity=datetime.now(timezone.utc)
                ),
                AIAgent(
                    agent_type=AgentType.FINANCIAL_STRATEGIST,
                    name="Financial Strategy Agent",
                    version="simulation-1.0.0",
                    model_type="Unvalidated simulation placeholder",
                    is_active=True,
                    accuracy=0.0,
                    success_rate=0.0,
                    decisions_made=0,
                    last_activity=datetime.now(timezone.utc)
                )
            ]
            
            for agent in agents:
                session.add(agent)
            
            # Create unmistakably labeled simulation venture fixtures.
            sample_ventures = [
                DigitalVenture(
                    name="[SIMULATION FIXTURE] SaaS Analytics Platform",
                    description="Synthetic record for local interface and workflow tests",
                    venture_type=VentureType.SAAS,
                    status=VentureStatus.MVP,
                    initial_investment=50000.0,
                    monthly_revenue=8500.0,
                    monthly_expenses=3200.0,
                    profit_margin=0.62,
                    risk_level=RiskLevel.LOW,
                    risk_score=0.15,
                    heuristic_risk_index=0.15,
                    customer_count=127,
                    churn_rate=0.03,
                    growth_rate=0.18,
                    ai_enabled=True,
                    automation_level=0.75
                ),
                DigitalVenture(
                    name="[SIMULATION FIXTURE] B2B Tools Marketplace",
                    description="Synthetic record for local interface and workflow tests",
                    venture_type=VentureType.ECOMMERCE,
                    status=VentureStatus.SCALING,
                    initial_investment=75000.0,
                    monthly_revenue=15200.0,
                    monthly_expenses=6800.0,
                    profit_margin=0.55,
                    risk_level=RiskLevel.ULTRA_LOW,
                    risk_score=0.08,
                    heuristic_risk_index=0.08,
                    customer_count=89,
                    churn_rate=0.02,
                    growth_rate=0.22,
                    ai_enabled=True,
                    automation_level=0.85
                ),
                DigitalVenture(
                    name="[SIMULATION FIXTURE] Content Platform",
                    description="Synthetic record for local interface and workflow tests",
                    venture_type=VentureType.CONTENT_PLATFORM,
                    status=VentureStatus.VALIDATION,
                    initial_investment=30000.0,
                    monthly_revenue=2100.0,
                    monthly_expenses=1800.0,
                    profit_margin=0.14,
                    risk_level=RiskLevel.MODERATE,
                    risk_score=0.35,
                    heuristic_risk_index=0.35,
                    customer_count=45,
                    churn_rate=0.08,
                    growth_rate=0.12,
                    ai_enabled=True,
                    automation_level=0.60
                )
            ]
            
            for venture in sample_ventures:
                session.add(venture)
            
            session.commit()
            print("✅ Initial data populated successfully")
            return True
            
    except Exception as e:
        print(f"❌ Failed to populate initial data: {e}")
        return False

def init_database():
    """Complete database initialization"""
    print("🚀 Initializing WealthMachine Enterprise Database...")
    
    # Create tables
    if not create_all_tables():
        return False
    
    # Populate initial data
    if not populate_initial_data():
        return False
    
    print("✅ Database initialization completed successfully!")
    return True

if __name__ == "__main__":
    init_database()
