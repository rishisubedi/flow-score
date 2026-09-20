from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
import httpx

from app.db.database import get_db
from app.core.security import get_client_id
from app.models.schemas import UnderwritingRequest, CreditDecisionOutput, FCAAuditTrail, InternalComplianceLog

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
        except httpx.RequestError as exc:
            # In a production environment, you would log this to Sentry or Datadog
            print(f"Webhook delivery failed for {exc.request.url!r}. Reason: {exc}")

@router.post("/", response_model=CreditDecisionOutput, status_code=status.HTTP_202_ACCEPTED)
async def submit_underwriting_request(
    request: UnderwritingRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    client_id: str = Depends(get_client_id)
):
    """
    Submit a list of Open Banking transactions for AI underwriting analysis.
    """
    try:
        # [PLACEHOLDER] Day 4-7: Trigger the LangGraph Agent Workflow here.
        # For Day 3, we mock the response to solidify the API contract.
        
        mock_response = CreditDecisionOutput(
            applicant_id=request.applicant_id,
            risk_score=750,
            decision="APPROVED",
            dti_ratio=0.35,
            audit_trail=FCAAuditTrail(
                internal_compliance_log=InternalComplianceLog(
                    income_volatility_score=0.15,
                    expense_baseline=800.0,
                    affordability_logic="DTI calculated at 35% based on 12-month average."
                ),
                customer_facing_explanation="Based on your stable income trajectory, we are happy to approve you.",
                consumer_duty_statement="This decision was made transparently and offers fair value to the consumer."
            )
        )

        # TODO: Save mock_response to Database (Day 8)
        
        # Dispatch the async webhook if the client provided one
        if request.webhook_url:
            background_tasks.add_task(
                process_webhook_callback, 
                webhook_url=request.webhook_url, 
                payload=mock_response.model_dump(mode='json')
            )
            
        return mock_response
        
    except Exception as e:
        # Catch-all to prevent unhandled exceptions from crashing the server
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during underwriting processing: {str(e)}"
        )
