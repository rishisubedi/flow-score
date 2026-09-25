from app.agents.nodes.supervisor import supervisor_node
from app.agents.state import AgentState

def test_supervisor_agent_fallback_logic():
    """
    Edge Case: Simulate a catastrophic failure in the upstream LangGraph nodes (e.g. OpenAI API goes down).
    The Supervisor Agent should safely catch the error and fallback to a MANUAL_REVIEW decision, 
    preventing an unhandled exception or hallucination from being sent to the B2B client.
    """
    # Create a mock state simulating multiple upstream agent failures
    mock_state: AgentState = {
        "applicant_id": "app_emergency_123",
        "transactions": [],
        "categorized_transactions": [],
        "income_metrics": {},
        "expense_metrics": {},
        "policy": None,
        "final_decision": None,
        "errors": [
            "Income Analyst LLM failed: API Timeout",
            "Expense Tracker LLM failed: Rate Limit Exceeded",
            "Ingestion Agent failed: Malformed context"
        ]
    }
    
    # Directly invoke the Supervisor Node
    result = supervisor_node(mock_state)
    
    # Assert the node successfully triggered the safety net
    assert "final_decision" in result
    decision = result["final_decision"]
    
    # Validate the default conservative outputs
    assert decision["decision"] == "MANUAL_REVIEW"
    assert decision["risk_score"] == 0
    assert decision["dti_ratio"] == 9.99
    assert decision["applicant_id"] == "app_emergency_123"
    assert "System failure triggered safety override" in decision["audit_trail"]["internal_compliance_log"]["affordability_logic"]
