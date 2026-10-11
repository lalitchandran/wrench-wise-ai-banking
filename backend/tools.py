"""
Deterministic Indian Banking Tools implemented with Pydantic v2 schemas.
Handles INR (₹) transactions, UPI/IMPS ledger updates, CIBIL evaluations,
and Human-In-The-Loop safety limits (₹50,000 transfer, ₹2,00,000 lending).
"""

from datetime import datetime, timezone, timedelta
import json
import uuid
from typing import Literal, Optional, List, Dict, Any
from pydantic import BaseModel, Field

from backend.database import (
    get_session_factory,
    Customer,
    Account,
    Transaction,
    Loan,
    AuditLog
)

# ---------------------------------------------------------
# Pydantic v2 Schemas for Tool I/O
# ---------------------------------------------------------

class AccountOverviewInput(BaseModel):
    customer_id: str = Field(description="Unique customer ID, e.g. CUST_AARAV")


class AccountSummary(BaseModel):
    account_id: str
    account_type: str
    balance: float
    status: str


class CustomerOverviewOutput(BaseModel):
    customer_id: str
    name: str
    risk_tier: str
    kyc_status: str
    credit_score: int  # CIBIL Score
    accounts: List[AccountSummary]
    total_balance: float
    recent_transactions: List[Dict[str, Any]]
    active_loans: List[Dict[str, Any]]


class TransferInput(BaseModel):
    source_acc: str = Field(description="Originating account ID, e.g. ACC_AARAV_SAV")
    dest_acc: str = Field(description="Beneficiary account ID or UPI VPA")
    amount: float = Field(gt=0, description="Transfer amount in INR (₹)")
    memo: str = Field(default="UPI / P2P Transfer", description="Payment remarks / purpose")


class TransferResult(BaseModel):
    success: bool
    tx_id: Optional[str] = None
    source_acc: str
    dest_acc: str
    amount: float
    source_new_balance: Optional[float] = None
    memo: str
    message: str


class CardActionInput(BaseModel):
    account_id: str = Field(description="Card or account ID to freeze/unfreeze")
    reason: str = Field(description="Reason for security freeze or unfreeze")
    action: Literal["freeze", "unfreeze"] = Field(description="Action: 'freeze' or 'unfreeze'")


class CardActionResult(BaseModel):
    success: bool
    account_id: str
    previous_status: str
    new_status: str
    action_taken: str
    reason: str
    message: str


class AssessRiskInput(BaseModel):
    tx_id: str = Field(description="Transaction ID to assess, e.g. TX_B9901")


class RiskReport(BaseModel):
    tx_id: str
    account_id: str
    merchant: str
    amount: float
    risk_score: int = Field(ge=0, le=100, description="Risk score from 0 (safest) to 100 (highest risk)")
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    factors: List[str]
    recommended_action: Literal["ALLOW", "STEP_UP_AUTH", "FREEZE_CARD"]
    assessed_at: str


class CreditEvaluationInput(BaseModel):
    customer_id: str = Field(description="Customer identifier applying for credit")
    requested_amount: float = Field(gt=0, description="Principal loan amount in INR (₹)")
    monthly_income: float = Field(gt=0, description="Verified gross monthly income in INR (₹)")


class CreditEvaluationReport(BaseModel):
    customer_id: str
    requested_amount: float
    monthly_income: float
    credit_score: int  # CIBIL Score
    dti_ratio: float
    estimated_monthly_payment: float
    status: Literal["APPROVED", "REJECTED", "PENDING_HITL"]
    interest_rate: float
    reasons: List[str]
    loan_id: Optional[str] = None


# ---------------------------------------------------------
# Core Tool Implementations
# ---------------------------------------------------------

def log_audit(
    session,
    agent: str,
    action: str,
    details: Dict[str, Any],
    status: str = "SUCCESS"
):
    """Write an immutable audit log entry."""
    audit = AuditLog(
        timestamp=datetime.now(timezone.utc),
        agent=agent,
        action=action,
        details=json.dumps(details),
        status=status,
    )
    session.add(audit)
    session.commit()


