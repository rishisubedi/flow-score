from app.agents.state import AgentState

def ingestion_node(state: AgentState) -> dict:
    """
    Filters and categorizes the raw transaction data.
    In Day 5/6, this will pass cleaned, categorized data to the Income and Expense agents.
    """
    transactions = state.get("transactions", [])
    
    # Simple heuristic categorization for MVP
    # In a later iteration, this could be an LLM call itself, but heuristics are faster for standard B2B payloads
    categorized = []
    for tx in transactions:
        # Convert the Pydantic model to a dict for easier LangGraph state passing
        tx_dict = tx.model_dump()
        
        # Basic categorization fallback if the B2B client didn't provide one
        if not tx.category:
            desc = tx.description.lower()
            if "uber" in desc or "deliveroo" in desc or "earnings" in desc:
                tx_dict["category"] = "INCOME_GIG"
            elif "rent" in desc or "properties" in desc or "housing" in desc:
                tx_dict["category"] = "RENT"
            elif "gas" in desc or "water" in desc or "electric" in desc:
                tx_dict["category"] = "UTILITIES"
            elif "tesco" in desc or "sainsbury" in desc or "aldi" in desc:
                tx_dict["category"] = "GROCERIES"
            else:
                tx_dict["category"] = "OTHER"
        
        categorized.append(tx_dict)
        
    return {"categorized_transactions": categorized}
