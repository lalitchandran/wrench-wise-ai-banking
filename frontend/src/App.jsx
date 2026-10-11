import React, { useState, useEffect, useRef } from 'react';
import {
  Building2,
  ShieldAlert,
  CreditCard,
  Send,
  UserCheck,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Database,
  Layers,
  Activity,
  ArrowRightLeft,
  DollarSign,
  FileText,
  Lock,
  Unlock,
  RefreshCw,
  Cpu,
  ChevronDown,
  ChevronRight,
  Info,
  ExternalLink,
  ShieldCheck,
  Sparkles,
  HeartHandshake,
  Compass,
  Wallet,
  TrendingUp,
  Award,
  Zap,
  Check,
  Clock,
  Search,
  Filter,
  User
} from 'lucide-react';

const API_BASE = '/api';

export default function App() {
  const [customers, setCustomers] = useState([]);
  const [selectedCustomerId, setSelectedCustomerId] = useState('CUST_AARAV');
  const [currentProfile, setCurrentProfile] = useState(null);
  
  // Chat state
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      agent: '🧭 Aditi (Banking Navigator)',
      agentKey: 'supervisor',
      content: `### Namaste & Welcome to Bharat Apex Bank 🙏\n\nI am **Aditi**, your AI Banking Assistant. Together with our team of specialists:\n- 💳 **Rohan (Payments):** UPI & IMPS transfers, instant balance verification\n- 🛡️ **Priya (Fraud Guard):** 24/7 transaction anomaly & risk surveillance\n- 📈 **Vikram (Lending):** CIBIL evaluation & personal loan underwriting\n\nHow can we help you today? You can select a quick action above or type any instruction in Rupees (₹).`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  
  // Observability & HITL
  const [activeAgent, setActiveAgent] = useState('supervisor');
  const [executionTrace, setExecutionTrace] = useState([]);
  const [pendingHITL, setPendingHITL] = useState(null);
  const [activeTab, setActiveTab] = useState('trace'); // 'trace' | 'ledger'
  const [expandedTraceIdx, setExpandedTraceIdx] = useState(0);
  
  // Ledger state
  const [ledgerData, setLedgerData] = useState({ accounts: [], transactions: [], loans: [], audit_logs: [] });
  const [ledgerSearch, setLedgerSearch] = useState('');
  const [ledgerSubTab, setLedgerSubTab] = useState('accounts');

  // Blueprint Modal
  const [showArchModal, setShowArchModal] = useState(false);

  const chatEndRef = useRef(null);

  useEffect(() => {
    fetchCustomers();
    fetchLedger();
  }, []);

  useEffect(() => {
    if (selectedCustomerId) {
      fetchCustomerProfile(selectedCustomerId);
    }
  }, [selectedCustomerId]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, pendingHITL]);

  const fetchCustomers = async () => {
    try {
      const res = await fetch(`${API_BASE}/customers`);
      const data = await res.json();
      if (data.customers) {
        setCustomers(data.customers);
      }
    } catch (err) {
      console.error('Error fetching customers:', err);
    }
  };

  const fetchCustomerProfile = async (id) => {
    try {
      const res = await fetch(`${API_BASE}/customer/${id}/overview`);
      const data = await res.json();
      setCurrentProfile(data);
    } catch (err) {
      console.error('Error fetching customer profile:', err);
    }
  };

  const fetchLedger = async () => {
    try {
      const res = await fetch(`${API_BASE}/ledger/tables`);
      const data = await res.json();
      setLedgerData(data);
    } catch (err) {
      console.error('Error fetching ledger:', err);
    }
  };

  const handleSendMessage = async (textToSend = null) => {
    const text = textToSend || inputValue;
    if (!text.trim() || isProcessing) return;

    const userMsg = {
      role: 'user',
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMsg]);
    if (!textToSend) setInputValue('');
    setIsProcessing(true);

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          customer_id: selectedCustomerId
        })
      });
      const data = await res.json();

      setActiveAgent(data.active_agent || 'supervisor');
      if (data.execution_trace) {
        setExecutionTrace(data.execution_trace);
        setExpandedTraceIdx(data.execution_trace.length - 1);
      }
      setPendingHITL(data.pending_hitl || null);

      const assistantMsg = {
        role: 'assistant',
        agent: formatAgentName(data.active_agent),
        agentKey: data.active_agent,
        content: data.final_response || 'Request executed.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages(prev => [...prev, assistantMsg]);

      fetchCustomerProfile(selectedCustomerId);
      fetchLedger();
    } catch (err) {
      console.error('Chat error:', err);
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          agent: '🧭 Aditi (System)',
          agentKey: 'supervisor',
          content: '⚠️ Namaste, we encountered an issue communicating with our banking core. Please retry.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleHITLDecision = async (decision) => {
    if (!pendingHITL) return;
    setIsProcessing(true);

    try {
      const res = await fetch(`${API_BASE}/hitl/decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          decision: decision,
          customer_id: selectedCustomerId,
          pending_hitl: pendingHITL
        })
      });
      const data = await res.json();

      setActiveAgent(data.active_agent || 'supervisor');
      if (data.execution_trace) {
        setExecutionTrace(prev => [...prev, ...data.execution_trace]);
        setExpandedTraceIdx(data.execution_trace.length - 1);
      }
      setPendingHITL(null);

      const assistantMsg = {
        role: 'assistant',
        agent: formatAgentName(data.active_agent),
        agentKey: data.active_agent,
        content: data.final_response || `Action has been ${decision.toLowerCase()}.`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages(prev => [...prev, assistantMsg]);

      fetchCustomerProfile(selectedCustomerId);
      fetchLedger();
    } catch (err) {
      console.error('HITL error:', err);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleResetDB = async () => {
    if (!window.confirm('Reset SQLite database to original seeded state (Aarav, Bhavna, Chirag in INR ₹)?')) return;
    try {
      await fetch(`${API_BASE}/database/reset`, { method: 'POST' });
      fetchCustomers();
      fetchCustomerProfile(selectedCustomerId);
      fetchLedger();
      setMessages([
        {
          role: 'assistant',
          agent: '🧭 Aditi (Banking Navigator)',
          agentKey: 'supervisor',
          content: '🔄 Database restored to pristine Indian banking seed state (Aarav, Bhavna, Chirag in INR ₹).',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
      setPendingHITL(null);
      setExecutionTrace([]);
    } catch (err) {
      console.error('Reset error:', err);
    }
  };

  const formatAgentName = (agentKey) => {
    switch (agentKey) {
      case 'supervisor': return '🧭 Aditi (Banking Navigator)';
      case 'account_agent': return '💳 Rohan (Payments Specialist)';
      case 'fraud_agent': return '🛡️ Priya (Fraud Guardian)';
      case 'credit_agent': return '📈 Vikram (Lending Advisor)';
      case 'hitl_gate': return '⚖️ Compliance Council (HITL Gate)';
      default: return agentKey || 'Specialist';
    }
  };

  const renderSimpleMarkdown = (text) => {
    if (!text) return '';
    let html = text
      .replace(/### (.*?)\n/g, '<h3>$1</h3>')
      .replace(/#### (.*?)\n/g, '<h4>$1</h4>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`(.*?)`/g, '<code>$1</code>')
      .replace(/\n\n/g, '<p></p>')
      .replace(/- (.*?)\n/g, '<li>$1</li>');
    return <div className="chat-markdown" dangerouslySetInnerHTML={{ __html: html }} />;
  };

  const filteredAccounts = ledgerData.accounts.filter(a =>
    a.account_id.toLowerCase().includes(ledgerSearch.toLowerCase()) ||
    a.customer_id.toLowerCase().includes(ledgerSearch.toLowerCase())
  );
  const filteredTransactions = ledgerData.transactions.filter(t =>
    t.tx_id.toLowerCase().includes(ledgerSearch.toLowerCase()) ||
    t.merchant.toLowerCase().includes(ledgerSearch.toLowerCase()) ||
    t.account_id.toLowerCase().includes(ledgerSearch.toLowerCase())
  );
  const filteredLoans = ledgerData.loans.filter(l =>
    l.loan_id.toLowerCase().includes(ledgerSearch.toLowerCase()) ||
    l.customer_id.toLowerCase().includes(ledgerSearch.toLowerCase())
  );
  const filteredAudits = ledgerData.audit_logs.filter(a =>
    a.action.toLowerCase().includes(ledgerSearch.toLowerCase()) ||
    a.agent.toLowerCase().includes(ledgerSearch.toLowerCase())
  );

  const latestFraudStep = executionTrace.slice().reverse().find(
    s => (s.agent?.includes('Fraud') || s.agent === 'fraud_agent') && s.result && s.result.risk_score !== undefined
  );
  const fraudScore = latestFraudStep ? latestFraudStep.result.risk_score : null;
  const fraudLevel = latestFraudStep ? latestFraudStep.result.risk_level : null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: 'var(--bg-page)', color: 'var(--text-main)' }}>
      {/* ----------------- Clean Top White Header with Yellow Accent ----------------- */}
      <header style={{
        background: '#ffffff',
        borderBottom: '1px solid var(--border-light)',
        padding: '0.85rem 2rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        boxShadow: 'var(--shadow-sm)',
        zIndex: 50
      }}>
        {/* Brand & Crest */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            background: 'linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%)',
            width: '40px',
            height: '40px',
            borderRadius: '12px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 2px 8px rgba(245, 158, 11, 0.25)'
          }}>
            <Building2 size={22} color="#ffffff" />
          </div>
          <div>
            <div style={{ fontWeight: 800, fontSize: '1.25rem', color: '#0f172a', display: 'flex', alignItems: 'center', gap: '8px' }}>
              Bharat Apex Bank
              <span style={{
                fontSize: '0.7rem',
                background: '#fef3c7',
                color: '#b45309',
                border: '1px solid #fde68a',
                padding: '2px 8px',
                borderRadius: '999px',
                fontWeight: 700
              }}>
                AI Mesh (INR ₹)
              </span>
            </div>
            <div style={{ fontSize: '0.78rem', color: '#64748b' }}>
              Simple, Humanized Multi-Agent Banking Powered by LangGraph
            </div>
          </div>
        </div>

        {/* User Persona & Financial Highlights */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '1.4rem' }}>
          {/* Persona Switcher Card */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            background: '#f8fafc',
            border: '1px solid var(--border-light)',
            padding: '6px 14px',
            borderRadius: '12px'
          }}>
            <div style={{
              width: '28px',
              height: '28px',
              borderRadius: '50%',
              background: '#f59e0b',
              color: '#ffffff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 800,
              fontSize: '0.75rem'
            }}>
              {selectedCustomerId === 'CUST_AARAV' ? 'AS' : selectedCustomerId === 'CUST_BHAVNA' ? 'BP' : 'CV'}
            </div>
            <div>
              <div style={{ fontSize: '0.68rem', color: '#64748b', fontWeight: 600, textTransform: 'uppercase' }}>Active Account</div>
              <select
                value={selectedCustomerId}
                onChange={(e) => {
                  setSelectedCustomerId(e.target.value);
                  setMessages([]);
                  setPendingHITL(null);
                  setExecutionTrace([]);
                }}
                style={{
                  background: 'transparent',
                  color: '#0f172a',
                  border: 'none',
                  fontWeight: 700,
                  fontSize: '0.85rem',
                  cursor: 'pointer',
                  outline: 'none',
                  paddingRight: '4px'
                }}
              >
                <option value="CUST_AARAV">Aarav Sharma (Prime / Bengaluru)</option>
                <option value="CUST_BHAVNA">Bhavna Patel (High Velocity / Mumbai)</option>
                <option value="CUST_CHIRAG">Chirag Verma (Personal Loan / Delhi)</option>
              </select>
            </div>
          </div>

          {/* Quick Balance Counter */}
          {currentProfile && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '1.2rem' }}>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '0.68rem', color: '#64748b', fontWeight: 700, textTransform: 'uppercase' }}>Total Balance</div>
                <div style={{ fontSize: '1.18rem', fontWeight: 800, color: '#0f172a' }}>
                  ₹{currentProfile.total_balance?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </div>
              </div>

              <div style={{ height: '24px', width: '1px', background: 'var(--border-light)' }} />

              <div style={{ fontSize: '0.78rem', display: 'flex', flexDirection: 'column', gap: '2px' }}>
                <div style={{ color: '#475569' }}>
                  CIBIL Score: <strong style={{ color: '#0f172a' }}>{currentProfile.credit_score}</strong>
                </div>
                <div style={{ color: '#475569', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  KYC: <Check size={12} color="#10b981" /> <strong style={{ color: '#10b981' }}>Verified</strong>
                </div>
              </div>
            </div>
          )}

          {/* Header Action Buttons */}
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={() => setShowArchModal(true)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                background: '#ffffff',
                border: '1px solid var(--border-light)',
                color: '#0f172a',
                padding: '7px 14px',
                borderRadius: '10px',
                fontSize: '0.82rem',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
              onMouseEnter={(e) => e.target.style.background = '#fef3c7'}
              onMouseLeave={(e) => e.target.style.background = '#ffffff'}
            >
              <Layers size={14} color="#f59e0b" /> Architecture Map
            </button>

            <button
              onClick={handleResetDB}
              title="Reset SQLite database"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                background: '#ffffff',
                border: '1px solid var(--border-light)',
                color: '#64748b',
                padding: '7px 14px',
                borderRadius: '10px',
                fontSize: '0.82rem',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
              onMouseEnter={(e) => e.target.style.background = '#fee2e2'}
              onMouseLeave={(e) => e.target.style.background = '#ffffff'}
            >
              <RefreshCw size={13} color="#ef4444" /> Reset DB
            </button>
          </div>
        </div>
      </header>

      {/* ----------------- Clean Main Body Layout ----------------- */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* ================= LEFT PANE: Clean Chat Hub ================= */}
        <div style={{
          flex: 1.15,
          display: 'flex',
          flexDirection: 'column',
          borderRight: '1px solid var(--border-light)',
          background: '#ffffff',
          position: 'relative'
        }}>
          {/* Subheader: Active Specialist Bar */}
          <div style={{
            padding: '0.75rem 2rem',
            background: '#fafafa',
            borderBottom: '1px solid var(--border-light)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span className="pulse-dot" style={{
                background: activeAgent.includes('fraud') ? '#ef4444' :
                            activeAgent.includes('account') ? '#10b981' :
                            activeAgent.includes('credit') ? '#f59e0b' : '#f59e0b'
              }} />
              <span style={{ fontSize: '0.78rem', color: '#64748b', fontWeight: 600, textTransform: 'uppercase' }}>
                Current Specialist:
              </span>
              <span style={{
                fontSize: '0.82rem',
                fontWeight: 700,
                color: '#0f172a',
                background: '#fef3c7',
                border: '1px solid #fde68a',
                padding: '2px 10px',
                borderRadius: '999px'
              }}>
                {formatAgentName(activeAgent)}
              </span>
            </div>

            <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
              Checkpointer: <strong style={{ color: '#0f172a' }}>MemorySaver Active</strong>
            </div>
          </div>

          {/* Quick Scenario Buttons Ribbon */}
          <div style={{
            padding: '0.7rem 2rem',
            background: '#ffffff',
            borderBottom: '1px solid var(--border-light)',
            display: 'flex',
            gap: '8px',
            overflowX: 'auto',
            whiteSpace: 'nowrap'
          }}>
            <button
              onClick={() => handleSendMessage('Transfer ₹35,000 to Bhavna')}
              className="btn-pill-action"
            >
              <ArrowRightLeft size={13} color="#f59e0b" /> Transfer ₹35,000 to Bhavna
            </button>

            <button
              onClick={() => handleSendMessage('Review suspicious charge on my credit card')}
              className="btn-pill-action"
            >
              <ShieldAlert size={13} color="#ef4444" /> Review Suspicious Charge
            </button>

            <button
              onClick={() => handleSendMessage('Apply for a ₹1,50,000 personal loan')}
              className="btn-pill-action"
            >
              <FileText size={13} color="#2563eb" /> Apply for ₹1,50,000 Loan
            </button>

            <button
              onClick={() => handleSendMessage('Transfer ₹85,000 to Bhavna for commercial invoice')}
              className="btn-pill-action"
              style={{ background: '#fffbeb', borderColor: '#fde68a', color: '#b45309' }}
            >
              <AlertTriangle size={13} color="#f59e0b" /> Transfer ₹85,000 (&gt; ₹50k HITL)
            </button>

            <button
              onClick={() => handleSendMessage('Apply for a ₹3,50,000 commercial expansion loan')}
              className="btn-pill-action"
              style={{ background: '#fffbeb', borderColor: '#fde68a', color: '#b45309' }}
            >
              <AlertTriangle size={13} color="#f59e0b" /> Apply for ₹3,50,000 Loan (&gt; ₹2L HITL)
            </button>
          </div>

          {/* Messages Stream */}
          <div style={{
            flex: 1,
            overflowY: 'auto',
            padding: '1.6rem 2rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '1.3rem',
            background: '#f8fafc'
          }}>
            {messages.map((msg, index) => {
              const isUser = msg.role === 'user';
              return (
                <div
                  key={index}
                  style={{
                    display: 'flex',
                    flexDirection: isUser ? 'row-reverse' : 'row',
                    gap: '12px',
                    alignItems: 'flex-start'
                  }}
                >
                  {/* User / Agent Avatar */}
                  <div style={{
                    width: '36px',
                    height: '36px',
                    borderRadius: '50%',
                    background: isUser ? '#f59e0b' : '#ffffff',
                    border: '1px solid var(--border-light)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                    boxShadow: 'var(--shadow-sm)'
                  }}>
                    {isUser ? <User size={18} color="#ffffff" /> : <Sparkles size={18} color="#f59e0b" />}
                  </div>

                  {/* Message Bubble */}
                  <div style={{
                    maxWidth: '82%',
                    background: isUser ? '#fffbeb' : '#ffffff',
                    border: isUser ? '1px solid #fde68a' : '1px solid var(--border-light)',
                    borderRadius: '16px',
                    padding: '1.1rem 1.4rem',
                    boxShadow: 'var(--shadow-sm)'
                  }}>
                    <div style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      marginBottom: '6px',
                      fontSize: '0.74rem',
                      color: '#64748b'
                    }}>
                      <span style={{ fontWeight: 700, color: isUser ? '#b45309' : '#0f172a' }}>
                        {isUser ? currentProfile?.name || 'You' : msg.agent}
                      </span>
                      <span>{msg.timestamp}</span>
                    </div>

                    <div style={{ fontSize: '0.92rem', color: '#1e293b', lineHeight: 1.62 }}>
                      {renderSimpleMarkdown(msg.content)}
                    </div>
                  </div>
                </div>
              );
            })}

            {isProcessing && (
              <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                <div style={{ width: '36px', height: '36px', borderRadius: '50%', background: '#ffffff', border: '1px solid var(--border-light)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Sparkles size={16} color="#f59e0b" />
                </div>
                <div className="card-clean" style={{ padding: '0.8rem 1.2rem', borderRadius: '12px', fontSize: '0.86rem', color: '#b45309', background: '#fffbeb', border: '1px solid #fde68a', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span className="pulse-dot" style={{ background: '#f59e0b' }} />
                  Aditi coordinating banking specialists...
                </div>
              </div>
            )}

            {/* Human-In-The-Loop Approval Action Banner */}
            {pendingHITL && (
              <div style={{
                background: '#fffbeb',
                border: '2px solid #f59e0b',
                borderRadius: '14px',
                padding: '1.3rem',
                margin: '0.5rem 0',
                boxShadow: '0 4px 14px rgba(245, 158, 11, 0.15)'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                  <AlertTriangle size={22} color="#d97706" />
                  <h4 style={{ color: '#b45309', margin: 0, fontWeight: 800, fontSize: '1.02rem' }}>
                    Action Required: High-Value Confirmation
                  </h4>
                </div>

                <div style={{
                  background: '#ffffff',
                  padding: '1rem',
                  borderRadius: '10px',
                  marginBottom: '12px',
                  border: '1px solid #fde68a'
                }}>
                  <div style={{ fontSize: '0.92rem', fontWeight: 700, color: '#0f172a' }}>
                    {pendingHITL.summary}
                  </div>
                  <div style={{ fontSize: '0.82rem', color: '#64748b', marginTop: '4px', lineHeight: 1.5 }}>
                    Action requested by <strong>{formatAgentName(pendingHITL.requested_by)}</strong>.
                    The amount of <strong>₹{pendingHITL.amount?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</strong> exceeds our automated policy limit of <strong>₹{pendingHITL.threshold?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</strong>.
                    Please confirm if you want to proceed.
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '12px' }}>
                  <button
                    onClick={() => handleHITLDecision('APPROVED')}
                    style={{
                      flex: 1,
                      padding: '11px 18px',
                      borderRadius: '10px',
                      fontWeight: 700,
                      fontSize: '0.9rem',
                      background: '#10b981',
                      color: '#ffffff',
                      border: 'none',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '8px',
                      cursor: 'pointer',
                      boxShadow: '0 2px 6px rgba(16, 185, 129, 0.25)'
                    }}
                  >
                    <CheckCircle2 size={17} /> Approve & Settle
                  </button>

                  <button
                    onClick={() => handleHITLDecision('REJECTED')}
                    style={{
                      flex: 1,
                      padding: '11px 18px',
                      borderRadius: '10px',
                      fontWeight: 700,
                      fontSize: '0.9rem',
                      background: '#ffffff',
                      color: '#ef4444',
                      border: '1px solid #fca5a5',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '8px',
                      cursor: 'pointer'
                    }}
                  >
                    <XCircle size={17} /> Decline & Cancel
                  </button>
                </div>
              </div>
            )}

            <div ref={chatEndRef} />
          </div>

          {/* Chat Input Bar */}
          <div style={{
            padding: '1rem 2rem',
            background: '#ffffff',
            borderTop: '1px solid var(--border-light)',
            display: 'flex',
            gap: '10px'
          }}>
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSendMessage();
              }}
              placeholder={`Ask Aditi or type banking instruction in ₹ (e.g. "Transfer ₹35,000 to Bhavna", "Check my balance")...`}
              style={{
                flex: 1,
                background: '#f8fafc',
                border: '1px solid var(--border-light)',
                borderRadius: '12px',
                padding: '12px 18px',
                color: '#0f172a',
                fontSize: '0.92rem',
                outline: 'none',
                transition: 'border 0.2s'
              }}
              onFocus={(e) => e.target.style.borderColor = 'var(--yellow-main)'}
              onBlur={(e) => e.target.style.borderColor = 'var(--border-light)'}
            />

            <button
              onClick={() => handleSendMessage()}
              disabled={isProcessing || !inputValue.trim()}
              className="btn-yellow"
              style={{
                padding: '0 24px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                fontSize: '0.9rem',
                opacity: isProcessing || !inputValue.trim() ? 0.6 : 1
              }}
            >
              <Send size={16} /> Send
            </button>
          </div>
        </div>

        {/* ================= RIGHT PANE: Observability & Core Ledger ================= */}
        <div style={{
          flex: 0.85,
          display: 'flex',
          flexDirection: 'column',
          background: '#f8fafc',
          overflow: 'hidden'
        }}>
          {/* Segmented Navigation */}
          <div style={{
            display: 'flex',
            borderBottom: '1px solid var(--border-light)',
            background: '#ffffff',
            padding: '6px 12px'
          }}>
            <button
              onClick={() => setActiveTab('trace')}
              style={{
                flex: 1,
                padding: '10px',
                background: activeTab === 'trace' ? '#fef3c7' : 'transparent',
                border: 'none',
                borderRadius: '8px',
                color: activeTab === 'trace' ? '#b45309' : '#64748b',
                fontWeight: 700,
                fontSize: '0.82rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px'
              }}
            >
              <Activity size={15} color={activeTab === 'trace' ? '#d97706' : '#64748b'} /> Agent Observability
            </button>

            <button
              onClick={() => setActiveTab('ledger')}
              style={{
                flex: 1,
                padding: '10px',
                background: activeTab === 'ledger' ? '#fef3c7' : 'transparent',
                border: 'none',
                borderRadius: '8px',
                color: activeTab === 'ledger' ? '#b45309' : '#64748b',
                fontWeight: 700,
                fontSize: '0.82rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px'
              }}
            >
              <Database size={15} color={activeTab === 'ledger' ? '#d97706' : '#64748b'} /> Core Ledger (INR ₹)
            </button>
          </div>

          {/* Tab 1: Live Agent Observability */}
          {activeTab === 'trace' && (
            <div style={{ flex: 1, overflowY: 'auto', padding: '1.4rem', display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>
              {/* Specialist Team Matrix */}
              <div className="card-clean" style={{ padding: '1.1rem' }}>
                <div style={{ fontSize: '0.72rem', color: '#64748b', fontWeight: 700, textTransform: 'uppercase', marginBottom: '8px' }}>
                  Multi-Agent Routing Mesh
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: '8px', textAlign: 'center', width: '100%' }}>
                  <div style={{
                    padding: '10px 4px',
                    borderRadius: '10px',
                    minWidth: 0,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: activeAgent.includes('supervisor') ? '#fef3c7' : '#f8fafc',
                    border: activeAgent.includes('supervisor') ? '1px solid #f59e0b' : '1px solid var(--border-light)',
                    color: activeAgent.includes('supervisor') ? '#b45309' : '#64748b',
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    textAlign: 'center',
                    overflowWrap: 'anywhere'
                  }}>
                    <span aria-hidden="true">🧭</span><span>Aditi</span><span style={{ fontSize: '0.66rem', fontWeight: 500, color: '#64748b' }}>Navigator</span>
                  </div>
                  <div style={{
                    padding: '10px 4px',
                    borderRadius: '10px',
                    minWidth: 0,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: activeAgent.includes('account') ? '#d1fae5' : '#f8fafc',
                    border: activeAgent.includes('account') ? '1px solid #10b981' : '1px solid var(--border-light)',
                    color: activeAgent.includes('account') ? '#065f46' : '#64748b',
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    textAlign: 'center',
                    overflowWrap: 'anywhere'
                  }}>
                    <span aria-hidden="true">💳</span><span>Rohan</span><span style={{ fontSize: '0.66rem', fontWeight: 500, color: '#64748b' }}>Payments</span>
                  </div>
                  <div style={{
                    padding: '10px 4px',
                    borderRadius: '10px',
                    minWidth: 0,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: activeAgent.includes('fraud') ? '#fee2e2' : '#f8fafc',
                    border: activeAgent.includes('fraud') ? '1px solid #ef4444' : '1px solid var(--border-light)',
                    color: activeAgent.includes('fraud') ? '#991b1b' : '#64748b',
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    textAlign: 'center',
                    overflowWrap: 'anywhere'
                  }}>
                    <span aria-hidden="true">🛡️</span><span>Priya</span><span style={{ fontSize: '0.66rem', fontWeight: 500, color: '#64748b' }}>Fraud Guard</span>
                  </div>
                  <div style={{
                    padding: '10px 4px',
                    borderRadius: '10px',
                    minWidth: 0,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: activeAgent.includes('credit') ? '#fef3c7' : '#f8fafc',
                    border: activeAgent.includes('credit') ? '1px solid #f59e0b' : '1px solid var(--border-light)',
                    color: activeAgent.includes('credit') ? '#b45309' : '#64748b',
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    textAlign: 'center',
                    overflowWrap: 'anywhere'
                  }}>
                    <span aria-hidden="true">📈</span><span>Vikram</span><span style={{ fontSize: '0.66rem', fontWeight: 500, color: '#64748b' }}>Lending</span>
                  </div>
                </div>
              </div>

              {/* Fraud Meter Card */}
              {fraudScore !== null && (
                <div className="card-clean" style={{ padding: '1.2rem', background: '#fff5f5', border: '1px solid #fecaca' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <div style={{ fontSize: '0.84rem', fontWeight: 700, color: '#991b1b', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <ShieldAlert size={17} color="#ef4444" /> Security Risk Assessment
                    </div>
                    <span style={{
                      fontSize: '0.72rem',
                      fontWeight: 800,
                      padding: '2px 8px',
                      borderRadius: '999px',
                      background: fraudLevel === 'CRITICAL' ? '#ef4444' : fraudLevel === 'HIGH' ? '#f97316' : '#10b981',
                      color: '#ffffff'
                    }}>
                      {fraudLevel}
                    </span>
                  </div>

                  <div style={{ height: '8px', width: '100%', background: '#fee2e2', borderRadius: '4px', overflow: 'hidden', marginBottom: '8px' }}>
                    <div style={{
                      width: `${fraudScore}%`,
                      height: '100%',
                      background: '#ef4444',
                      transition: 'width 0.5s ease'
                    }} />
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.76rem', color: '#64748b' }}>
                    <span>Calculated Threat: <strong>{fraudScore}/100</strong></span>
                    <span>Safety Action: <code>FREEZE_CARD</code></span>
                  </div>
                </div>
              )}

              {/* Trace Timeline Feed */}
              <div>
                <div style={{ fontSize: '0.74rem', fontWeight: 700, color: '#64748b', textTransform: 'uppercase', marginBottom: '10px' }}>
                  Execution Timeline ({executionTrace.length} Steps)
                </div>

                {executionTrace.length === 0 ? (
                  <div className="card-clean" style={{ padding: '1.5rem', textAlign: 'center', color: '#94a3b8', fontSize: '0.85rem' }}>
                    No steps logged yet. Send a message to see live state routing and tool executions.
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {executionTrace.map((step, idx) => {
                      const isExpanded = expandedTraceIdx === idx;
                      return (
                        <div key={idx} className="card-clean" style={{ overflow: 'hidden' }}>
                          <div
                            onClick={() => setExpandedTraceIdx(isExpanded ? -1 : idx)}
                            style={{
                              padding: '10px 14px',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              cursor: 'pointer',
                              background: isExpanded ? '#fef3c7' : '#ffffff'
                            }}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              {isExpanded ? <ChevronDown size={14} color="#b45309" /> : <ChevronRight size={14} color="#94a3b8" />}
                              <span style={{ fontSize: '0.74rem', color: '#94a3b8', fontWeight: 700 }}>#{idx + 1}</span>
                              <span style={{ fontSize: '0.82rem', fontWeight: 700, color: '#0f172a' }}>{step.agent}</span>
                              <span style={{
                                fontSize: '0.68rem',
                                color: '#b45309',
                                background: 'rgba(245, 158, 11, 0.15)',
                                padding: '1px 6px',
                                borderRadius: '4px',
                                fontWeight: 600
                              }}>
                                {step.action}
                              </span>
                            </div>
                            <span style={{ fontSize: '0.72rem', color: '#94a3b8' }}>{step.timestamp}</span>
                          </div>

                          {isExpanded && (
                            <div style={{ padding: '12px 14px', borderTop: '1px solid var(--border-light)', background: '#fafafa' }}>
                              <p style={{ fontSize: '0.82rem', color: '#334155', marginBottom: '8px', lineHeight: 1.5 }}>
                                {step.details}
                              </p>

                              {step.payload && Object.keys(step.payload).length > 0 && (
                                <div style={{ marginBottom: '8px' }}>
                                  <div style={{ fontSize: '0.7rem', color: '#64748b', fontWeight: 700, marginBottom: '4px' }}>Tool Payload:</div>
                                  <pre style={{ fontSize: '0.72rem', background: '#f1f5f9', padding: '8px', borderRadius: '6px', color: '#0f172a', overflowX: 'auto', border: '1px solid var(--border-light)' }}>
                                    {JSON.stringify(step.payload, null, 2)}
                                  </pre>
                                </div>
                              )}

                              {step.result && Object.keys(step.result).length > 0 && (
                                <div>
                                  <div style={{ fontSize: '0.7rem', color: '#64748b', fontWeight: 700, marginBottom: '4px' }}>Tool Output:</div>
                                  <pre style={{ fontSize: '0.72rem', background: '#f1f5f9', padding: '8px', borderRadius: '6px', color: '#0f172a', overflowX: 'auto', border: '1px solid var(--border-light)' }}>
                                    {JSON.stringify(step.result, null, 2)}
                                  </pre>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Tab 2: Core Banking Ledger (SQLite Relational Tables) */}
          {activeTab === 'ledger' && (
            <div style={{ flex: 1, overflowY: 'auto', padding: '1.4rem', display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <div style={{ position: 'relative', flex: 1 }}>
                  <Search size={14} color="#94a3b8" style={{ position: 'absolute', left: '12px', top: '10px' }} />
                  <input
                    type="text"
                    placeholder="Search records by ID, merchant, or customer..."
                    value={ledgerSearch}
                    onChange={(e) => setLedgerSearch(e.target.value)}
                    style={{
                      width: '100%',
                      background: '#ffffff',
                      border: '1px solid var(--border-light)',
                      borderRadius: '8px',
                      padding: '8px 12px 8px 34px',
                      color: '#0f172a',
                      fontSize: '0.82rem',
                      outline: 'none'
                    }}
                  />
                </div>

                <button
                  onClick={fetchLedger}
                  title="Refresh core ledger"
                  style={{
                    background: '#ffffff',
                    border: '1px solid var(--border-light)',
                    color: '#64748b',
                    padding: '8px 12px',
                    borderRadius: '8px',
                    cursor: 'pointer'
                  }}
                >
                  <RefreshCw size={14} />
                </button>
              </div>

              {/* Sub-tabs for Tables */}
              <div style={{ display: 'flex', gap: '6px', background: '#ffffff', padding: '4px', borderRadius: '8px', border: '1px solid var(--border-light)' }}>
                {['accounts', 'transactions', 'loans', 'audit_logs'].map(tabKey => (
                  <button
                    key={tabKey}
                    onClick={() => setLedgerSubTab(tabKey)}
                    style={{
                      flex: 1,
                      padding: '6px',
                      fontSize: '0.74rem',
                      fontWeight: 700,
                      borderRadius: '6px',
                      border: 'none',
                      cursor: 'pointer',
                      background: ledgerSubTab === tabKey ? '#f59e0b' : 'transparent',
                      color: ledgerSubTab === tabKey ? '#ffffff' : '#64748b'
                    }}
                  >
                    {tabKey.toUpperCase().replace('_', ' ')}
                  </button>
                ))}
              </div>

              <div className="card-clean" style={{ padding: '0.8rem', overflowX: 'auto', background: '#ffffff' }}>
                {ledgerSubTab === 'accounts' && (
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem' }}>
                    <thead>
                      <tr style={{ color: '#64748b', borderBottom: '1px solid var(--border-light)', textAlign: 'left' }}>
                        <th style={{ padding: '6px' }}>Account ID</th>
                        <th style={{ padding: '6px' }}>Owner</th>
                        <th style={{ padding: '6px' }}>Type</th>
                        <th style={{ padding: '6px' }}>Balance (INR ₹)</th>
                        <th style={{ padding: '6px' }}>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredAccounts.map(acc => (
                        <tr key={acc.account_id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                          <td style={{ padding: '6px', color: '#b45309' }}><code>{acc.account_id}</code></td>
                          <td style={{ padding: '6px', color: '#334155' }}>{acc.customer_id}</td>
                          <td style={{ padding: '6px' }}>{acc.account_type.replace('_', ' ')}</td>
                          <td style={{ padding: '6px', fontWeight: 800, color: '#0f172a' }}>₹{acc.balance?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                          <td style={{ padding: '6px' }}>
                            <span style={{
                              padding: '2px 6px',
                              borderRadius: '4px',
                              fontSize: '0.68rem',
                              fontWeight: 700,
                              background: acc.status === 'ACTIVE' ? '#d1fae5' : '#fee2e2',
                              color: acc.status === 'ACTIVE' ? '#065f46' : '#991b1b'
                            }}>
                              {acc.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}

                {ledgerSubTab === 'transactions' && (
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem' }}>
                    <thead>
                      <tr style={{ color: '#64748b', borderBottom: '1px solid var(--border-light)', textAlign: 'left' }}>
                        <th style={{ padding: '6px' }}>TX ID</th>
                        <th style={{ padding: '6px' }}>Account</th>
                        <th style={{ padding: '6px' }}>Merchant</th>
                        <th style={{ padding: '6px' }}>Amount (₹)</th>
                        <th style={{ padding: '6px' }}>Flagged</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredTransactions.map(tx => (
                        <tr key={tx.tx_id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                          <td style={{ padding: '6px', color: '#b45309' }}><code>{tx.tx_id}</code></td>
                          <td style={{ padding: '6px', color: '#64748b' }}>{tx.account_id}</td>
                          <td style={{ padding: '6px', color: '#0f172a' }}>{tx.merchant}</td>
                          <td style={{ padding: '6px', fontWeight: 800, color: tx.amount < 0 ? '#ef4444' : '#10b981' }}>
                            ₹{Math.abs(tx.amount)?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                          </td>
                          <td style={{ padding: '6px' }}>
                            {tx.is_flagged ? (
                              <span style={{ background: '#fee2e2', color: '#991b1b', padding: '2px 6px', borderRadius: '4px', fontSize: '0.68rem', fontWeight: 800 }}>
                                ⚠️ FLAGGED
                              </span>
                            ) : (
                              <span style={{ color: '#94a3b8' }}>CLEAN</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}

                {ledgerSubTab === 'loans' && (
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem' }}>
                    <thead>
                      <tr style={{ color: '#64748b', borderBottom: '1px solid var(--border-light)', textAlign: 'left' }}>
                        <th style={{ padding: '6px' }}>Loan ID</th>
                        <th style={{ padding: '6px' }}>Customer</th>
                        <th style={{ padding: '6px' }}>Principal (₹)</th>
                        <th style={{ padding: '6px' }}>Rate p.a.</th>
                        <th style={{ padding: '6px' }}>FOIR / DTI</th>
                        <th style={{ padding: '6px' }}>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredLoans.map(ln => (
                        <tr key={ln.loan_id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                          <td style={{ padding: '6px', color: '#b45309' }}><code>{ln.loan_id}</code></td>
                          <td style={{ padding: '6px', color: '#334155' }}>{ln.customer_id}</td>
                          <td style={{ padding: '6px', fontWeight: 800, color: '#0f172a' }}>₹{ln.principal?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                          <td style={{ padding: '6px' }}>{ln.interest_rate}%</td>
                          <td style={{ padding: '6px' }}>{(ln.dti_ratio * 100).toFixed(1)}%</td>
                          <td style={{ padding: '6px' }}>
                            <span style={{
                              padding: '2px 6px',
                              borderRadius: '4px',
                              fontSize: '0.68rem',
                              fontWeight: 700,
                              background: ln.status === 'APPROVED' ? '#d1fae5' : '#fef3c7',
                              color: ln.status === 'APPROVED' ? '#065f46' : '#b45309'
                            }}>
                              {ln.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}

                {ledgerSubTab === 'audit_logs' && (
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem' }}>
                    <thead>
                      <tr style={{ color: '#64748b', borderBottom: '1px solid var(--border-light)', textAlign: 'left' }}>
                        <th style={{ padding: '6px' }}>Time</th>
                        <th style={{ padding: '6px' }}>Specialist</th>
                        <th style={{ padding: '6px' }}>Action</th>
                        <th style={{ padding: '6px' }}>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredAudits.map(aud => (
                        <tr key={aud.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                          <td style={{ padding: '6px', color: '#94a3b8' }}>{aud.timestamp?.substring(11, 19)}</td>
                          <td style={{ padding: '6px', color: '#0f172a' }}>{aud.agent}</td>
                          <td style={{ padding: '6px', color: '#334155' }}><code>{aud.action}</code></td>
                          <td style={{ padding: '6px' }}>
                            <span style={{
                              padding: '1px 5px',
                              borderRadius: '4px',
                              fontSize: '0.68rem',
                              fontWeight: 700,
                              background: aud.status === 'SUCCESS' ? '#d1fae5' : '#fee2e2',
                              color: aud.status === 'SUCCESS' ? '#065f46' : '#991b1b'
                            }}>
                              {aud.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ----------------- Clean White Architecture Blueprint Modal ----------------- */}
      {showArchModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(15, 23, 42, 0.65)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 100,
          backdropFilter: 'blur(8px)'
        }}>
          <div style={{
            background: '#ffffff',
            borderRadius: '16px',
            width: '90%',
            maxWidth: '1000px',
            maxHeight: '90vh',
            overflowY: 'auto',
            padding: '2rem',
            boxShadow: 'var(--shadow-lg)',
            border: '1px solid var(--border-light)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.2rem' }}>
              <div>
                <h3 style={{ fontSize: '1.4rem', color: '#0f172a', fontWeight: 800 }}>
                  Bharat Apex Bank Architecture Blueprint
                </h3>
                <div style={{ fontSize: '0.85rem', color: '#64748b' }}>
                  Enterprise Multi-Agent Topology & Core Banking Framework
                </div>
              </div>
              <button
                onClick={() => setShowArchModal(false)}
                style={{
                  background: '#f1f5f9',
                  border: 'none',
                  color: '#0f172a',
                  padding: '6px 14px',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontWeight: 700
                }}
              >
                ✕ Close
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem', fontSize: '0.82rem' }}>
              <div style={{ background: '#fef3c7', border: '1px solid #fde68a', color: '#b45309', padding: '12px 16px', borderRadius: '10px', fontWeight: 700 }}>
                1. BANKING CHANNELS / CLIENTS: React Web App &middot; Streamlit Concierge &middot; Quick UPI / NetBanking Scenarios
              </div>
              <div style={{ background: '#f1f5f9', border: '1px solid #e2e8f0', color: '#334155', padding: '12px 16px', borderRadius: '10px', fontWeight: 700 }}>
                2. API & EXPERIENCE LAYER: FastAPI REST Gateway &middot; Session Threading (MemorySaver) &middot; Schema Validation
              </div>
              <div style={{ background: '#d1fae5', border: '1px solid #a7f3d0', color: '#065f46', padding: '12px 16px', borderRadius: '10px', fontWeight: 700 }}>
                3. AI CONTROL PLANE: PII Detection &middot; Overdraft Protection &middot; Human-in-the-Loop Limits (₹50,000 Transfer / ₹2,00,000 Lending)
              </div>
              <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', padding: '14px', borderRadius: '10px' }}>
                <div style={{ fontWeight: 800, color: '#0f172a', marginBottom: '8px' }}>4. LANGGRAPH MULTI-AGENT ORCHESTRATOR</div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px', textAlign: 'center' }}>
                  <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', padding: '10px', borderRadius: '8px' }}>
                    <strong style={{ color: '#0f172a' }}>🧭 Aditi (Supervisor)</strong>
                    <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Intent & Policy Router</div>
                  </div>
                  <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', padding: '10px', borderRadius: '8px' }}>
                    <strong style={{ color: '#0f172a' }}>💳 Rohan (Accounts)</strong>
                    <div style={{ fontSize: '0.72rem', color: '#64748b' }}>UPI, Balances & Transfers</div>
                  </div>
                  <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', padding: '10px', borderRadius: '8px' }}>
                    <strong style={{ color: '#0f172a' }}>🛡️ Priya (Fraud Guard)</strong>
                    <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Anomaly Scoring & Card Lock</div>
                  </div>
                  <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', padding: '10px', borderRadius: '8px' }}>
                    <strong style={{ color: '#0f172a' }}>📈 Vikram (Lending)</strong>
                    <div style={{ fontSize: '0.72rem', color: '#64748b' }}>CIBIL & FOIR Underwriting</div>
                  </div>
                </div>
              </div>
              <div style={{ background: '#f1f5f9', border: '1px solid #e2e8f0', color: '#334155', padding: '12px 16px', borderRadius: '10px', fontWeight: 700 }}>
                5. AGENT TOOL LAYER: get_account_overview &middot; execute_transfer &middot; flag_or_block_card &middot; assess_transaction_risk &middot; evaluate_credit_application
              </div>
              <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', color: '#0f172a', padding: '14px 16px', borderRadius: '10px' }}>
                <div style={{ fontWeight: 800, color: '#f59e0b', marginBottom: '6px' }}>6. RELATIONAL CORE-BANKING ENGINE (SQLite via SQLAlchemy in INR ₹)</div>
                <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', color: '#64748b' }}>
                  <span>&bull; <code>customers</code> (Aarav, Bhavna, Chirag)</span>
                  <span>&bull; <code>accounts</code> (Savings, Current, Credit Cards in ₹)</span>
                  <span>&bull; <code>transactions</code> (UPI / IMPS Ledger entries)</span>
                  <span>&bull; <code>loans</code> (Underwritten loan contracts)</span>
                  <span>&bull; <code>audit_logs</code> (Immutable audit trail)</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
