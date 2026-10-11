# BHARAT APEX BANK: Production-Grade Simulated Banking Multi-Agent System

An enterprise multi-agent core-banking system constructed with **LangGraph**, **FastAPI**, **SQLite (SQLAlchemy)**, **Pydantic v2**, and modern dual frontends (**React** + **Streamlit**).

---

## 🏛️ Architecture Overview

The system mirrors modern enterprise AI banking architecture:
<img width="1143" height="856" alt="image" src="https://github.com/user-attachments/assets/1f85f1b5-9a8a-4d06-a261-2b7cf3cdf1d9" />


    subgraph apiLayer["2. API & Experience Layer"]
        gateway["FastAPI REST Gateway<br/>/api/chat · /api/hitl/decision · /api/ledger/tables"]
    end

    subgraph guardrails["3. AI Control Plane & Guardrails"]
        overdraft["Overdraft Rejection Protection"]
        pii["PII & Permission Enforcement<br/>KYC verified / risk-tier cutoffs"]
        hitlPolicy{"HITL Safety Gate"}
        transferPolicy["Transfers over $5,000<br/>Human sign-off"]
        creditPolicy["Credit disbursements over $20,000<br/>Underwriter sign-off"]
        hitlPolicy --> transferPolicy & creditPolicy
    end

    subgraph orchestrator["4. Multi-Agent Orchestrator — LangGraph Stateful Graph"]
        supervisor["Supervisor Node<br/>Intent classifier, router & state coordinator"]
        accounts["Account Services Agent<br/>Ledger, balances & atomic P2P transfers"]
        fraud["Fraud & Risk Agent<br/>Risk scoring, anomaly engine & card locks"]
        credit["Credit & Lending Agent<br/>DTI analysis, FICO APR tiers & underwriting"]
        hitlGate["HITL Gate<br/>Graph interrupt & resume"]
        supervisor --> accounts & fraud & credit
        supervisor --> hitlGate
    end

    subgraph tools["5. Agent Tools — Pydantic v2 Schemas"]
        overview["get_account_overview(customer_id)"]
        transfer["execute_transfer(source_acc, dest_acc, amount, memo)"]
        card["flag_or_block_card(account_id, reason, action)"]
        risk["assess_transaction_risk(tx_id) → RiskReport"]
        evaluate["evaluate_credit_application(customer_id, requested_amount, monthly_income)"]
    end

    subgraph data["6. Enterprise Data & Ledger — SQLite via SQLAlchemy"]
        customers[("customers<br/>Alice Martin, Bob Chen, Charlie Davis")]
        accountsDb[("accounts<br/>Checking, Savings, Credit Cards")]
        transactions[("transactions<br/>Ledger history, velocity & flags")]
        loans[("loans<br/>Underwritten credit contracts")]
        audit[("audit_logs<br/>Immutable audit ledger")]
    end

    spa --> gateway
    dashboard --> gateway
    gateway --> overdraft & pii & hitlPolicy
    overdraft --> supervisor
    pii --> supervisor
    hitlPolicy --> hitlGate

    accounts --> overview & transfer
    fraud --> card & risk
    credit --> evaluate
    hitlGate --> transferPolicy & creditPolicy

    overview --> customers & accountsDb
    transfer --> accountsDb & transactions & audit
    card --> accountsDb & audit
    risk --> transactions & audit
    evaluate --> customers & loans & audit

    classDef channel fill:#eef2ff,stroke:#818cf8,color:#1e1b4b
    classDef api fill:#ecfeff,stroke:#22d3ee,color:#083344
    classDef guard fill:#fefce8,stroke:#facc15,color:#422006
    classDef agent fill:#f5f3ff,stroke:#a78bfa,color:#2e1065
    classDef tool fill:#f0fdfa,stroke:#2dd4bf,color:#042f2e
    classDef database fill:#f0fdf4,stroke:#4ade80,color:#052e16
    classDef critical fill:#fef2f2,stroke:#f87171,color:#450a0a

    class spa,dashboard channel
    class gateway api
    class overdraft,pii guard
    class hitlPolicy,transferPolicy,creditPolicy,hitlGate critical
    class supervisor,accounts,fraud,credit agent
    class overview,transfer,card,risk,evaluate tool
    class customers,accountsDb,transactions,loans,audit database