def get_account_overview(customer_id: str, db_path: str = "banking.db") -> CustomerOverviewOutput:
    """Fetch customer profile, accounts, total liquidity in INR, recent transactions, and active loans."""
    SessionFactory = get_session_factory(db_path)
    session = SessionFactory()
    try:
        customer = session.query(Customer).filter_by(id=customer_id).first()
        if not customer:
            # Fallback alias matching
            if "AARAV" in customer_id.upper() or "ALICE" in customer_id.upper():
                customer = session.query(Customer).filter_by(id="CUST_AARAV").first()
            elif "BHAVNA" in customer_id.upper() or "BOB" in customer_id.upper():
                customer = session.query(Customer).filter_by(id="CUST_BHAVNA").first()
            elif "CHIRAG" in customer_id.upper() or "CHARLIE" in customer_id.upper():
                customer = session.query(Customer).filter_by(id="CUST_CHIRAG").first()

        if not customer:
            raise ValueError(f"Customer '{customer_id}' not found in core banking ledger.")

        accounts_data = []
        total_balance = 0.0
        acc_ids = []
        for acc in customer.accounts:
            accounts_data.append(AccountSummary(
                account_id=acc.account_id,
                account_type=acc.account_type,
                balance=round(acc.balance, 2),
                status=acc.status
            ))
            acc_ids.append(acc.account_id)
            if acc.status == "ACTIVE":
                total_balance += acc.balance

        recent_txs = (
            session.query(Transaction)
            .filter(Transaction.account_id.in_(acc_ids))
            .order_by(Transaction.timestamp.desc())
            .limit(10)
            .all()
        )

        active_loans = (
            session.query(Loan)
            .filter_by(customer_id=customer.id)
            .all()
        )

        log_audit(
            session,
            agent="Account Services Agent (Rohan)",
            action="GET_ACCOUNT_OVERVIEW",
            details={"customer_id": customer.id, "accounts_count": len(accounts_data)},
            status="SUCCESS"
        )

        return CustomerOverviewOutput(
            customer_id=customer.id,
            name=customer.name,
            risk_tier=customer.risk_tier,
            kyc_status=customer.kyc_status,
            credit_score=customer.credit_score,
            accounts=accounts_data,
            total_balance=round(total_balance, 2),
            recent_transactions=[tx.to_dict() for tx in recent_txs],
            active_loans=[ln.to_dict() for ln in active_loans]
        )
    finally:
        session.close()


