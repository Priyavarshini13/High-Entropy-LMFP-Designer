import { useEffect, useState } from "react";
import "./App.css";
import { api } from "./api";
import { AuthView, type AuthUser } from "./components/AuthView";
import { DashboardView } from "./components/DashboardView";
import { ProjectsView } from "./components/ProjectsView";
import { LiteratureIntelligenceView } from "./components/LiteratureIntelligenceView";
import { CopilotChatView } from "./components/CopilotChatView";
import { MaterialsDesignerView } from "./components/MaterialsDesignerView";
import { PropertyPredictionView } from "./components/PropertyPredictionView";
import { ExperimentManagementView } from "./components/ExperimentManagementView";
import {
  getChatSessions,
  deleteChatSession,
  clearAllChatSessions,
  type ChatSession,
} from "./utils/researchHistory";

const hashToSectionId = (hash: string) => {
  const clean = hash.replace(/^#\/?/, "").toLowerCase().replace(/[-_]/g, " ").trim();
  if (!clean || clean === "ecmt" || clean === "ecmt ai" || clean === "ecmt-ai" || clean === "q" || clean === "dashboard" || clean === "overview") return "ECMT AI";
  if (clean === "projects") return "Projects";
  if (clean.includes("lit")) return "Literature Intelligence";
  if (clean.includes("copilot") || clean.includes("chat") || clean.includes("disc")) return "Research Copilot";
  if (clean.includes("mat") || clean.includes("designer")) return "Materials Designer";
  if (clean.includes("pred")) return "Property Prediction";
  if (clean.includes("exp")) return "Experiment Management";
  return "ECMT AI";
};

function App() {
  const [active, setActive] = useState(() => hashToSectionId(window.location.hash));
  const [apiStatus, setApiStatus] = useState("Checking...");
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [modulesOpen, setModulesOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(true);
  const [resetTrigger, setResetTrigger] = useState(0);

  // Dynamic Chat Sessions & Research History State
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [chatSessions, setChatSessions] = useState<ChatSession[]>(() => getChatSessions());

  // Authentication State (Initially null or read from localStorage)
  const [authUser, setAuthUser] = useState<AuthUser | null>(() => {
    const saved = localStorage.getItem("ecmt_ai_user");
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        return null;
      }
    }
    return null;
  });
  const [profileMenuOpen, setProfileMenuOpen] = useState(false);

  // Listen to chat sessions storage updates
  useEffect(() => {
    const onSessionsUpdate = () => {
      setChatSessions(getChatSessions());
    };
    window.addEventListener("ecmt_chat_sessions_updated", onSessionsUpdate);
    return () => window.removeEventListener("ecmt_chat_sessions_updated", onSessionsUpdate);
  }, []);

  const navigateTo = (id: string) => {
    setActive(id);
    window.location.hash = id.toLowerCase().replace(/\s+/g, "-");
  };

  const handleNewResearch = () => {
    setActiveSessionId(null);
    setResetTrigger((prev) => prev + 1);
    navigateTo("ECMT AI");
  };

  const toggleTheme = () => {
    setTheme((prev) => (prev === "light" ? "dark" : "light"));
  };

  const handleSignOut = () => {
    localStorage.removeItem("ecmt_ai_user");
    localStorage.removeItem("ecmt_session_token");
    setAuthUser(null);
    setProfileMenuOpen(false);
  };

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  // Warm-up ping to wake up free cloud backend (Render) if asleep
  useEffect(() => {
    api.getHealth().catch(() => {});
  }, []);

  useEffect(() => {
    const onHashChange = () => {
      setActive(hashToSectionId(window.location.hash));
    };
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  useEffect(() => {
    let mounted = true;
    api
      .getHealth()
      .then((data) => {
        if (mounted) {
          setApiStatus(data.status === "healthy" ? "Connected" : "Degraded");
        }
      })
      .catch(() => {
        if (mounted) {
          setApiStatus("Disconnected");
        }
      });
    return () => {
      mounted = false;
    };
  }, []);

  const renderActiveView = () => {
    switch (active) {
      case "ECMT AI":
      case "Q":
      case "Dashboard":
      case "Overview":
        return (
          <DashboardView
            key={activeSessionId || `home-${resetTrigger}`}
            onNavigate={(dest) => navigateTo(dest)}
            resetTrigger={resetTrigger}
            activeSessionId={activeSessionId}
            onSelectSession={(sid) => setActiveSessionId(sid)}
          />
        );
      case "Projects":
        return <ProjectsView onNavigate={(dest) => navigateTo(dest)} />;
      case "Literature Intelligence":
      case "Literature AI":
      case "Literature":
        return <LiteratureIntelligenceView />;
      case "Research Copilot":
      case "Copilot":
      case "Research Discovery":
      case "Discovery":
        return <CopilotChatView onNavigate={(dest) => navigateTo(dest)} />;
      case "Materials Designer":
      case "Material Design":
      case "Chemistry Validation":
        return <MaterialsDesignerView onNavigate={(dest) => navigateTo(dest)} />;
      case "Property Prediction":
      case "ML Predictions":
        return <PropertyPredictionView onNavigate={(dest) => navigateTo(dest)} />;
      case "Experiment Management":
      case "Experiment Lab":
      case "Experiments":
        return <ExperimentManagementView onNavigate={(dest) => navigateTo(dest)} />;
      default:
        return <DashboardView onNavigate={(dest) => navigateTo(dest)} resetTrigger={resetTrigger} />;
    }
  };

  const isECMTActive = active === "ECMT AI" || active === "Q" || active === "Dashboard" || active === "Overview";

  // If not authenticated, display the initial auth gateway landing page
  if (!authUser) {
    return (
      <AuthView
        onAuthSuccess={(user) => {
          setAuthUser(user);
          localStorage.setItem("ecmt_ai_user", JSON.stringify(user));
        }}
      />
    );
  }

  return (
    <div className="app-shell">
      {/* Sidebar - ECMT AI Clean Navigation */}
      <aside className="sidebar">
        {/* Brand Header */}
        <div className="brand">
          <div
            className="brand-title"
            onClick={() => navigateTo("ECMT AI")}
            style={{ cursor: "pointer" }}
          >
            <span>ECMT</span>
            <span className="brand-badge-ai">AI</span>
          </div>
          <button
            type="button"
            className="brand-toggle-btn"
            title="Toggle sidebar"
            onClick={() => {}}
          >
            ◫
          </button>
        </div>

        <nav>
          {/* Section: Workspace */}
          <div className="nav-label">Workspace</div>

          {/* Projects */}
          <button
            type="button"
            className={`nav-item ${active === "Projects" ? "active" : ""}`}
            onClick={() => navigateTo("Projects")}
          >
            <span className="nav-icon">📁</span>
            <span>Projects</span>
          </button>

          {/* ECMT AI (Main AI Research Workspace) */}
          <button
            type="button"
            className={`nav-item ${isECMTActive ? "active" : ""}`}
            onClick={() => navigateTo("ECMT AI")}
          >
            <span className="nav-icon" style={{ fontWeight: 700 }}>⚛</span>
            <span>ECMT AI</span>
          </button>

          {/* Modules (Collapsible) */}
          <button
            type="button"
            className={`nav-item ${modulesOpen ? "active" : ""}`}
            onClick={() => setModulesOpen(!modulesOpen)}
          >
            <span className="nav-icon">▦</span>
            <span style={{ flex: 1, textAlign: "left" }}>Modules</span>
            <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>
              {modulesOpen ? "▲" : "▼"}
            </span>
          </button>

          {/* Expanded Modules List */}
          {modulesOpen && (
            <div style={{ paddingLeft: "24px", marginTop: "2px", marginBottom: "6px" }}>
              <button
                type="button"
                className={`nav-item ${active === "Materials Designer" ? "active" : ""}`}
                style={{ fontSize: "12.5px", padding: "6px 10px" }}
                onClick={() => navigateTo("Materials Designer")}
              >
                <span>⚗</span>
                <span>Materials Designer</span>
              </button>
              <button
                type="button"
                className={`nav-item ${active === "Property Prediction" ? "active" : ""}`}
                style={{ fontSize: "12.5px", padding: "6px 10px" }}
                onClick={() => navigateTo("Property Prediction")}
              >
                <span>⌁</span>
                <span>Property Prediction</span>
              </button>
              <button
                type="button"
                className={`nav-item ${active === "Literature Intelligence" ? "active" : ""}`}
                style={{ fontSize: "12.5px", padding: "6px 10px" }}
                onClick={() => navigateTo("Literature Intelligence")}
              >
                <span>▤</span>
                <span>Literature</span>
              </button>
              <button
                type="button"
                className={`nav-item ${active === "Experiment Management" ? "active" : ""}`}
                style={{ fontSize: "12.5px", padding: "6px 10px" }}
                onClick={() => navigateTo("Experiment Management")}
              >
                <span>⌘</span>
                <span>Experiments</span>
              </button>
            </div>
          )}

          {/* Solid Pill Button: + New research */}
          <button
            type="button"
            className="btn-new-research"
            onClick={handleNewResearch}
          >
            <span>+</span>
            <span>New research</span>
          </button>

          {/* Dynamic Research history */}
          <div style={{ marginTop: "14px" }}>
            <div
              className="sidebar-history-header"
              onClick={() => setHistoryOpen(!historyOpen)}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>🕒</span>
                <span>Research history</span>
                {chatSessions.length > 0 && (
                  <span
                    style={{
                      fontSize: "10px",
                      background: "#eff6ff",
                      color: "#1d4ed8",
                      padding: "1px 6px",
                      borderRadius: "9999px",
                      fontWeight: 700,
                      border: "1px solid #bfdbfe",
                    }}
                  >
                    {chatSessions.length}
                  </span>
                )}
              </div>
              <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                {historyOpen ? "⌄" : "›"}
              </span>
            </div>

            {historyOpen && (
              <div style={{ paddingLeft: "6px", marginTop: "6px" }}>
                {chatSessions.length === 0 ? (
                  <div
                    style={{
                      fontSize: "11.5px",
                      color: "var(--text-muted)",
                      padding: "6px 8px",
                      fontStyle: "italic",
                      lineHeight: "1.4",
                    }}
                  >
                    No search inquiries yet. Questions asked on ECMT AI will appear here.
                  </div>
                ) : (
                  <>
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        padding: "3px 8px 6px",
                      }}
                    >
                      <span
                        style={{
                          fontSize: "10px",
                          fontWeight: 700,
                          color: "var(--text-muted)",
                          textTransform: "uppercase",
                          letterSpacing: "0.5px",
                        }}
                      >
                        Recent Queries
                      </span>
                      <span
                        style={{
                          fontSize: "10.5px",
                          color: "var(--danger)",
                          cursor: "pointer",
                          fontWeight: 600,
                        }}
                        onClick={(e) => {
                          e.stopPropagation();
                          clearAllChatSessions();
                          setChatSessions([]);
                          setActiveSessionId(null);
                          setResetTrigger((prev) => prev + 1);
                        }}
                        title="Clear research history"
                      >
                        Clear
                      </span>
                    </div>

                    <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                      {chatSessions.slice(0, 15).map((session) => {
                        const isCurrentActive = isECMTActive && activeSessionId === session.id;
                        return (
                          <div
                            key={session.id}
                            style={{
                              fontSize: "12px",
                              color: isCurrentActive ? "#1d4ed8" : "var(--text-main)",
                              padding: "6px 8px",
                              cursor: "pointer",
                              borderRadius: "6px",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "space-between",
                              gap: "6px",
                              transition: "all 0.15s ease",
                            }}
                            className={`sidebar-history-item ${isCurrentActive ? "active-history-item" : ""}`}
                            onClick={() => {
                              setActiveSessionId(session.id);
                              navigateTo("ECMT AI");
                            }}
                            title={session.title}
                          >
                            <div style={{ display: "flex", alignItems: "center", gap: "6px", minWidth: 0, flex: 1 }}>
                              <span style={{ color: isCurrentActive ? "#2563eb" : "var(--text-muted)", fontSize: "10px" }}>
                                •
                              </span>
                              <span
                                style={{
                                  overflow: "hidden",
                                  textOverflow: "ellipsis",
                                  whiteSpace: "nowrap",
                                  fontWeight: isCurrentActive ? 600 : 500,
                                }}
                              >
                                {session.title}
                              </span>
                            </div>
                            <div style={{ display: "flex", alignItems: "center", gap: "4px", flexShrink: 0 }}>
                              <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                                {session.dateStr}
                              </span>
                              <button
                                type="button"
                                className="history-delete-btn"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  e.preventDefault();
                                  const updated = deleteChatSession(session.id);
                                  setChatSessions(updated);
                                  if (activeSessionId === session.id) {
                                    setActiveSessionId(null);
                                    setResetTrigger((prev) => prev + 1);
                                  }
                                }}
                                title="Delete this chat from history"
                              >
                                ✕
                              </button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        </nav>

        {/* Sidebar Bottom: User Profile, Theme Switch, Version */}
        <div className="sidebar-bottom">
          {/* User Profile with Clickable Sign Out Dropdown */}
          <div style={{ position: "relative" }}>
            <div
              className="profile-card"
              onClick={() => setProfileMenuOpen(!profileMenuOpen)}
              title="Click to manage profile or sign out"
            >
              <div className="avatar-circle">{authUser.avatarLetter}</div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="profile-name">{authUser.fullName}</div>
                <div className="profile-sub" style={{ textOverflow: "ellipsis", overflow: "hidden", whiteSpace: "nowrap" }}>
                  {authUser.account} <span style={{ fontSize: "9px" }}>⌄</span>
                </div>
              </div>
            </div>

            {profileMenuOpen && (
              <div className="profile-dropdown-menu">
                <div
                  className="profile-dropdown-item"
                  onClick={handleSignOut}
                  title="Sign out and return to initial auth page"
                >
                  <span style={{ fontSize: "14px" }}>⎋</span>
                  <span>Sign Out</span>
                </div>
              </div>
            )}
          </div>

          {/* Theme Toggle matching screenshot: ☼ Light */}
          <div className="theme-row">
            <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span>☼</span>
              <span>Light</span>
            </span>
            <div
              className={`theme-switch ${theme === "light" ? "active" : ""}`}
              onClick={toggleTheme}
              title={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
            >
              <div className="theme-switch-thumb" />
            </div>
          </div>

          {/* Version & Demo Badge matching screenshot */}
          <div className="version-row">
            <span>v1.0.0</span>
            <span className="demo-pill" title={`API Status: ${apiStatus}`}>
              DEMO
            </span>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="main-content">
        {/* Only show topbar when inside a deep module, keeping ECMT AI completely clean */}
        {!isECMTActive && (
          <header className="topbar">
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span
                style={{ fontSize: "12px", color: "var(--text-muted)", cursor: "pointer" }}
                onClick={() => navigateTo("ECMT AI")}
              >
                ECMT AI
              </span>
              <span style={{ color: "var(--border)" }}>/</span>
              <span style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-main)" }}>
                {active}
              </span>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => navigateTo("ECMT AI")}
                style={{ fontSize: "12px", borderRadius: "9999px" }}
              >
                Ask ECMT AI
              </button>
              <button
                className="btn btn-primary btn-sm"
                onClick={() => navigateTo("Materials Designer")}
                style={{ fontSize: "12px", borderRadius: "9999px" }}
              >
                + New Candidate
              </button>
            </div>
          </header>
        )}

        {renderActiveView()}
      </main>
    </div>
  );
}

export default App;
