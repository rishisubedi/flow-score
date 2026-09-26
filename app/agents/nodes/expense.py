from app.core.llm import get_llm
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from app.agents.state import AgentState

class ExpenseMetrics(BaseModel):
    """Strict schema for the Expense Tracker LLM."""
    essential_expenses: float = Field(description="Total of all essential expenses (rent, utilities, groceries).")
    discretionary_expenses: float = Field(description="Total of all discretionary/non-essential expenses.")
    expense_baseline_narrative: str = Field(description="A brief narrative explaining the user's spending habits.")

def expense_analyst_node(state: AgentState) -> dict:
    """
    Analyzes 'EXPENSE' transactions to isolate strict baseline living costs from discretionary spend.
    """
    transactions = state.get("categorized_transactions", [])
    
    # Filter for expenses
    expense_txs = [tx for tx in transactions if tx.get("amount", 0) < 0 or tx.get("category") not in ["INCOME_GIG", "OTHER"]]
    
    if not expense_txs:
        return {
            "expense_metrics": {
                "essential_expenses": 0.0,
                "discretionary_expenses": 0.0,
                "expense_baseline_narrative": "No expenses recorded in this period.",
            }
        }

    # Initialize the LLM dynamically using the tenant's BYOK credentials
    llm = get_llm(state.get("llm_config", {}))
    
    # Enforce strict structured output (Function Calling)
    structured_llm = llm.with_structured_output(ExpenseMetrics)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert Credit Risk Expense Analyst for a UK Bank. Your job is to strictly isolate essential living costs from discretionary spending. Evaluate the baseline and provide a professional narrative for the compliance audit trail."),
        ("human", "Here are the expense transactions: {transactions}\n\nAnalyze these and output the strictly required metrics.")
    ])
    
    chain = prompt | structured_llm
    
    try:
        # Execute the LLM call
        result: ExpenseMetrics = chain.invoke({"transactions": expense_txs})
        return {"expense_metrics": result.model_dump() if hasattr(result, 'model_dump') else result}
    except Exception as e:
        # Fallback in case of API failure to prevent the graph from crashing
        # We assume all expenses are essential as a conservative fallback for risk calculations
        return {
            "errors": [f"Expense Tracker LLM failed: {str(e)}"],
            "expense_metrics": {
                "essential_expenses": sum(abs(tx.get("amount", 0)) for tx in expense_txs),
                "discretionary_expenses": 0.0,
                "expense_baseline_narrative": "Automated LLM analysis failed. Defaulting all expenses to essential baseline."
            }
        }
