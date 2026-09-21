from langgraph.graph import StateGraph, END
from app.agents.state import AgentState
from app.agents.nodes.ingestion import ingestion_node
from app.agents.nodes.income import income_analyst_node

# --- Stubs for Days 6, and 7 ---

def expense_node_stub(state: AgentState) -> dict:
    return {"expense_metrics": {"status": "pending_day_6"}}

def supervisor_node_stub(state: AgentState) -> dict:
    return {"final_decision": None} # Placeholder until Day 7

def build_graph():
    """
    Compiles the Multi-Agent State Graph.
    This defines the control flow of the entire underwriting process.
    """
    # 1. Initialize the state graph with our TypedDict
    workflow = StateGraph(AgentState)
    
    # 2. Add all agent nodes to the graph
    workflow.add_node("ingestion", ingestion_node)
    workflow.add_node("income_analyst", income_analyst_node)
    workflow.add_node("expense_tracker", expense_node_stub)
    workflow.add_node("supervisor", supervisor_node_stub)
    
    # 3. Define the Control Flow (Edges)
    
    # The workflow strictly begins at the ingestion node to clean data
    workflow.set_entry_point("ingestion")
    
    # FAN-OUT: After ingestion, the data splits and is processed by Income and Expense agents IN PARALLEL
    workflow.add_edge("ingestion", "income_analyst")
    workflow.add_edge("ingestion", "expense_tracker")
    
    # FAN-IN: Both parallel agents must finish before their outputs are merged and sent to the Supervisor
    workflow.add_edge("income_analyst", "supervisor")
    workflow.add_edge("expense_tracker", "supervisor")
    
    # The Supervisor makes the final decision, ending the graph
    workflow.add_edge("supervisor", END)
    
    # Compile the graph into a runnable LangChain runnable
    return workflow.compile()

# Instantiate the compiled graph so it can be imported into the FastAPI endpoint
underwriting_graph = build_graph()
