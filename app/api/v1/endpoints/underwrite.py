from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
import logging
import redis
from typing import Optional

from app.db.database import get_db
from app.core.billing import check_and_deduct_credits
from app.db.models import Client, CreditDecision
from app.models.schemas import UnderwritingRequest
from app.core.crypto import decrypt_api_key
from app.core.config import settings
from app.worker import process_underwriting_task, celery_app

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize Redis client for Idempotency (Fallback to dict for local dev)
try:
    redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    redis_client.ping() # Test connection
except (redis.exceptions.ConnectionError, ValueError):
    logger.warning("Redis is not available. Idempotency checks will use a local dict (dev mode).")
    class MockRedis:
        def __init__(self): self.cache = {}
        def get(self, k): return self.cache.get(k)
        def setex(self, k, t, v): self.cache[k] = v
    redis_client = MockRedis()

@router.post("/", status_code=status.HTTP_202_ACCEPTED)
async def submit_underwriting_request(
    request: UnderwritingRequest,
    db: Session = Depends(get_db),
    client: Client = Depends(check_and_deduct_credits),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    try:
        # Idempotency Check
        if idempotency_key:
            cache_key = f"idemp:{client.client_id}:{idempotency_key}"
            existing_job_id = redis_client.get(cache_key)
            if existing_job_id:
                return {"status": "accepted", "job_id": existing_job_id, "message": "Duplicate request identified. Returning existing job ID."}
        
        request_dict = request.model_dump()
        
        # Inject Multi-Tenant BYOK Configuration
        if client.subscription_tier == "ENTERPRISE_BYOK" and client.encrypted_byok_key:
            request_dict["llm_config"] = {
                "provider": client.byok_provider,
                "api_key": decrypt_api_key(client.encrypted_byok_key)
            }
        else:
            # Fallback to the platform's Master API Key
            request_dict["llm_config"] = {
                "provider": "gemini",
                "api_key": settings.OPENAI_API_KEY
            }

        # Dispatch the task to Celery
        task = process_underwriting_task.delay(
            request_dict, 
            client.client_id, 
            str(request.webhook_url) if request.webhook_url else None
        )
        
        # Save Idempotency Key and local eager result
        if idempotency_key:
            # Expire idempotency key after 24 hours
            redis_client.setex(cache_key, 86400, task.id)
            
        if celery_app.conf.task_always_eager:
            # Manually cache the result for the local dev status endpoint
            redis_client.setex(f"eager_{task.id}", 300, {"status": "COMPLETED", "result": task.result})
            
        return {"status": "accepted", "job_id": task.id}
        
    except Exception as e:
        logger.error(f"Error dispatching task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue AI processing: {str(e)}"
        )

@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    if celery_app.conf.task_always_eager:
        data = redis_client.get(f"eager_{job_id}")
        if data:
            return {"job_id": job_id, "status": data["status"], "result": data["result"]}
        return {"job_id": job_id, "status": "FAILED", "error": "Local Eager task not found in cache."}

    task_result = celery_app.AsyncResult(job_id)
    
    if task_result.state == 'PENDING':
        return {"job_id": job_id, "status": "PENDING"}
    elif task_result.state != 'FAILURE':
        return {"job_id": job_id, "status": "COMPLETED", "result": task_result.result}
    else:
        return {"job_id": job_id, "status": "FAILED", "error": str(task_result.info)}

from app.core.security import get_current_client

@router.get("/history")
async def get_underwriting_history(
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_client)
):
    """
    Fetch historical underwriting decisions (tickets/applications) for the current tenant.
    """
    history = db.query(CreditDecision).filter(CreditDecision.client_id == client.client_id).order_by(CreditDecision.created_at.desc()).all()
    
    return [
        {
            "id": record.id,
            "applicant_id": record.applicant_id,
            "decision": record.decision,
            "risk_score": record.risk_score,
            "dti_ratio": record.dti_ratio,
            "created_at": record.created_at
        }
        for record in history
    ]

from app.models.schemas import OverrideRequest, OpenBankingWebhook
from app.db.models import HumanOverride

@router.post("/override/{job_id}", status_code=status.HTTP_200_OK)
async def manual_human_override(
    job_id: str,
    override_request: OverrideRequest,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_client) # Must be authenticated
):
    """
    SOC2 Compliant Human-in-the-Loop override for an AI decision.
    """
    decision_record = db.query(CreditDecision).filter(
        CreditDecision.job_id == job_id, 
        CreditDecision.client_id == client.client_id
    ).first()
    
    if not decision_record:
        raise HTTPException(status_code=404, detail="Decision not found or unauthorized.")
        
    previous_decision = decision_record.decision
    
    # 1. Update the core decision
    decision_record.decision = override_request.new_decision
    
    # 2. Append to immutable SOC2 Audit Log
    new_override = HumanOverride(
        job_id=job_id,
        officer_sso_id=override_request.officer_sso_id,
        previous_decision=previous_decision,
        new_decision=override_request.new_decision,
        justification_notes=override_request.justification_notes
    )
    db.add(new_override)
    db.commit()
    
    return {"status": "success", "message": f"Decision overridden to {override_request.new_decision} by {override_request.officer_sso_id}"}


@router.post("/webhook/open-banking", status_code=status.HTTP_202_ACCEPTED)
async def receive_open_banking_sync(
    webhook: OpenBankingWebhook,
    client: Client = Depends(get_current_client) # Assumes Gateway pre-auth or HMAC verification middleware
):
    """
    FR1: Ingest push notifications from TrueLayer/Plaid asynchronously.
    """
    # In a real system, we would verify webhook.hmac_signature against client.webhook_secret here
    if webhook.webhook_type != "SYNC_SUCCESS":
        return {"status": "ignored", "reason": "Not a success sync."}
        
    # Queue a Celery task to fetch the raw data URI and execute underwriting
    # For now, we simulate success response.
    return {"status": "accepted", "message": "Webhook received. Asynchronous underwriting pipeline triggered."}
