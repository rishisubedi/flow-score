import httpx
import json
import asyncio
from datetime import datetime, timedelta

async def run_demo():
    """
    Simulates a B2B lender sending a thin-file gig-worker's data to the FlowScore API.
    Used for local demonstrations during interviews.
    """
    url = "http://localhost:8080/v1/underwrite/"
    
    # Generate mock dates relative to today
    today = datetime.now()
    
    # 1. Construct a mock payload simulating a gig-worker (e.g. Uber Driver)
    payload = {
        "applicant_id": "gig_worker_9942",
        "transactions": [
            # Income
            {"transaction_id": "tx_1", "date": (today - timedelta(days=2)).isoformat(), "amount": 150.50, "description": "UBER PAYOUT", "category": "INCOME_GIG"},
            {"transaction_id": "tx_2", "date": (today - timedelta(days=9)).isoformat(), "amount": 210.00, "description": "UBER PAYOUT", "category": "INCOME_GIG"},
            {"transaction_id": "tx_3", "date": (today - timedelta(days=16)).isoformat(), "amount": 185.00, "description": "UBER PAYOUT", "category": "INCOME_GIG"},
            
            # Essential Expenses
            {"transaction_id": "tx_4", "date": (today - timedelta(days=5)).isoformat(), "amount": -450.00, "description": "TESCO SUPERSTORE", "category": "GROCERIES"},
            {"transaction_id": "tx_5", "date": (today - timedelta(days=1)).isoformat(), "amount": -120.00, "description": "BRITISH GAS", "category": "UTILITIES"},
            
            # Discretionary Expenses
            {"transaction_id": "tx_6", "date": (today - timedelta(days=4)).isoformat(), "amount": -45.00, "description": "NANDOS", "category": "DINING"},
            {"transaction_id": "tx_7", "date": (today - timedelta(days=14)).isoformat(), "amount": -15.99, "description": "NETFLIX", "category": "ENTERTAINMENT"},
        ],
        "policy": {
            "max_dti_allowed": 0.50,
            "min_monthly_income": 500.0,
            "strict_fca_mode": True
        }
    }

    print("🚀 Transmitting Open Banking payload to FlowScore AI Engine...")
    print(f"📡 Target: {url}")
    print("-" * 50)
    
    async with httpx.AsyncClient() as client:
        try:
            # We use a dummy tenant API key for the security dependency
            response = await client.post(
                url, 
                json=payload, 
                headers={"X-API-Key": "tenantA:secret123"},
                timeout=30.0
            )
            
            print(f"✅ Response Status: {response.status_code}")
            print("🧠 AI Decision Output:")
            print(json.dumps(response.json(), indent=4))
            
        except httpx.ConnectError:
            print("❌ Connection Error: Is the FastAPI server running on localhost:8080?")
            print("💡 Run: docker-compose up --build")

if __name__ == "__main__":
    asyncio.run(run_demo())