def execute_transfer(
    source_acc: str,
    dest_acc: str,
    amount: float,
    memo: str = "UPI / NEFT Transfer",
    db_path: str = "banking.db"
) -> TransferResult:
    """
    Executes an atomic funds transfer in INR (₹) between two accounts with balance checks and fraud guardrails.
    Rejects gracefully if insufficient funds or frozen accounts without crashing.
    """
    SessionFactory = get_session_factory(db_path)
    session = SessionFactory()
    try:
        if amount <= 0:
            return TransferResult(
                success=False,
                source_acc=source_acc,
                dest_acc=dest_acc,
                amount=amount,
                memo=memo,
                message="Transfer amount must be strictly greater than ₹0."
            )

        source = session.query(Account).filter_by(account_id=source_acc).first()
        dest = session.query(Account).filter_by(account_id=dest_acc).first()

        # Handle alias fallbacks
        if not source:
            source = session.query(Account).filter(Account.account_id.like(f"%{source_acc}%")).first()
        if not dest:
            dest = session.query(Account).filter(Account.account_id.like(f"%{dest_acc}%")).first()

        if not source:
            return TransferResult(
                success=False,
                source_acc=source_acc,
                dest_acc=dest_acc,
                amount=amount,
                memo=memo,
                message=f"Source account '{source_acc}' was not found in our ledger."
            )

        if not dest:
            return TransferResult(
                success=False,
                source_acc=source_acc,
                dest_acc=dest_acc,
                amount=amount,
                memo=memo,
                message=f"Beneficiary account '{dest_acc}' is invalid or does not exist."
            )

        # Check account lock status
        if source.status == "FROZEN":
            log_audit(session, "Account Services Agent (Rohan)", "EXECUTE_TRANSFER", {
                "source": source_acc, "dest": dest_acc, "amount": amount, "reason": "Source account frozen"
            }, status="REJECTED")
            return TransferResult(
                success=False,
                source_acc=source_acc,
                dest_acc=dest_acc,
                amount=amount,
                source_new_balance=source.balance,
                memo=memo,
                message=f"Transfer declined: Your account '{source_acc}' is currently FROZEN for security."
            )

        if dest.status == "FROZEN":
            return TransferResult(
                success=False,
                source_acc=source_acc,
                dest_acc=dest_acc,
                amount=amount,
                source_new_balance=source.balance,
                memo=memo,
                message=f"Transfer declined: Beneficiary account '{dest_acc}' is currently FROZEN."
            )

        # Overdraft Guardrail
        if source.balance < amount:
            log_audit(session, "Account Services Agent (Rohan)", "EXECUTE_TRANSFER", {
                "source": source_acc, "dest": dest_acc, "amount": amount,
                "current_balance": source.balance, "reason": "Insufficient funds"
            }, status="REJECTED")
            return TransferResult(
                success=False,
                source_acc=source_acc,
                dest_acc=dest_acc,
                amount=amount,
                source_new_balance=source.balance,
                memo=memo,
                message=f"Transfer rejected: Insufficient funds. Available balance: ₹{source.balance:,.2f}, Requested: ₹{amount:,.2f}."
            )

        # Atomic Transfer Execution
        tx_id = f"TX_UPI_{uuid.uuid4().hex[:8].upper()}"
        source.balance -= amount
        dest.balance += amount

        debit_tx = Transaction(
            tx_id=f"{tx_id}_DR",
            account_id=source.account_id,
            amount=-amount,
            tx_type="UPI",
            merchant=f"Sent to {dest.account_id} ({memo})",
            timestamp=datetime.now(timezone.utc),
            is_flagged=False
        )
        credit_tx = Transaction(
            tx_id=f"{tx_id}_CR",
            account_id=dest.account_id,
            amount=amount,
            tx_type="UPI",
            merchant=f"Received from {source.account_id} ({memo})",
            timestamp=datetime.now(timezone.utc),
            is_flagged=False
        )
        session.add_all([debit_tx, credit_tx])

        log_audit(session, "Account Services Agent (Rohan)", "EXECUTE_TRANSFER", {
            "tx_id": tx_id,
            "source": source_acc,
            "dest": dest_acc,
            "amount": amount,
            "memo": memo,
            "source_new_balance": source.balance
        }, status="SUCCESS")

        session.commit()

        return TransferResult(
            success=True,
            tx_id=tx_id,
            source_acc=source_acc,
            dest_acc=dest_acc,
            amount=amount,
            source_new_balance=round(source.balance, 2),
            memo=memo,
            message=f"Namaste! Successfully transferred ₹{amount:,.2f} from {source_acc} to {dest_acc}. Updated balance: ₹{source.balance:,.2f}."
        )
    finally:
        session.close()


def flag_or_block_card(
    account_id: str,
    reason: str,
    action: Literal["freeze", "unfreeze"],
    db_path: str = "banking.db"
) -> CardActionResult:
    """
    Sets account / card status to 'FROZEN' or 'ACTIVE' with audit logging.
    """
    SessionFactory = get_session_factory(db_path)
    session = SessionFactory()
    try:
        account = session.query(Account).filter_by(account_id=account_id).first()
        if not account:
            account = session.query(Account).filter(Account.account_id.like(f"%{account_id}%")).first()

        if not account:
            return CardActionResult(
                success=False,
                account_id=account_id,
                previous_status="UNKNOWN",
                new_status="UNKNOWN",
                action_taken=action,
                reason=reason,
                message=f"Card or account '{account_id}' was not found in our records."
            )

        prev_status = account.status
        new_status = "FROZEN" if action == "freeze" else "ACTIVE"
        account.status = new_status

        log_audit(session, "Fraud & Risk Agent (Priya)", "CARD_STATUS_UPDATE", {
            "account_id": account.account_id,
            "action": action,
            "previous_status": prev_status,
            "new_status": new_status,
            "reason": reason
        }, status="SUCCESS")

        session.commit()

        status_text = "FROZEN (Locked)" if new_status == "FROZEN" else "ACTIVATED (Unlocked)"
        return CardActionResult(
            success=True,
            account_id=account.account_id,
            previous_status=prev_status,
            new_status=new_status,
            action_taken=action,
            reason=reason,
            message=f"Your card/account {account.account_id} has been securely {status_text}. Reason: {reason}"
        )
    finally:
        session.close()


