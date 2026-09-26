from fastapi import Security, HTTPException, status, Depends
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Client

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

def get_current_client(
    api_key: str = Security(api_key_header),
    db: Session = Depends(get_db)
) -> Client:
    """
    Validates the API key against the database and returns the Client object.
    """
    client = db.query(Client).filter(Client.api_key_hash == api_key).first()
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
        )
        
    return client
