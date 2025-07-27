"""
Database initialization script
Creates tables and populates with initial data for WealthMachine Enterprise
"""
import asyncio
from datetime import datetime
from sqlalchemy.orm import Session

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
            
            # Create AI agents
            agents = [
                AIAgent(
                    agent_type=AgentType.MARKET_INTELLIGENCE,
                    name="Market Intelligence Agent",
                    version="1.0.0",
                    model_type="LSTM + Sentiment Analysis",
                    is_active=True,
                    accuracy=0.85,
                    success_rate=0.82,
                    decisions_made=0,
                    last_activity=datetime.utcnow()
                ),
                AIAgent(
                    agent_type=AgentType.RISK_ASSESSMENT,
                    name="Risk Assessment Agent", 
                    version="1.0.0",
                    model_type="Hybrid LSTM + Random Forest",
                    is_active=True,
                    accuracy=0.92,
                    success_rate=0.89,
                    decisions_made=0,
                    last_activity=datetime.utcnow()
                ),
                AIAgent(
                    agent_type=AgentType.LEGAL_COMPLIANCE,
                    name="Legal Compliance Agent",
                    version="1.0.0", 
                    model_type="BERT + Regulatory NLP",
                    is_active=True,
                    accuracy=0.88,
                    success_rate=0.91,
                    decisions_made=0,
                    last_activity=datetime.utcnow()
                ),
                AIAgent(
                    agent_type=AgentType.FINANCIAL_STRATEGIST,
                    name="Financial Strategy Agent",
                    version="1.0.0",
                    model_type="Monte Carlo + Portfolio Optimization", 
                    is_active=True,
                    accuracy=0.90,
                    success_rate=0.87,
                    decisions_made=0,
                    last_activity=datetime.utcnow()
                )
            ]
            
            for agent in agents:
                session.add(agent)
            
            # Create sample digital ventures
            sample_ventures = [
                DigitalVenture(
                    name="AI-Powered SaaS Analytics Platform",
                    description="Enterprise analytics platform with AI-driven insights",
                    venture_type=VentureType.SAAS,
                    status=VentureStatus.MVP,
                    initial_investment=50000.0,
                    monthly_revenue=8500.0,
                    monthly_expenses=3200.0,
                    profit_margin=0.62,
                    risk_level=RiskLevel.LOW,
                    risk_score=0.15,
                    failure_probability=0.0008, # 0.08% - meets ultra-low target
                    customer_count=127,
                    churn_rate=0.03,
                    growth_rate=0.18,
                    ai_enabled=True,
                    automation_level=0.75
                ),
                DigitalVenture(
                    name="Digital Marketplace for B2B Tools",
                    description="Curated marketplace for enterprise software solutions",
                    venture_type=VentureType.ECOMMERCE,
                    status=VentureStatus.SCALING,
                    initial_investment=75000.0,
                    monthly_revenue=15200.0,
                    monthly_expenses=6800.0,
                    profit_margin=0.55,
                    risk_level=RiskLevel.ULTRA_LOW,
                    risk_score=0.08,
                    failure_probability=0.0003, # 0.03% - ultra-low risk
                    customer_count=89,
                    churn_rate=0.02,
                    growth_rate=0.22,
                    ai_enabled=True,
                    automation_level=0.85
                ),
                DigitalVenture(
                    name="Content Creation AI Platform",
                    description="AI-powered content generation for digital marketing",
                    venture_type=VentureType.CONTENT_PLATFORM,
                    status=VentureStatus.VALIDATION,
                    initial_investment=30000.0,
                    monthly_revenue=2100.0,
                    monthly_expenses=1800.0,
                    profit_margin=0.14,
                    risk_level=RiskLevel.MODERATE,
                    risk_score=0.35,
                    failure_probability=0.012, # 1.2% - above target, needs optimization
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