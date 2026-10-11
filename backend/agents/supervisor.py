"""
Supervisor Node (Aditi - Banking Navigator & Supervisor Router).
Evaluates user intent, validates customer KYC and permissions,
coordinates multi-step tasks, and routes context to specialized agents.
"""

from typing import Dict, Any
from backend.state import AgentState
from backend.agents.utils import get_llm, add_trace
from backend.database import get_session_factory, Customer


def supervisor_node(state: AgentState) -> Dict[str, Any]:
    """
    Supervisor router node (Aditi).
    Inspects user input, customer identity, and decides which agent should act next.
    """
    messages = state.get("messages", [])
    customer_id = state.get("customer_id", "CUST_AARAV")
    db_path = state.get("db_path", "banking.db")
    
    # Normalize customer_id for backwards compatibility
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
        elif hasattr(msg, "content") and not getattr(msg, "tool_calls", None):
            user_msg = msg.content
            break

    user_msg_lower = user_msg.lower()

    # Verify customer and permissions
    SessionFactory = get_session_factory(db_path)
    session = SessionFactory()
    customer_name = customer_id
    kyc_status = "UNKNOWN"
    try:
        cust = session.query(Customer).filter_by(id=customer_id).first()
        if cust:
            customer_name = cust.name
            kyc_status = cust.kyc_status
    finally:
        session.close()

    # If returning with a HITL decision, route directly to the requesting agent
    pending_hitl = state.get("pending_hitl")
    hitl_decision = state.get("hitl_decision")
    if pending_hitl and hitl_decision:
        target_agent = pending_hitl.get("requested_by", "account_agent")
        routing_trace = add_trace(
            [],
            agent="Supervisor (Aditi)",
            action="HITL_RESUME_ROUTING",
            details=f"Human authorization '{hitl_decision}' received for {customer_name}. Resuming workflow at {target_agent}.",
            payload={"pending_hitl": pending_hitl, "decision": hitl_decision},
            result={"target_agent": target_agent}
        )
        return {
            "customer_id": customer_id,
            "active_agent": target_agent,
            "next_step": target_agent,
            "intent": "hitl_resolution",
            "execution_trace": [routing_trace]
        }

    # KYC Verification Guardrail
    if kyc_status == "FAILED":
        trace = add_trace(
            [],
            agent="Supervisor (Aditi)",
            action="PERMISSION_DENIED",
            details=f"Aadhaar / PAN KYC status is FAILED for {customer_id}. Financial services restricted as per RBI norms.",
        )
        return {
            "customer_id": customer_id,
            "active_agent": "supervisor",
            "next_step": "end",
            "final_response": "Namaste. Your account KYC (Aadhaar/PAN) verification has not been completed. As per regulatory compliance, transactions are currently on hold. Please visit your nearest branch or update KYC via mobile app.",
            "execution_trace": [trace]
        }

    # Intent Classification Logic
    fraud_keywords = [
        "fraud", "suspicious", "charge", "unauthorized", "stolen", "freeze", "lock",
        "unlock", "unfreeze", "block", "compromised", "risk", "flagged", "dubai", "scam"
    ]
    credit_keywords = [
        "loan", "credit", "borrow", "lending", "mortgage", "dti", "foir", "underwriting",
        "renovation", "auto loan", "apply for", "debt", "cibil", "personal loan"
    ]
    account_keywords = [
        "transfer", "send", "balance", "statement", "overview", "upi", "imps", "neft", "wire", "deposit",
        "withdraw", "savings", "transactions", "pay", "rupee", "rs"
    ]

    is_fraud = any(k in user_msg_lower for k in fraud_keywords)
    is_credit = any(k in user_msg_lower for k in credit_keywords)
    is_account = any(k in user_msg_lower for k in account_keywords)

    if is_fraud and not ("transfer" in user_msg_lower and "card" not in user_msg_lower and "suspicious" not in user_msg_lower):
        target_agent = "fraud_agent"
        intent_desc = "fraud_investigation_and_security"
    elif is_credit and not ("transfer" in user_msg_lower and "loan" not in user_msg_lower):
        target_agent = "credit_agent"
        intent_desc = "credit_underwriting_and_loans"
    elif is_account:
        target_agent = "account_agent"
        intent_desc = "account_inquiry_or_funds_transfer"
    else:
        target_agent = "account_agent"
        intent_desc = "general_banking_overview"

    routing_trace = add_trace(
        [],
        agent="Supervisor (Aditi)",
        action="ROUTING_DECISION",
        details=f"Evaluated request for {customer_name}. Intent classified as '{intent_desc}' -> Coordinated to {target_agent}.",
        payload={"customer_id": customer_id, "intent": intent_desc, "user_query": user_msg},
        result={"target_agent": target_agent, "kyc_status": kyc_status}
    )

    return {
        "customer_id": customer_id,
        "active_agent": target_agent,
        "next_step": target_agent,
        "intent": intent_desc,
        "execution_trace": [routing_trace]
    }
