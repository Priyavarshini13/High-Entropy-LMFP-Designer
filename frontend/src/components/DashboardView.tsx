import React, { useEffect, useRef, useState } from "react";
import { api, type CopilotResponse } from "../api";
import {
  getChatSessions,
  getChatSession,
  createChatSession,
  addMessageToSession,
  deleteChatSession,
  type ChatSession,
  type ChatMessage,
} from "../utils/researchHistory";

interface DashboardViewProps {
  onNavigate: (section: string) => void;
  resetTrigger?: number;
  activeSessionId?: string | null;
  onSelectSession?: (sessionId: string | null) => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  onNavigate: _onNavigate,
  resetTrigger,
  activeSessionId,
  onSelectSession,
}) => {
  const [query, setQuery] = useState("");
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(activeSessionId || null);

  // Initialize messages directly from activeSessionId if present
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    if (activeSessionId) {
      const s = getChatSession(activeSessionId);
      if (s) {
        if (s.messages && s.messages.length > 0) return s.messages;
        return [
          {
            id: `msg-${s.id}-u`,
            sender: "user",
            text: s.title,
            timestamp: s.timestamp || "",
          },
          ...(s.directAnswerSnippet
            ? [
                {
                  id: `msg-${s.id}-c`,
                  sender: "copilot" as const,
                  text: s.directAnswerSnippet,
                  direct_answer: s.directAnswerSnippet,
                  timestamp: s.timestamp || "",
                },
              ]
            : []),
        ];
      }
    }
    return [];
  });

  const [loading, setLoading] = useState(false);
  const [linkCandidateOpen, setLinkCandidateOpen] = useState(false);
  const [selectedCandidate, setSelectedCandidate] = useState<string | null>(null);
  const [chatSessions, setChatSessions] = useState<ChatSession[]>(() => getChatSessions());

  // Image Upload State (Task 1: Research Copilot Attachment)
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const [attachedPreview, setAttachedPreview] = useState<string | null>(null);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [enlargedImageUrl, setEnlargedImageUrl] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const followUpFileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Live real-time clock & date matching Novyte Q
  const [timeStr, setTimeStr] = useState(() => {
    const d = new Date();
    return d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit", hour12: true }).toLowerCase();
  });
  const [dateStr, setDateStr] = useState(() => {
    const d = new Date();
    return d.toLocaleDateString([], { weekday: "long", day: "numeric", month: "long" });
  });

  useEffect(() => {
    const interval = setInterval(() => {
      const d = new Date();
      setTimeStr(d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit", hour12: true }).toLowerCase());
      setDateStr(d.toLocaleDateString([], { weekday: "long", day: "numeric", month: "long" }));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  // Listen to chat sessions storage updates
  useEffect(() => {
    const onSessionsUpdate = () => {
      setChatSessions(getChatSessions());
    };
    window.addEventListener("ecmt_chat_sessions_updated", onSessionsUpdate);
    return () => window.removeEventListener("ecmt_chat_sessions_updated", onSessionsUpdate);
  }, []);

  // Handle activeSessionId changes (e.g. user clicks a session in the sidebar)
  useEffect(() => {
    if (activeSessionId) {
      const session = getChatSession(activeSessionId);
      if (session) {
        setCurrentSessionId(session.id);
        if (session.messages && session.messages.length > 0) {
          setMessages(session.messages);
        } else {
          setMessages([
            {
              id: `msg-${session.id}-u`,
              sender: "user",
              text: session.title,
              timestamp: session.timestamp || "",
            },
            ...(session.directAnswerSnippet
              ? [
                  {
                    id: `msg-${session.id}-c`,
                    sender: "copilot" as const,
                    text: session.directAnswerSnippet,
                    direct_answer: session.directAnswerSnippet,
                    timestamp: session.timestamp || "",
                  },
                ]
              : []),
          ]);
        }
        setSelectedCandidate(session.candidate || null);
        return;
      }
    }
    // If activeSessionId is null/cleared
    if (!activeSessionId) {
      setCurrentSessionId(null);
      setMessages([]);
      setSelectedCandidate(null);
      setQuery("");
    }
  }, [activeSessionId]);

  // Reset to clean home screen when resetTrigger updates
  useEffect(() => {
    if (resetTrigger && resetTrigger > 0) {
      setCurrentSessionId(null);
      setMessages([]);
      setSelectedCandidate(null);
      setQuery("");
      handleRemoveAttachedFile();
      onSelectSession?.(null);
    }
  }, [resetTrigger]);

  // Auto-scroll when messages change or loading state changes
  useEffect(() => {
    if (messages.length > 0) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, loading]);

  // Handle Image File Selection
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate size (25MB limit)
    const MAX_SIZE = 25 * 1024 * 1024;
    if (file.size > MAX_SIZE) {
      alert("File size exceeds 25 MB limit. Please select an image under 25 MB.");
      return;
    }

    // Validate format
    const allowed = [".png", ".jpg", ".jpeg", ".webp", ".tiff", ".tif"];
    const ext = "." + file.name.split(".").pop()?.toLowerCase();
    if (!allowed.includes(ext)) {
      alert(`Unsupported image format (${ext}). Allowed formats: ${allowed.join(", ")}`);
      return;
    }

    setAttachedFile(file);
    const objectUrl = URL.createObjectURL(file);
    setAttachedPreview(objectUrl);
  };

  const handleRemoveAttachedFile = () => {
    if (attachedPreview) {
      URL.revokeObjectURL(attachedPreview);
    }
    setAttachedFile(null);
    setAttachedPreview(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
    if (followUpFileInputRef.current) followUpFileInputRef.current.value = "";
  };

  const handleSend = async (customQuery?: string) => {
    const q = (customQuery || query).trim();
    if ((!q && !attachedFile) || loading) return;

    const actualQuery = q || (attachedFile ? `Characterization analysis for ${attachedFile.name}` : "");
    let targetSessionId = currentSessionId;
    const timeNow = new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit", hour12: true }).toLowerCase();

    // 1. Upload attached characterization image if present
    let uploadedImageUrl: string | undefined = undefined;
    let uploadedImageName: string | undefined = undefined;

    if (attachedFile) {
      setUploadingImage(true);
      try {
        const uploadRes = await api.uploadImage(attachedFile, "copilot");
        uploadedImageUrl = uploadRes.url;
        uploadedImageName = uploadRes.original_filename;
      } catch (uploadErr: any) {
        console.error("Image upload failed:", uploadErr);
        alert(`Notice: Image upload failed (${uploadErr.message}). Continuing with text query.`);
      } finally {
        setUploadingImage(false);
      }
    }

    // Clean up local preview
    handleRemoveAttachedFile();

    // 2. Manage chat session state
    if (!targetSessionId || messages.length === 0) {
      const newSession = createChatSession(actualQuery, selectedCandidate, uploadedImageUrl, uploadedImageName);
      targetSessionId = newSession.id;
      setCurrentSessionId(newSession.id);
      setMessages(newSession.messages);
      onSelectSession?.(newSession.id);
    } else {
      const userMsg: Omit<ChatMessage, "id"> = {
        sender: "user",
        text: actualQuery,
        timestamp: timeNow,
        attached_image_url: uploadedImageUrl,
        attached_image_name: uploadedImageName,
      };
      const updatedSession = addMessageToSession(targetSessionId, userMsg, actualQuery, selectedCandidate);
      setMessages([...updatedSession.messages]);
    }

    setQuery("");
    setLoading(true);

    try {
      const compContext = selectedCandidate ? { formula_string: selectedCandidate } : undefined;
      const historyPayload = messages.map((m) => ({
        sender: m.sender,
        text: m.text,
      }));

      const res: CopilotResponse = await api.chatCopilot(
        actualQuery,
        compContext,
        historyPayload,
        uploadedImageUrl,
        uploadedImageName
      );

      const copilotMsg: Omit<ChatMessage, "id"> = {
        sender: "copilot",
        text: res.response,
        direct_answer: res.direct_answer,
        explanation: res.explanation,
        comparison_table: res.comparison_table,
        citations: res.citations,
        conflicts_and_limitations: res.conflicts_and_limitations,
        timestamp: new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit", hour12: true }).toLowerCase(),
      };

      if (targetSessionId) {
        const finalizedSession = addMessageToSession(targetSessionId, copilotMsg, actualQuery, selectedCandidate);
        setMessages([...finalizedSession.messages]);
      }
    } catch (err: any) {
      const errorMsg: Omit<ChatMessage, "id"> = {
        sender: "copilot",
        text: `Unable to complete research query: ${err.message || "Network or service error."}`,
        timestamp: new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit", hour12: true }).toLowerCase(),
      };
      if (targetSessionId) {
        const finalizedSession = addMessageToSession(targetSessionId, errorMsg, actualQuery, selectedCandidate);
        setMessages([...finalizedSession.messages]);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSend();
    }
  };

  const handleOpenExistingSession = (sessionId: string) => {
    onSelectSession?.(sessionId);
    const session = getChatSession(sessionId);
    if (session) {
      setCurrentSessionId(session.id);
      if (session.messages && session.messages.length > 0) {
        setMessages(session.messages);
      } else {
        setMessages([
          {
            id: `msg-${session.id}-u`,
            sender: "user",
            text: session.title,
            timestamp: session.timestamp || "",
          },
          ...(session.directAnswerSnippet
            ? [
                {
                  id: `msg-${session.id}-c`,
                  sender: "copilot" as const,
                  text: session.directAnswerSnippet,
                  direct_answer: session.directAnswerSnippet,
                  timestamp: session.timestamp || "",
                },
              ]
            : []),
        ]);
      }
      setSelectedCandidate(session.candidate || null);
    }
  };

  const handleStartNewResearch = () => {
    setCurrentSessionId(null);
    setMessages([]);
    setSelectedCandidate(null);
    setQuery("");
    handleRemoveAttachedFile();
    onSelectSession?.(null);
  };

  // --------------------------------------------------------------------------
  // STATE 1: INITIAL CLEAN "WHAT SHOULD ECMT AI WORK ON?" SCREEN (NOVYTE Q STYLE)
  // --------------------------------------------------------------------------
  if (messages.length === 0) {
    return (
      <div className="novyte-q-canvas">
        {/* Hidden File Input for Characterization Images */}
        <input
          type="file"
          ref={fileInputRef}
          style={{ display: "none" }}
          accept=".png,.jpg,.jpeg,.webp,.tiff,.tif"
          onChange={handleFileChange}
        />

        <div className="novyte-q-center">
          {/* Main Question Heading */}
          <h1 className="novyte-q-title">What should ECMT AI work on?</h1>

          {/* Floating Image Attachment Preview */}
          {attachedPreview && (
            <div
              style={{
                marginBottom: "12px",
                display: "inline-flex",
                alignItems: "center",
                gap: "10px",
                padding: "6px 14px 6px 8px",
                background: "#ffffff",
                border: "1px solid #bfdbfe",
                borderRadius: "9999px",
                boxShadow: "0 4px 14px rgba(37, 99, 235, 0.08)",
                fontSize: "13.5px",
              }}
            >
              <img
                src={attachedPreview}
                alt="Characterization preview"
                style={{ width: "28px", height: "28px", borderRadius: "6px", objectFit: "cover" }}
              />
              <span style={{ fontWeight: 600, color: "#1d4ed8", maxWidth: "240px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {attachedFile?.name}
              </span>
              <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                ({((attachedFile?.size || 0) / (1024 * 1024)).toFixed(2)} MB)
              </span>
              <button
                type="button"
                onClick={handleRemoveAttachedFile}
                style={{
                  width: "20px",
                  height: "20px",
                  borderRadius: "50%",
                  background: "#fee2e2",
                  color: "#ef4444",
                  fontSize: "11px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  cursor: "pointer",
                  border: "none",
                }}
                title="Remove attached image"
              >
                ✕
              </button>
            </div>
          )}

          {/* Big Rounded Search Input Bar */}
          <div className="novyte-q-search-box">
            <button
              type="button"
              className="novyte-q-plus"
              onClick={() => fileInputRef.current?.click()}
              title="Attach characterization image (XRD pattern, SEM micrograph, TEM, or electrode photo)"
              style={{
                cursor: "pointer",
                background: "none",
                border: "none",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                padding: "2px",
              }}
            >
              📎
            </button>
            <input
              type="text"
              className="novyte-q-input"
              placeholder={attachedFile ? `Ask a scientific question about ${attachedFile.name}...` : "A question, a compound, or a task"}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              autoFocus
            />
            <button
              className="novyte-q-arrow-btn"
              onClick={() => handleSend()}
              title="Submit research inquiry to ECMT AI"
              disabled={uploadingImage || loading}
            >
              ➔
            </button>
          </div>

          {/* Link Project / Candidate Pill */}
          <div style={{ position: "relative" }}>
            <button
              type="button"
              className="novyte-q-link-pill"
              onClick={() => setLinkCandidateOpen(!linkCandidateOpen)}
            >
              <span style={{ fontSize: "11px" }}>🔗</span>
              <span>{selectedCandidate ? `Linked: ${selectedCandidate}` : "Link a candidate"}</span>
              <span style={{ fontSize: "9px", color: "var(--text-muted)" }}>▼</span>
            </button>

            {linkCandidateOpen && (
              <div
                style={{
                  position: "absolute",
                  top: "100%",
                  left: "50%",
                  transform: "translateX(-50%)",
                  marginTop: "6px",
                  background: "var(--bg-card)",
                  border: "1px solid var(--border)",
                  borderRadius: "8px",
                  boxShadow: "0 8px 24px rgba(0,0,0,0.08)",
                  padding: "6px",
                  zIndex: 20,
                  width: "280px",
                }}
              >
                <div
                  style={{
                    padding: "8px 10px",
                    fontSize: "13px",
                    fontWeight: 600,
                    cursor: "pointer",
                    borderRadius: "6px",
                    color: "var(--text-main)",
                  }}
                  onClick={() => {
                    setSelectedCandidate(null);
                    setLinkCandidateOpen(false);
                  }}
                >
                  None (Universal LMFP Literature)
                </div>
                <div
                  style={{
                    padding: "8px 10px",
                    fontSize: "13px",
                    cursor: "pointer",
                    borderRadius: "6px",
                    color: "var(--text-main)",
                  }}
                  onClick={() => {
                    setSelectedCandidate("LiMn0.7Fe0.24Mg0.02Ti0.02Co0.02PO4");
                    setLinkCandidateOpen(false);
                  }}
                >
                  LiMn0.7Fe0.24Mg0.02Ti0.02Co0.02PO4 (HE-LMFP)
                </div>
                <div
                  style={{
                    padding: "8px 10px",
                    fontSize: "13px",
                    cursor: "pointer",
                    borderRadius: "6px",
                    color: "var(--text-main)",
                  }}
                  onClick={() => {
                    setSelectedCandidate("LiMn0.75Fe0.25PO4");
                    setLinkCandidateOpen(false);
                  }}
                >
                  LiMn0.75Fe0.25PO4 (Baseline LMFP)
                </div>
              </div>
            )}
          </div>

          {/* 3 Clean Suggested Tasks / Prompt Cards (Exact Novyte Q Layout) */}
          <div className="novyte-q-suggestions">
            <div
              className="novyte-q-row"
              onClick={() => handleSend("Compare Mg, Co, and Ti dopants in LMFP")}
            >
              <div className="novyte-q-row-left">
                <div className="novyte-q-icon-box" style={{ background: "rgba(37, 99, 235, 0.08)", borderColor: "rgba(37, 99, 235, 0.2)", color: "#2563eb" }}>🧪</div>
                <div>
                  <strong className="novyte-q-row-title">
                    Compare Mg, Co, and Ti dopants in LMFP
                  </strong>
                  <span className="novyte-q-row-sub">Quick answer · condition parity comparison</span>
                </div>
              </div>
              <span className="novyte-q-chevron">&gt;</span>
            </div>

            <div
              className="novyte-q-row"
              onClick={() => handleSend("Design a project for high-entropy LMFP with multi-cation stability")}
            >
              <div className="novyte-q-row-left">
                <div className="novyte-q-icon-box" style={{ background: "rgba(16, 185, 129, 0.08)", borderColor: "rgba(16, 185, 129, 0.2)", color: "#10b981" }}>⚛</div>
                <div>
                  <strong className="novyte-q-row-title">
                    Design a project for high-entropy LMFP with multi-cation stability
                  </strong>
                  <span className="novyte-q-row-sub">ECMT AI drafts stages and predictive stability</span>
                </div>
              </div>
              <span className="novyte-q-chevron">&gt;</span>
            </div>

            <div
              className="novyte-q-row"
              onClick={() => handleSend("Find routes and synthesis papers for spray-dried LMFP")}
            >
              <div className="novyte-q-row-left">
                <div className="novyte-q-icon-box" style={{ background: "rgba(124, 58, 237, 0.08)", borderColor: "rgba(124, 58, 237, 0.2)", color: "#7c3aed" }}>📖</div>
                <div>
                  <strong className="novyte-q-row-title">
                    Find routes and synthesis papers for spray-dried LMFP
                  </strong>
                  <span className="novyte-q-row-sub">
                    Documented routes, patents and samples in Literature
                  </span>
                </div>
              </div>
              <span className="novyte-q-chevron">&gt;</span>
            </div>
          </div>

          {/* Recent Research History Chips */}
          {chatSessions.length > 0 && (
            <div style={{ width: "100%", marginTop: "28px" }}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: "10px",
                  padding: "0 4px",
                }}
              >
                <span
                  style={{
                    fontSize: "11px",
                    fontWeight: 700,
                    color: "var(--text-muted)",
                    letterSpacing: "0.5px",
                    textTransform: "uppercase",
                  }}
                >
                  Recent Inquiries ({chatSessions.length})
                </span>
                <span
                  style={{
                    fontSize: "11px",
                    color: "var(--primary)",
                    cursor: "pointer",
                    fontWeight: 600,
                  }}
                  onClick={() => handleOpenExistingSession(chatSessions[0].id)}
                >
                  Open latest ›
                </span>
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                {chatSessions.slice(0, 4).map((session) => (
                  <button
                    key={session.id}
                    type="button"
                    onClick={() => handleOpenExistingSession(session.id)}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "6px",
                      padding: "6px 12px",
                      borderRadius: "9999px",
                      background: "#ffffff",
                      border: "1px solid var(--border)",
                      fontSize: "12.5px",
                      color: "var(--text-main)",
                      boxShadow: "0 1px 3px rgba(0,0,0,0.03)",
                      cursor: "pointer",
                      transition: "all 0.15s ease",
                      maxWidth: "320px",
                    }}
                    title={session.title}
                  >
                    <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>🕒</span>
                    <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontWeight: 500 }}>
                      {session.title}
                    </span>
                    <span style={{ fontSize: "10px", color: "var(--text-muted)", marginLeft: "4px" }}>
                      ({session.messages?.length || 1})
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Bottom Left Live Clock */}
        <div className="novyte-q-clock">
          <div className="novyte-q-time">{timeStr}</div>
          <div className="novyte-q-date">{dateStr}</div>
        </div>

        {/* Bottom Right Watermark ECMT AI */}
        <div className="novyte-q-watermark">ECMT AI</div>
      </div>
    );
  }

  // --------------------------------------------------------------------------
  // STATE 2: ACTIVE CONVERSATION VIEW (RESTORED CHAT HISTORY & CONTINUATION)
  // --------------------------------------------------------------------------
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "calc(100vh - 56px)",
        maxWidth: "960px",
        margin: "0 auto",
        width: "100%",
        padding: "20px 24px",
      }}
    >
      {/* Hidden File Input for Follow-up Characterization Images */}
      <input
        type="file"
        ref={followUpFileInputRef}
        style={{ display: "none" }}
        accept=".png,.jpg,.jpeg,.webp,.tiff,.tif"
        onChange={handleFileChange}
      />

      {/* Enlarged Image Modal View */}
      {enlargedImageUrl && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(0, 0, 0, 0.8)",
            zIndex: 9999,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "24px",
          }}
          onClick={() => setEnlargedImageUrl(null)}
        >
          <div
            style={{
              position: "relative",
              maxWidth: "92vw",
              maxHeight: "92vh",
              backgroundColor: "#ffffff",
              borderRadius: "14px",
              padding: "16px",
              boxShadow: "0 25px 60px rgba(0,0,0,0.5)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <button
              type="button"
              onClick={() => setEnlargedImageUrl(null)}
              style={{
                position: "absolute",
                top: "-12px",
                right: "-12px",
                width: "34px",
                height: "34px",
                borderRadius: "50%",
                backgroundColor: "#0f172a",
                color: "#ffffff",
                fontSize: "16px",
                fontWeight: 700,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                cursor: "pointer",
                border: "2px solid #ffffff",
                boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
              }}
            >
              ✕
            </button>
            <img
              src={enlargedImageUrl}
              alt="Characterization Micrograph"
              style={{
                maxWidth: "88vw",
                maxHeight: "82vh",
                objectFit: "contain",
                borderRadius: "8px",
                display: "block",
              }}
            />
          </div>
        </div>
      )}

      {/* Top action strip: New research & active candidate */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "16px",
          paddingBottom: "12px",
          borderBottom: "1px solid var(--border)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={handleStartNewResearch}
            style={{ fontSize: "13px", borderRadius: "9999px", padding: "5px 14px" }}
            title="Return to search"
          >
            ← Back
          </button>
          <span style={{ fontSize: "16px", fontWeight: 700, color: "var(--text-main)" }}>
            Research Session
          </span>
          {selectedCandidate && (
            <span
              style={{
                fontSize: "12.5px",
                background: "var(--bg-subtle)",
                padding: "3px 10px",
                borderRadius: "12px",
                border: "1px solid var(--border)",
                color: "var(--text-muted)",
              }}
            >
              🔗 {selectedCandidate}
            </span>
          )}
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          {currentSessionId && (
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => {
                deleteChatSession(currentSessionId);
                handleStartNewResearch();
              }}
              style={{
                fontSize: "13px",
                borderRadius: "9999px",
                padding: "5px 12px",
                color: "#dc2626",
                borderColor: "rgba(239, 68, 68, 0.3)",
              }}
              title="Delete this chat from history"
            >
              🗑 Delete chat
            </button>
          )}
          <button
            className="btn-new-research"
            onClick={handleStartNewResearch}
            style={{ fontSize: "13.5px", padding: "6px 16px", borderRadius: "9999px" }}
          >
            <span>+</span>
            <span>New research</span>
          </button>
        </div>
      </div>

      {/* Messages Thread */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          display: "flex",
          flexDirection: "column",
          gap: "20px",
          paddingRight: "8px",
        }}
      >
        {messages.map((m, idx) => (
          <div
            key={m.id || idx}
            style={{
              alignSelf: m.sender === "user" ? "flex-end" : "flex-start",
              maxWidth: m.sender === "user" ? "80%" : "100%",
              width: m.sender === "user" ? "auto" : "100%",
            }}
          >
            {m.sender === "user" ? (
              <div
                style={{
                  background: "#0f172a",
                  color: "#ffffff",
                  padding: "14px 20px",
                  borderRadius: "18px 18px 4px 18px",
                  fontSize: "15.5px",
                  lineHeight: "1.55",
                  boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
                  fontWeight: 500,
                }}
              >
                {/* Attached Image Thumbnail */}
                {m.attached_image_url && (
                  <div style={{ marginBottom: "10px" }}>
                    <div
                      style={{
                        cursor: "pointer",
                        borderRadius: "10px",
                        overflow: "hidden",
                        border: "1px solid rgba(255, 255, 255, 0.2)",
                        maxWidth: "280px",
                        background: "rgba(0, 0, 0, 0.25)",
                      }}
                      onClick={() => setEnlargedImageUrl(m.attached_image_url || null)}
                      title="Click to enlarge image"
                    >
                      <img
                        src={m.attached_image_url}
                        alt={m.attached_image_name || "Characterization micrograph"}
                        style={{ width: "100%", maxHeight: "180px", objectFit: "cover", display: "block" }}
                      />
                      <div
                        style={{
                          padding: "5px 10px",
                          fontSize: "11.5px",
                          color: "rgba(255, 255, 255, 0.8)",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                        }}
                      >
                        <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          📷 {m.attached_image_name || "Characterization Image"}
                        </span>
                        <span style={{ fontSize: "10px", opacity: 0.8 }}>🔍 View</span>
                      </div>
                    </div>
                  </div>
                )}
                {m.text}
              </div>
            ) : (
              <div
                className="card"
                style={{
                  padding: "26px",
                  borderRadius: "14px",
                  border: "1px solid var(--border)",
                  boxShadow: "0 2px 12px rgba(0,0,0,0.03)",
                }}
              >
                {/* Direct Answer */}
                {m.direct_answer ? (
                  <div style={{ marginBottom: "18px" }}>
                    <div
                      style={{
                        fontSize: "12px",
                        fontWeight: 700,
                        letterSpacing: "0.5px",
                        color: "var(--text-muted)",
                        textTransform: "uppercase",
                        marginBottom: "8px",
                      }}
                    >
                      DIRECT ANSWER
                    </div>
                    <div
                      style={{
                        fontSize: "15.5px",
                        lineHeight: "1.65",
                        color: "var(--text-main)",
                        whiteSpace: "pre-line",
                      }}
                    >
                      {m.direct_answer}
                    </div>
                  </div>
                ) : (
                  <div style={{ fontSize: "15.5px", lineHeight: "1.65", whiteSpace: "pre-line" }}>
                    {m.text}
                  </div>
                )}

                {/* Scientific Explanation */}
                {m.explanation && (
                  <div style={{ marginTop: "18px", paddingTop: "16px", borderTop: "1px solid var(--border)" }}>
                    <div
                      style={{
                        fontSize: "12px",
                        fontWeight: 700,
                        letterSpacing: "0.5px",
                        color: "var(--text-muted)",
                        textTransform: "uppercase",
                        marginBottom: "8px",
                      }}
                    >
                      SCIENTIFIC EXPLANATION
                    </div>
                    <div
                      style={{
                        fontSize: "15px",
                        lineHeight: "1.65",
                        color: "var(--text-secondary)",
                        whiteSpace: "pre-line",
                      }}
                    >
                      {m.explanation}
                    </div>
                  </div>
                )}

                {/* 7-Column Condition Parity Comparison Table */}
                {m.comparison_table && m.comparison_table.length > 0 && (
                  <div style={{ marginTop: "20px", paddingTop: "16px", borderTop: "1px solid var(--border)" }}>
                    <div
                      style={{
                        fontSize: "12px",
                        fontWeight: 700,
                        letterSpacing: "0.5px",
                        color: "var(--text-muted)",
                        textTransform: "uppercase",
                        marginBottom: "10px",
                      }}
                    >
                      EXPERIMENTAL EVIDENCE &amp; CONDITION COMPARISON
                    </div>
                    <div style={{ overflowX: "auto" }}>
                      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13.5px" }}>
                        <thead>
                          <tr style={{ background: "var(--bg-subtle)", borderBottom: "1px solid var(--border)" }}>
                            <th style={{ padding: "9px 12px", textAlign: "left" }}>Dopant / Composition</th>
                            <th style={{ padding: "9px 12px", textAlign: "center" }}>Category</th>
                            <th style={{ padding: "9px 12px", textAlign: "left" }}>Reported Capacity &amp; C-rate</th>
                            <th style={{ padding: "9px 12px", textAlign: "left" }}>Cycling Retention</th>
                            <th style={{ padding: "9px 12px", textAlign: "left" }}>Synthesis</th>
                            <th style={{ padding: "9px 12px", textAlign: "left" }}>Source</th>
                            <th style={{ padding: "9px 12px", textAlign: "left" }}>Limitations</th>
                          </tr>
                        </thead>
                        <tbody>
                          {m.comparison_table.map((row, rIdx) => (
                            <tr key={rIdx} style={{ borderBottom: "1px solid var(--border)" }}>
                              <td style={{ padding: "9px 12px" }}>
                                <strong>{row.dopant || "None"}</strong> ·{" "}
                                <code style={{ fontSize: "12.5px" }}>{row.composition || "LMFP"}</code>
                              </td>
                              <td style={{ padding: "9px 12px", textAlign: "center" }}>
                                <span
                                  style={{
                                    fontSize: "11.5px",
                                    padding: "2px 7px",
                                    borderRadius: "4px",
                                    background: "var(--bg-subtle)",
                                    border: "1px solid var(--border)",
                                  }}
                                >
                                  {row.category || "Single-Dopant"}
                                </span>
                              </td>
                              <td style={{ padding: "9px 12px" }}>
                                {row.reported_capacity || row.capacity_0_1c || "—"}
                              </td>
                              <td style={{ padding: "9px 12px" }}>
                                {row.cycling_retention || row.retention || "—"}
                              </td>
                              <td style={{ padding: "9px 12px" }}>{row.synthesis || "—"}</td>
                              <td style={{ padding: "9px 12px" }}>
                                <span style={{ color: "var(--text-muted)" }}>
                                  {row.evidence_source || row.paper_id}
                                </span>
                              </td>
                              <td style={{ padding: "9px 12px", color: "var(--text-muted)", fontSize: "12.5px" }}>
                                {row.limitations || "Conditions diverge."}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Verified Citations */}
                {m.citations && m.citations.length > 0 && (
                  <div
                    style={{
                      marginTop: "18px",
                      paddingTop: "14px",
                      borderTop: "1px solid var(--border)",
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                      flexWrap: "wrap",
                    }}
                  >
                    <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-muted)" }}>
                      CITATIONS:
                    </span>
                    {m.citations.slice(0, 5).map((c, cIdx) => (
                      <span
                        key={cIdx}
                        style={{
                          fontSize: "12px",
                          padding: "3px 10px",
                          borderRadius: "12px",
                          background: "var(--bg-subtle)",
                          border: "1px solid var(--border)",
                          color: "var(--text-secondary)",
                        }}
                      >
                        [{c.paper_id || c.doi}, p. {c.page_number || 1}]
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div
            className="card"
            style={{
              padding: "16px 20px",
              display: "flex",
              alignItems: "center",
              gap: "12px",
              color: "var(--text-muted)",
              fontSize: "14px",
            }}
          >
            <div className="spinner" style={{ width: "16px", height: "16px", borderWidth: "2px" }} />
            <span>Retrieving grounded literature evidence and synthesizing scientific response...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Floating Bottom Input Bar for Follow-up questions */}
      <div style={{ marginTop: "16px" }}>
        {attachedPreview && (
          <div
            style={{
              marginBottom: "8px",
              display: "inline-flex",
              alignItems: "center",
              gap: "10px",
              padding: "4px 12px 4px 8px",
              background: "#ffffff",
              border: "1px solid #bfdbfe",
              borderRadius: "9999px",
              boxShadow: "0 2px 8px rgba(37, 99, 235, 0.08)",
              fontSize: "12.5px",
            }}
          >
            <img
              src={attachedPreview}
              alt="Preview"
              style={{ width: "24px", height: "24px", borderRadius: "4px", objectFit: "cover" }}
            />
            <span style={{ fontWeight: 600, color: "#1d4ed8", maxWidth: "200px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {attachedFile?.name}
            </span>
            <button
              type="button"
              onClick={handleRemoveAttachedFile}
              style={{
                width: "18px",
                height: "18px",
                borderRadius: "50%",
                background: "#fee2e2",
                color: "#ef4444",
                fontSize: "10px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                cursor: "pointer",
                border: "none",
              }}
              title="Remove attached image"
            >
              ✕
            </button>
          </div>
        )}

        <div className="novyte-q-search-box" style={{ maxWidth: "100%", boxShadow: "0 2px 14px rgba(0,0,0,0.06)" }}>
          <button
            type="button"
            className="novyte-q-plus"
            onClick={() => followUpFileInputRef.current?.click()}
            title="Attach XRD pattern, SEM micrograph, TEM, or electrode photo"
            style={{
              cursor: "pointer",
              background: "none",
              border: "none",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: "2px",
            }}
          >
            📎
          </button>
          <input
            type="text"
            className="novyte-q-input"
            placeholder={attachedFile ? `Ask a scientific question about ${attachedFile.name}...` : "Ask ECMT AI a follow-up question or enter another composition..."}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
          />
          <button
            className="novyte-q-arrow-btn"
            onClick={() => handleSend()}
            disabled={loading || uploadingImage}
            title="Send inquiry"
          >
            ➔
          </button>
        </div>
      </div>
    </div>
  );
};
