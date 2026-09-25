from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.agents.state import AgentState
from app.models.schemas import CreditDecisionOutput, FCAAuditTrail, InternalComplianceLog
from app.core.config import settings

def supervisor_node(state: AgentState) -> dict:
    """
    The Fan-In Supervisor Agent.
    It receives the parallel analysis from both the Income Analyst and Expense Tracker,
    applies the lender's custom risk policy, and synthesizes a final FCA-compliant credit decision.
    """
    income = state.get("income_metrics", {})
    expense = state.get("expense_metrics", {})
    policy = state.get("policy", None)
    applicant_id = state.get("applicant_id", "UNKNOWN")
    errors = state.get("errors", [])
    
    # Check for catastrophic upstream failures
    if errors and len(errors) > 2:
        return _fallback_rejection(applicant_id, "Multiple upstream agents failed. Safely defaulting to MANUAL_REVIEW.")

    # Initialize the Orchestrator LLM
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0, api_key=settings.OPENAI_API_KEY)
    structured_llm = llm.with_structured_output(CreditDecisionOutput)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are the Chief Risk Officer (Supervisor AI) for a UK Bank.
        Your job is to synthesize data from the Income Analyst and Expense Tracker agents to make a final credit decision for a thin-file applicant.
        
        Lender Risk Policy Constraints:
        - Max DTI allowed: {max_dti}
        - Min monthly income: {min_income}
        - Strict FCA Mode: {strict_fca}
        
        Rules:
        1. Calculate the final Debt-to-Income (DTI) ratio. (baseline_expenses / total_income).
        2. Generate a risk_score from 0 (terrible) to 1000 (perfect).
        3. Determine if they are APPROVED, REJECTED, or need MANUAL_REVIEW based on the policy constraints.
        4. Produce a Dual-Layer Audit Trail:
           a. An internal log for compliance officers detailing the math and logic.
           b. A consumer-facing explanation adhering strictly to FCA transparency (clear, polite, non-discriminatory).
        """),
        ("human", """
        Applicant ID: {applicant_id}
        
        Income Metrics (From Agent A):
        {income}
        
        Expense Metrics (From Agent B):
        {expense}
        
        Synthesize this and output the final decision. Ensure you always return the applicant ID exactly as '{applicant_id}'.
        """)
    ])
    
    chain = prompt | structured_llm
    
    try:
        # Pass the extracted context safely to the prompt
        result: CreditDecisionOutput = chain.invoke({
            "applicant_id": applicant_id,
            "max_dti": policy.max_dti_allowed if policy else 0.45,
            "min_income": policy.min_monthly_income if policy else 1000.0,
            "strict_fca": policy.strict_fca_mode if policy else True,
            "income": income,
            "expense": expense
        })
        
        # We store the final object back in the state as a dict/Pydantic depending on downstream needs.
        # Returning it as a dict using model_dump() aligns with standard LangGraph practice.
        return {"final_decision": result.model_dump() if hasattr(result, 'model_dump') else result}
    
    except Exception as e:
        return _fallback_rejection(applicant_id, f"Supervisor Agent Error: {str(e)}")

def _fallback_rejection(applicant_id: str, reason: str) -> dict:
    """Safety net: If the AI hallucinates or the API goes down, gracefully fail to a Manual Review."""
    return {
        "errors": [reason],
        "final_decision": {
            "applicant_id": applicant_id,
            "risk_score": 0,
            "decision": "MANUAL_REVIEW",
            "dti_ratio": 9.99,
            "audit_trail": {
                "internal_compliance_log": {
                    "income_volatility_score": 1.0,
                    "expense_baseline": 0.0,
                    "affordability_logic": f"System failure triggered safety override. {reason}"
                },
                "customer_facing_explanation": "We are currently reviewing your application manually to ensure we provide you with the most accurate and fair assessment.",
                "consumer_duty_statement": "In accordance with FCA guidelines, this decision has been paused for human review due to a system interruption."
            }
        }
    }