```text
1. BANKING CHANNELS / CLIENTS
   ├── React Single-Page Application (Vite + Tailwind / Glassmorphism)
   └── Streamlit Conversational Dashboard

2. API & EXPERIENCE LAYER
   └── FastAPI REST Gateway (/api/chat, /api/hitl/decision, /api/ledger/tables)

3. AI CONTROL PLANE & GUARDRAILS
   ├── Overdraft Rejection Protection
   ├── PII & Permission Enforcement (KYC Verified / Risk Tier Cutoffs)
   └── Human-In-The-Loop (HITL) Safety Gate:
       ├── Fund Transfers > $5,000 (Requires human sign-off)
       └── Credit Disbursements > $20,000 (Requires underwriter sign-off)

4. MULTI-AGENT ORCHESTRATOR (LangGraph Stateful Graph)
   ├── Supervisor Node (Intent Classifier, Router & State Coordinator)
   ├── Account Services Agent (Ledger, Balances, Atomic P2P Transfers)
   ├── Fraud & Risk Agent (Risk Scoring 0–100, Anomaly Engine, Card Locks)
   ├── Credit & Lending Agent (DTI Analysis, FICO APR Tiers, Underwriting)
   └── HITL Gate (Graph execution interrupt & resume)

5. AGENT TOOLS (Pydantic v2 Schemas)
   ├── get_account_overview(customer_id)
   ├── execute_transfer(source_acc, dest_acc, amount, memo)
   ├── flag_or_block_card(account_id, reason, action)
   ├── assess_transaction_risk(tx_id) -> RiskReport
   └── evaluate_credit_application(customer_id, requested_amount, monthly_income)

6. ENTERPRISE DATA & LEDGER (SQLite via SQLAlchemy)
   ├── customers (Alice Martin, Bob Chen, Charlie Davis)
   ├── accounts (Checking, Savings, Credit Cards)
   ├── transactions (Ledger history with velocity & flag indicators)
   ├── loans (Underwritten credit contracts)
   └── audit_logs (Immutable audit ledger)
```

---

## 👤 Seeded Customer Personas

| Persona | Status | Risk Tier | FICO | Monthly Income | Balances | Key Scenarios |
|---|---|---|---|---|---|---|
| **Alice Martin** (`CUST_ALICE`) | VERIFIED | LOW | 815 | $14,500 | $28.5k Chk, $54k Sav | High liquidity, large transfers, prime loan applications |
| **Bob Chen** (`CUST_BOB`) | VERIFIED | MEDIUM | 720 | $8,200 | $4.2k Chk, $3.45k CC | Suspicious overseas charge (`TX_B9901` Dubai), card freezing |
| **Charlie Davis** (`CUST_CHARLIE`) | VERIFIED | MEDIUM | 645 | $4,600 | $1.85k Chk, $820 Sav | Loan applicant, Debt-to-Income (DTI) evaluation, overdraft guardrail |

---

## ⚡ Quick Start: 1-Click Launch

### Single Batch File (`run_all.bat`)
Double-click `run_all.bat` or run:
```cmd
-->ls
-->cd lc
-->.\run_all.bat
```
This automatically:
1. Installs Python dependencies (`requirements.txt`).
2. Seeds the SQLite database (`banking.db`).
3. Serves the unified FastAPI backend + compiled React frontend.
4. Opens `http://127.0.0.1:8000` directly in your browser.

---

## 🚀 Running Manually

### Option 1: React + FastAPI (Recommended)
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Build React frontend (if modified)
cd frontend
npm install
npm run build
cd ..

# 3. Start unified server
uvicorn backend.server:app --host 127.0.0.1 --port 8000 --reload
```
Open **`http://localhost:8000`** in your browser.

### Option 2: Streamlit Interactive Dashboard
```bash
streamlit run app.py
```
Open **`http://localhost:8501`** in your browser.

---

## 🧪 Automated Test Suite

Run the full pytest suite verifying all banking workflows, guardrails, and HITL interruptions:
```bash
pytest tests/test_workflows.py -v
```

All 10 tests validate:
- ✅ Account inquiries & atomic P2P transfers
- ✅ Overdraft guardrails (graceful rejection when balance is insufficient)
- ✅ HITL interruption on transfers > $5,000
- ✅ Fraud risk scoring (0–100) & card freeze/unfreeze mutations
- ✅ Credit underwriting with Debt-to-Income (DTI) calculations
- ✅ HITL escalation for loans > $20,000 and subsequent operator approval execution

---

## 🛡️ Core Banking Guardrails & HITL Logic

1. **Overdraft Protection:** Rejects transactions where `requested_amount > account.balance` gracefully without throwing exceptions.
2. **Transfer Safety Limit:** Transfers exceeding **$5,000** trigger the **Human-In-The-Loop Gate**, halting the state graph until an operator clicks `[Approve Action]` or `[Reject Action]`.
3. **Credit Underwriting Threshold:** Loans exceeding **$20,000** escalate to senior committee review before disbursement.
4. **Audit Trail:** Every agent tool invocation writes an immutable record to the `audit_logs` table.
