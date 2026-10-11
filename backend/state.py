"""
State definitions for LangGraph Multi-Agent Banking Engine.
Defines AgentState, trace structures, and HITL payload schemas.
"""

from typing import TypedDict, Annotated, List, Dict, Any, Optional
import operator
from datetime import datetime, timezone


def merge_dicts(a: Optional[Dict[str, Any]], b: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Custom reducer for dict state that replaces or clears dict."""
    if b is None:
        return None
    return b


class ExecutionStep(TypedDict, total=False):
    timestamp: str
    agent: str
    action: str
    tool_name: Optional[str]
    payload: Optional[Dict[str, Any]]
    result: Optional[Dict[str, Any]]
    decision: Optional[str]
    details: Optional[str]


class HITLRequest(TypedDict, total=False):
    action_type: str  # "fund_transfer" | "credit_disbursement"
    requested_by: str  # "account_agent" | "credit_agent"
    amount: float
    threshold: float
    summary: str
    payload: Dict[str, Any]
    status: str  # "PENDING" | "APPROVED" | "REJECTED"


class AgentState(TypedDict, total=False):
    # Chat message history
    messages: Annotated[List[Any], operator.add]
    
    # Active authenticated customer
    customer_id: str
    
    # Currently executing agent / routing decision
    active_agent: str
    next_step: Optional[str]
    intent: Optional[str]
    
    # Traceability for UI visualization & auditing
    execution_trace: Annotated[List[Dict[str, Any]], operator.add]
    
    # Human-In-The-Loop gate data
    pending_hitl: Optional[Dict[str, Any]]
    hitl_decision: Optional[str]  # "APPROVED", "REJECTED", or None
    
    # Output response rendered to customer
    final_response: Optional[str]
    
    # SQLite DB connection path
    db_path: str


def create_initial_state(customer_id: str, message: str, db_path: str = "banking.db") -> AgentState:
    """Helper to initialize graph state with a user message."""
    return {
        "messages": [{"role": "user", "content": message}],
        "customer_id": customer_id,
        "active_agent": "supervisor",
        "next_step": None,
        "intent": None,
        "execution_trace": [{
            "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
            "agent": "supervisor",
            "action": "INIT",
            "details": f"Session initialized for {customer_id}: '{message}'",
        }],
        "pending_hitl": None,
        "hitl_decision": None,
        "final_response": None,
        "db_path": db_path
    }
