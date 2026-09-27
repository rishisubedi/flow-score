import streamlit as st
import requests
import json
import time
import uuid
import pandas as pd

API_URL = "http://localhost:8080/v1/underwrite/"
ADMIN_URL = "http://localhost:8080/v1/admin/client/"

st.set_page_config(page_title="FlowScore AI Dashboard", page_icon="🏦", layout="wide")

st.title("🏦 FlowScore B2B SaaS Platform")
st.markdown("Multi-Tenant LLM Underwriting Engine with BYOK Architecture & Metered Billing.")

# Initialize session state for tenant auth
if "x_api_key" not in st.session_state:
    st.session_state.x_api_key = "demo_bank:secret123"

if "retry_submission" not in st.session_state:
    st.session_state.retry_submission = False

tab1, tab2, tab3 = st.tabs(["🚀 Underwriting Engine", "💳 Tenant Admin & Billing", "📜 Historical Audits"])

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
                
        if st.button("💳 Purchase 10 API Credits (Mock Stripe)"):
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

with tab3:
    st.header("Historical Underwriting Decisions")
    st.markdown("View past applications/tickets processed by the AI.")
    
    if st.button("Refresh History"):
        headers = {"X-API-Key": st.session_state.x_api_key}
        
        with st.spinner("Fetching historical tickets..."):
            try:
                time.sleep(0.5) 
                hist_resp = requests.get(f"{API_URL}history", headers=headers)
                
                if hist_resp.status_code == 200:
                    hist_data = hist_resp.json()
                    if not hist_data:
                        st.info("No historical tickets found. Run an underwriting job first!")
                    else:
                        for record in hist_data:
                            with st.expander(f"Applicant: {record['applicant_id']} | Date: {record['created_at'][:10]}"):
                                st.write(f"**Decision:** {record['decision']}")
                                st.write(f"**Risk Score:** {record['risk_score']}")
                                st.write(f"**DTI Ratio:** {record['dti_ratio']}")
                else:
                    st.error(f"Failed to fetch history (Error {hist_resp.status_code}). Please check your API Key and connection.")
            except requests.exceptions.ConnectionError:
                st.error("Failed to connect to the server to fetch history. Please try again.")

