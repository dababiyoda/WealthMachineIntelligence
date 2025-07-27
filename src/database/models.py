"""
Enterprise-grade database models for WealthMachine
Implements comprehensive tracking of digital ventures, AI agents, and performance metrics
"""
from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, JSON, ForeignKey, Text, Index, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
import uuid

Base = declarative_base()

class VentureStatus(enum.Enum):
    """Digital venture lifecycle states"""
    IDEATION = "ideation"
    VALIDATION = "validation"
    MVP = "mvp"
    SCALING = "scaling"
    OPTIMIZING = "optimizing"
    MATURE = "mature"
    ON_HOLD = "on_hold"
    DISCONTINUED = "discontinued"

class VentureType(enum.Enum):
    """Types of digital ventures"""
    SAAS = "saas"
    ECOMMERCE = "ecommerce"
    CONTENT_PLATFORM = "content_platform"
    MARKETPLACE = "marketplace"
    API_SERVICE = "api_service"
    SUBSCRIPTION_BOX = "subscription_box"

class RiskLevel(enum.Enum):
    """Risk assessment levels"""
    ULTRA_LOW = "ultra_low"  # P(failure) ≤ 0.01%
    LOW = "low"              # P(failure) ≤ 0.1%
    MODERATE = "moderate"    # P(failure) ≤ 1%
    HIGH = "high"            # P(failure) ≤ 5%
    VERY_HIGH = "very_high"  # P(failure) > 5%

class AgentType(enum.Enum):
    """AI Agent types in the system"""
    MARKET_INTELLIGENCE = "market_intelligence"
    RISK_ASSESSMENT = "risk_assessment"
    LEGAL_COMPLIANCE = "legal_compliance"
    FINANCIAL_STRATEGIST = "financial_strategist"
    TECH_INNOVATOR = "tech_innovator"
    BRAND_STRATEGIST = "brand_strategist"

class DigitalVenture(Base):
    """Core model for digital business ventures"""
    __tablename__ = 'digital_ventures'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    venture_type = Column(SQLEnum(VentureType), nullable=False)
    status = Column(SQLEnum(VentureStatus), default=VentureStatus.IDEATION)
    
    # Financial metrics
    initial_investment = Column(Float, default=0.0)
    current_valuation = Column(Float, default=0.0)
    monthly_revenue = Column(Float, default=0.0)
    monthly_expenses = Column(Float, default=0.0)
    profit_margin = Column(Float, default=0.0)
    
    # Risk assessment
    risk_level = Column(SQLEnum(RiskLevel), default=RiskLevel.MODERATE)
    risk_score = Column(Float, default=0.5)  # 0-1 scale
    failure_probability = Column(Float, default=0.01)  # Target ≤ 0.01%
    
    # Growth metrics
    customer_count = Column(Integer, default=0)
    churn_rate = Column(Float, default=0.0)
    growth_rate = Column(Float, default=0.0)
    market_share = Column(Float, default=0.0)
    
    # AI integration
    ai_enabled = Column(Boolean, default=True)
    automation_level = Column(Float, default=0.0)  # 0-1 scale
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    launched_at = Column(DateTime(timezone=True))
    discontinued_at = Column(DateTime(timezone=True))
    
    # Relationships
    performance_metrics = relationship("PerformanceMetric", back_populates="venture", cascade="all, delete-orphan")
    risk_assessments = relationship("RiskAssessment", back_populates="venture", cascade="all, delete-orphan")
    ai_decisions = relationship("AIDecision", back_populates="venture", cascade="all, delete-orphan")
    market_analyses = relationship("MarketAnalysis", back_populates="venture", cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_venture_status_type', 'status', 'venture_type'),
        Index('idx_venture_risk', 'risk_level', 'failure_probability'),
        Index('idx_venture_financial', 'monthly_revenue', 'profit_margin'),
    )

