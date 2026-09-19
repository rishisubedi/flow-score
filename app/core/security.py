from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
import secrets
from app.core.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

def get_client_id(api_key: str = Security(api_key_header)) -> str:
    """
    Validates the API key and returns the associated client_id (tenant).
    Optimized for MVP: Expects format 'client_id:secret_key' or uses default.
    """
    # Allow client-specific keys formatted as "client_id:secret_token"
    if ":" in api_key:
        client_id, secret = api_key.split(":", 1)
        # TODO: In production, verify the secret hash against the DB/Redis here
        return client_id
    
    # Fallback for the master API Key
    if secrets.compare_digest(api_key, settings.API_KEY):
        return "default_tenant"
        
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API Key",
    )
