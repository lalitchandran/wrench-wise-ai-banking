"""
Automated tests for Indian Banking workflows, INR transactions, and safety guardrails.
1. Account Services & UPI/IMPS Transfer (including overdraft protection guardrail)
2. Fraud & Risk Assessment (including card freeze/unfreeze on suspicious overseas charges)
3. Credit Underwriting & Lending (including CIBIL, DTI calculations and HITL escalation > ₹2 Lakhs)
"""

import os
import gc
import pytest
from backend.database import init_db, get_session_factory, Customer, Account, Transaction, Loan
from backend.tools import (
    get_account_overview,
    execute_transfer,
    flag_or_block_card,
    assess_transaction_risk,
    evaluate_credit_application,
)
from backend.graph import run_banking_turn

TEST_DB = "test_indian_banking.db"


@pytest.fixture(scope="module", autouse=True)
def setup_test_database():
    """Initializes and seeds isolated test database with Indian personas."""
    if os.path.exists(TEST_DB):
        try:
            os.remove(TEST_DB)
        except Exception:
            pass
    init_db(TEST_DB, seed=True)
    yield
    gc.collect()
    if os.path.exists(TEST_DB):
        try:
            os.remove(TEST_DB)
        except Exception:
            pass


class TestAccountServicesWorkflow:
    """Tests Scenario 1: Account Inquiries, UPI/NEFT Transfers, and Guardrails."""

    def test_get_account_overview(self):
        overview = get_account_overview("CUST_AARAV", db_path=TEST_DB)
        assert overview.name == "Aarav Sharma"
        assert overview.kyc_status == "VERIFIED"
        assert overview.total_balance > 800000.0  # Aarav has ₹2.85 Lakhs + ₹5.4 Lakhs
        assert len(overview.accounts) == 2

    def test_execute_transfer_success(self):
        # Aarav transfers ₹35,000 to Bhavna
        res = execute_transfer(
            source_acc="ACC_AARAV_SAV",
            dest_acc="ACC_BHAVNA_SAV",
            amount=35000.0,
            memo="Test Rent Split UPI",
            db_path=TEST_DB
        )
        assert res.success is True
        assert res.amount == 35000.0
        assert res.source_new_balance is not None

        # Verify DB mutation
        SessionFactory = get_session_factory(TEST_DB)
        session = SessionFactory()
        try:
            bhavna_acc = session.query(Account).filter_by(account_id="ACC_BHAVNA_SAV").first()
            assert bhavna_acc.balance >= 62000.0 + 35000.0
        finally:
            session.close()

    def test_transfer_overdraft_guardrail(self):
        # Guardrail: transferring more than available balance must fail gracefully
        res = execute_transfer(
            source_acc="ACC_CHIRAG_SAV",
            dest_acc="ACC_AARAV_SAV",
            amount=999999.0,  # Chirag only has ₹18,500
            memo="Attempted Overdraft",
            db_path=TEST_DB
        )
        assert res.success is False
        assert "Insufficient funds" in res.message

    def test_transfer_hitl_escalation_in_graph(self):
        # Transfers > ₹50,000 must trigger HITL Gate in the LangGraph agent turn
        result = run_banking_turn(
            message="Transfer ₹85,000 to Bhavna",
            customer_id="CUST_AARAV",
            db_path=TEST_DB,
            thread_id="test_trf_hitl"
        )
        assert result.get("pending_hitl") is not None
        pending = result["pending_hitl"]
        assert pending["action_type"] == "fund_transfer"
        assert pending["amount"] == 85000.0
        assert "Human-In-The-Loop" in result["final_response"]


