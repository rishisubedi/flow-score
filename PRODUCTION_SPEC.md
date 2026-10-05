# FlowScore v2.0: Production-Level Software Specification

This document outlines the architectural extensions, functional requirements, and file specifications required to transition FlowScore from an MVP to a Tier-1 Enterprise B2B SaaS platform capable of processing high-volume banking data securely.

---

## 1. Architectural Extensions (The Path to Production)

To serve enterprise clients (Tier-1 Banks, Credit Unions), the infrastructure must be hardened across four pillars: Security, Observability, Scalability, and Orchestration.

### 1.1 Security & Compliance Extensions
* **API Gateway & WAF:** Implement Kong or AWS API Gateway to handle rate-limiting, IP whitelisting, and Web Application Firewall (WAF) protection against DDoS and prompt-injection scraping.
* **Identity & Access Management (IAM):** Delegate authentication to an OIDC provider (Auth0 or Okta) implementing strictly scoped JWTs. 
* **Key Management Service (KMS):** Replace plaintext/hashed BYOK (Bring Your Own Key) storage with HashiCorp Vault or AWS KMS. API keys must be encrypted at rest and decrypted dynamically in memory only during LangGraph execution.
* **SOC2 & GDPR Tooling:** Implement hard-delete workflows (Right to be Forgotten) and immutable access logs (recording exactly which human/agent accessed which PII).

### 1.2 Observability & Telemetry Extensions
* **Distributed Tracing:** Implement OpenTelemetry. Every request gets a `TraceID` injected at the API Gateway, which propagates through FastAPI -> Redis -> Celery -> LangGraph.
* **APM & Metrics:** Integrate Datadog or Prometheus/Grafana to monitor:
  * LLM Token Usage per Tenant (for accurate billing).
  * LangGraph Node Latency (identifying if the `Income Analyst` is slower than the `Expense Tracker`).
  * Safety-Net Override Trigger Rates (monitoring LLM hallucination frequencies).

### 1.3 Scalability & Infrastructure Extensions
* **Kubernetes (K8s):** Migrate from `docker-compose` to KEDA (Kubernetes Event-driven Autoscaling). KEDA will automatically spin up hundreds of Celery Worker pods when the Redis queue backs up, and scale to zero during off-hours.
* **Managed Data Tier:** Migrate local PostgreSQL and Redis to managed, highly available clusters (e.g., AWS RDS Multi-AZ, AWS ElastiCache).

---

## 2. Functional Requirements (FRs)

### FR1: Open Banking Webhook Ingestion
The system must expose a secure endpoint to receive asynchronous push notifications from Plaid/TrueLayer when a user's bank data has finished syncing, automatically triggering the underwriting pipeline without manual API polling.

### FR2: Human-in-the-Loop (HITL) Overrides
Risk Officers must have a UI to view the FCA Audit Trail and manually override an AI decision (e.g., changing `REJECTED` to `APPROVED`). The system must require a justification note and cryptographically log the human override.

### FR3: Real-Time Execution Streaming (SSE)
The API must support Server-Sent Events (SSE). Instead of the client polling `GET /status/{job_id}`, the server must stream LangGraph execution states in real-time (e.g., `["STATUS: INGESTING", "STATUS: ANALYZING_INCOME", "STATUS: GENERATING_AUDIT"]`).

### FR4: Dynamic Rule Injection
Enterprise tenants must be able to upload custom YAML rule files (e.g., "Reject instantly if Gambling expenses > 15% of income") that the LangGraph Supervisor Agent dynamically reads and strictly enforces prior to LLM evaluation.

---

## 3. Non-Functional Requirements (NFRs)

* **NFR1 - Latency (SLA):** The asynchronous underwriting pipeline must achieve a P95 latency of < 15 seconds from data ingestion to final decision. HTTP API endpoints must return a `202 Accepted` within 200ms.
* **NFR2 - Availability:** The system must achieve 99.99% uptime, utilizing multi-region failover.
* **NFR3 - Data Isolation:** Strict logical isolation at the database level using Row-Level Security (RLS) in PostgreSQL, ensuring Tenant A can never query Tenant B's applicants.
* **NFR4 - Determinism:** Given the same set of transactions and the same lender policy, the LLM pipeline must return the exact same mathematical DTI ratio and decision 100% of the time (Temperature = 0.0, deterministic seeding).

---

## 4. File & Schema Specification Updates

To support these extensions, the database models (`app/db/models.py`) and schemas (`app/models/schemas.py`) must be extended.

### 4.1 Extended Database Schema (PostgreSQL)
```sql
-- Enhancing the Tenant table for KMS and RBAC
ALTER TABLE tenants 
ADD COLUMN encrypted_byok_key BYTEA,
ADD COLUMN kms_key_id VARCHAR(255),
ADD COLUMN webhook_secret VARCHAR(255);

-- New Table: Immutable Audit Logs (SOC2 Compliance)
CREATE TABLE human_overrides (
    override_id UUID PRIMARY KEY,
    job_id UUID REFERENCES credit_decisions(job_id),
    officer_sso_id VARCHAR(255) NOT NULL, -- Okta/Auth0 ID of the human
    previous_decision VARCHAR(50),
    new_decision VARCHAR(50),
    justification_notes TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.2 Webhook Payload Specification (`app/models/schemas.py`)
```python
class OpenBankingWebhook(BaseModel):
    webhook_type: Literal["SYNC_SUCCESS", "SYNC_FAILED"]
    provider: Literal["PLAID", "TRUELAYER"]
    applicant_id: str
    raw_data_uri: HttpUrl
    hmac_signature: str = Field(..., description="For verifying the payload originates from the provider.")
```

### 4.3 Streaming Output Specification (SSE)
```json
// Example of the JSON lines streamed to the client during processing
{"event": "step", "node": "Income Analyst", "status": "processing", "timestamp": "2026-10-05T10:00:01Z"}
{"event": "step", "node": "Income Analyst", "status": "complete", "result": "Income Volatility: 0.12", "timestamp": "2026-10-05T10:00:04Z"}
{"event": "final_decision", "decision": "APPROVED", "risk_score": 840}
```

---

## 5. Deployment & CI/CD Strategy

* **Containerization:** All services (FastAPI, Celery, Redis) remain Dockerized, but are deployed via Helm charts.
* **CI/CD (GitHub Actions):**
  1. **PR Stage:** Triggers `flake8`, `mypy`, and `pytest` (with mocked LLM calls).
  2. **Merge Stage:** Builds Docker images and pushes to AWS ECR.
  3. **Deploy Stage:** ArgoCD detects the new image tag and rolls out a Canary deployment (shifting 10% of traffic to the new version to monitor hallucination rates before full release).
