import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.db.database import get_db
from app.db.models import Client
from app.core.crypto import encrypt_api_key
from app.core.security import get_hash

router = APIRouter()

class ClientCreate(BaseModel):
    client_id: str
    subscription_tier: str = "PAYG"
    credits_remaining: int = 10
    byok_provider: Optional[str] = None
    byok_api_key: Optional[str] = None

class ClientUpdate(BaseModel):
    subscription_tier: Optional[str] = None
    credits_remaining: Optional[int] = None
    byok_provider: Optional[str] = None
    byok_api_key: Optional[str] = None

@router.post("/", response_model=dict)
def create_client(client: ClientCreate, db: Session = Depends(get_db)):
    db_client = db.query(Client).filter(Client.client_id == client.client_id).first()
    if db_client:
        raise HTTPException(status_code=400, detail="Client already registered")
        
    client_dict = client.model_dump()
    raw_key = client_dict.pop("byok_api_key", None)
    if raw_key:
        client_dict["encrypted_byok_key"] = encrypt_api_key(raw_key)
        
    # Generate secure Enterprise API Key (returned once, stored as bcrypt hash)
    raw_api_key = f"fs_live_{client.client_id}_{secrets.token_urlsafe(32)}"
    client_dict["api_key_hash"] = get_hash(raw_api_key)
        
    new_client = Client(**client_dict)
    db.add(new_client)
    db.commit()
    db.refresh(new_client)
    
    return {
        "message": "Client created. STORE THIS API KEY NOW. IT WILL NEVER BE SHOWN AGAIN.",
        "client_id": new_client.client_id,
        "raw_api_key": raw_api_key
    }

@router.put("/{client_id}", response_model=dict)
def update_client(client_id: str, update_data: ClientUpdate, db: Session = Depends(get_db)):
    db_client = db.query(Client).filter(Client.client_id == client_id).first()
    if not db_client:
        raise HTTPException(status_code=404, detail="Client not found")
        
    for key, value in update_data.model_dump(exclude_unset=True).items():
        if key == "byok_api_key" and value:
            setattr(db_client, "encrypted_byok_key", encrypt_api_key(value))
        else:
            setattr(db_client, key, value)
        
    db.commit()
    return {"message": "Client updated"}

@router.get("/{client_id}", response_model=dict)
def get_client(client_id: str, db: Session = Depends(get_db)):
    db_client = db.query(Client).filter(Client.client_id == client_id).first()
    if not db_client:
        raise HTTPException(status_code=404, detail="Client not found")
        
    return {
        "client_id": db_client.client_id,
        "subscription_tier": db_client.subscription_tier,
        "credits_remaining": db_client.credits_remaining,
        "byok_provider": db_client.byok_provider
    }
