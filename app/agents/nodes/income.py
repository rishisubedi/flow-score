from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from app.agents.state import AgentState
from app.core.config import settings

class IncomeMetrics(BaseModel):
    """Strict schema for the Income Analyst LLM to adhere to."""
    total_income: float = Field(description="Sum of all income transactions over the period in GBP.")
    volatility_score: float = Field(description="Score from 0.0 (highly stable/salaried) to 1.0 (highly volatile/erratic) indicating income fluctuation.")
    income_stability_narrative: str = Field(description="A professional, FCA-compliant explanation of the applicant's income stability and trajectory.")

def income_analyst_node(state: AgentState) -> dict:
    """
    Analyzes 'INCOME' transactions to determine gig-economy wage stability.
    Uses GPT-4o-mini with structured outputs to guarantee deterministic JSON formatting.
    """
    transactions = state.get("categorized_transactions", [])
    
    # Filter for income only to drastically reduce the LLM token context window
    income_txs = [tx for tx in transactions if tx.get("amount", 0) > 0 or tx.get("category") == "INCOME_GIG"]
    
    # Edge Case: No income found at all
    if not income_txs:
        return {
            "income_metrics": {
                "total_income": 0.0,
                "volatility_score": 1.0,
                "income_stability_narrative": "CRITICAL RISK: No income transactions were detected in the provided open banking history.",
            }
        }

    # Initialize the LLM (Requires OPENAI_API_KEY in environment)
    # We use gpt-4o-mini for speed and cost-efficiency in high-volume underwriting
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0, api_key=settings.OPENAI_API_KEY)
    
    # Enforce strict structured output (Function Calling)
    structured_llm = llm.with_structured_output(IncomeMetrics)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert Credit Risk Income Analyst for a UK Bank. Your job is to evaluate the stability of a gig-worker's income based on their transaction history. Evaluate the volatility and provide a professional narrative for the compliance audit trail."),
        ("human", "Here are the income transactions: {transactions}\n\nAnalyze these and output the strictly required metrics.")
    ])
    
    chain = prompt | structured_llm
    
    try:
        # Execute the LLM call synchronously (LangGraph manages the parallel async execution under the hood)
        result: IncomeMetrics = chain.invoke({"transactions": income_txs})
        return {"income_metrics": result.model_dump()}
    except Exception as e:
        # Fallback in case of API timeout/failure to prevent the entire LangGraph from crashing
        return {
            "errors": [f"Income Analyst LLM failed: {str(e)}"],
            "income_metrics": {
                "total_income": sum(tx.get("amount", 0) for tx in income_txs),
                "volatility_score": 0.99,
                "income_stability_narrative": "Automated LLM analysis failed. Defaulting to high volatility. Manual review heavily recommended."
            }
        }
