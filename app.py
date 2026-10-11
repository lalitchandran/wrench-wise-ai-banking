"""
Streamlit Web Application: Bharat Apex Digital Bank Multi-Agent System.
Features:
- Clean White & Warm Yellow Human-Centered UI
- Humanized Indian Personas (Aarav Sharma, Bhavna Patel, Chirag Verma)
- Indian Rupee (INR - ₹) Currency, CIBIL Scores, UPI/NEFT Rails
- Humanized Agents: Aditi (Supervisor), Rohan (Accounts), Priya (Fraud), Vikram (Credit)
- Real-time Human-In-The-Loop (HITL) Gate with Approve / Reject actions (> ₹50k / > ₹2 Lakhs)
- Live SQLite Core Ledger Explorer & 1-Click Banking Scenarios
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime

from backend.database import (
    init_db,
    reset_db,
    get_session_factory,
    Customer,
    Account,
    Transaction,
    Loan,
    AuditLog
)
from backend.graph import run_banking_turn
from backend.tools import get_account_overview

# -----------------------------------------------------------------------------
# Page Configuration & Styling
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Bharat Apex Bank | Multi-Agent Banking System",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for Clean White & Yellow Modern Humanized Fintech
st.markdown("""
<style>
    /* Global Styles */
    .stApp {
        background: #f8fafc;
        color: #0f172a;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Top Header Bar */
    .bank-header {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 1.2rem 1.8rem;
        margin-bottom: 1.2rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
    }
    .bank-title {
        font-size: 1.6rem;
        font-weight: 800;
        color: #0f172a;
        letter-spacing: -0.5px;
        display: flex;
        align-items: center;
        gap: 0.6rem;
    }
    .bank-subtitle {
        font-size: 0.88rem;
        color: #64748b;
    }
    
    /* Persona Card */
    .persona-badge {
        background: #fef3c7;
        border: 1px solid #fde68a;
        border-radius: 8px;
        padding: 0.4rem 0.9rem;
        font-size: 0.85rem;
        font-weight: 700;
        color: #b45309;
    }
    
    /* Agent Active Status Pill */
    .agent-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 14px;
        border-radius: 20px;
        font-size: 0.82rem;
        font-weight: 700;
        background: #fef3c7;
        color: #b45309;
        border: 1px solid #fde68a;
    }
    
    /* HITL Alert Box */
    .hitl-container {
        background: #fffbeb;
        border: 2px solid #f59e0b;
        border-radius: 12px;
        padding: 1.2rem;
        margin: 1rem 0;
        box-shadow: 0 4px 14px rgba(245, 158, 11, 0.15);
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Initialize Core Banking Engine
# -----------------------------------------------------------------------------
DB_PATH = "banking.db"
init_db(DB_PATH, seed=True)

# Session State Initialization
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_customer" not in st.session_state:
    st.session_state.current_customer = "CUST_AARAV"
if "pending_hitl" not in st.session_state:
    st.session_state.pending_hitl = None
if "last_trace" not in st.session_state:
    st.session_state.last_trace = []
if "active_agent_display" not in st.session_state:
    st.session_state.active_agent_display = "Aditi (Supervisor Router)"

# -----------------------------------------------------------------------------
# Sidebar: Personas & Quick Actions
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 👤 Indian Customer Persona")
    persona_options = {
        "CUST_AARAV": "Aarav Sharma (Prime / Bengaluru)",
        "CUST_BHAVNA": "Bhavna Patel (High Velocity / Mumbai)",
        "CUST_CHIRAG": "Chirag Verma (Personal Loan / Delhi)"
    }
    
    if st.session_state.current_customer not in persona_options:
        st.session_state.current_customer = "CUST_AARAV"

    selected_persona = st.selectbox(
        "Logged-in Customer:",
        options=list(persona_options.keys()),
        format_func=lambda x: persona_options[x],
        index=list(persona_options.keys()).index(st.session_state.current_customer)
    )

    if selected_persona != st.session_state.current_customer:
        st.session_state.current_customer = selected_persona
        st.session_state.messages = []
        st.session_state.pending_hitl = None
        st.session_state.last_trace = []
        st.session_state.active_agent_display = "Aditi (Supervisor Router)"
        st.rerun()

    overview = get_account_overview(st.session_state.current_customer, db_path=DB_PATH)
    
    st.markdown(f"""
    <div style="background:#ffffff; border-radius:10px; padding:1rem; margin-top:0.5rem; border:1px solid #e2e8f0; box-shadow:0 1px 3px rgba(0,0,0,0.05);">
        <div style="font-weight:800; font-size:1.15rem; color:#0f172a;">{overview.name}</div>
        <div style="color:#64748b; font-size:0.8rem;">ID: <code>{overview.customer_id}</code></div>
        <div style="display:flex; justify-content:space-between; margin-top:0.6rem; font-size:0.85rem;">
            <span>KYC: <b style="color:#10b981;">{overview.kyc_status}</b></span>
            <span>Risk Tier: <b>{overview.risk_tier}</b></span>
        </div>
        <div style="display:flex; justify-content:space-between; margin-top:0.3rem; font-size:0.85rem;">
            <span>CIBIL Score: <b style="color:#0f172a;">{overview.credit_score}</b></span>
            <span>Available: <b style="color:#10b981;">₹{overview.total_balance:,.2f}</b></span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### ⚡ Quick-Action Scenarios")
    st.caption("Trigger multi-agent workflows in 1 click:")

    if st.button("💸 Transfer ₹35,000 to Bhavna", use_container_width=True):
        st.session_state.prefill_prompt = "Transfer ₹35,000 to Bhavna"

    if st.button("🛡️ Review Suspicious Dubai Charge", use_container_width=True):
        st.session_state.prefill_prompt = "Review suspicious charge on my credit card"

    if st.button("📑 Apply for ₹1,50,000 Personal Loan", use_container_width=True):
        st.session_state.prefill_prompt = "Apply for a ₹1,50,000 personal loan"

    st.markdown("#### 🚨 HITL Threshold Triggers")
    if st.button("⚠️ Transfer ₹85,000 (HITL > ₹50,000)", use_container_width=True):
        st.session_state.prefill_prompt = "Transfer ₹85,000 to Bhavna for commercial invoice"

    if st.button("⚠️ Apply for ₹3,50,000 Loan (HITL > ₹2 Lakhs)", use_container_width=True):
        st.session_state.prefill_prompt = "Apply for a ₹3,50,000 commercial expansion loan"

    st.markdown("---")
    if st.button("🔄 Reset Core Banking DB", use_container_width=True, help="Re-seeds original Indian SQLite state"):
        reset_db(DB_PATH)
        st.session_state.messages = []
        st.session_state.pending_hitl = None
        st.session_state.last_trace = []
        st.success("Database restored to seed state.")
        st.rerun()

# -----------------------------------------------------------------------------
# Main Screen Layout: Dual-View (Chat vs Observability Drawer)
# -----------------------------------------------------------------------------
st.markdown("""
<div class="bank-header">
    <div>
        <div class="bank-title">🏛️ Bharat Apex Digital Bank | Multi-Agent Console</div>
        <div class="bank-subtitle">Clean, Human-Designed AI Banking Engine powered by LangGraph, SQLite, and INR (₹)</div>
    </div>
    <div>
        <span class="persona-badge">Agent Mesh Active (INR ₹)</span>
    </div>
</div>
""", unsafe_allow_html=True)

col_chat, col_inspect = st.columns([1.1, 0.9], gap="large")

# -----------------------------------------------------------------------------
# Column 1: Main Conversational Interface
# -----------------------------------------------------------------------------
with col_chat:
    st.subheader("💬 AI Banking Concierge")

    st.markdown(f"""
    <div style="margin-bottom:0.8rem;">
        <span style="font-size:0.8rem; color:#64748b; margin-right:8px;">ACTIVE SPECIALIST:</span>
        <span class="agent-pill">⚡ {st.session_state.active_agent_display}</span>
    </div>
    """, unsafe_allow_html=True)

    chat_container = st.container(height=420)
    with chat_container:
        if not st.session_state.messages:
            st.info(f"Namaste, {overview.name}! 🙏 I am Aditi, your Banking Concierge. How can we help you today?")
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # Human-In-The-Loop Approval Action Box
    if st.session_state.pending_hitl:
        hitl = st.session_state.pending_hitl
        st.markdown(f"""
        <div class="hitl-container">
            <h4 style="color:#b45309; margin-top:0;">⚠️ Action Required: High-Value Confirmation</h4>
            <p style="color:#0f172a;"><strong>{hitl.get('summary')}</strong></p>
            <p style="font-size:0.85rem; color:#64748b;">
                This action involves an amount of <strong>₹{hitl.get('amount', 0):,.2f}</strong>,
                which exceeds our automated retail policy limit (₹{hitl.get('threshold', 0):,.2f}).
                Please confirm to proceed.
            </p>
        </div>
        """, unsafe_allow_html=True)

        col_app, col_rej = st.columns(2)
        with col_app:
            if st.button("✅ Approve Action", use_container_width=True, type="primary"):
                with st.spinner("Authorizing and executing high-value transaction..."):
                    result = run_banking_turn(
                        message="[HUMAN_ACTION_APPROVED]",
                        customer_id=st.session_state.current_customer,
                        db_path=DB_PATH,
                        thread_id=f"session_{st.session_state.current_customer}",
                        hitl_decision="APPROVED",
                        existing_pending_hitl=st.session_state.pending_hitl
                    )
                    st.session_state.pending_hitl = None
                    st.session_state.active_agent_display = result.get("active_agent", "supervisor")
                    st.session_state.last_trace = result.get("execution_trace", [])
                    st.session_state.messages.append({"role": "assistant", "content": result.get("final_response", "")})
                    st.rerun()

        with col_rej:
            if st.button("❌ Decline Action", use_container_width=True):
                with st.spinner("Cancelling transaction..."):
                    result = run_banking_turn(
                        message="[HUMAN_ACTION_REJECTED]",
                        customer_id=st.session_state.current_customer,
                        db_path=DB_PATH,
                        thread_id=f"session_{st.session_state.current_customer}",
                        hitl_decision="REJECTED",
                        existing_pending_hitl=st.session_state.pending_hitl
                    )
                    st.session_state.pending_hitl = None
                    st.session_state.active_agent_display = result.get("active_agent", "supervisor")
                    st.session_state.last_trace = result.get("execution_trace", [])
                    st.session_state.messages.append({"role": "assistant", "content": result.get("final_response", "")})
                    st.rerun()

    prompt_to_send = None
    if "prefill_prompt" in st.session_state and st.session_state.prefill_prompt:
        prompt_to_send = st.session_state.prefill_prompt
        st.session_state.prefill_prompt = None
    else:
        user_input = st.chat_input("Ask a question or enter banking command in ₹...")
        if user_input:
            prompt_to_send = user_input

    if prompt_to_send:
        st.session_state.messages.append({"role": "user", "content": prompt_to_send})
        
        with st.spinner("Aditi coordinating specialists..."):
            result = run_banking_turn(
                message=prompt_to_send,
                customer_id=st.session_state.current_customer,
                db_path=DB_PATH,
                thread_id=f"session_{st.session_state.current_customer}"
            )
            
            st.session_state.active_agent_display = result.get("active_agent", "supervisor")
            st.session_state.last_trace = result.get("execution_trace", [])
            st.session_state.pending_hitl = result.get("pending_hitl")
            
            final_text = result.get("final_response", "Transaction processed.")
            st.session_state.messages.append({"role": "assistant", "content": final_text})
            st.rerun()

# -----------------------------------------------------------------------------
# Column 2: Live Agent Observability Sidebar / Drawer
# -----------------------------------------------------------------------------
with col_inspect:
    st.subheader("🔍 Observability & Core Ledger (INR ₹)")

    tab_trace, tab_ledger, tab_topology = st.tabs(["📊 Specialist Actions", "💾 Core Ledger", "🕸️ Architecture"])

    with tab_trace:
        st.markdown("#### Live State Transitions & Tool Invocations")
        
        if not st.session_state.last_trace:
            st.info("Execute a command or click a quick scenario to inspect live agent hops.")
        else:
            for idx, step in enumerate(reversed(st.session_state.last_trace)):
                agent_name = step.get("agent", "Agent")
                action_name = step.get("action", "ACTION")
                ts = step.get("timestamp", "")
                
                with st.expander(f"Step {len(st.session_state.last_trace) - idx}: [{ts}] {agent_name} -> {action_name}", expanded=(idx==0)):
                    st.markdown(f"**Details:** {step.get('details', 'N/A')}")
                    
                    if step.get("payload"):
                        st.markdown("**Tool Payload:**")
                        st.code(json.dumps(step["payload"], indent=2), language="json")
                        
                    if step.get("result"):
                        st.markdown("**Raw Result:**")
                        st.code(json.dumps(step["result"], indent=2), language="json")

        fraud_steps = [s for s in st.session_state.last_trace if "Fraud" in s.get("agent", "") and "result" in s]
        if fraud_steps:
            f_res = fraud_steps[-1].get("result", {})
            score = f_res.get("risk_score", 0)
            level = f_res.get("risk_level", "LOW")
            st.markdown("#### 🛡️ Transaction Risk Meter")
            st.progress(score / 100.0)
            st.caption(f"Score: **{score}/100** | Level: **{level}**")

    with tab_ledger:
        st.markdown("#### Real-Time Database Tables")
        
        SessionFactory = get_session_factory(DB_PATH)
        session = SessionFactory()
        try:
            accounts = session.query(Account).all()
            df_acc = pd.DataFrame([a.to_dict() for a in accounts])
            st.markdown("##### 💳 Accounts (INR ₹)")
            st.dataframe(df_acc, use_container_width=True, hide_index=True)

            txs = session.query(Transaction).order_by(Transaction.timestamp.desc()).limit(10).all()
            df_tx = pd.DataFrame([t.to_dict() for t in txs])
            st.markdown("##### 📝 Recent Transactions")
            st.dataframe(df_tx, use_container_width=True, hide_index=True)

            loans = session.query(Loan).all()
            if loans:
                df_ln = pd.DataFrame([l.to_dict() for l in loans])
                st.markdown("##### 📄 Loans & Underwriting")
                st.dataframe(df_ln, use_container_width=True, hide_index=True)

            audits = session.query(AuditLog).order_by(AuditLog.id.desc()).limit(10).all()
            if audits:
                df_aud = pd.DataFrame([a.to_dict() for a in audits])
                st.markdown("##### 🔒 Audit Ledger")
                st.dataframe(df_aud, use_container_width=True, hide_index=True)
        finally:
            session.close()

    with tab_topology:
        st.markdown("#### Indian Multi-Agent Architecture")
        st.markdown("""
        - 🧭 **Aditi (Supervisor Router):** Evaluates user intent, validates Aadhaar/PAN KYC, dispatches tasks.
        - 💳 **Rohan (Account Services Agent):** Manages balances, UPI/NEFT transfers, overdraft protection.
        - 🛡️ **Priya (Fraud & Risk Guardian):** Assesses overseas charges, computes risk score (0–100), executes card freeze.
        - 📈 **Vikram (Credit & Lending Advisor):** Evaluates CIBIL score, FOIR/DTI ratio, and personal/auto loan underwriting.
        - ⚖️ **Compliance Council (HITL Gate):** Enforces human officer approvals for transfers > ₹50,000 and loans > ₹2,00,000.
        """)