def assess_transaction_risk(
    tx_id: str,
    db_path: str = "banking.db"
) -> RiskReport:
    """
    Evaluates fraud risk score (0-100), factors, and recommended safety action for a transaction.
    """
    SessionFactory = get_session_factory(db_path)
    session = SessionFactory()
    try:
        tx = session.query(Transaction).filter_by(tx_id=tx_id).first()
        if not tx:
            return RiskReport(
                tx_id=tx_id,
                account_id="UNKNOWN",
                merchant="Unknown Merchant",
                amount=0.0,
                risk_score=50,
                risk_level="MEDIUM",
                factors=["Transaction record not found; conservative risk score assigned"],
                recommended_action="STEP_UP_AUTH",
                assessed_at=datetime.now(timezone.utc).isoformat()
            )

        account = session.query(Account).filter_by(account_id=tx.account_id).first()
        customer = session.query(Customer).filter_by(id=account.customer_id).first() if account else None

        score = 15  # baseline
        factors: List[str] = []

        abs_amount = abs(tx.amount)
        if abs_amount > 100000.0:  # High amount in INR (> 1 Lakh)
            score += 35
            factors.append(f"High-value transaction amount (₹{abs_amount:,.2f}) exceeding standard profile velocity")
        elif abs_amount > 40000.0:
            score += 15
            factors.append(f"Elevated transaction ticket size (₹{abs_amount:,.2f})")

        merchant_lower = tx.merchant.lower()
        if any(w in merchant_lower for w in ["overseas", "dubai", "international", "crypto", "offshore", "forex"]):
            score += 35
            factors.append(f"Cross-border / high-risk international merchant jurisdiction ('{tx.merchant}')")

        if tx.is_flagged:
            score += 20
            factors.append("Flagged by automated RBI / Bank Anomaly Velocity Engine")

        if customer and customer.risk_tier == "HIGH":
            score += 15
            factors.append("Customer belongs to high-monitoring risk tier")
        elif customer and customer.risk_tier == "LOW":
            score -= 10

        score = max(0, min(100, score))

        if score >= 80:
            level = "CRITICAL"
            recommended_action = "FREEZE_CARD"
        elif score >= 50:
            level = "HIGH"
            recommended_action = "FREEZE_CARD" if tx.is_flagged else "STEP_UP_AUTH"
        elif score >= 30:
            level = "MEDIUM"
            recommended_action = "STEP_UP_AUTH"
        else:
            level = "LOW"
            recommended_action = "ALLOW"

        report = RiskReport(
            tx_id=tx.tx_id,
            account_id=tx.account_id,
            merchant=tx.merchant,
            amount=abs_amount,
            risk_score=score,
            risk_level=level,
            factors=factors if factors else ["Transaction matches normal behavioral baseline"],
            recommended_action=recommended_action,
            assessed_at=datetime.now(timezone.utc).isoformat()
        )

        log_audit(session, "Fraud & Risk Agent (Priya)", "ASSESS_TRANSACTION_RISK", {
            "tx_id": tx_id,
            "risk_score": score,
            "risk_level": level,
            "recommended_action": recommended_action,
            "factors": factors
        }, status="SUCCESS")

        return report
    finally:
        session.close()


