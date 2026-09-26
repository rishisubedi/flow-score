import streamlit as st
import requests
import json
import time
import uuid

API_URL = "http://localhost:8080/v1/underwrite/"
ADMIN_URL = "http://localhost:8080/v1/admin/client/"

st.set_page_config(page_title="FlowScore AI Dashboard", page_icon="📈", layout="wide")

st.title("📈 FlowScore B2B SaaS Platform")
st.markdown("Multi-Tenant LLM Underwriting Engine with BYOK Architecture & Metered Billing.")

# Initialize session state for tenant auth
if "x_api_key" not in st.session_state:
    st.session_state.x_api_key = "demo_bank:secret123"

tab1, tab2 = st.tabs(["🚀 Underwriting Engine", "⚙️ Tenant Admin & Billing"])

with tab2:
    st.header("SaaS Tenant Configuration")
    st.markdown("Configure your B2B account, purchase API credits, or set up Bring-Your-Own-Key (BYOK).")
    
    col_admin1, col_admin2 = st.columns(2)
    
    with col_admin1:
        st.subheader("1. Register / Manage Tenant")
        client_id = st.text_input("Tenant ID (e.g. 'monzo', 'revolut')", value="demo_bank")
        api_secret = st.text_input("API Secret Token", type="password", value="secret123")
        
        plan = st.selectbox("Subscription Tier", ["PAYG (Managed LLM)", "ENTERPRISE_BYOK"])
        
        byok_provider = None
        byok_key = None
        if plan == "ENTERPRISE_BYOK":
            st.info("Enterprise BYOK allows you to bypass our rate limits using your own LLM API key. FlowScore will route traffic directly to your provider.")
            byok_provider = st.selectbox("LLM Provider", ["gemini", "openai"])
            byok_key = st.text_input("Your LLM API Key", type="password")
            
        if st.button("Save Tenant Configuration"):
            payload = {
                "client_id": client_id,
                "api_key_hash": f"{client_id}:{api_secret}",
                "subscription_tier": "ENTERPRISE_BYOK" if plan == "ENTERPRISE_BYOK" else "PAYG",
                "credits_remaining": 5
            }
            if plan == "ENTERPRISE_BYOK":
                payload["byok_provider"] = byok_provider
                payload["byok_api_key"] = byok_key
                
            resp = requests.post(ADMIN_URL, json=payload)
            if resp.status_code == 400: # Already exists, update it
                resp = requests.put(f"{ADMIN_URL}{client_id}", json=payload)
                
            if resp.status_code in [200, 201]:
                st.success("Tenant configuration saved successfully in PostgreSQL!")
                st.session_state.x_api_key = f"{client_id}:{api_secret}"
            else:
                st.error(f"Error saving tenant: {resp.text}")

    with col_admin2:
        st.subheader("2. Billing Dashboard")
        st.write("Active API Key for testing:")
        st.code(st.session_state.x_api_key)
        
        if st.button("Refresh Credit Balance"):
            try:
                c_id = st.session_state.x_api_key.split(":")[0]
                resp = requests.get(f"{ADMIN_URL}{c_id}")
                if resp.status_code == 200:
                    data = resp.json()
                    st.metric("Remaining API Credits", data["credits_remaining"])
                    st.write(f"**Tier:** {data['subscription_tier']}")
                else:
                    st.error("Could not fetch tenant data. Did you register it?")
            except Exception as e:
                st.error("Error fetching credits.")
                
        if st.button("💰 Purchase 10 API Credits (Mock Stripe)"):
            c_id = st.session_state.x_api_key.split(":")[0]
            resp = requests.get(f"{ADMIN_URL}{c_id}")
            if resp.status_code == 200:
                current_credits = resp.json()["credits_remaining"]
                update = requests.put(f"{ADMIN_URL}{c_id}", json={"credits_remaining": current_credits + 10})
                if update.status_code == 200:
                    st.success("Successfully charged card. 10 credits added!")
                    st.balloons()
            else:
                st.error("Register tenant first.")

