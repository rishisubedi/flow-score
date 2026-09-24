# FlowScore API 🌊💳

**An AI-Powered, Open Banking Credit Underwriting Engine for "Thin-File" Customers.**

FlowScore API is a B2B SaaS Risk Engine that leverages Multi-Agent AI to analyze Open Banking transaction data, providing fair, dynamic, and strictly explainable credit risk scores.

## 🇬🇧 Our Mission: Democratizing Credit in the UK

In the UK, millions of people are locked out of the financial system or forced to rely on predatory, high-interest payday loans because they are deemed "thin-file" by traditional credit bureaus (Experian, Equifax, TransUnion). 

These underserved groups primarily include:
* **Immigrants & Expats:** New arrivals to the UK who have no local credit footprint, despite often having strong earning potential and responsible financial habits.
* **Gig-Economy & Freelance Workers:** Uber drivers, Deliveroo riders, and self-employed creators whose income is volatile or irregular. Legacy banks struggle to underwrite these profiles because standard Debt-to-Income (DTI) models expect a fixed monthly salary.
* **Young Adults:** Those entering the financial system for the first time without prior credit cards or mortgages.

### How FlowScore Fixes This
FlowScore bypasses the traditional, outdated credit score. Instead, it ingests 12 months of rich, real-time **Open Banking data** (e.g., via TrueLayer or Plaid) and uses a network of specialized AI agents to evaluate a borrower's *true* cash flow. 

* An **Income Analyst Agent** measures the stability, frequency, and trajectory of gig-economy payouts.
* An **Expense Tracker Agent** isolates strict baseline living costs (rent, utilities, groceries) from discretionary spending.

**FCA Consumer Duty Compliance:**
In the UK financial sector, transparency is legally mandated. FlowScore is built strictly around the **FCA Consumer Duty** rules. Instead of an unexplainable "black-box" AI decision, FlowScore’s Supervisor Agent synthesizes the data and outputs a strict, natural-language **Audit Trail**. This ensures algorithmic transparency, fair value, and guarantees that lenders can clearly explain exactly *why* a decision was made to the consumer.

---

## 🛠 Core Tech Stack
* **Backend:** Python 3.11+, FastAPI
* **AI Orchestration:** LangGraph (Multi-Agent State Management)
* **LLMs:** OpenAI GPT-4o / Claude 3.5 Sonnet
* **Data Validation:** Pydantic (Strict Output Parsing)
* **Database:** PostgreSQL (SQLAlchemy & Alembic)
* **Infrastructure:** Docker & docker-compose (Optimized for GCP Cloud Run)

## 🚀 Getting Started

To run the FlowScore API MVP locally:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/rishisubedi/flow-score.git
   cd flow-score
   ```

2. **Configure the Environment:**
   Copy the example environment file and insert your API keys (e.g., OpenAI).
   ```bash
   cp .env.example .env
   ```

3. **Start the Infrastructure:**
   Use Docker Compose to spin up the FastAPI web server and the local PostgreSQL database simultaneously.
   ```bash
   docker-compose up --build
   ```

4. **Access the API:**
   Once running, navigate to `http://localhost:8080/docs` to interact with the auto-generated Swagger UI documentation.

---

## 📈 Current Project Status (10-Day Sprint)

**Sprint Completion: 80%**
`[████████..]`


* **[x] Day 1:** Core Infrastructure, Dockerization, and FastAPI Setup.
* **[x] Day 2:** PostgreSQL Database, SQLAlchemy ORM, and Strict Pydantic Schemas.
* **[x] Day 3:** Core POST `/v1/underwrite` endpoint, Dependency Injection, and Async Webhooks.
* **[x] Day 4:** LangGraph Foundation & State Definition.
* **[x] Day 5:** Income Analyst Agent Implementation.
* **[x] Day 6:** Expense Tracker Agent Implementation.
* **[x] Day 7:** Supervisor Agent & FCA Explainability Layer.
* **[x] Day 8:** Database Integration & Final Output Formatting.
* **[ ] Day 9:** Edge Cases, Pytest, & Handling LLM Hallucinations.
* **[ ] Day 10:** Final Polish, Demo Prep, & Cloud Run Deployment.

### 🧠 Multi-Agent Architecture (LangGraph)
The AI decision-making pipeline utilizes a highly optimized **Fan-Out / Fan-In** LangGraph architecture:
1. **Ingestion Node:** Parses strict Pydantic schemas and auto-categorizes B2B open banking payloads.
2. **Parallel Fan-Out:** Data is routed simultaneously to the `Income Analyst` and `Expense Tracker` nodes, cutting LLM inference latency in half.
3. **Synchronized Fan-In:** The custom `merge_lists` reducer guarantees that parallel outputs and errors don't overwrite each other in the `AgentState` TypedDict.
4. **Supervisor Node:** Synthesizes the parallel data to generate the final FCA-compliant audit trail and DTI calculation.

### 💼 Enterprise Features Built-In
During the sprint, we injected several commercial improvements to maximize our Total Addressable Market (TAM):
* **O(1) Multi-Tenancy:** Securely support hundreds of B2B lenders on the same PostgreSQL database.
* **Async Webhooks with Exponential Backoff:** Non-blocking callbacks that automatically retry (using `tenacity`) if the client's server goes down, preventing audit-trail data loss.
* **Prompt Injection Protection:** Strict Pydantic RegEx constraints and Payload DoW (Denial of Wallet) capping to prevent malicious actors from hacking the LLM pipeline.
* **Injectable Risk Appetites:** Lenders can dynamically inject their own custom DTI and income thresholds into the API payload.
* **Dual-Layer Audit Trails:** Outputs a dense compliance log for the bank's risk officers, alongside a polite, consumer-facing explanation for their UI.

## 📄 Documentation & Architecture
For a deep dive into the Multi-Agent consensus network and the database schema, please read the [Technical Specification Document (TSD)](TECHNICAL_SPECIFICATION.md).
