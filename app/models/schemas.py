from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime

# --- Input Models ---
class Transaction(BaseModel):
    transaction_id: str
    date: datetime
    amount: float = Field(..., description="Amount in GBP. Positive for income, negative for expense.")
    description: str
    category: Optional[str] = None

class UnderwritingRequest(BaseModel):
    applicant_id: str
    transactions: List[Transaction] = Field(..., min_length=1, description="List of 12-month Open Banking transactions")

# --- Output Models (FCA Compliant) ---
class FCAAuditTrail(BaseModel):
    income_assessment: str = Field(..., description="Explanation of income stability and volatility.")
    expense_assessment: str = Field(..., description="Explanation of baseline living costs.")
    affordability_logic: str = Field(..., description="Explanation of DTI and affordability calculation.")
    consumer_duty_statement: str = Field(..., description="Statement confirming fair value and good consumer outcomes.")

class CreditDecisionOutput(BaseModel):
    applicant_id: str
    risk_score: int = Field(..., ge=0, le=1000, description="Risk score from 0 (highest risk) to 1000 (lowest risk).")
    decision: Literal["APPROVED", "REJECTED", "MANUAL_REVIEW"]
    dti_ratio: float = Field(..., description="Calculated Debt-to-Income ratio.")
    audit_trail: FCAAuditTrail
