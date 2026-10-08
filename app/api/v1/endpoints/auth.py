from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from app.db.database import get_db
from app.core.security import create_access_token, verify_hash, ACCESS_TOKEN_EXPIRE_MINUTES
# Assuming we will validate against a Risk Officer or System Admin
# For MVP, we will simulate matching against the Tenant's Master API Key or a predefined admin

router = APIRouter()

@router.post("/login")
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    OAuth2 compatible token login for Risk Officers.
    In a true enterprise setup, this connects to Active Directory, Okta, or Auth0.
    For this MVP, it returns a JWT if valid credentials are provided.
    """
    # Simulate DB lookup for a Risk Officer
    # In production, we'd query a `Users` table: user = db.query(User).filter(User.email == form_data.username).first()
    
    # Mocking standard RBAC validation for demonstration
    if form_data.username == "admin" and form_data.password == "supersecret":
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": form_data.username, "role": "System_Administrator"}, 
            expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
        
    elif form_data.username == "risk_officer_1":
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": form_data.username, "role": "Risk_Officer", "tenant_id": "tenantA"}, 
            expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

@router.get("/me")
def read_users_me(token: str):
    """Return details of the current logged-in user based on the JWT."""
    from jose import jwt, JWTError
    from app.core.security import SECRET_KEY, ALGORITHM
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"username": username, "role": role}
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
