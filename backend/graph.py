"""
LangGraph compilation and execution pipeline for Multi-Agent Banking System.
Configures supervisor routing, specialized agent nodes, and the Human-In-The-Loop gate.
"""

from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from backend.state import AgentState, create_initial_state
from backend.agents.supervisor import supervisor_node
from backend.agents.account_agent import account_agent_node
from backend.agents.fraud_agent import fraud_agent_node
from backend.agents.credit_agent import credit_agent_node
from backend.agents.hitl_gate import hitl_gate_node


def supervisor_router(state: AgentState) -> str:
    """Conditional edge from supervisor node."""
    next_step = state.get("next_step")
    if next_step == "account_agent":
        return "account_agent"
    elif next_step == "fraud_agent":
        return "fraud_agent"
    elif next_step == "credit_agent":
        return "credit_agent"
    return END


def account_router(state: AgentState) -> str:
    """Conditional edge from account agent."""
    if state.get("next_step") == "hitl_gate":
        return "hitl_gate"
    return END


def credit_router(state: AgentState) -> str:
    """Conditional edge from credit agent."""
    if state.get("next_step") == "hitl_gate":
        return "hitl_gate"
    return END


def hitl_router(state: AgentState) -> str:
    """Conditional edge from HITL Gate."""
    next_step = state.get("next_step")
    if next_step == "account_agent":
        return "account_agent"
    elif next_step == "credit_agent":
        return "credit_agent"
    return END


def build_banking_graph(checkpointer: Optional[Any] = None, interrupt_hitl: bool = True):
    """
    Constructs and compiles the multi-agent banking state graph.
    """
    workflow = StateGraph(AgentState)

    # Register Nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("account_agent", account_agent_node)
    workflow.add_node("fraud_agent", fraud_agent_node)
    workflow.add_node("credit_agent", credit_agent_node)
    workflow.add_node("hitl_gate", hitl_gate_node)

    # Set Entry Point
    workflow.set_entry_point("supervisor")

    # Add Directed & Conditional Edges
    workflow.add_conditional_edges(
        "supervisor",
        supervisor_router,
        {
            "account_agent": "account_agent",
            "fraud_agent": "fraud_agent",
            "credit_agent": "credit_agent",
            END: END
        }
    )

    workflow.add_conditional_edges(
        "account_agent",
        account_router,
        {
            "hitl_gate": "hitl_gate",
            END: END
        }
    )

    workflow.add_conditional_edges(
        "credit_agent",
        credit_router,
        {
            "hitl_gate": "hitl_gate",
            END: END
        }
    )

    workflow.add_edge("fraud_agent", END)

    workflow.add_conditional_edges(
        "hitl_gate",
        hitl_router,
        {
            "account_agent": "account_agent",
            "credit_agent": "credit_agent",
            END: END
        }
    )

    interrupt_nodes = ["hitl_gate"] if interrupt_hitl else []
    
    # Compile with or without checkpointer
    if checkpointer is not None:
        return workflow.compile(
            checkpointer=checkpointer,
            interrupt_before=interrupt_nodes if interrupt_hitl else None
        )
    return workflow.compile()


# Global in-memory checkpointer for multi-turn sessions
_memory_saver = MemorySaver()
_compiled_app = build_banking_graph(checkpointer=_memory_saver, interrupt_hitl=False)


def run_banking_turn(
    message: str,
    customer_id: str,
    db_path: str = "banking.db",
    thread_id: Optional[str] = None,
    hitl_decision: Optional[str] = None,
    existing_pending_hitl: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Executes a turn of the multi-agent graph with conversational state and HITL handling.
    """
    if thread_id is None:
        thread_id = f"session_{customer_id}"

    config = {"configurable": {"thread_id": thread_id}}

    # Handle HITL resume if decision provided
    if hitl_decision and existing_pending_hitl:
        resume_state: AgentState = {
            "messages": [{"role": "user", "content": f"[HUMAN_ACTION_{hitl_decision}]"}],
            "customer_id": customer_id,
            "active_agent": "hitl_gate",
            "next_step": existing_pending_hitl.get("requested_by", "account_agent"),
            "intent": "hitl_resolution",
            "execution_trace": [],
            "pending_hitl": existing_pending_hitl,
            "hitl_decision": hitl_decision,
            "final_response": None,
            "db_path": db_path
        }
        # Run from HITL Gate
        final_state = _compiled_app.invoke(resume_state, config=config)
        return final_state

    # Regular conversational invocation
    initial_state = create_initial_state(customer_id, message, db_path=db_path)
    final_state = _compiled_app.invoke(initial_state, config=config)
    return final_state
