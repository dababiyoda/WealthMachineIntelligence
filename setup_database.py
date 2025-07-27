"""
Standalone database setup script
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from src.database.connection import db, get_db
from src.database.models import (
    Base, AIAgent, DigitalVenture, AgentType, VentureType, VentureStatus, RiskLevel
)

def setup_database():
    """Setup database with tables and initial data"""
    print("🚀 Setting up WealthMachine Enterprise Database...")
    
    try:
        # Create all tables
        Base.metadata.create_all(bind=db.engine)
        print("✅ Database tables created")
        
        # Add initial data
        with get_db() as session:
            # Check if data exists
            if session.query(AIAgent).count() > 0:
                print("✅ Database already has data")
                return
            
            # Create AI agents
            agents = [
                AIAgent(
                    agent_type=AgentType.MARKET_INTELLIGENCE,
                    name="Market Intelligence Agent",
                    version="1.0.0",
                    model_type="LSTM + Sentiment Analysis",
                    is_active=True,
                    accuracy=0.85,
                    success_rate=0.82
                ),
                AIAgent(
                    agent_type=AgentType.RISK_ASSESSMENT,
                    name="Risk Assessment Agent", 
                    version="1.0.0",
                    model_type="Hybrid LSTM + Random Forest",
                    is_active=True,
                    accuracy=0.92,
                    success_rate=0.89
                ),
                AIAgent(
                    agent_type=AgentType.LEGAL_COMPLIANCE,
                    name="Legal Compliance Agent",
                    version="1.0.0", 
                    model_type="BERT + Regulatory NLP",
                    is_active=True,
                    accuracy=0.88,
                    success_rate=0.91
                )
            ]
            
            for agent in agents:
                session.add(agent)
            
            # Sample ventures
            ventures = [
                DigitalVenture(
                    name="AI-Powered SaaS Analytics",
                    description="Enterprise analytics with AI insights",
                    venture_type=VentureType.SAAS,
                    status=VentureStatus.MVP,
                    initial_investment=50000.0,
                    monthly_revenue=8500.0,
                    monthly_expenses=3200.0,
                    risk_level=RiskLevel.LOW,
                    risk_score=0.15,
                    failure_probability=0.0008, # 0.08% - meets target
                    customer_count=127,
                    churn_rate=0.03,
                    ai_enabled=True,
                    automation_level=0.75
                ),
                DigitalVenture(
                    name="B2B Digital Marketplace",
                    description="Curated enterprise software marketplace",
                    venture_type=VentureType.ECOMMERCE,
                    status=VentureStatus.SCALING,
                    initial_investment=75000.0,
                    monthly_revenue=15200.0,
                    monthly_expenses=6800.0,
                    risk_level=RiskLevel.ULTRA_LOW,
                    risk_score=0.08,
                    failure_probability=0.0003, # 0.03% - ultra-low
                    customer_count=89,
                    churn_rate=0.02,
                    ai_enabled=True,
                    automation_level=0.85
                )
            ]
            
            for venture in ventures:
                session.add(venture)
                
            session.commit()
            print("✅ Initial data created")
            
        print("✅ Database setup completed successfully!")
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        raise

if __name__ == "__main__":
    setup_database()