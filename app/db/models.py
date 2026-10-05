from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base
import uuid

class CreditDecision(Base):
    __tablename__ = "credit_decisions"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, unique=True, index=True, nullable=True) # Added for async tracking
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
    
    # Relationships
    overrides = relationship("HumanOverride", back_populates="decision_record")

class HumanOverride(Base):
    __tablename__ = "human_overrides"
    
    override_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String, ForeignKey("credit_decisions.job_id"), nullable=False)
    officer_sso_id = Column(String, nullable=False) # e.g. Auth0/Okta ID
    previous_decision = Column(String, nullable=False)
    new_decision = Column(String, nullable=False)
    justification_notes = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    decision_record = relationship("CreditDecision", back_populates="overrides")

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(String, unique=True, index=True, nullable=False)
    api_key_hash = Column(String, unique=True, index=True, nullable=False)
    
    subscription_tier = Column(String, default="PAYG", nullable=False) # PAYG, PRO, ENTERPRISE_BYOK
    credits_remaining = Column(Integer, default=10, nullable=False)
    
    # BYOK KMS Encryption Fields
    byok_provider = Column(String, nullable=True) # "openai" or "gemini"
    byok_api_key = Column(String, nullable=True) # Legacy plaintext, to be deprecated
    encrypted_byok_key = Column(String, nullable=True) # Fernet/KMS Encrypted String
    kms_key_id = Column(String, nullable=True)
    webhook_secret = Column(String, nullable=True) # For verifying incoming OpenBanking webhooks
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

