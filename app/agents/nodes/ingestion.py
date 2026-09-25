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
        # Convert the Pydantic model to a dict if it's not already one
        tx_dict = tx.model_dump() if hasattr(tx, 'model_dump') else tx.copy()
        
        category = tx_dict.get("category")
        description = tx_dict.get("description", "").lower()
        
        # Basic categorization fallback if the B2B client didn't provide one
        if not category:
            if "uber" in description or "deliveroo" in description or "earnings" in description:
                tx_dict["category"] = "INCOME_GIG"
            elif "rent" in description or "properties" in description or "housing" in description:
                tx_dict["category"] = "RENT"
            elif "gas" in description or "water" in description or "electric" in description:
                tx_dict["category"] = "UTILITIES"
            elif "tesco" in description or "sainsbury" in description or "aldi" in description:
                tx_dict["category"] = "GROCERIES"
            else:
                tx_dict["category"] = "OTHER"
        
        categorized.append(tx_dict)
        
    return {"categorized_transactions": categorized}
