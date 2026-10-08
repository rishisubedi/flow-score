from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest
import uuid

from app.main import app
from app.db.database import Base, get_db
from app.core.security import get_current_client
from app.db.models import Client, CreditDecision

# 1. In-memory SQLite Database for Testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Mock Authentication for tests
def override_get_current_client():
    db = TestingSessionLocal()
    # Ensure a test client exists
    test_client = db.query(Client).filter(Client.client_id == "test_tenant").first()
    if not test_client:
        test_client = Client(
            client_id="test_tenant",
            api_key_hash="test_tenant:secret",
            subscription_tier="ENTERPRISE_BYOK",
            credits_remaining=100
        )
        db.add(test_client)
        db.commit()
        db.refresh(test_client)
    return test_client

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_client] = override_get_current_client

client = TestClient(app)


# -------------------------------------------------------------------
# ENTERPRISE FEATURE TESTS
# -------------------------------------------------------------------

def test_telemetry_trace_id_middleware():
    """Test that the Trace-ID middleware injects and returns the trace header."""
    response = client.get("/health")
    assert response.status_code == 200
    assert "x-trace-id" in response.headers
    assert len(response.headers["x-trace-id"]) > 10


def test_admin_kms_encryption_on_creation():
    """Test that creating a tenant correctly uses BCrypt for the API Key and Fernet for BYOK key."""
    payload = {
        "client_id": f"enterprise_{uuid.uuid4().hex[:8]}",
        "subscription_tier": "ENTERPRISE_BYOK",
        "byok_provider": "openai",
        "byok_api_key": "sk-super-secret-plaintext-key"
    }
    
    response = client.post("/v1/admin/client/", json=payload)
    assert response.status_code == 200
    assert "raw_api_key" in response.json()
    
    # Verify in database that it's encrypted
    db = TestingSessionLocal()
    db_client = db.query(Client).filter(Client.client_id == payload["client_id"]).first()
    
    assert db_client is not None
    # 1. Check BYOK KMS (Fernet)
    assert db_client.byok_api_key is None # Legacy plaintext field MUST be null
    assert db_client.encrypted_byok_key is not None
    assert db_client.encrypted_byok_key != "sk-super-secret-plaintext-key" # Must be encrypted
    assert db_client.encrypted_byok_key.startswith("gAAAAA") # Fernet token signature
    
    # 2. Check API Key Hashing (Bcrypt)
    from app.core.security import verify_hash
    raw_api_key = response.json()["raw_api_key"]
    assert verify_hash(raw_api_key, db_client.api_key_hash)


def test_auth_jwt_login():
    """Test that Risk Officers can securely log in via OAuth2 to receive a JWT Token."""
    # Standard OAuth2 Form Data
    login_data = {
        "username": "risk_officer_1",
        "password": "some_password"
    }
    response = client.post("/v1/auth/login", data=login_data)
    
    assert response.status_code == 200
    token_data = response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    
    # Verify we can use the token
    token = token_data["access_token"]
    me_response = client.get(f"/v1/auth/me?token={token}")
    assert me_response.status_code == 200
    assert me_response.json()["username"] == "risk_officer_1"
    assert me_response.json()["role"] == "Risk_Officer"


def test_open_banking_webhook_hmac_ingestion():
    """Test the asynchronous Open Banking webhook ingestion endpoint (FR1)."""
    payload = {
        "webhook_type": "SYNC_SUCCESS",
        "provider": "TRUELAYER",
        "applicant_id": "app_999",
        "raw_data_uri": "https://api.truelayer.com/v1/data",
        "hmac_signature": "sha256=mocksignature123"
    }
    response = client.post("/v1/underwrite/webhook/open-banking", json=payload)
    assert response.status_code == 202
    assert response.json()["status"] == "accepted"


def test_human_override_soc2_compliance():
    """Test that Risk Officers can manually override AI decisions and generate an immutable audit log (FR2)."""
    db = TestingSessionLocal()
    
    # 1. Seed a fake AI decision
    job_id = f"job_{uuid.uuid4().hex[:8]}"
    mock_decision = CreditDecision(
        job_id=job_id,
        client_id="test_tenant",
        applicant_id="app_123",
        risk_score=400,
        decision="REJECTED",
        dti_ratio=0.85,
        audit_trail={"msg": "mock AI rejection"}
    )
    db.add(mock_decision)
    db.commit()
    
    # 2. Submit Risk Officer Override
    override_payload = {
        "officer_sso_id": "okta_user_456",
        "new_decision": "APPROVED",
        "justification_notes": "Applicant provided physical proof of additional offshore income. Overriding AI."
    }
    response = client.post(f"/v1/underwrite/override/{job_id}", json=override_payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
    # 3. Verify the core decision changed
    updated_decision = db.query(CreditDecision).filter(CreditDecision.job_id == job_id).first()
    assert updated_decision.decision == "APPROVED"
    
    # 4. Verify the immutable SOC2 log exists
    from app.db.models import HumanOverride
    audit_log = db.query(HumanOverride).filter(HumanOverride.job_id == job_id).first()
    assert audit_log is not None
    assert audit_log.officer_sso_id == "okta_user_456"
    assert audit_log.previous_decision == "REJECTED"
    assert audit_log.new_decision == "APPROVED"
    assert audit_log.justification_notes.startswith("Applicant provided physical")
