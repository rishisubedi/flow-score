from sqlalchemy import Column, String, Integer, Float, DateTime, JSON
from sqlalchemy.sql import func
from app.db.database import Base

class CreditDecision(Base):
    __tablename__ = "credit_decisions"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(String, index=True, nullable=False)  # Multi-tenant ID
    applicant_id = Column(String, index=True, nullable=False)
    
    # Core output metrics
    risk_score = Column(Integer, nullable=False)
    decision = Column(String, nullable=False)  # APPROVED, REJECTED, MANUAL_REVIEW
    dti_ratio = Column(Float, nullable=False)
    
    # FCA Compliance Audit Trail (Dual-layer stored as JSON)
    audit_trail = Column(JSON, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(String, unique=True, index=True, nullable=False)
    api_key_hash = Column(String, unique=True, index=True, nullable=False)
    
    subscription_tier = Column(String, default="PAYG", nullable=False) # PAYG, PRO, ENTERPRISE_BYOK
    credits_remaining = Column(Integer, default=10, nullable=False)
    
    byok_provider = Column(String, nullable=True) # "openai" or "gemini"
    byok_api_key = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

