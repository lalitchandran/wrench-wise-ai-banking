"""
Human-In-The-Loop (HITL) Gate Node.
Intercepts high-value transactions (> $5,000 transfers or > $20,000 credit disbursements).
Pauses execution until operator/user approves or rejects.
"""

from typing import Dict, Any
from backend.state import AgentState
from backend.agents.utils import add_trace


def hitl_gate_node(state: AgentState) -> Dict[str, Any]:
    """
    Evaluates whether the pending high-value action has human approval.
    If approved or rejected, routes back to the originating agent to finalize.
    """
    pending_hitl = state.get("pending_hitl")
    hitl_decision = state.get("hitl_decision")

    if not pending_hitl:
        # No pending approval needed
        return {
            "active_agent": "hitl_gate",
            "next_step": "end",
        }

    # If decision was provided ("APPROVED" or "REJECTED")
    if hitl_decision in ["APPROVED", "REJECTED"]:
        requested_by = pending_hitl.get("requested_by", "account_agent")
        trace = add_trace(
            [],
            agent="HITL Compliance Gate",
            action=f"DECISION_{hitl_decision}",
            details=f"Human operator provided decision: {hitl_decision} for {pending_hitl.get('summary')}.",
            payload=pending_hitl,
            result={"decision": hitl_decision}
        )
        return {
            "active_agent": "hitl_gate",
            "next_step": requested_by,
            "execution_trace": [trace]
        }

    # If waiting for decision
    trace = add_trace(
        [],
        agent="HITL Compliance Gate",
        action="PAUSED_AWAITING_CONFIRMATION",
        details=f"Execution paused at HITL Gate: {pending_hitl.get('summary')}. Requires human review.",
        payload=pending_hitl
    )
    return {
        "active_agent": "hitl_gate",
        "next_step": "paused",
        "execution_trace": [trace]
    }
