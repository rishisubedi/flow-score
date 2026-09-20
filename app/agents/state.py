from typing import Annotated, List, Dict, Any, Optional
from typing_extensions import TypedDict
from app.models.schemas import Transaction, CreditDecisionOutput, LenderPolicy

def merge_lists(a: List, b: List) -> List:
    """Reducer function to safely append to lists in parallel nodes."""
    return a + b

class AgentState(TypedDict):
    """
    The central state object that is passed around between all LangGraph agents.
    Every node reads from this and returns a dict with the keys they want to update.
    """
    applicant_id: str
    transactions: List[Transaction]
    policy: LenderPolicy
    
    # Data pipeline outputs
    categorized_transactions: List[Dict[str, Any]]
    
    # Agent outputs
    income_metrics: Dict[str, Any]
    expense_metrics: Dict[str, Any]
    
    # Final Orchestrator output
    final_decision: Optional[CreditDecisionOutput]
    
    # We use Annotated and a reducer (merge_lists) so parallel nodes can append errors safely without overwriting each other
    errors: Annotated[List[str], merge_lists]
