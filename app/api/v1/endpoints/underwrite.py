from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
import httpx
import asyncio
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.db.database import get_db
from app.core.billing import check_and_deduct_credits
from app.db.models import Client, CreditDecision
from app.models.schemas import UnderwritingRequest, CreditDecisionOutput
from app.agents.graph import underwriting_graph

logger = logging.getLogger(__name__)
router = APIRouter()

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException))
)
async def deliver_webhook_with_retry(webhook_url: str, payload: dict):
    async with httpx.AsyncClient() as client:
        response = await client.post(str(webhook_url), json=payload, timeout=10.0)
        response.raise_for_status()
        logger.info(f"Webhook successfully delivered to {webhook_url}")

async def process_webhook_callback(webhook_url: str, payload: dict):
    try:
        await deliver_webhook_with_retry(webhook_url, payload)
    except Exception as exc:
        logger.error(f"Permanent webhook failure for {webhook_url} after 5 retries. Reason: {exc}")

def execute_langgraph_workflow(request_data: dict) -> dict:
    initial_state = {
        "applicant_id": request_data.get("applicant_id"),
        "transactions": request_data.get("transactions", []),
        "policy": request_data.get("policy", {}),
        "categorized_transactions": [],
        "income_metrics": {},
        "expense_metrics": {},
        "final_decision": None,
        "errors": [],
        "llm_config": request_data.get("llm_config", {})
    }
    return underwriting_graph.invoke(initial_state)

@router.post("/", response_model=CreditDecisionOutput, status_code=status.HTTP_201_CREATED)
async def submit_underwriting_request(
    request: UnderwritingRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    client: Client = Depends(check_and_deduct_credits)
):
    try:
        request_dict = request.model_dump()
        
        # Inject Multi-Tenant BYOK Configuration
        if client.subscription_tier == "ENTERPRISE_BYOK" and client.byok_api_key:
            request_dict["llm_config"] = {
                "provider": client.byok_provider,
                "api_key": client.byok_api_key
            }
        else:
            # Fallback to the platform's Master API Key
            from app.core.config import settings
            request_dict["llm_config"] = {
                "provider": "gemini",
                "api_key": settings.OPENAI_API_KEY
            }

        # Offload heavy AI reasoning to an asyncio ThreadPool
        final_state = await asyncio.to_thread(execute_langgraph_workflow, request_dict)
        
        decision_data = final_state.get("final_decision")
        if not decision_data:
            raise ValueError(f"LangGraph failed to produce a final decision. Errors: {final_state.get('errors')}")

        final_output = CreditDecisionOutput(**decision_data)

        # Database Persistence
        db_record = CreditDecision(
            client_id=client.client_id,
            applicant_id=final_output.applicant_id,
            risk_score=final_output.risk_score,
            decision=final_output.decision,
            dti_ratio=final_output.dti_ratio,
            audit_trail=final_output.model_dump(mode='json').get('audit_trail')
        )
        db.add(db_record)
        db.commit()
        db.refresh(db_record)
        
        # Dispatch the async webhook
        if request.webhook_url:
            background_tasks.add_task(
                process_webhook_callback, 
                webhook_url=str(request.webhook_url), 
                payload=final_output.model_dump(mode='json')
            )
            
        return final_output
        
    except Exception as e:
        import traceback
        logger.error(f"Underwriting Error: {str(e)}")
        logger.error(traceback.format_exc())
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during AI processing: {str(e)}"
        )