class TestFraudAndRiskWorkflow:
    """Tests Scenario 2: Suspicious Activity Assessment & Card Freezing."""

    def test_assess_transaction_risk_high_score(self):
        # Bhavna's overseas transaction TX_B9901 (₹1,48,999 in Dubai)
        report = assess_transaction_risk("TX_B9901", db_path=TEST_DB)
        assert report.risk_score >= 70
        assert report.risk_level in ["HIGH", "CRITICAL"]
        assert report.recommended_action == "FREEZE_CARD"
        assert any("Dubai" in f or "Cross-border" in f or "anomaly" in f or "High-value" in f for f in report.factors)

    def test_flag_or_block_card_mutation(self):
        # Freeze Bhavna's credit card
        freeze_res = flag_or_block_card(
            account_id="ACC_BHAVNA_CC",
            reason="Suspected fraudulent overseas transaction in Dubai",
            action="freeze",
            db_path=TEST_DB
        )
        assert freeze_res.success is True
        assert freeze_res.new_status == "FROZEN"

        # Verify DB mutation
        SessionFactory = get_session_factory(TEST_DB)
        session = SessionFactory()
        try:
            acc = session.query(Account).filter_by(account_id="ACC_BHAVNA_CC").first()
            assert acc.status == "FROZEN"
        finally:
            session.close()

        # Unfreeze card
        unfreeze_res = flag_or_block_card(
            account_id="ACC_BHAVNA_CC",
            reason="Customer verified transaction identity via OTP",
            action="unfreeze",
            db_path=TEST_DB
        )
        assert unfreeze_res.success is True
        assert unfreeze_res.new_status == "ACTIVE"

    def test_fraud_agent_graph_turn(self):
        # Test agent graph routing to Priya (Fraud Agent)
        res = run_banking_turn(
            message="Review suspicious charge on my credit card",
            customer_id="CUST_BHAVNA",
            db_path=TEST_DB,
            thread_id="test_fraud_flow"
        )
        assert res["active_agent"] == "fraud_agent"
        assert "Risk Score" in res["final_response"] or "TX_B9901" in res["final_response"]


class TestCreditAndLendingWorkflow:
    """Tests Scenario 3: Underwriting, CIBIL/DTI calculations, and HITL for Disbursements > ₹2 Lakhs."""

    def test_standard_credit_underwriting_approval(self):
        # Aarav requests ₹1,20,000 loan (Aarav has prime CIBIL 815, high income)
        report = evaluate_credit_application(
            customer_id="CUST_AARAV",
            requested_amount=120000.0,
            monthly_income=225000.0,
            db_path=TEST_DB
        )
        assert report.status == "APPROVED"
        assert report.interest_rate <= 9.0
        assert report.dti_ratio < 0.25
        assert report.loan_id is not None

    def test_credit_hitl_escalation_for_large_loan(self):
        # Loan > ₹2,00,000 must escalate to HITL Gate
        res = run_banking_turn(
            message="Apply for a ₹3,50,000 home expansion loan",
            customer_id="CUST_AARAV",
            db_path=TEST_DB,
            thread_id="test_loan_hitl"
        )
        assert res.get("pending_hitl") is not None
        pending = res["pending_hitl"]
        assert pending["action_type"] == "credit_disbursement"
        assert pending["amount"] == 350000.0
        assert "Senior Underwriter Review Required" in res["final_response"] or "HITL" in res["final_response"]

    def test_hitl_approval_execution(self):
        # Simulate operator approving high-value loan
        initial = run_banking_turn(
            message="Apply for ₹2,50,000 personal loan",
            customer_id="CUST_AARAV",
            db_path=TEST_DB,
            thread_id="test_hitl_approve_chain"
        )
        pending = initial["pending_hitl"]
        assert pending is not None

        # Operator submits APPROVE
        resumed = run_banking_turn(
            message="[HUMAN_ACTION_APPROVED]",
            customer_id="CUST_AARAV",
            db_path=TEST_DB,
            thread_id="test_hitl_approve_chain",
            hitl_decision="APPROVED",
            existing_pending_hitl=pending
        )
        assert resumed["pending_hitl"] is None
        assert "Approved & Disbursed" in resumed["final_response"]
