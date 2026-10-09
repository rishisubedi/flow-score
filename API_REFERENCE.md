# FlowScore API Reference (v1)

Welcome to the comprehensive API documentation for **FlowScore**, the Open Banking underwriting engine. 

FlowScore operates entirely over HTTPS. All payloads are JSON-encoded. The API is divided into two primary scopes: **B2B Machine-to-Machine (M2M)** endpoints for automated loan processing, and **OAuth2 JWT** endpoints for Human Risk Officers.

---

## 🔐 Authentication

FlowScore utilizes a dual-layer authentication model to satisfy Enterprise SOC2 requirements.

### 1. B2B API Keys (M2M)
For automated services communicating with FlowScore (e.g., your FinTech app submitting a loan application), you must pass your API key via the `X-API-Key` HTTP header. 
* **Note:** API Keys are generated once during Tenant Creation. They are securely pre-hashed using SHA-256 and BCrypt before being stored in our PostgreSQL database. You must store the raw key securely upon generation.

```http
X-API-Key: fs_live_tenantA_8xK9pL2...
```

### 2. OAuth2 Bearer Tokens (Human UI)
For Risk Officers and System Administrators logging into a dashboard to perform manual overrides, FlowScore utilizes standard OAuth2 JSON Web Tokens (JWT).
Tokens must be passed via the `Authorization` header.

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 🏢 Tenant & Admin Management

### Create a New Tenant (B2B Client)
Creates a new lender profile on the platform and generates a mathematically secure API Key.

* **URL:** `POST /v1/admin/client/`
* **Auth Required:** System Admin (Not public)

**Request Body:**
```json
{
  "client_id": "tenant_monzo_uk",
  "subscription_tier": "ENTERPRISE_BYOK",
  "byok_provider": "openai",
  "byok_api_key": "sk-your-openai-key-here"
}
```
*(Note: `byok_api_key` is immediately AES-256 KMS encrypted via Fernet in the database and never stored in plaintext).*

**Response (200 OK):**
```json
{
  "message": "Client created. STORE THIS API KEY NOW. IT WILL NEVER BE SHOWN AGAIN.",
  "client_id": "tenant_monzo_uk",
  "raw_api_key": "fs_live_tenant_monzo_uk_aBCdEfGhIjKlMnOpQrStUvWxYz123456"
}
```

---

## 🧑‍💻 Human Access (OAuth2)

### Risk Officer Login
Authenticates a human operator and returns a short-lived JWT.

* **URL:** `POST /v1/auth/login`
* **Content-Type:** `application/x-www-form-urlencoded`

**Request Body:**
```text
username=risk_officer_1&password=your_secure_password
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUz...",
  "token_type": "bearer"
}
```

---

## 🤖 Core Underwriting Engine

### Submit Underwriting Job
Ingests 12 months of Open Banking data and dispatches the LangGraph AI multi-agent workflow via a Celery background worker.

* **URL:** `POST /v1/underwrite/`
* **Auth Required:** `X-API-Key` Header
* **Idempotency:** Include an `Idempotency-Key` header (UUID) to safely retry network failures without being double-billed.

**Request Headers:**
```http
X-API-Key: fs_live_tenant_monzo_uk_aBCd...
Idempotency-Key: 123e4567-e89b-12d3-a456-426614174000
```

**Request Body (`UnderwritingRequest`):**
```json
{
  "applicant_id": "cust_9942",
  "webhook_url": "https://your-fintech-app.com/webhooks/flowscore",
  "policy": {
    "max_dti_allowed": 0.45,
    "min_monthly_income": 1200.0,
    "strict_fca_mode": true
  },
  "custom_rules": "Reject instantly if gambling exceeds 15% of total outflow.",
  "transactions": [
    {
      "transaction_id": "tx_1",
      "amount": 450.0,
      "category": "INCOME",
      "description": "DELIVEROO PAYOUT",
      "date": "2023-10-01"
    }
  ]
}
```

**Response (202 Accepted):**
```json
{
  "status": "accepted",
  "job_id": "8a7b6c5d-4e3f-2a1b-9c8d-7e6f5a4b3c2d"
}
```

### Poll Job Status
If you did not provide a `webhook_url` in the initial payload, you can poll this endpoint to retrieve the AI decision.

* **URL:** `GET /v1/underwrite/status/{job_id}`
* **Auth Required:** `X-API-Key` Header

**Response (200 OK - COMPLETED):**
```json
{
  "job_id": "8a7b6c5d-...",
  "status": "COMPLETED",
  "result": {
    "decision": "APPROVED",
    "risk_score": 750,
    "dti_ratio": 0.32,
    "audit_trail": {
      "customer_facing_explanation": "Your application was approved because your verified freelance income comfortably covers your baseline living expenses.",
      "internal_compliance_log": {
         "income_volatility_score": 0.8,
         "affordability_logic": "Consistent delivery gig payouts recognized."
      }
    }
  }
}
```

---

## 📡 Webhook Ingestion (Async Open Banking)

### Ingest Provider Webhook (Plaid / TrueLayer)
Allows direct ingestion of bank syncing completion events from third-party Open Banking providers.

* **URL:** `POST /v1/underwrite/webhook/open-banking`
* **Auth Required:** None (Relies on HMAC Signature validation)

**Request Body:**
```json
{
  "webhook_type": "SYNC_SUCCESS",
  "provider": "TRUELAYER",
  "applicant_id": "cust_9942",
  "raw_data_uri": "https://api.truelayer.com/v1/data",
  "hmac_signature": "sha256=a1b2c3d4..."
}
```

---

## ⚖️ SOC2 Compliance

### Human-in-the-Loop Override
Allows an authenticated Risk Officer to manually override the AI's credit decision. Generates an immutable SQL log to satisfy SOC2 and FCA audit requirements.

* **URL:** `POST /v1/underwrite/override/{job_id}`
* **Auth Required:** `Authorization: Bearer <JWT>` (Requires Risk_Officer role)

**Request Body:**
```json
{
  "officer_sso_id": "okta_ro_442",
  "new_decision": "APPROVED",
  "justification_notes": "Applicant provided physical proof of additional offshore income via email. Overriding AI rejection."
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Decision overridden. Immutable SOC2 audit log created."
}
```

---
*FlowScore API v1.0. Built for zero-crash resilience and FCA Consumer Duty alignment.*
