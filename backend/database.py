"""
Database layer for Simulated Core Banking Engine (Indian Banking System).
Uses SQLite with SQLAlchemy ORM.
Features Indian Rupee (INR - ₹), CIBIL credit scores, PAN/Aadhaar KYC,
and realistic Indian customer personas: Aarav Sharma, Bhavna Patel, Chirag Verma.
"""

from datetime import datetime, timezone, timedelta
import os
import json
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    create_engine, Column, String, Float, Integer, Boolean, DateTime, ForeignKey, Text
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session

Base = declarative_base()


class Customer(Base):
    __tablename__ = "customers"

    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    risk_tier = Column(String(20), nullable=False, default="LOW")  # LOW, MEDIUM, HIGH
    kyc_status = Column(String(20), nullable=False, default="VERIFIED")  # VERIFIED, PENDING, FAILED
    credit_score = Column(Integer, nullable=False, default=750)  # CIBIL Score (300-900)
    monthly_income = Column(Float, nullable=False, default=75000.0)  # INR ₹
    existing_monthly_debt = Column(Float, nullable=False, default=15000.0)  # INR ₹

    accounts = relationship("Account", back_populates="customer", cascade="all, delete-orphan")
    loans = relationship("Loan", back_populates="customer", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "risk_tier": self.risk_tier,
            "kyc_status": self.kyc_status,
            "credit_score": self.credit_score,
            "monthly_income": self.monthly_income,
            "existing_monthly_debt": self.existing_monthly_debt,
        }


class Account(Base):
    __tablename__ = "accounts"

    account_id = Column(String(50), primary_key=True)
    customer_id = Column(String(50), ForeignKey("customers.id"), nullable=False)
    account_type = Column(String(30), nullable=False)  # SAVINGS, CURRENT, CREDIT_CARD
    balance = Column(Float, nullable=False, default=0.0)  # INR ₹
    status = Column(String(20), nullable=False, default="ACTIVE")  # ACTIVE, FROZEN, CLOSED

    customer = relationship("Customer", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "account_id": self.account_id,
            "customer_id": self.customer_id,
            "account_type": self.account_type,
            "balance": round(self.balance, 2),
            "status": self.status,
        }


class Transaction(Base):
    __tablename__ = "transactions"

    tx_id = Column(String(50), primary_key=True)
    account_id = Column(String(50), ForeignKey("accounts.account_id"), nullable=False)
    amount = Column(Float, nullable=False)  # INR ₹
    tx_type = Column(String(30), nullable=False)  # UPI, IMPS, NEFT, PURCHASE, SALARY
    merchant = Column(String(100), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    is_flagged = Column(Boolean, nullable=False, default=False)

    account = relationship("Account", back_populates="transactions")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tx_id": self.tx_id,
            "account_id": self.account_id,
            "amount": round(self.amount, 2),
            "tx_type": self.tx_type,
            "merchant": self.merchant,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "is_flagged": self.is_flagged,
        }


class Loan(Base):
    __tablename__ = "loans"

    loan_id = Column(String(50), primary_key=True)
    customer_id = Column(String(50), ForeignKey("customers.id"), nullable=False)
    principal = Column(Float, nullable=False)  # INR ₹
    interest_rate = Column(Float, nullable=False)  # Annual % e.g., 8.5 for 8.5%
    status = Column(String(30), nullable=False, default="PENDING")  # APPROVED, REJECTED, PENDING_APPROVAL, ACTIVE
    dti_ratio = Column(Float, nullable=False)
    term_months = Column(Integer, nullable=False, default=36)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    customer = relationship("Customer", back_populates="loans")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "loan_id": self.loan_id,
            "customer_id": self.customer_id,
            "principal": round(self.principal, 2),
            "interest_rate": round(self.interest_rate, 2),
            "status": self.status,
            "dti_ratio": round(self.dti_ratio, 4),
            "term_months": self.term_months,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    agent = Column(String(50), nullable=False)
    action = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    status = Column(String(30), nullable=False, default="SUCCESS")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "agent": self.agent,
            "action": self.action,
            "details": self.details,
            "status": self.status,
        }


