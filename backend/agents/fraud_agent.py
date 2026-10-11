"""
Fraud & Risk Agent (Priya - Security & Fraud Guardian).
Assesses suspicious activity, computes transaction risk scores (0–100),
and executes card freeze/unfreeze workflows for Indian customer accounts.
"""

from typing import Dict, Any, Optional
import re
from backend.state import AgentState
from backend.agents.utils import add_trace
from backend.tools import assess_transaction_risk, flag_or_block_card
from backend.database import get_session_factory, Transaction, Account


def fraud_agent_node(state: AgentState) -> Dict[str, Any]:
    """
    Evaluates fraud risks, scores flagged transactions, and manages card freeze/unfreeze actions.
    """
    customer_id = state.get("customer_id", "CUST_BHAVNA")
    db_path = state.get("db_path", "banking.db")
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

    # 1. Lock / Freeze or Unlock / Unfreeze card
    if any(k in user_msg_lower for k in ["freeze", "lock", "unfreeze", "unlock"]):
        action = "unfreeze" if any(k in user_msg_lower for k in ["unfreeze", "unlock"]) else "freeze"

        SessionFactory = get_session_factory(db_path)
        session = SessionFactory()
        target_account_id = None
        try:
            acc_match = re.search(r'(ACC_[A-Z0-9_]+)', user_msg)
            if acc_match:
                target_account_id = acc_match.group(1)
            else:
                accounts = session.query(Account).filter_by(customer_id=customer_id).all()
                for a in accounts:
                    if a.account_type in ["CREDIT_CARD", "CREDIT"]:
                        target_account_id = a.account_id
                        break
                if not target_account_id and accounts:
                    target_account_id = accounts[0].account_id
        finally:
            session.close()

        if not target_account_id:
            target_account_id = f"ACC_{customer_id.replace('CUST_', '')}_CC"

        reason = "Security freeze initiated by cardholder via Fraud Prevention Guardian" if action == "freeze" else "Cardholder verified identity and safety"
        result = flag_or_block_card(target_account_id, reason=reason, action=action, db_path=db_path)

        trace = add_trace(
            [],
            agent="Fraud & Risk Agent (Priya)",
            action="CARD_LOCK_ACTION",
            details=f"Executed {action.upper()} on card {target_account_id}. New status: {result.new_status}",
            payload={"account_id": target_account_id, "action": action, "reason": reason},
            result=result.model_dump()
        )

        status_icon = "🔒" if action == "freeze" else "🔓"
        resp_md = (
            f"### {status_icon} Card Security Update\n\n"
            f"**Card / Account ID:** `{target_account_id}`\n"
            f"- **Security Action:** `{action.upper()}`\n"
            f"- **Current Status:** `{result.new_status}`\n"
            f"- **Audit Reason:** {reason}\n\n"
            f"{result.message}"
        )

        return {
            "active_agent": "fraud_agent",
            "next_step": "end",
            "final_response": resp_md,
            "execution_trace": [trace]
        }

    # 2. Risk Assessment / Review suspicious charges
    SessionFactory = get_session_factory(db_path)
    session = SessionFactory()
    target_tx = None
    try:
        tx_match = re.search(r'(TX_[A-Z0-9_]+)', user_msg)
        if tx_match:
            target_tx = session.query(Transaction).filter_by(tx_id=tx_match.group(1)).first()

        if not target_tx:
            accounts = session.query(Account).filter_by(customer_id=customer_id).all()
            acc_ids = [a.account_id for a in accounts]
            flagged_tx = (
                session.query(Transaction)
                .filter(Transaction.account_id.in_(acc_ids), Transaction.is_flagged == True)
                .order_by(Transaction.timestamp.desc())
                .first()
            )
            if flagged_tx:
                target_tx = flagged_tx
            else:
                target_tx = (
                    session.query(Transaction)
                    .filter(Transaction.account_id.in_(acc_ids))
                    .order_by(Transaction.timestamp.desc())
                    .first()
                )
    finally:
        session.close()

    if not target_tx:
        risk_report = assess_transaction_risk("TX_B9901", db_path=db_path)
    else:
        risk_report = assess_transaction_risk(target_tx.tx_id, db_path=db_path)

    trace = add_trace(
        [],
        agent="Fraud & Risk Agent (Priya)",
        action="ASSESS_TRANSACTION_RISK",
        details=f"Risk Score: {risk_report.risk_score}/100 ({risk_report.risk_level}) for TX {risk_report.tx_id} at {risk_report.merchant}.",
        payload={"tx_id": risk_report.tx_id, "amount": risk_report.amount},
        result=risk_report.model_dump()
    )

    badge_color = {
        "LOW": "🟢 LOW",
        "MEDIUM": "🟡 MEDIUM",
        "HIGH": "🟠 HIGH",
        "CRITICAL": "🔴 CRITICAL"
    }.get(risk_report.risk_level, "⚪")

    factors_bullets = "\n".join([f"- {f}" for f in risk_report.factors])

    resp_md = (
        f"### 🛡️ Fraud & Risk Assessment Report\n\n"
        f"Hello, I am **Priya** from Fraud Prevention. I investigated the flagged charge:\n\n"
        f"**Transaction ID:** `{risk_report.tx_id}`\n"
        f"- **Merchant:** **{risk_report.merchant}**\n"
        f"- **Amount:** `₹{risk_report.amount:,.2f}`\n"
        f"- **Card / Account:** `{risk_report.account_id}`\n\n"
        f"#### Risk Analysis Metrics\n"
        f"- **Calculated Risk Score:** **`{risk_report.risk_score}/100`**\n"
        f"- **Threat Severity:** **{badge_color}**\n"
        f"- **Recommended Protocol:** `{risk_report.recommended_action}`\n\n"
        f"#### Anomaly Factors Detected\n"
        f"{factors_bullets}\n\n"
        f"**Next Steps:** You can type *\"Freeze my card\"* to lock this card right away and prevent any unauthorized charges."
    )

    return {
        "active_agent": "fraud_agent",
        "next_step": "end",
        "final_response": resp_md,
        "execution_trace": [trace]
    }
