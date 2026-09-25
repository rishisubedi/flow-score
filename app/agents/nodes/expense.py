from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from app.agents.state import AgentState
from app.core.config import settings

class ExpenseMetrics(BaseModel):
    """Strict schema for the Expense Tracker LLM to adhere to."""
    essential_living_costs: float = Field(description="Sum of all essential baseline expenses (rent, utilities, groceries, etc.) in GBP.")
    discretionary_spend: float = Field(description="Sum of all non-essential lifestyle expenses (dining out, entertainment, etc.) in GBP.")
    affordability_narrative: str = Field(description="A professional, FCA-compliant explanation of the applicant's spending behavior and ability to absorb a new credit repayment.")

def expense_analyst_node(state: AgentState) -> dict:
    """
    Analyzes 'EXPENSE' transactions to determine baseline living costs vs discretionary spending.
    Uses GPT-4o-mini to programmatically separate fixed affordability constraints from lifestyle choices.
    """
    transactions = state.get("categorized_transactions", [])
    
    # Filter for expenses only (outgoing funds)
    # We assume expenses are either strictly negative amounts or tagged appropriately.
    expense_txs = [tx for tx in transactions if tx.get("amount", 0) < 0 or tx.get("category", "").upper() in ["EXPENSE", "ESSENTIAL", "DISCRETIONARY"]]
    
    # Edge Case: No expenses found
    if not expense_txs:
        return {
            "expense_metrics": {
                "essential_living_costs": 0.0,
                "discretionary_spend": 0.0,
                "affordability_narrative": "ANOMALY: No outgoing transactions detected. Potential account dormancy or data extraction failure.",
            }
        }

    # Initialize the LLM (Requires OPENAI_API_KEY in environment)
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0, api_key=settings.OPENAI_API_KEY)
    
    # Enforce strict structured output (Function Calling)
    structured_llm = llm.with_structured_output(ExpenseMetrics)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert Credit Risk Expense Analyst for a UK Bank. 
        Your objective is to evaluate a thin-file customer's spending history strictly adhering to FCA Consumer Duty standards.
        You must segregate 'essential living costs' (rent, energy, council tax, groceries) from 'discretionary spend' (pubs, betting, subscriptions).
        This segregation determines their true disposable income and affordability. Provide a professional narrative for the audit trail."""),
        ("human", "Here are the expense transactions: {transactions}\n\nAnalyze these and output the strictly required metrics. Please return absolute positive values for the totals (e.g., 500.0 instead of -500.0).")
    ])
    
    chain = prompt | structured_llm
    
    try:
        # Execute the LLM call
        result: ExpenseMetrics = chain.invoke({"transactions": expense_txs})
        return {"expense_metrics": result.model_dump() if hasattr(result, 'model_dump') else result}
    except Exception as e:
        # Fallback in case of API failure to prevent the graph from crashing
        # We assume all expenses are essential as a conservative fallback for risk calculations
        total_outgoing = sum(abs(tx.get("amount", 0)) for tx in expense_txs)
        return {
            "errors": [f"Expense Tracker LLM failed: {str(e)}"],
            "expense_metrics": {
                "essential_living_costs": total_outgoing,
                "discretionary_spend": 0.0,
                "affordability_narrative": "Automated LLM analysis failed. All outgoing transactions defaulted to essential living costs for conservative affordability calculation."
            }
        }