def get_engine(db_path: str = "banking.db"):
    return create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False}
    )


def get_session_factory(db_path: str = "banking.db"):
    engine = get_engine(db_path)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def seed_database(session: Session):
    """Seed realistic initial Indian banking data for Aarav, Bhavna, and Chirag."""
    if session.query(Customer).first():
        return

    now = datetime.now(timezone.utc)

    # 1. Aarav Sharma (Prime customer, high balance, clean history, Bengaluru tech leader)
    aarav = Customer(
        id="CUST_AARAV",
        name="Aarav Sharma",
        email="aarav.sharma@bharatapex.in",
        risk_tier="LOW",
        kyc_status="VERIFIED",  # Aadhaar & PAN e-KYC Verified
        credit_score=815,       # CIBIL Score 815 (Excellent)
        monthly_income=225000.0, # ₹2,25,000 / month
        existing_monthly_debt=22000.0,
    )
    acc_aarav_sav = Account(
        account_id="ACC_AARAV_SAV",
        customer_id="CUST_AARAV",
        account_type="SAVINGS",
        balance=285000.00,  # ₹2,85,000.00
        status="ACTIVE"
    )
    acc_aarav_fd = Account(
        account_id="ACC_AARAV_FD",
        customer_id="CUST_AARAV",
        account_type="FIXED_DEPOSIT",
        balance=540000.00,  # ₹5,40,000.00
        status="ACTIVE"
    )
    tx_aarav_1 = Transaction(
        tx_id="TX_A101",
        account_id="ACC_AARAV_SAV",
        amount=-3450.00,
        tx_type="UPI",
        merchant="Swiggy Gourmet Bangalore",
        timestamp=now - timedelta(days=1, hours=3),
        is_flagged=False
    )
    tx_aarav_2 = Transaction(
        tx_id="TX_A102",
        account_id="ACC_AARAV_SAV",
        amount=225000.00,
        tx_type="SALARY",
        merchant="Tata Consultancy Monthly Salary",
        timestamp=now - timedelta(days=5),
        is_flagged=False
    )
    tx_aarav_3 = Transaction(
        tx_id="TX_A103",
        account_id="ACC_AARAV_FD",
        amount=8450.00,
        tx_type="INTEREST",
        merchant="Quarterly Fixed Deposit Yield",
        timestamp=now - timedelta(days=15),
        is_flagged=False
    )

    # 2. Bhavna Patel (High transaction velocity, flagged overseas charge pending review, Mumbai)
    bhavna = Customer(
        id="CUST_BHAVNA",
        name="Bhavna Patel",
        email="bhavna.patel@fintechpulse.in",
        risk_tier="MEDIUM",
        kyc_status="VERIFIED",
        credit_score=725,       # CIBIL Score 725
        monthly_income=110000.0, # ₹1,10,000 / month
        existing_monthly_debt=28000.0,
    )
    acc_bhavna_sav = Account(
        account_id="ACC_BHAVNA_SAV",
        customer_id="CUST_BHAVNA",
        account_type="SAVINGS",
        balance=62000.00,   # ₹62,000.00
        status="ACTIVE"
    )
    acc_bhavna_cc = Account(
        account_id="ACC_BHAVNA_CC",
        customer_id="CUST_BHAVNA",
        account_type="CREDIT_CARD",
        balance=48500.00,   # ₹48,500.00
        status="ACTIVE"
    )
    tx_bhavna_flagged = Transaction(
        tx_id="TX_B9901",
        account_id="ACC_BHAVNA_CC",
        amount=148999.00,   # ₹1,48,999.00 suspicious overseas transaction in Dubai!
        tx_type="PURCHASE",
        merchant="Dubai Luxury Electronics & Gold (Overseas)",
        timestamp=now - timedelta(hours=3),
        is_flagged=True     # Flagged suspicious international charge!
    )
    tx_bhavna_2 = Transaction(
        tx_id="TX_B9902",
        account_id="ACC_BHAVNA_SAV",
        amount=-850.00,
        tx_type="UPI",
        merchant="Blinkit Quick Grocery Mumbai",
        timestamp=now - timedelta(hours=7),
        is_flagged=False
    )
    tx_bhavna_3 = Transaction(
        tx_id="TX_B9903",
        account_id="ACC_BHAVNA_SAV",
        amount=-2400.00,
        tx_type="UPI",
        merchant="Zomato Dining Bandra",
        timestamp=now - timedelta(days=2),
        is_flagged=False
    )

    # 3. Chirag Verma (Moderate credit, requesting auto/personal loan, Delhi NCR)
    chirag = Customer(
        id="CUST_CHIRAG",
        name="Chirag Verma",
        email="chirag.verma@delhicapitals.in",
        risk_tier="MEDIUM",
        kyc_status="VERIFIED",
        credit_score=648,       # CIBIL Score 648 (Fair)
        monthly_income=48000.0, # ₹48,000 / month
        existing_monthly_debt=16500.0,
    )
    acc_chirag_sav = Account(
        account_id="ACC_CHIRAG_SAV",
        customer_id="CUST_CHIRAG",
        account_type="SAVINGS",
        balance=18500.00,   # ₹18,500.00
        status="ACTIVE"
    )
    acc_chirag_upi = Account(
        account_id="ACC_CHIRAG_UPI",
        customer_id="CUST_CHIRAG",
        account_type="UPI_WALLET",
        balance=4200.00,    # ₹4,200.00
        status="ACTIVE"
    )
    tx_chirag_1 = Transaction(
        tx_id="TX_C301",
        account_id="ACC_CHIRAG_SAV",
        amount=-750.00,
        tx_type="UPI",
        merchant="Indian Oil Corporation Petrol Pump",
        timestamp=now - timedelta(days=1),
        is_flagged=False
    )
    tx_chirag_2 = Transaction(
        tx_id="TX_C302",
        account_id="ACC_CHIRAG_SAV",
        amount=48000.00,
        tx_type="SALARY",
        merchant="NCR Logistics Monthly Payroll",
        timestamp=now - timedelta(days=6),
        is_flagged=False
    )

    # Pre-seeded active loan for Chirag to demonstrate DTI impact
    loan_chirag_existing = Loan(
        loan_id="LN_C201",
        customer_id="CUST_CHIRAG",
        principal=80000.00,  # ₹80,000 Two-Wheeler Loan
        interest_rate=9.5,
        status="ACTIVE",
        dti_ratio=0.38,
        term_months=24,
        created_at=now - timedelta(days=90)
    )

    # Initial audit log
    audit_init = AuditLog(
        timestamp=now,
        agent="SYSTEM",
        action="SYSTEM_INIT",
        details="Core banking ledger initialized with Indian personas: Aarav Sharma, Bhavna Patel, Chirag Verma in INR (₹).",
        status="SUCCESS"
    )

    session.add_all([
        aarav, acc_aarav_sav, acc_aarav_fd, tx_aarav_1, tx_aarav_2, tx_aarav_3,
        bhavna, acc_bhavna_sav, acc_bhavna_cc, tx_bhavna_flagged, tx_bhavna_2, tx_bhavna_3,
        chirag, acc_chirag_sav, acc_chirag_upi, tx_chirag_1, tx_chirag_2, loan_chirag_existing,
        audit_init
    ])
    session.commit()


def init_db(db_path: str = "banking.db", seed: bool = True):
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
    if seed:
        SessionFactory = sessionmaker(bind=engine)
        session = SessionFactory()
        try:
            seed_database(session)
        finally:
            session.close()


def reset_db(db_path: str = "banking.db"):
    engine = get_engine(db_path)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    SessionFactory = sessionmaker(bind=engine)
    session = SessionFactory()
    try:
        seed_database(session)
    finally:
        session.close()
