"""
Credit & Lending Agent (Vikram - Credit & Lending Advisor).
Runs loan eligibility, Debt-to-Income (FOIR) analysis, and CIBIL score evaluations in INR (₹).
Escalates credit disbursements over ₹2,00,000 to the Human-In-The-Loop (HITL) Gate.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
from backend.state import AgentState
from backend.agents.utils import extract_amount, add_trace
from backend.tools import evaluate_credit_application
from backend.database import get_session_factory, Customer, Loan


def credit_agent_node(state: AgentState) -> Dict[str, Any]:
    """
    Evaluates loan underwriting, computes DTI ratios in INR, and triggers HITL gate for loans > ₹2,00,000.
    """
    customer_id = state.get("customer_id", "CUST_CHIRAG")
    db_path = state.get("db_path", "banking.db")
    pending_hitl = state.get("pending_hitl")
    hitl_decision = state.get("hitl_decision")
    messages = state.get("messages", [])

    # Normalize customer_id
    if customer_id == "CUST_ALICE":
        customer_id = "CUST_AARAV"
    elif customer_id == "CUST_BOB":
        customer_id = "CUST_BHAVNA"
    elif customer_id == "CUST_CHARLIE":
        customer_id = "CUST_CHIRAG"

    user_msg = ""
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "user":
            user_msg = msg.get("content", "")
            break
        elif hasattr(msg, "content"):
            user_msg = msg.content
            break

    user_msg_lower = user_msg.lower()

    # 1. Resuming from Human-In-The-Loop decision for loan disbursement
    if pending_hitl and pending_hitl.get("action_type") == "credit_disbursement":
        payload = pending_hitl.get("payload", {})
        loan_id = payload.get("loan_id")
        amount = payload.get("requested_amount", 0.0)
        interest_rate = payload.get("interest_rate", 9.5)

        SessionFactory = get_session_factory(db_path)
        session = SessionFactory()
        try:
            loan = session.query(Loan).filter_by(loan_id=loan_id).first() if loan_id else None
            new_status = "APPROVED" if hitl_decision == "APPROVED" else "REJECTED"
            if loan:
                loan.status = new_status
                session.commit()
        finally:
            session.close()

        if hitl_decision == "APPROVED":
            trace = add_trace(
                [],
                agent="Credit & Lending Agent (Vikram)",
                action="HITL_LOAN_DISBURSED",
                details=f"HITL Approved! Loan {loan_id} for ₹{amount:,.2f} disbursed.",
                payload=payload,
                result={"status": "APPROVED", "loan_id": loan_id}
            )
            resp_md = (
                f"### 🎉 Congratulations! High-Value Loan Approved & Disbursed\n\n"
                f"**Loan Account Number:** `{loan_id}`\n"
                f"- **Principal Sanctioned:** `₹{amount:,.2f}`\n"
                f"- **Fixed Interest Rate:** `{interest_rate:.2f}% p.a.`\n"
                f"- **Tenure:** `36 Months`\n\n"
                f"The Credit Sanction Committee (HITL) has approved your loan. "
                f"Funds have been credited to your primary savings account."
            )
        else:
            trace = add_trace(
                [],
                agent="Credit & Lending Agent (Vikram)",
                action="HITL_LOAN_REJECTED",
                details=f"HITL Rejected! Loan {loan_id} for ₹{amount:,.2f} declined by sanction committee.",
                payload=payload,
                result={"status": "REJECTED", "loan_id": loan_id}
            )
            resp_md = (
                f"### ❌ Loan Application Declined\n\n"
                f"Your credit disbursement request for **₹{amount:,.2f}** (`{loan_id}`) was **declined** "
                f"following review by our senior underwriting desk."
            )

        return {
            "active_agent": "credit_agent",
            "next_step": "end",
            "pending_hitl": None,
            "hitl_decision": None,
            "final_response": resp_md,
            "execution_trace": [trace]
        }

    # 2. Extract requested loan amount in INR
    amount = extract_amount(user_msg)
    if not amount:
        if "renovation" in user_msg_lower or "home" in user_msg_lower:
            amount = 150000.0  # ₹1.5 Lakhs
        elif "auto" in user_msg_lower or "car" in user_msg_lower:
            amount = 120000.0  # ₹1.2 Lakhs
        else:
            amount = 100000.0  # ₹1 Lakh

    # Retrieve customer income
    SessionFactory = get_session_factory(db_path)
    session = SessionFactory()
    monthly_income = 60000.0
    try:
        cust = session.query(Customer).filter_by(id=customer_id).first()
        if cust:
            monthly_income = cust.monthly_income
    finally:
        session.close()

    # Underwrite application
    report = evaluate_credit_application(
        customer_id=customer_id,
        requested_amount=amount,
        monthly_income=monthly_income,
        db_path=db_path
    )

    # 3. Check if loan disbursement exceeds ₹2,00,000 threshold -> HITL Gate
    if report.status == "PENDING_HITL" or amount > 200000.0:
        hitl_req = {
            "action_type": "credit_disbursement",
            "requested_by": "credit_agent",
            "amount": amount,
            "threshold": 200000.0,
            "summary": f"High-Value Loan Sanction: ₹{amount:,.2f} for {customer_id}",
            "payload": {
                "customer_id": customer_id,
                "requested_amount": amount,
                "loan_id": report.loan_id,
                "interest_rate": report.interest_rate,
                "dti_ratio": report.dti_ratio,
                "estimated_monthly_payment": report.estimated_monthly_payment
            },
            "status": "PENDING"
        }
        trace = add_trace(
            [],
            agent="Credit & Lending Agent (Vikram)",
            action="HITL_CREDIT_ESCALATION",
            details=f"Loan disbursement of ₹{amount:,.2f} exceeds ₹2,00,000 threshold. Escalated to HITL Sanction Committee.",
            payload=hitl_req,
            result=report.model_dump()
        )
        resp_md = (
            f"### ⚠️ Senior Underwriter Review Required (HITL)\n\n"
            f"Namaste! Your loan application for **₹{amount:,.2f}** exceeds our instant retail lending limit of **₹2,00,000.00**.\n\n"
            f"- **Applicant ID:** `{customer_id}`\n"
            f"- **Requested Principal:** `₹{amount:,.2f}`\n"
            f"- **Estimated Monthly EMI:** `₹{report.estimated_monthly_payment:,.2f}`\n"
            f"- **Debt-to-Income (FOIR):** `{report.dti_ratio:.1%}`\n"
            f"- **Applicable Interest Rate:** `{report.interest_rate:.2f}% p.a.`\n\n"
            f"A designated Credit Officer must **Approve** or **Reject** the disbursement below."
        )
        return {
            "active_agent": "credit_agent",
            "next_step": "hitl_gate",
            "pending_hitl": hitl_req,
            "final_response": resp_md,
            "execution_trace": [trace]
        }

    # Standard underwriting (< ₹2,00,000)
    trace = add_trace(
        [],
        agent="Credit & Lending Agent (Vikram)",
        action="EVALUATE_CREDIT",
        details=f"Underwriting evaluation complete for ₹{amount:,.2f}. Status: {report.status}, DTI: {report.dti_ratio:.1%}.",
        payload={"customer_id": customer_id, "amount": amount, "income": monthly_income},
        result=report.model_dump()
    )

    reasons_list = "\n".join([f"- {r}" for r in report.reasons])

    if report.status == "APPROVED":
        resp_md = (
            f"### 📋 Credit Underwriting: Approved ✅\n\n"
            f"**Application Reference:** `{report.loan_id}`\n\n"
            f"#### Loan Terms & EMI\n"
            f"- **Sanctioned Amount:** **₹{report.requested_amount:,.2f}**\n"
            f"- **Fixed Interest Rate:** **{report.interest_rate:.2f}% p.a.**\n"
            f"- **Tenure:** 36 Months\n"
            f"- **Estimated Monthly EMI:** **₹{report.estimated_monthly_payment:,.2f}**\n"
            f"- **Debt-to-Income (FOIR):** **{report.dti_ratio:.1%}**\n\n"
            f"#### Assessment Rationale\n"
            f"{reasons_list}\n\n"
            f"*The loan agreement has been recorded in your core account ledger.*"
        )
    else:
        resp_md = (
            f"### 📋 Credit Underwriting: Declined ❌\n\n"
            f"**Application Reference:** `{report.loan_id}`\n\n"
            f"- **Requested Principal:** ₹{report.requested_amount:,.2f}\n"
            f"- **Debt-to-Income Ratio:** {report.dti_ratio:.1%}\n\n"
            f"#### Underwriting Rationale\n"
            f"{reasons_list}\n\n"
            f"*You may reapply after clearing existing EMIs or adding a verified co-applicant.*"
        )

    return {
        "active_agent": "credit_agent",
        "next_step": "end",
        "final_response": resp_md,
        "execution_trace": [trace]
    }
