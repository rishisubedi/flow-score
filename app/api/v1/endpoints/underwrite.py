from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
import httpx
import asyncio
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.db.database import get_db
from app.core.security import get_client_id
from app.models.schemas import UnderwritingRequest, CreditDecisionOutput
from app.db.models import CreditDecision
from app.agents.graph import underwriting_graph

logger = logging.getLogger(__name__)
router = APIRouter()

# OPTIMIZATION: Added Exponential Backoff Retry logic using Tenacity.
# If a B2B client's server is temporarily down, FlowScore will automatically retry 
# sending the webhook payload instead of silently dropping the audit trail.
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException))
)
async def deliver_webhook_with_retry(webhook_url: str, payload: dict):
    async with httpx.AsyncClient() as client:
        # Timeout configured to prevent hanging connections
        response = await client.post(str(webhook_url), json=payload, timeout=10.0)
        response.raise_for_status()
        logger.info(f"Webhook successfully delivered to {webhook_url}")

async def process_webhook_callback(webhook_url: str, payload: dict):
    """
    Background task entrypoint that wraps the retry logic.
    Ensures the main API thread isn't blocked by slow network requests.
    """
    try:
        await deliver_webhook_with_retry(webhook_url, payload)
    except Exception as exc:
        logger.error(f"Permanent webhook failure for {webhook_url} after 5 retries. Reason: {exc}")

def execute_langgraph_workflow(request_data: dict) -> dict:
    """
    Executes the compiled LangGraph workflow synchronously.
    Wrapped in an asyncio ThreadPool downstream.
    """
    initial_state = {
        "applicant_id": request_data.get("applicant_id"),
        "transactions": request_data.get("transactions", []),
        "policy": request_data.get("policy", {}),
        "categorized_transactions": [],
        "income_metrics": {},
        "expense_metrics": {},
        "final_decision": None,
        "errors": []
    }
    
    return underwriting_graph.invoke(initial_state)

@router.post("/", response_model=CreditDecisionOutput, status_code=status.HTTP_201_CREATED)
async def submit_underwriting_request(
    request: UnderwritingRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    client_id: str = Depends(get_client_id)
):
    """
    Submit a list of Open Banking transactions for AI underwriting analysis.
    The LangGraph network processes it, persists it to PostgreSQL, and fires an async webhook with retries.
    """
    try:
        # Offload heavy AI reasoning to an asyncio ThreadPool
        request_dict = request.model_dump()
        final_state = await asyncio.to_thread(execute_langgraph_workflow, request_dict)
        
        decision_data = final_state.get("final_decision")
        if not decision_data:
            raise ValueError(f"LangGraph failed to produce a final decision. Errors: {final_state.get('errors')}")

        final_output = CreditDecisionOutput(**decision_data)

        # Database Persistence
        db_record = CreditDecision(
            client_id=client_id,
            applicant_id=final_output.applicant_id,
            risk_score=final_output.risk_score,
            decision=final_output.decision,
            dti_ratio=final_output.dti_ratio,
            audit_trail=final_output.audit_trail.model_dump(mode='json')
        )
        db.add(db_record)
        db.commit()
        db.refresh(db_record)
        logger.info(f"Database persist successful. DB ID: {db_record.id}")
        
        # Dispatch the async webhook with embedded exponential backoff logic
        if request.webhook_url:
            background_tasks.add_task(
                process_webhook_callback, 
                webhook_url=str(request.webhook_url), 
                payload=final_output.model_dump(mode='json')
            )
            
        return final_output
        
    except Exception as e:
        logger.error(f"Underwriting Error: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during AI processing: {str(e)}"
        )
