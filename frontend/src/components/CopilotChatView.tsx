import React, { useState, useEffect } from "react";
import {
  api,
  type CopilotResponse,
  type ResearchGapItem,
  type ScientificConflictItem,
  type ScientificHypothesisItem,
} from "../api";

interface Message {
  sender: "user" | "copilot";
  text: string;
  direct_answer?: string;
  comparison_table?: Array<{
    paper_id: string;
    sample: string;
    composition: string;
    dopant: string;
    capacity_0_1c: string;
    capacity_1c: string;
    capacity_5c: string;
    retention: string;
  }>;
  citations?: Array<{
    paper_id: string;
    page_number: number;
    sample_label?: string;
    evidence_quote: string;
  }>;
  timestamp: string;
}

interface CopilotChatViewProps {
  onNavigate?: (section: string) => void;
}

export const CopilotChatView: React.FC<CopilotChatViewProps> = ({ onNavigate }) => {
  const [activeTab, setActiveTab] = useState<"chat" | "discovery">("chat");

  // Chat State
  const [messages, setMessages] = useState<Message[]>([
    {
      sender: "copilot",
      text: "How can I assist your LMFP research today? Ask about dopant effects, high-rate kinetics, phase stability, or literature benchmarks.",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const quickPrompts = [
    "How does Mg doping influence rate capability at 5C?",
    "Compare Mg-, Ti-, and Co-doped LMFP rate kinetics",
    "What crystal structure and space group is confirmed in srep26686?",
    "What are the reported mechanisms of Mn dissolution?",
  ];

  // Discovery State
  const [discoveryQuery, setDiscoveryQuery] = useState("");
  const [discoveryFilter, setDiscoveryFilter] = useState<"gaps" | "conflicts" | "hypotheses">("gaps");
  const [gaps, setGaps] = useState<ResearchGapItem[]>([]);
  const [conflicts, setConflicts] = useState<ScientificConflictItem[]>([]);
  const [hypotheses, setHypotheses] = useState<ScientificHypothesisItem[]>([]);
  const [loadingDiscovery, setLoadingDiscovery] = useState(false);

  const loadDiscoveryData = async (dopant?: string) => {
    setLoadingDiscovery(true);
    try {
      const [gapsRes, conflictsRes, hypRes] = await Promise.all([
        api.getResearchGaps({ dopant: dopant || undefined }),
        api.getScientificConflicts({ dopant: dopant || undefined }),
        api.getScientificHypotheses({ dopant: dopant || undefined }),
      ]);
      setGaps(gapsRes.gaps || []);
      setConflicts(conflictsRes || []);
      setHypotheses(hypRes.hypotheses || []);
    } catch (err) {
      console.error("Discovery load error:", err);
    } finally {
      setLoadingDiscovery(false);
    }
  };

  useEffect(() => {
    if (activeTab === "discovery" && gaps.length === 0) {
      loadDiscoveryData();
    }
  }, [activeTab]);

  const handleSendMessage = async (textToSend?: string) => {
    const query = textToSend || input;
    if (!query.trim() || loading) return;

    const userMsg: Message = {
      sender: "user",
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!textToSend) setInput("");
    setLoading(true);

    try {
      const historyPayload = messages.slice(-4).map((m) => ({
        sender: m.sender,
        text: m.text,
      }));

      const res: CopilotResponse = await api.chatCopilot(query, undefined, historyPayload);
      const copilotMsg: Message = {
        sender: "copilot",
        text: res.response,
        direct_answer: res.direct_answer,
        comparison_table: res.comparison_table,
        citations: res.citations,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, copilotMsg]);
    } catch (err: any) {
      const errorMsg: Message = {
        sender: "copilot",
        text: `Error connecting to Copilot service: ${err.message}`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="view-container">
      {/* Header with Mode Switcher */}
      <section className="section-heading" style={{ marginBottom: "16px" }}>
        <div>
          <h2>Research Copilot &amp; Discovery</h2>
          <p>Evidence-grounded assistant and cross-study literature discovery across 1,215 curated records.</p>
        </div>
        <div style={{ display: "flex", gap: "6px" }}>
          <button
            type="button"
            className={`tab-pill ${activeTab === "chat" ? "active" : ""}`}
            style={{ fontSize: "12px", padding: "6px 14px" }}
            onClick={() => setActiveTab("chat")}
          >
            💬 Copilot Chat
          </button>
          <button
            type="button"
            className={`tab-pill ${activeTab === "discovery" ? "active" : ""}`}
            style={{ fontSize: "12px", padding: "6px 14px" }}
            onClick={() => setActiveTab("discovery")}
          >
            🔬 Discovery Studio
          </button>
        </div>
      </section>

      {/* =========================================================================
          TAB 1: CLEAN COPILOT CHAT
          ========================================================================= */}
      {activeTab === "chat" && (
        <div>
          {/* Suggested Question Chips */}
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginBottom: "14px" }}>
            <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-muted)", alignSelf: "center" }}>
              SUGGESTED:
            </span>
            {quickPrompts.map((q, idx) => (
              <button
                key={idx}
                type="button"
                className="btn btn-secondary btn-sm"
                style={{ fontSize: "11px", padding: "4px 10px" }}
                onClick={() => handleSendMessage(q)}
                disabled={loading}
              >
                {q}
              </button>
            ))}
          </div>

          {/* Chat Messages Card */}
          <div
            className="card"
            style={{
              minHeight: "400px",
              maxHeight: "560px",
              overflowY: "auto",
              padding: "18px",
              display: "flex",
              flexDirection: "column",
              gap: "16px",
              marginBottom: "14px",
              background: "var(--bg-card)",
            }}
          >
            {messages.map((m, idx) => {
              const isUser = m.sender === "user";
              return (
                <div
                  key={idx}
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: isUser ? "flex-end" : "flex-start",
                    width: "100%",
                  }}
                >
                  <div
                    style={{
                      maxWidth: isUser ? "75%" : "85%",
                      padding: isUser ? "10px 16px" : "16px 20px",
                      borderRadius: "10px",
                      background: isUser
                        ? "linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)"
                        : "var(--bg-card)",
                      color: isUser ? "#ffffff" : "var(--text-main)",
                      border: isUser ? "none" : "1px solid var(--border)",
                      boxShadow: "0 2px 10px rgba(0,0,0,0.04)",
                    }}
                  >
                    {/* Direct Answer Box */}
                    {!isUser && m.direct_answer && (
                      <div
                        style={{
                          background: "var(--primary-subtle)",
                          borderLeft: "3px solid var(--primary)",
                          padding: "10px 14px",
                          borderRadius: "6px",
                          marginBottom: "12px",
                        }}
                      >
                        <strong style={{ fontSize: "11px", color: "var(--primary)", display: "block", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                          Direct Answer
                        </strong>
                        <div style={{ fontSize: "13.5px", fontWeight: 600, color: "var(--text-main)", marginTop: "2px" }}>
                          {m.direct_answer}
                        </div>
                      </div>
                    )}

                    {/* Main Text */}
                    <div style={{ fontSize: "13px", lineHeight: "1.5", whiteSpace: "pre-line" }}>
                      {m.text}
                    </div>

                    {/* Multi-Paper Comparison Table if available */}
                    {!isUser && m.comparison_table && m.comparison_table.length > 0 && (
                      <div style={{ marginTop: "12px", overflowX: "auto" }}>
                        <table className="data-table" style={{ fontSize: "11px", width: "100%" }}>
                          <thead>
                            <tr>
                              <th>Paper</th>
                              <th>Composition</th>
                              <th>0.1C</th>
                              <th>2C / 5C</th>
                              <th>Retention</th>
                            </tr>
                          </thead>
                          <tbody>
                            {m.comparison_table.map((row, rIdx) => (
                              <tr key={rIdx}>
                                <td><strong>{row.paper_id}</strong></td>
                                <td><code>{row.composition}</code></td>
                                <td>{row.capacity_0_1c}</td>
                                <td>{row.capacity_5c || row.capacity_1c || "—"}</td>
                                <td>{row.retention}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}

                    {/* Evidence Citations */}
                    {!isUser && m.citations && m.citations.length > 0 && (
                      <div style={{ marginTop: "10px", paddingTop: "8px", borderTop: "1px solid #e2e8f0" }}>
                        <span style={{ fontSize: "10px", fontWeight: 700, color: "#64748b", display: "block", marginBottom: "4px" }}>
                          CITATIONS:
                        </span>
                        {m.citations.map((c, cIdx) => (
                          <div key={cIdx} style={{ fontSize: "11px", color: "#475569", marginBottom: "3px" }}>
                            <strong style={{ color: "#1e40af" }}>{c.paper_id}</strong> (p. {c.page_number}): "{c.evidence_quote}"
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Workflow Actions */}
                    {!isUser && idx > 0 && onNavigate && (
                      <div style={{ marginTop: "12px", paddingTop: "8px", borderTop: "1px solid #e2e8f0", display: "flex", gap: "6px" }}>
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          style={{ fontSize: "10px", padding: "3px 8px" }}
                          onClick={() => onNavigate("Materials Designer")}
                        >
                          ⚗ Send to Designer
                        </button>
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          style={{ fontSize: "10px", padding: "3px 8px" }}
                          onClick={() => onNavigate("Property Prediction")}
                        >
                          ⌁ Simulate (ML)
                        </button>
                      </div>
                    )}
                  </div>

                  <span style={{ fontSize: "10px", color: "#94a3b8", marginTop: "3px", marginInline: "6px" }}>
                    {m.timestamp}
                  </span>
                </div>
              );
            })}

            {loading && (
              <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--text-secondary)", fontSize: "12px" }}>
                <div className="spinner" style={{ width: 14, height: 14 }} />
                <span>Searching literature corpus and synthesizing answer...</span>
              </div>
            )}
          </div>

          {/* Question Input */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            style={{ display: "flex", gap: "8px" }}
          >
            <input
              type="text"
              className="input-field"
              placeholder="Ask a scientific question (e.g. 'What is the effect of Mg doping on rate capability?')..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={loading}
              style={{ flex: 1, padding: "8px 12px", fontSize: "13px" }}
            />
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading || !input.trim()}
              style={{ padding: "8px 18px", fontWeight: 600 }}
            >
              Send ➔
            </button>
          </form>
        </div>
      )}

      {/* =========================================================================
          TAB 2: SIMPLIFIED DISCOVERY STUDIO
          ========================================================================= */}
      {activeTab === "discovery" && (
        <div>
          {/* Search / Question Bar */}
          <div className="card" style={{ padding: "14px 18px", marginBottom: "14px" }}>
            <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
              <input
                type="text"
                className="input-field"
                placeholder="Filter by research question or element (e.g. Mg, Ti, 55°C)..."
                value={discoveryQuery}
                onChange={(e) => setDiscoveryQuery(e.target.value)}
                style={{ flex: 1, padding: "6px 10px", fontSize: "12px" }}
              />
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => loadDiscoveryData(discoveryQuery)}
                disabled={loadingDiscovery}
              >
                {loadingDiscovery ? "Analyzing..." : "Analyze Evidence ➔"}
              </button>
              {discoveryQuery && (
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => {
                    setDiscoveryQuery("");
                    loadDiscoveryData();
                  }}
                >
                  Reset
                </button>
              )}
            </div>
          </div>

          {/* Simple 3 Tabs for Results */}
          <div style={{ display: "flex", gap: "8px", marginBottom: "14px" }}>
            <button
              type="button"
              className={`tab-pill ${discoveryFilter === "gaps" ? "active" : ""}`}
              onClick={() => setDiscoveryFilter("gaps")}
            >
              Literature Gaps ({gaps.length})
            </button>
            <button
              type="button"
              className={`tab-pill ${discoveryFilter === "conflicts" ? "active" : ""}`}
              onClick={() => setDiscoveryFilter("conflicts")}
            >
              Scientific Conflicts ({conflicts.length})
            </button>
            <button
              type="button"
              className={`tab-pill ${discoveryFilter === "hypotheses" ? "active" : ""}`}
              onClick={() => setDiscoveryFilter("hypotheses")}
            >
              Formulated Hypotheses ({hypotheses.length})
            </button>
          </div>

          {/* Results List */}
          {loadingDiscovery ? (
            <div className="loading-state">
              <div className="spinner" />
              <p>Analyzing evidence across 1,215 records...</p>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {/* Gaps List */}
              {discoveryFilter === "gaps" && (
                gaps.length > 0 ? (
                  gaps.map((gap) => (
                    <div key={gap.gap_id} className="card" style={{ padding: "14px 18px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "4px" }}>
                        <div>
                          <span className="badge badge-purple" style={{ marginRight: "6px" }}>{gap.gap_id}</span>
                          <strong style={{ fontSize: "13px", color: "#0f172a" }}>{gap.title}</strong>
                        </div>
                        {onNavigate && (
                          <button
                            type="button"
                            className="btn btn-secondary btn-sm"
                            style={{ fontSize: "10px", padding: "3px 8px" }}
                            onClick={() => onNavigate("Materials Designer")}
                          >
                            Design Formula ➔
                          </button>
                        )}
                      </div>
                      <p style={{ fontSize: "12px", color: "#475569", margin: "4px 0 6px" }}>{gap.description}</p>
                      <div style={{ fontSize: "11px", color: "var(--primary)", fontStyle: "italic" }}>
                        "{gap.scientific_question}"
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="empty-state">
                    <p>No literature gaps found for query "{discoveryQuery}". Click Reset to view all.</p>
                  </div>
                )
              )}

              {/* Conflicts List */}
              {discoveryFilter === "conflicts" && (
                conflicts.length > 0 ? (
                  conflicts.map((c) => (
                    <div key={c.conflict_id} className="card" style={{ padding: "14px 18px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                        <div>
                          <span className="badge badge-amber" style={{ marginRight: "6px" }}>{c.conflict_id}</span>
                          <strong style={{ fontSize: "13px", color: "#0f172a" }}>{c.title || c.topic}</strong>
                        </div>
                      </div>
                      <p style={{ fontSize: "12px", color: "#475569", margin: "4px 0 6px" }}>{c.divergence_description}</p>
                      <div style={{ fontSize: "11px", color: "#166534" }}>
                        <strong>Reconciliation:</strong> {c.suggested_resolution || c.reconciliation_hypothesis}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="empty-state">
                    <p>No scientific conflicts found for query "{discoveryQuery}". Click Reset to view all.</p>
                  </div>
                )
              )}

              {/* Hypotheses List */}
              {discoveryFilter === "hypotheses" && (
                hypotheses.length > 0 ? (
                  hypotheses.map((h) => (
                    <div key={h.hypothesis_id} className="card" style={{ padding: "14px 18px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                        <div>
                          <span className="badge badge-green" style={{ marginRight: "6px" }}>{h.hypothesis_id}</span>
                          <strong style={{ fontSize: "13px", color: "#0f172a" }}>{h.hypothesis_statement}</strong>
                        </div>
                        {onNavigate && (
                          <button
                            type="button"
                            className="btn btn-primary btn-sm"
                            style={{ fontSize: "10px", padding: "3px 8px" }}
                            onClick={() => onNavigate("Materials Designer")}
                          >
                            Test in Designer ➔
                          </button>
                        )}
                      </div>
                      <div style={{ fontSize: "11px", color: "#475569", marginTop: "4px" }}>
                        Candidate: <code>{h.experimental_protocol.candidate_composition}</code>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="empty-state">
                    <p>No hypotheses formulated under query "{discoveryQuery}". Click Reset to view all.</p>
                  </div>
                )
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
