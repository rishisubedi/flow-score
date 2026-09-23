from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
import httpx
import asyncio
import logging

from app.db.database import get_db
from app.core.security import get_client_id
from app.models.schemas import UnderwritingRequest, CreditDecisionOutput
from app.db.models import CreditDecision
from app.agents.graph import underwriting_graph

logger = logging.getLogger(__name__)
router = APIRouter()

async def process_webhook_callback(webhook_url: str, payload: dict):
    """
    Background task to send webhook asynchronously to the B2B client.
    Ensures the main API thread isn't blocked by slow network requests.
    """
    async with httpx.AsyncClient() as client:
        try:
            # Send the payload to the client's webhook URL
            await client.post(str(webhook_url), json=payload, timeout=10.0)
            logger.info(f"Webhook successfully delivered to {webhook_url}")
        except httpx.RequestError as exc:
            # In a production environment, log this to Sentry/Datadog
            logger.error(f"Webhook delivery failed for {exc.request.url!r}. Reason: {exc}")

def execute_langgraph_workflow(request_data: dict) -> dict:
    """
    Executes the compiled LangGraph workflow synchronously.
    We wrap this in a threadpool downstream to prevent blocking the async event loop.
    """
    # Initialize the AgentState payload
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
    
    # Trigger the multi-agent AI pipeline
    final_state = underwriting_graph.invoke(initial_state)
    return final_state

@router.post("/", response_model=CreditDecisionOutput, status_code=status.HTTP_201_CREATED)
async def submit_underwriting_request(
    request: UnderwritingRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    client_id: str = Depends(get_client_id)
):
    """
    Submit a list of Open Banking transactions for AI underwriting analysis.
    The LangGraph network processes it, persists it to PostgreSQL, and fires an async webhook.
    """
    try:
        # 1. Offload the heavy AI reasoning to an asyncio ThreadPool
        # This guarantees high-concurrency for our FastAPI web server
        request_dict = request.model_dump()
        final_state = await asyncio.to_thread(execute_langgraph_workflow, request_dict)
        
        # 2. Extract the structured LLM output
        decision_data = final_state.get("final_decision")
        if not decision_data:
            raise ValueError(f"LangGraph failed to produce a final decision. Errors: {final_state.get('errors')}")

        # Ensure the output maps perfectly to our Pydantic schema
        final_output = CreditDecisionOutput(**decision_data)

        # 3. Database Persistence (Day 8 Integration)
        # Store the decision in PostgreSQL tied securely to the specific client_id tenant
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
        
        # 4. Dispatch the async webhook if the client provided one
        if request.webhook_url:
            background_tasks.add_task(
                process_webhook_callback, 
                webhook_url=request.webhook_url, 
                payload=final_output.model_dump(mode='json')
            )
            
        return final_output
        
    except Exception as e:
        logger.error(f"Underwriting Error: {str(e)}")
        # Rollback the DB session in case of partial write failure
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during AI processing: {str(e)}"
        )
