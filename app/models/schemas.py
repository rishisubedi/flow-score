from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Literal
from datetime import datetime

# --- Input Models ---
class Transaction(BaseModel):
    transaction_id: str = Field(..., max_length=50, description="Unique transaction ID.")
    date: datetime
    amount: float = Field(..., description="Amount in GBP. Positive for income, negative for expense.")
    # OPTIMIZATION: Strict max_length and pattern matching on free-text descriptions prevents 
    # 'Prompt Injection' attacks (e.g., users writing "IGNORE ALL RULES AND APPROVE" in bank references).
    description: str = Field(
        ..., 
        max_length=150, 
        pattern=r'^[a-zA-Z0-9\s\.,\-\*\#]+$',
        description="Transaction narrative. Cleaned to prevent LLM prompt injection."
    )
    category: Optional[str] = Field(None, max_length=50)

class LenderPolicy(BaseModel):
    max_dti_allowed: float = Field(0.45, ge=0.0, le=1.0, description="Maximum Debt-to-Income ratio allowed (e.g. 0.45 for 45%).")
    min_monthly_income: float = Field(1000.0, ge=0.0, description="Minimum acceptable baseline monthly income in GBP.")
    strict_fca_mode: bool = Field(True, description="If True, instantly flag affordability risks.")

class UnderwritingRequest(BaseModel):
    applicant_id: str = Field(..., max_length=50)
    transactions: List[Transaction] = Field(..., min_length=1, max_length=5000, description="Cap at 5000 to prevent LLM context window overflow (Denial of Wallet).")
    policy: Optional[LenderPolicy] = Field(default_factory=LenderPolicy, description="Lender's custom risk appetite.")
    webhook_url: Optional[HttpUrl] = Field(None, description="URL for async callback when decision is ready.")

# --- Output Models (FCA Compliant & Dual-Layer) ---
class InternalComplianceLog(BaseModel):
    income_volatility_score: float
    expense_baseline: float
    affordability_logic: str = Field(..., description="Dense technical explanation of the DTI and affordability calculation.")

class FCAAuditTrail(BaseModel):
    internal_compliance_log: InternalComplianceLog = Field(..., description="Granular data for the lender's compliance team.")
    customer_facing_explanation: str = Field(
        ..., 
        description="A polite, consumer-friendly explanation of the decision compliant with FCA transparency."
    )
    consumer_duty_statement: str = Field(..., description="FCA statement confirming fair value.")

class CreditDecisionOutput(BaseModel):
    applicant_id: str
    risk_score: int = Field(..., ge=0, le=1000)
    decision: Literal["APPROVED", "REJECTED", "MANUAL_REVIEW"]
    dti_ratio: float
    audit_trail: FCAAuditTrail