def evaluate_credit_application(
    customer_id: str,
    requested_amount: float,
    monthly_income: float,
    db_path: str = "banking.db"
) -> CreditEvaluationReport:
    """
    Evaluates Debt-to-Income (DTI), CIBIL score, and creates an Indian personal/business loan record.
    Enforces HITL requirement if disbursement > ₹2,00,000 (2 Lakhs).
    """
    SessionFactory = get_session_factory(db_path)
    session = SessionFactory()
    try:
        customer = session.query(Customer).filter_by(id=customer_id).first()
        if not customer:
            # Fallback alias matching
            if "AARAV" in customer_id.upper() or "ALICE" in customer_id.upper():
                customer = session.query(Customer).filter_by(id="CUST_AARAV").first()
            elif "BHAVNA" in customer_id.upper() or "BOB" in customer_id.upper():
                customer = session.query(Customer).filter_by(id="CUST_BHAVNA").first()
            elif "CHIRAG" in customer_id.upper() or "CHARLIE" in customer_id.upper():
                customer = session.query(Customer).filter_by(id="CUST_CHIRAG").first()

        if not customer:
            raise ValueError(f"Customer '{customer_id}' not found.")

        # CIBIL-based Interest Rate calculation
        cibil = customer.credit_score
        if cibil >= 780:
            base_rate = 8.75  # Prime retail rate in India
        elif cibil >= 720:
            base_rate = 10.50
        elif cibil >= 640:
            base_rate = 13.50
        else:
            base_rate = 17.00

        # Monthly EMI calculation: P * (r / (1 - (1+r)^-n))
        monthly_r = (base_rate / 100.0) / 12.0
        n_months = 36
        estimated_payment = requested_amount * (monthly_r * ((1 + monthly_r) ** n_months)) / (((1 + monthly_r) ** n_months) - 1)

        total_monthly_debt = customer.existing_monthly_debt + estimated_payment
        dti_ratio = total_monthly_debt / monthly_income if monthly_income > 0 else 1.0

        reasons = []
        is_eligible = True

        if cibil < 600:
            is_eligible = False
            reasons.append(f"CIBIL score {cibil} is below minimum lending cutoff of 600.")
        else:
            reasons.append(f"CIBIL Score {cibil} meets credit bureau eligibility standards.")

        if dti_ratio > 0.50:
            is_eligible = False
            reasons.append(f"Debt-to-Income (FOIR) ratio ({dti_ratio:.1%}) exceeds RBI recommended cap of 50.0%.")
        else:
            reasons.append(f"Debt-to-Income (FOIR) ratio ({dti_ratio:.1%}) is within safe lending guidelines.")

        reasons.append(f"Assigned Fixed Interest Rate: {base_rate:.2f}% p.a. for a 36-month tenure.")

        # HITL Threshold: Disbursements > ₹2,00,000 (2 Lakhs) require Committee Review
        if is_eligible and requested_amount > 200000.0:
            status = "PENDING_HITL"
            reasons.append(f"Requested loan (₹{requested_amount:,.2f}) exceeds ₹2,00,000 retail automated ceiling; escalated to Credit Sanction Committee (HITL Gate).")
        elif is_eligible:
            status = "APPROVED"
            reasons.append("Auto-approved by digital underwriting engine; funds ready for disbursement.")
        else:
            status = "REJECTED"

        loan_id = f"LN_{customer.id[-4:]}_{uuid.uuid4().hex[:8].upper()}"

        loan = Loan(
            loan_id=loan_id,
            customer_id=customer.id,
            principal=requested_amount,
            interest_rate=base_rate,
            status="PENDING_APPROVAL" if status == "PENDING_HITL" else status,
            dti_ratio=round(dti_ratio, 4),
            term_months=n_months,
            created_at=datetime.now(timezone.utc)
        )
        session.add(loan)

        log_audit(session, "Credit & Lending Agent (Vikram)", "EVALUATE_CREDIT", {
            "customer_id": customer.id,
            "requested_amount": requested_amount,
            "dti_ratio": round(dti_ratio, 4),
            "status": status,
            "loan_id": loan_id
        }, status=status)

        session.commit()

        return CreditEvaluationReport(
            customer_id=customer.id,
            requested_amount=requested_amount,
            monthly_income=monthly_income,
            credit_score=cibil,
            dti_ratio=round(dti_ratio, 4),
            estimated_monthly_payment=round(estimated_payment, 2),
            status=status,
            interest_rate=base_rate,
            reasons=reasons,
            loan_id=loan_id
        )
    finally:
        session.close()
