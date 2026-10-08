from datetime import datetime, timedelta
from typing import Optional
from fastapi import Security, HTTPException, status, Depends
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.db.database import get_db
from app.db.models import Client
from app.core.config import settings

# --- Cybersecurity & Encryption Configurations ---
# Enterprise standard dictates BCrypt for password/API key hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 Scheme for UI/Dashboard Login (JWT)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

# API Key Header for B2B Machine-to-Machine calls
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# JWT Secret configurations (should be loaded from secure env/KMS in prod)
SECRET_KEY = settings.OPENAI_API_KEY if hasattr(settings, "OPENAI_API_KEY") else "supersafesecretkey"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# --- Hashing Utilities ---
def verify_hash(plain_text: str, hashed_text: str) -> bool:
    """Verifies a plaintext secret against a bcrypt hash."""
    return pwd_context.verify(plain_text, hashed_text)

def get_hash(secret: str) -> str:
    """Generates a bcrypt hash for a secret string."""
    return pwd_context.hash(secret)

# --- JWT Utilities ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Creates a short-lived JSON Web Token for UI dashboard access (RBAC)."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- Dependency Injections ---
def get_current_client(
    api_key: str = Security(api_key_header),
    db: Session = Depends(get_db)
) -> Client:
    """
    M2M API Authentication: Validates the incoming X-API-Key against the securely hashed keys in the database.
    Prevents Timing Attacks by using passlib's secure string comparisons.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key in headers",
        )

    # In a real enterprise system at massive scale, we'd look up by a public Client_ID first,
    # then verify the secret key. Here, we iterate (which is acceptable for MVP, but O(N)).
    # We will assume the API Key has a prefix like "fs_live_CLIENTID_SECRET" to make this O(1).
    
    parts = api_key.split("_")
    if len(parts) >= 4 and parts[0] == "fs":
        client_id_prefix = parts[2]
        client = db.query(Client).filter(Client.client_id == client_id_prefix).first()
        
        if client and verify_hash(api_key, client.api_key_hash):
            return client

    # Fallback to full scan if structure doesn't match (for legacy keys)
    clients = db.query(Client).all()
    for client in clients:
        try:
            if verify_hash(api_key, client.api_key_hash):
                return client
        except Exception:
            pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API Key credentials",
    )
