"""
FastAPI Server for Apex OmniBank Multi-Agent System.
Connects the React frontend to the LangGraph Multi-Agent Engine and SQLite Core Ledger.
"""

import os
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

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

DB_PATH = "banking.db"
init_db(DB_PATH, seed=True)

app = FastAPI(
    title="Apex OmniBank Multi-Agent API",
    description="Enterprise Banking Multi-Agent Mesh with LangGraph, SQLite, and HITL Guardrails",
    version="1.0.0"
)

# Enable CORS for local Vite development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Request / Response Schemas
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    customer_id: str
    thread_id: Optional[str] = None


class HITLDecisionRequest(BaseModel):
    decision: str  # "APPROVED" or "REJECTED"
    customer_id: str
    pending_hitl: Dict[str, Any]
    thread_id: Optional[str] = None


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "mesh_status": "ACTIVE",
        "active_agents": ["supervisor", "account_agent", "fraud_agent", "credit_agent", "hitl_gate"]
    }


@app.get("/api/customers")
def get_customers():
    """Retrieve all personas with real-time balance calculations."""
    SessionFactory = get_session_factory(DB_PATH)
    session = SessionFactory()
    try:
        customers = session.query(Customer).all()
        result = []
        for c in customers:
            total_bal = sum(a.balance for a in c.accounts if a.status == "ACTIVE")
            cust_dict = c.to_dict()
            cust_dict["total_balance"] = round(total_bal, 2)
            cust_dict["account_count"] = len(c.accounts)
            result.append(cust_dict)
        return {"customers": result}
    finally:
        session.close()


@app.get("/api/customer/{customer_id}/overview")
def get_customer_profile(customer_id: str):
    """Retrieve deep customer profile including accounts, loans, and recent transactions."""
    try:
        overview = get_account_overview(customer_id, db_path=DB_PATH)
        return overview.model_dump()
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/chat")
def chat_with_mesh(req: ChatRequest):
    """Process a natural language banking instruction via LangGraph Multi-Agent Topology."""
    try:
        thread = req.thread_id or f"session_{req.customer_id}"
        graph_result = run_banking_turn(
            message=req.message,
            customer_id=req.customer_id,
            db_path=DB_PATH,
            thread_id=thread
        )
        return {
            "active_agent": graph_result.get("active_agent", "supervisor"),
            "intent": graph_result.get("intent"),
            "final_response": graph_result.get("final_response", "Request processed."),
            "execution_trace": graph_result.get("execution_trace", []),
            "pending_hitl": graph_result.get("pending_hitl")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/hitl/decision")
def submit_hitl_decision(req: HITLDecisionRequest):
    """Submit operator approval or rejection for an interrupted high-value action."""
    try:
        thread = req.thread_id or f"session_{req.customer_id}"
        graph_result = run_banking_turn(
            message=f"[HUMAN_ACTION_{req.decision}]",
            customer_id=req.customer_id,
            db_path=DB_PATH,
            thread_id=thread,
            hitl_decision=req.decision,
            existing_pending_hitl=req.pending_hitl
        )
        return {
            "active_agent": graph_result.get("active_agent", "supervisor"),
            "intent": "hitl_resolution",
            "final_response": graph_result.get("final_response", ""),
            "execution_trace": graph_result.get("execution_trace", []),
            "pending_hitl": graph_result.get("pending_hitl")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ledger/tables")
def get_ledger_tables():
    """Returns a full real-time snapshot of the SQLite core banking engine tables."""
    SessionFactory = get_session_factory(DB_PATH)
    session = SessionFactory()
    try:
        accounts = [a.to_dict() for a in session.query(Account).all()]
        txs = [t.to_dict() for t in session.query(Transaction).order_by(Transaction.timestamp.desc()).limit(25).all()]
        loans = [l.to_dict() for l in session.query(Loan).all()]
        audits = [ad.to_dict() for ad in session.query(AuditLog).order_by(AuditLog.id.desc()).limit(25).all()]
        return {
            "accounts": accounts,
            "transactions": txs,
            "loans": loans,
            "audit_logs": audits
        }
    finally:
        session.close()


@app.post("/api/database/reset")
def reset_database_endpoint():
    """Restores SQLite database to pristine seeded state."""
    reset_db(DB_PATH)
    return {"status": "success", "message": "Database reset to initial seed state."}


# Mount built React static files if present in frontend/dist
frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.server:app", host="0.0.0.0", port=8000, reload=True)