with tab1:
    preset_scenarios = {
        "1. Standard Gig Worker (Volatile but solvent)": {
            "applicant_id": "gig_worker_001",
            "transactions": [
                {"transaction_id": "tx1", "amount": 250.0, "category": "INCOME_GIG", "description": "Uber Payout", "date": "2023-10-01"},
                {"transaction_id": "tx2", "amount": 200.0, "category": "INCOME_GIG", "description": "Uber Payout", "date": "2023-10-08"},
                {"transaction_id": "tx3", "amount": 220.0, "category": "INCOME_GIG", "description": "Uber Payout", "date": "2023-10-15"},
                {"transaction_id": "tx4", "amount": -400.0, "category": "RENT", "description": "Monthly Rent", "date": "2023-10-02"},
                {"transaction_id": "tx5", "amount": -100.0, "category": "UTILITIES", "description": "Electric Bill", "date": "2023-10-05"},
                {"transaction_id": "tx6", "amount": -50.0, "category": "OTHER", "description": "Pub/Entertainment", "date": "2023-10-10"}
            ],
            "policy": {"max_dti_allowed": 0.80, "min_monthly_income": 500.0, "strict_fca_mode": True}
        },
        "2. High Risk (Expenses > Income)": {
            "applicant_id": "high_risk_002",
            "transactions": [
                {"transaction_id": "tx1", "amount": 545.5, "category": "INCOME_GIG", "description": "Deliveroo", "date": "2023-10-01"},
                {"transaction_id": "tx2", "amount": -650.0, "category": "RENT", "description": "London Rent", "date": "2023-10-02"},
                {"transaction_id": "tx3", "amount": -200.0, "category": "OTHER", "description": "Online Shopping", "date": "2023-10-05"}
            ],
            "policy": {"max_dti_allowed": 0.50, "min_monthly_income": 500.0, "strict_fca_mode": True}
        }
    }

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📝 Open Banking Payload")
        scenario_name = st.selectbox("Load Preset Edge Scenario:", list(preset_scenarios.keys()))
        payload_str = st.text_area(
            "Edit Raw JSON Payload:",
            value=json.dumps(preset_scenarios[scenario_name], indent=4),
            height=400
        )

    with col2:
        st.subheader("🧠 Multi-Agent Analysis")
        
        if st.button("🚀 Run AI Underwriting (Consumes 1 Credit)", type="primary", use_container_width=True):
            try:
                payload = json.loads(payload_str)
                # Generate unique idempotency key for this button click
                idempotency_key = str(uuid.uuid4())
                headers = {
                    "X-API-Key": st.session_state.x_api_key,
                    "Idempotency-Key": idempotency_key
                }
                
                status_placeholder = st.empty()
                status_placeholder.info("Dispatching task to Celery Message Broker...")
                
                response = requests.post(API_URL, json=payload, headers=headers)
                    
                if response.status_code == 202:
                    job_data = response.json()
                    job_id = job_data["job_id"]
                    status_placeholder.success(f"Job Accepted by Broker! Job ID: {job_id}")
                    
                    # Polling Loop
                    with st.status("AI Agents Analyzing Data...", expanded=True) as status_box:
                        st.write("Income Analyst evaluating volatility...")
                        st.write("Expense Tracker calculating baseline...")
                        
                        max_retries = 30
                        for i in range(max_retries):
                            time.sleep(2) # Poll every 2 seconds
                            status_resp = requests.get(f"{API_URL}status/{job_id}", headers=headers)
                            if status_resp.status_code == 200:
                                status_data = status_resp.json()
                                if status_data["status"] == "COMPLETED":
                                    status_box.update(label="Analysis Complete!", state="complete", expanded=False)
                                    break
                                elif status_data["status"] == "FAILED":
                                    status_box.update(label="Analysis Failed!", state="error", expanded=True)
                                    st.error(status_data.get("error", "Unknown error in LangGraph"))
                                    st.stop()
                                else:
                                    st.write(f"Polling Celery Worker... (Attempt {i+1}/{max_retries})")
                            else:
                                st.write("Waiting for FastAPI...")
                                
                    if status_data["status"] == "COMPLETED":
                        data = status_data["result"]
                        m1, m2, m3 = st.columns(3)
                        decision = data.get("decision", "UNKNOWN")
                        m1.metric("Decision", decision)
                        m2.metric("Risk Score", data.get("risk_score", 0))
                        m3.metric("DTI Ratio", f"{data.get('dti_ratio', 0.0):.2f}")
                        
                        st.markdown("---")
                        st.subheader("⚖️ FCA Audit Trail")
                        audit = data.get("audit_trail", {})
                        st.success("**💬 Customer-Facing Explanation**\n\n" + audit.get("customer_facing_explanation", ""))
                        st.info("**📜 Consumer Duty Statement**\n\n" + audit.get("consumer_duty_statement", ""))
                        
                        with st.expander("🔍 View Internal Compliance Log (For Risk Officers)", expanded=True):
                            internal = audit.get("internal_compliance_log", {})
                            st.write(f"**Income Volatility Score:** `{internal.get('income_volatility_score')}`")
                            st.write(f"**Expense Baseline:** `£{internal.get('expense_baseline')}`")
                            st.write(f"> {internal.get('affordability_logic')}")
                        
                elif response.status_code == 402:
                    st.error("💳 402 Payment Required: You have run out of API credits!")
                    st.warning("Go to the 'Tenant Admin & Billing' tab to purchase more credits.")
                elif response.status_code == 401:
                    st.error("🔒 401 Unauthorized: Invalid API Key. Register your tenant first!")
                else:
                    st.error(f"Server Error {response.status_code}")
                    st.write(response.text)
                    
            except json.JSONDecodeError:
                st.error("Invalid JSON format.")
            except requests.exceptions.ConnectionError:
                st.error("Could not connect to FastAPI. Is it running?")
