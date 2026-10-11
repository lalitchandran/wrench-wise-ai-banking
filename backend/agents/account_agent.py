"""
Account Services Agent (Rohan - Payments & Accounts Specialist).
Handles accounts, ledger entries, UPI/IMPS/NEFT fund transfers, and mini-statements.
Enforces overdraft protection guardrail and HITL escalation for transfers > ₹50,000.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
from backend.state import AgentState
from backend.agents.utils import extract_amount, resolve_recipient_account, add_trace
from backend.tools import get_account_overview, execute_transfer
from backend.database import get_session_factory, Account, Customer


def account_agent_node(state: AgentState) -> Dict[str, Any]:
    """
    Processes account inquiries and funds transfers in INR (₹).
    Enforces ₹50,000 threshold for Human-In-The-Loop compliance confirmation.
    """
    customer_id = state.get("customer_id", "CUST_AARAV")
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

    # 1. Resuming from a Human-In-The-Loop approval/rejection cycle
    if pending_hitl and pending_hitl.get("action_type") == "fund_transfer":
        payload = pending_hitl.get("payload", {})
        source_acc = payload.get("source_acc")
        dest_acc = payload.get("dest_acc")
        amount = payload.get("amount", 0.0)
        memo = payload.get("memo", "Approved High-Value Transfer")

        if hitl_decision == "APPROVED":
            result = execute_transfer(source_acc, dest_acc, amount, memo=memo, db_path=db_path)
            trace = add_trace(
                [],
                agent="Account Services Agent (Rohan)",
                action="HITL_RESUMED_TRANSFER",
                details=f"HITL Approved! Transfer of ₹{amount:,.2f} executed.",
                payload=payload,
                result=result.model_dump()
            )
            response_text = (
                f"### ✅ High-Value Transfer Approved & Settled\n\n"
                f"**UTR / Reference ID:** `{result.tx_id}`\n"
                f"- **From Account:** `{source_acc}`\n"
                f"- **Beneficiary Account:** `{dest_acc}`\n"
                f"- **Amount Transferred:** `₹{amount:,.2f}`\n"
                f"- **Updated Available Balance:** `₹{result.source_new_balance:,.2f}`\n\n"
                f"Human compliance officer has signed off on this transaction. Funds transferred via instant UPI/IMPS rail."
            )
            return {
                "active_agent": "account_agent",
                "next_step": "end",
                "pending_hitl": None,
                "hitl_decision": None,
                "final_response": response_text,
                "execution_trace": [trace]
            }
        elif hitl_decision == "REJECTED":
            trace = add_trace(
                [],
                agent="Account Services Agent (Rohan)",
                action="HITL_TRANSFER_REJECTED",
                details=f"HITL Declined! High-value transfer of ₹{amount:,.2f} cancelled.",
                payload=payload,
                result={"status": "CANCELLED"}
            )
            response_text = (
                f"### ❌ Transfer Request Declined\n\n"
                f"The high-value transfer of **₹{amount:,.2f}** from `{source_acc}` to `{dest_acc}` "
                f"was **declined** by compliance officer review. No money was deducted from your account."
            )
            return {
                "active_agent": "account_agent",
                "next_step": "end",
                "pending_hitl": None,
                "hitl_decision": None,
                "final_response": response_text,
                "execution_trace": [trace]
            }

    # 2. Check if the intent is a Transfer / Payment
    if any(k in user_msg_lower for k in ["transfer", "send", "pay", "upi", "imps", "neft"]):
        amount = extract_amount(user_msg)
        if not amount:
            overview = get_account_overview(customer_id, db_path=db_path)
            return {
                "active_agent": "account_agent",
                "next_step": "end",
                "final_response": (
                    f"Namaste! Please specify the amount in Rupees and the recipient name or account.\n"
                    f"Your available balance in Savings is **₹{overview.accounts[0].balance:,.2f}**."
                ),
                "execution_trace": [
                    add_trace([], "Account Services Agent (Rohan)", "VALIDATION_INCOMPLETE", "Transfer amount missing in message.")
                ]
            }

        # Resolve sender's primary savings account
        SessionFactory = get_session_factory(db_path)
        session = SessionFactory()
        source_acc = None
        try:
            cust = session.query(Customer).filter_by(id=customer_id).first()
            if cust:
                for a in cust.accounts:
                    if a.account_type in ["SAVINGS", "CURRENT"] and a.status == "ACTIVE":
                        source_acc = a.account_id
                        break
                if not source_acc and cust.accounts:
                    source_acc = cust.accounts[0].account_id
        finally:
            session.close()

        if not source_acc:
            source_acc = f"ACC_{customer_id.replace('CUST_', '')}_SAV"

        # Resolve recipient
        dest_acc = None
        if "bhavna" in user_msg_lower or "bob" in user_msg_lower:
            dest_acc = resolve_recipient_account("Bhavna", db_path)
        elif "aarav" in user_msg_lower or "alice" in user_msg_lower:
            dest_acc = resolve_recipient_account("Aarav", db_path)
        elif "chirag" in user_msg_lower or "charlie" in user_msg_lower:
            dest_acc = resolve_recipient_account("Chirag", db_path)
        else:
            # Default recipient
            if customer_id == "CUST_AARAV":
                dest_acc = "ACC_BHAVNA_SAV"
            elif customer_id == "CUST_BHAVNA":
                dest_acc = "ACC_AARAV_SAV"
            else:
                dest_acc = "ACC_BHAVNA_SAV"

        # HITL Threshold Check: Transfer > ₹50,000 requires Human-In-The-Loop gate
        if amount > 50000.0:
            hitl_req = {
                "action_type": "fund_transfer",
                "requested_by": "account_agent",
                "amount": amount,
                "threshold": 50000.0,
                "summary": f"High-Value UPI/NEFT Transfer: ₹{amount:,.2f} from {source_acc} to {dest_acc}",
                "payload": {
                    "source_acc": source_acc,
                    "dest_acc": dest_acc,
                    "amount": amount,
                    "memo": f"Transfer to {dest_acc}"
                },
                "status": "PENDING"
            }
            trace = add_trace(
                [],
                agent="Account Services Agent (Rohan)",
                action="HITL_GATE_TRIGGERED",
                details=f"Transfer amount ₹{amount:,.2f} exceeds ₹50,000 threshold. Escalated to HITL Compliance Gate.",
                payload=hitl_req
            )
            return {
                "active_agent": "account_agent",
                "next_step": "hitl_gate",
                "pending_hitl": hitl_req,
                "final_response": (
                    f"### 🛡️ Human-In-The-Loop Compliance Approval Required\n\n"
                    f"Namaste! The requested transfer of **₹{amount:,.2f}** from `{source_acc}` to `{dest_acc}` "
                    f"exceeds our automated risk ceiling of **₹50,000.00**.\n\n"
                    f"As per fraud prevention protocols, a compliance officer must confirm this transfer.\n"
                    f"Please review and click **[Approve Action]** or **[Reject Action]** below."
                ),
                "execution_trace": [trace]
            }

        # Standard transfer (<= ₹50,000)
        result = execute_transfer(
            source_acc=source_acc,
            dest_acc=dest_acc,
            amount=amount,
            memo=f"Transfer to {dest_acc}",
            db_path=db_path
        )

        trace = add_trace(
            [],
            agent="Account Services Agent (Rohan)",
            action="EXECUTE_TRANSFER",
            details=f"Transfer of ₹{amount:,.2f} from {source_acc} to {dest_acc}: {result.message}",
            payload={"source": source_acc, "dest": dest_acc, "amount": amount},
            result=result.model_dump()
        )

        if result.success:
            resp_md = (
                f"### 💸 Transfer Successful\n\n"
                f"- **Reference UTR:** `{result.tx_id}`\n"
                f"- **From:** `{source_acc}`\n"
                f"- **Beneficiary:** `{dest_acc}`\n"
                f"- **Amount Sent:** `₹{result.amount:,.2f}`\n"
                f"- **Remaining Balance:** `₹{result.source_new_balance:,.2f}`\n\n"
                f"*Payment processed instantly over core banking ledger.*"
            )
        else:
            resp_md = (
                f"### ⚠️ Transfer Failed\n\n"
                f"**Reason:** {result.message}\n\n"
                f"No funds were deducted from your account."
            )

        return {
            "active_agent": "account_agent",
            "next_step": "end",
            "final_response": resp_md,
            "execution_trace": [trace]
        }

    # 3. Account Overview / Mini-Statement
    overview = get_account_overview(customer_id, db_path=db_path)
    trace = add_trace(
        [],
        agent="Account Services Agent (Rohan)",
        action="GET_ACCOUNT_OVERVIEW",
        details=f"Retrieved overview for {overview.name} ({customer_id}). Total Liquidity: ₹{overview.total_balance:,.2f}",
        payload={"customer_id": customer_id},
        result=overview.model_dump()
    )

    acc_lines = "\n".join([
        f"- **{acc.account_type.replace('_', ' ')}** (`{acc.account_id}`): **₹{acc.balance:,.2f}** [{acc.status}]"
        for acc in overview.accounts
    ])

    tx_lines = ""
    if overview.recent_transactions:
        tx_lines = "\n".join([
            f"- `{tx['timestamp'][:10]}` | **{tx['merchant']}** | `₹{abs(tx['amount']):,.2f}` ({tx['tx_type']})"
            + (" ⚠️ *Flagged*" if tx.get("is_flagged") else "")
            for tx in overview.recent_transactions[:4]
        ])
    else:
        tx_lines = "_No recent transactions on record._"

    resp_md = (
        f"### Namaste, {overview.name}! 🙏\n\n"
        f"Here is your official account portfolio overview:\n\n"
        f"**KYC:** `{overview.kyc_status}` | **Risk Tier:** `{overview.risk_tier}` | **CIBIL Score:** `{overview.credit_score}`\n\n"
        f"#### Your Accounts\n"
        f"{acc_lines}\n\n"
        f"**Total Available Liquidity:** `₹{overview.total_balance:,.2f}`\n\n"
        f"#### Recent Transactions\n"
        f"{tx_lines}"
    )

    return {
        "active_agent": "account_agent",
        "next_step": "end",
        "final_response": resp_md,
        "execution_trace": [trace]
    }
