"""
Shared utilities, LLM integration, and parameter extraction for Indian banking agents.
Supports ₹, Rs, INR, Lakhs extraction and Indian persona account resolution.
"""

import os
import re
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
from dotenv import load_dotenv

load_dotenv()

def get_llm():
    """Returns ChatOpenAI if API key available, else None for deterministic pipeline."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key and not api_key.startswith("your_"):
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(model="gpt-4o-mini", temperature=0)
        except Exception:
            return None
    return None


def extract_amount(text: str) -> Optional[float]:
    """Extract rupee amounts like ₹50,000, 350 rupees, Rs 15000, 2 lakh, etc."""
    # Check for Lakhs / Lacs: e.g. "2 lakh", "1.5 lakh", "35 lakh"
    lakh_match = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*(?:lakh|lac|lakhs|lacs)', text, re.IGNORECASE)
    if lakh_match:
        try:
            return float(lakh_match.group(1)) * 100000.0
        except ValueError:
            pass

    # Look for ₹ or Rs. or INR e.g. ₹50,000, Rs 5000, INR 8500
    match = re.search(r'(?:₹|rs\.?|inr|\$)\s*([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]{1,2})?|[0-9]+(?:\.[0-9]{1,2})?)', text, re.IGNORECASE)
    if match:
        val_str = match.group(1).replace(',', '')
        try:
            return float(val_str)
        except ValueError:
            pass

    # Look for "XX rupees" or "XX inr"
    match2 = re.search(r'([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]{1,2})?|[0-9]+)\s*(?:rupees|rupee|inr|rs|dollars|\$)', text, re.IGNORECASE)
    if match2:
        val_str = match2.group(1).replace(',', '')
        try:
            return float(val_str)
        except ValueError:
            pass

    # Look for bare numbers after transfer / loan / apply / send / pay
    match3 = re.search(r'(?:transfer|loan|apply for|send|pay|upi)\s+([0-9]{2,8})', text, re.IGNORECASE)
    if match3:
        try:
            return float(match3.group(1))
        except ValueError:
            pass

    return None


def resolve_recipient_account(recipient_name: str, db_path: str = "banking.db") -> Optional[str]:
    """Resolves Indian recipient name or account alias to an actual account ID."""
    from backend.database import get_session_factory, Customer, Account
    SessionFactory = get_session_factory(db_path)
    session = SessionFactory()
    try:
        lower = recipient_name.lower().strip()
        
        # Direct account ID match
        acc = session.query(Account).filter_by(account_id=recipient_name).first()
        if acc:
            return acc.account_id

        # Name mapping (with backward compatibility)
        name_alias = {
            "bhavna": "bhavna",
            "bob": "bhavna",
            "aarav": "aarav",
            "alice": "aarav",
            "chirag": "chirag",
            "charlie": "chirag"
        }
        target_name = name_alias.get(lower, lower)

        for cust in session.query(Customer).all():
            if cust.name.lower().startswith(target_name) or target_name in cust.name.lower():
                for a in cust.accounts:
                    if a.account_type in ["SAVINGS", "CURRENT"] and a.status == "ACTIVE":
                        return a.account_id
                if cust.accounts:
                    return cust.accounts[0].account_id

        # Fallback account defaults
        if "bhavna" in lower or "bob" in lower:
            return "ACC_BHAVNA_SAV"
        if "aarav" in lower or "alice" in lower:
            return "ACC_AARAV_SAV"
        if "chirag" in lower or "charlie" in lower:
            return "ACC_CHIRAG_SAV"

        return None
    finally:
        session.close()


def add_trace(
    execution_trace: list,
    agent: str,
    action: str,
    details: str,
    payload: Optional[Dict[str, Any]] = None,
    result: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Formats an execution step for agent observability."""
    return {
        "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
        "agent": agent,
        "action": action,
        "details": details,
        "payload": payload or {},
        "result": result or {}
    }
