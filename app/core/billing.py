from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.db.models import Client
from app.db.database import get_db
from app.core.security import get_current_client

def check_and_deduct_credits(
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db)
) -> Client:
    """
    Billing Middleware: Ensures the client has enough credits to execute an API call.
    Deducts 1 credit if permitted.
    """
    if client.subscription_tier != "ENTERPRISE_BYOK":
        if client.credits_remaining <= 0:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Insufficient API credits. Please upgrade your subscription or purchase more credits."
            )
        # Deduct a credit
        client.credits_remaining -= 1
        db.commit()
        db.refresh(client)
        
    return client