with tab1:
    st.markdown("### 🏦 Enterprise Loan Origination Dashboard")
    st.caption("Simulate real customer data ingestion via Open Banking APIs (e.g., Plaid, TrueLayer).")
    
    preset_scenarios = {
        "Applicant: Sarah (Gig Worker - Thin File)": {
            "applicant_id": "sarah_gig_001",
            "transactions": [
                {"transaction_id": "tx1", "amount": 350.0, "category": "INCOME_GIG", "description": "UBER PAYOUT", "date": "2023-10-01"},
                {"transaction_id": "tx2", "amount": 280.0, "category": "INCOME_GIG", "description": "UBER PAYOUT", "date": "2023-10-08"},
                {"transaction_id": "tx3", "amount": 400.0, "category": "INCOME_GIG", "description": "DELIVEROO", "date": "2023-10-15"},
                {"transaction_id": "tx4", "amount": -800.0, "category": "RENT", "description": "LONDON RENT TFL", "date": "2023-10-02"},
                {"transaction_id": "tx5", "amount": -120.0, "category": "UTILITIES", "description": "BRITISH GAS", "date": "2023-10-05"},
                {"transaction_id": "tx6", "amount": -45.0, "category": "OTHER", "description": "TESCO SUPERMARKET", "date": "2023-10-10"},
                {"transaction_id": "tx7", "amount": -30.0, "category": "OTHER", "description": "TFL TRAVEL CHARGE", "date": "2023-10-12"},
            ],
            "policy": {"max_dti_allowed": 0.55, "min_monthly_income": 800.0, "strict_fca_mode": True}
        },
        "Applicant: James (High Risk - Debt Spiraling)": {
            "applicant_id": "james_risk_002",
            "transactions": [
                {"transaction_id": "tx1", "amount": 1500.0, "category": "INCOME_SALARY", "description": "TESCO PLC PAYROLL", "date": "2023-10-01"},
                {"transaction_id": "tx2", "amount": -1200.0, "category": "RENT", "description": "RENTAL AGENCY", "date": "2023-10-02"},
                {"transaction_id": "tx3", "amount": -400.0, "category": "DEBT_REPAYMENT", "description": "KLARNA PAYMENTS", "date": "2023-10-05"},
                {"transaction_id": "tx4", "amount": -150.0, "category": "DEBT_REPAYMENT", "description": "AMEX CREDIT CARD", "date": "2023-10-15"},
                {"transaction_id": "tx5", "amount": -50.0, "category": "OTHER", "description": "PADDYPOWER BETTING", "date": "2023-10-18"},
            ],
            "policy": {"max_dti_allowed": 0.45, "min_monthly_income": 1000.0, "strict_fca_mode": True}
        }
    }

    col1, col2 = st.columns([1.2, 1])

    with col1:
        st.subheader("🌐 Open Banking Data Sync")
        scenario_name = st.selectbox("Select Real Customer Profile:", list(preset_scenarios.keys()))
        active_scenario = preset_scenarios[scenario_name]
        
        st.write(f"**Applicant ID:** `{active_scenario['applicant_id']}`")
        st.caption("Extracted Bank Transactions (Last 30 Days):")
        
        df = pd.DataFrame(active_scenario["transactions"])
        # Styling function for amount
        def color_amounts(val):
            color = 'lightgreen' if val > 0 else 'lightcoral'
            return f'color: {color}'
        
        st.dataframe(
            df[['date', 'description', 'category', 'amount']].style.map(color_amounts, subset=['amount']),
            use_container_width=True,
            hide_index=True
        )
        
        with st.expander("⚙️ Adjust Lender Policy (FCA Constraints)"):
            st.write("Modify the strictness of the underwriting engine for this applicant.")
            max_dti = st.slider("Max Allowed DTI Ratio", 0.1, 1.0, active_scenario["policy"]["max_dti_allowed"])
            min_inc = st.number_input("Min Monthly Income", value=active_scenario["policy"]["min_monthly_income"])
            active_scenario["policy"]["max_dti_allowed"] = max_dti
            active_scenario["policy"]["min_monthly_income"] = min_inc

        payload = active_scenario

    with col2:
        st.subheader("🧠 Multi-Agent Decision Engine")
        st.info("FlowScore LangGraph agents will analyze the transactional ledger, compute affordability, and generate a cryptographically-secure FCA audit trail.")
        
        submit_triggered = st.button("🚀 Run AI Underwriting (Consumes 1 Credit)", type="primary", use_container_width=True)
        if st.session_state.retry_submission:
            submit_triggered = True
            st.session_state.retry_submission = False
        
        if submit_triggered:
            try:
                idempotency_key = str(uuid.uuid4())
                headers = {
                    "X-API-Key": st.session_state.x_api_key,
                    "Idempotency-Key": idempotency_key
                }
                
                status_placeholder = st.empty()
                status_placeholder.info("Dispatching secure payload to Celery Broker...")
                
                response = requests.post(API_URL, json=payload, headers=headers)
                    
                if response.status_code == 202:
                    job_data = response.json()
                    job_id = job_data["job_id"]
                    status_placeholder.success(f"Job Accepted! Idempotency Key Tracking ID: {job_id}")
                    
                    # Polling Loop
                    with st.status("AI Agents Analyzing Data...", expanded=True) as status_box:
                        st.write("🔍 Identifying structural income...")
                        st.write("📊 Calculating highly volatile expense baselines...")
                        
                        max_retries = 30
                        status_data = None
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
                                    st.error(f"Inline Error: {status_data.get('error', 'Unknown error in LangGraph')}")
                                    if st.button("Retry Submission", key=f"retry_{job_id}"):
                                        st.session_state.retry_submission = True
                                        st.rerun()
                                    st.stop()
                                else:
                                    st.write(f"⏳ Polling Celery Worker... (Attempt {i+1}/{max_retries})")
                            else:
                                st.write("Waiting for FastAPI cluster...")
                                
                    if status_data and status_data["status"] == "COMPLETED":
                        data = status_data["result"]
                        
                        st.markdown("### 🎯 Final Underwriting Decision")
                        m1, m2, m3 = st.columns(3)
                        decision = data.get("decision", "UNKNOWN")
                        
                        if decision == "APPROVED":
                            m1.metric("Decision", decision, "Passed")
                        else:
                            m1.metric("Decision", decision, "-Failed")
                            
                        m2.metric("Risk Score", data.get("risk_score", 0))
                        m3.metric("DTI Ratio", f"{data.get('dti_ratio', 0.0):.2f}")
                        
                        st.markdown("---")
                        st.subheader("📜 FCA Audit & Explainability")
                        audit = data.get("audit_trail", {})
                        
                        st.success(f"**Customer-Facing Explanation (FCA Transparency)**\n\n{audit.get('customer_facing_explanation', '')}")
                        st.info(f"**Consumer Duty Statement**\n\n{audit.get('consumer_duty_statement', '')}")
                        
                        with st.expander("🔐 View Internal Compliance Log (For Risk Officers)", expanded=False):
                            internal = audit.get("internal_compliance_log", {})
                            st.write(f"**Income Volatility Score:** `{internal.get('income_volatility_score')}`")
                            st.write(f"**Expense Baseline:** `£{internal.get('expense_baseline')}`")
                            st.write(f"> {internal.get('affordability_logic')}")
                        
                elif response.status_code == 402:
                    st.error("💳 402 Payment Required: You have run out of API credits!")
                    st.warning("Go to the 'Tenant Admin & Billing' tab to purchase more credits.")
                elif response.status_code == 401:
                    st.error("🚫 401 Unauthorized: Invalid API Key. Register your tenant first!")
                else:
                    st.error(f"Submission Error {response.status_code}: {response.text}")
                    if st.button("Retry Submission", key="retry_btn_1"):
                        st.session_state.retry_submission = True
                        st.rerun()
                    
            except json.JSONDecodeError:
                st.error("Invalid JSON format.")
            except requests.exceptions.ConnectionError:
                st.error("Could not connect to FastAPI backend cluster.")
                if st.button("Retry Connection", key="retry_btn_2"):
                    st.session_state.retry_submission = True
                    st.rerun()
