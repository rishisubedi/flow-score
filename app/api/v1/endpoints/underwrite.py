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

# Initialize Redis client for Idempotency
redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

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
        if client.subscription_tier == "ENTERPRISE_BYOK" and client.byok_api_key:
            request_dict["llm_config"] = {
                "provider": client.byok_provider,
                "api_key": decrypt_api_key(client.byok_api_key)
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
        
        # Save Idempotency Key
        if idempotency_key:
            # Expire idempotency key after 24 hours
            redis_client.setex(cache_key, 86400, task.id)
            
        return {"status": "accepted", "job_id": task.id}
        
    except Exception as e:
        logger.error(f"Error dispatching task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue AI processing: {str(e)}"
        )

@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
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