class AIAgent(Base):
    """AI agents managing the system"""
    __tablename__ = 'ai_agents'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_type = Column(SQLEnum(AgentType), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    version = Column(String(50), default="1.0.0")
    
    # Performance metrics
    accuracy = Column(Float, default=0.0)
    decisions_made = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    
    # Model information
    model_type = Column(String(100))  # LSTM, Random Forest, BERT, etc.
    model_parameters = Column(JSON)
    last_training = Column(DateTime(timezone=True))
    
    # Status
    is_active = Column(Boolean, default=True)
    last_activity = Column(DateTime(timezone=True))
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    decisions = relationship("AIDecision", back_populates="agent")
    risk_assessments = relationship("RiskAssessment", back_populates="agent")

class PerformanceMetric(Base):
    """Time-series performance tracking"""
    __tablename__ = 'performance_metrics'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    venture_id = Column(String(36), ForeignKey('digital_ventures.id'), nullable=False)
    
    # Financial metrics
    revenue = Column(Float, nullable=False)
    expenses = Column(Float, nullable=False)
    profit = Column(Float, nullable=False)
    roi = Column(Float)  # Return on Investment
    
    # Customer metrics
    new_customers = Column(Integer, default=0)
    churned_customers = Column(Integer, default=0)
    active_users = Column(Integer, default=0)
    conversion_rate = Column(Float, default=0.0)
    
    # Operational metrics
    uptime = Column(Float, default=99.9)  # Percentage
    response_time = Column(Float)  # Milliseconds
    error_rate = Column(Float, default=0.0)
    
    # Timestamp
    measured_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    # Relationships
    venture = relationship("DigitalVenture", back_populates="performance_metrics")
    
    # Index for time-series queries
    __table_args__ = (
        Index('idx_metrics_venture_time', 'venture_id', 'measured_at'),
    )

class RiskAssessment(Base):
    """AI-driven risk assessments with history tracking"""
    __tablename__ = 'risk_assessments'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    venture_id = Column(String(36), ForeignKey('digital_ventures.id'), nullable=False)
    agent_id = Column(String(36), ForeignKey('ai_agents.id'), nullable=False)
    
    # Risk metrics
    risk_score = Column(Float, nullable=False)  # 0-1 scale
    failure_probability = Column(Float, nullable=False)  # Percentage
    confidence_level = Column(Float, nullable=False)  # 0-1 scale
    
    # Risk factors
    market_risk = Column(Float, default=0.0)
    operational_risk = Column(Float, default=0.0)
    financial_risk = Column(Float, default=0.0)
    technical_risk = Column(Float, default=0.0)
    regulatory_risk = Column(Float, default=0.0)
    
    # AI model details
    model_version = Column(String(50))
    features_used = Column(JSON)  # List of features used in assessment
    
    # Recommendations
    risk_level = Column(SQLEnum(RiskLevel), nullable=False)
    recommendations = Column(JSON)  # List of risk mitigation strategies
    
    # Timestamp
    assessed_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    # Relationships
    venture = relationship("DigitalVenture", back_populates="risk_assessments")
    agent = relationship("AIAgent", back_populates="risk_assessments")
    
    # Index for history tracking (10-version requirement)
    __table_args__ = (
        Index('idx_risk_venture_time', 'venture_id', 'assessed_at'),
        Index('idx_risk_agent', 'agent_id', 'assessed_at'),
    )

class AIDecision(Base):
    """Track all AI-driven decisions for audit and learning"""
    __tablename__ = 'ai_decisions'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    venture_id = Column(String(36), ForeignKey('digital_ventures.id'))
    agent_id = Column(String(36), ForeignKey('ai_agents.id'), nullable=False)
    
    # Decision details
    decision_type = Column(String(100), nullable=False)  # launch, scale, pivot, hold, discontinue
    decision_data = Column(JSON, nullable=False)  # Full decision context
    confidence = Column(Float, nullable=False)  # 0-1 scale
    
    # Outcome tracking
    was_executed = Column(Boolean, default=False)
    execution_result = Column(String(50))  # success, failure, partial
    impact_metrics = Column(JSON)  # Measured impact of decision
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    executed_at = Column(DateTime(timezone=True))
    evaluated_at = Column(DateTime(timezone=True))
    
    # Relationships
    venture = relationship("DigitalVenture", back_populates="ai_decisions")
    agent = relationship("AIAgent", back_populates="decisions")
    
    # Index for decision analysis
    __table_args__ = (
        Index('idx_decision_type_agent', 'decision_type', 'agent_id'),
        Index('idx_decision_venture_time', 'venture_id', 'created_at'),
    )

class MarketAnalysis(Base):
    """Market intelligence data for opportunities"""
    __tablename__ = 'market_analyses'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    venture_id = Column(String(36), ForeignKey('digital_ventures.id'))
    
    # Market data
    market_size = Column(Float)  # In dollars
    growth_rate = Column(Float)  # Percentage
    competition_level = Column(String(50))  # low, medium, high
    
    # Opportunity scoring
    opportunity_score = Column(Float, nullable=False)  # 0-1 scale
    timing_score = Column(Float)  # 0-1 scale for market timing
    
    # Trends and insights
    key_trends = Column(JSON)  # List of identified trends
    customer_segments = Column(JSON)  # Target segments
    competitive_advantages = Column(JSON)  # Unique value propositions
    
    # AI predictions
    lstm_prediction = Column(JSON)  # Time series predictions
    sentiment_analysis = Column(JSON)  # Market sentiment data
    
    # Timestamp
    analyzed_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    # Relationships
    venture = relationship("DigitalVenture", back_populates="market_analyses")
    
    # Index for market queries
    __table_args__ = (
        Index('idx_market_opportunity', 'opportunity_score', 'analyzed_at'),
    )

class KnowledgeGraphEntity(Base):
    """Entities in the knowledge graph"""
    __tablename__ = 'knowledge_entities'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_type = Column(String(100), nullable=False)  # venture, market, technology, competitor
    entity_name = Column(String(255), nullable=False)
    properties = Column(JSON, nullable=False)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    source_relationships = relationship("KnowledgeRelationship", 
                                      foreign_keys='KnowledgeRelationship.source_id',
                                      back_populates="source")
    target_relationships = relationship("KnowledgeRelationship", 
                                      foreign_keys='KnowledgeRelationship.target_id',
                                      back_populates="target")
    
    # Index for entity queries
    __table_args__ = (
        Index('idx_entity_type_name', 'entity_type', 'entity_name'),
    )

class KnowledgeRelationship(Base):
    """Relationships in the knowledge graph"""
    __tablename__ = 'knowledge_relationships'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_id = Column(String(36), ForeignKey('knowledge_entities.id'), nullable=False)
    target_id = Column(String(36), ForeignKey('knowledge_entities.id'), nullable=False)
    relationship_type = Column(String(100), nullable=False)
    properties = Column(JSON)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    source = relationship("KnowledgeGraphEntity", foreign_keys=[source_id], back_populates="source_relationships")
    target = relationship("KnowledgeGraphEntity", foreign_keys=[target_id], back_populates="target_relationships")
    
    # Index for graph traversal
    __table_args__ = (
        Index('idx_relationship_source', 'source_id', 'relationship_type'),
        Index('idx_relationship_target', 'target_id', 'relationship_type'),
    )