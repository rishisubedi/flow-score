import asyncio
from celery import Celery
from app.core.config import settings
from app.agents.graph import underwriting_graph
import httpx
import logging

logger = logging.getLogger(__name__)

celery_app = Celery(
    "flowscore_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

def deliver_webhook_sync(webhook_url: str, payload: dict):
    try:
        response = httpx.post(webhook_url, json=payload, timeout=10.0)
        response.raise_for_status()
        logger.info(f"Webhook successfully delivered to {webhook_url}")
    except Exception as exc:
        logger.error(f"Webhook delivery failed for {webhook_url}: {exc}")

@celery_app.task(name="process_underwriting")
def process_underwriting_task(request_dict: dict, client_id: str, webhook_url: str = None) -> dict:
    """
    Background worker task to execute the AI LangGraph pipeline.
    """
    initial_state = {
        "applicant_id": request_dict.get("applicant_id"),
        "transactions": request_dict.get("transactions", []),
        "policy": request_dict.get("policy", {}),
        "categorized_transactions": [],
        "income_metrics": {},
        "expense_metrics": {},
        "final_decision": None,
        "errors": [],
        "llm_config": request_dict.get("llm_config", {})
    }
    
    # Run the graph synchronously in the Celery worker
    final_state = underwriting_graph.invoke(initial_state)
    decision_data = final_state.get("final_decision")
    
    if not decision_data:
        raise ValueError(f"LangGraph failed to produce a decision. Errors: {final_state.get('errors')}")

    # Note: In a true production app, the Celery worker would open a DB session and persist this to PostgreSQL here.
    # For simplicity, we'll return it so the status endpoint can retrieve it from the Redis Result Backend.

    # Deliver webhook if requested
    if webhook_url:
        deliver_webhook_sync(webhook_url, decision_data)

    return decision_data
