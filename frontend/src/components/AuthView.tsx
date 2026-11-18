import React, { useState, useEffect } from "react";
import { api } from "../api";

declare global {
  interface Window {
    google?: any;
  }
}

export interface AuthUser {
  fullName: string;
  account: string;
  avatarLetter: string;
  provider: "email" | "google" | "guest";
  sub?: string;
}

interface AuthViewProps {
  onAuthSuccess: (user: AuthUser) => void;
}

export const AuthView: React.FC<AuthViewProps> = ({ onAuthSuccess }) => {
  // Mode: "signin" (full name, acc, password) vs "login" (acc or username, password)
  const [mode, setMode] = useState<"signin" | "login">("signin");

  // Sign In (Registration) Form State
  const [fullName, setFullName] = useState("");
  const [acc, setAcc] = useState("");
  const [password, setPassword] = useState("");

  // Log In Form State
  const [loginAccOrUser, setLoginAccOrUser] = useState("");
  const [loginPassword, setLoginPassword] = useState("");

  // UI state
  const [showPassword, setShowPassword] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Check URL hash for OAuth redirect token
  useEffect(() => {
    if (typeof window === "undefined") return;
    const hash = window.location.hash;
    if (hash && hash.includes("id_token=")) {
      const params = new URLSearchParams(hash.replace(/^#/, ""));
      const idToken = params.get("id_token");
      if (idToken) {
        setLoading(true);
        history.replaceState(null, "", window.location.pathname);
        api
          .verifyGoogleToken(idToken)
          .then((res) => {
            if (res.session_token) {
              localStorage.setItem("ecmt_session_token", res.session_token);
            }
            onAuthSuccess({
              fullName: res.user.fullName,
              account: res.user.email,
              avatarLetter: res.user.avatarLetter,
              provider: "google",
              sub: res.user.sub,
            });
          })
          .catch((err) => {
            setErrorMsg(err.message || "Failed to verify Google ID token.");
          })
          .finally(() => setLoading(false));
      }
    }
  }, []);

  // Initialize Google Identity Services if SDK loaded
  useEffect(() => {
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
    if (!clientId || typeof window === "undefined" || !window.google?.accounts?.id) return;

    try {
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: async (response: any) => {
          if (response.credential) {
            setLoading(true);
            setErrorMsg(null);
            try {
              const authRes = await api.verifyGoogleToken(response.credential);
              if (authRes.session_token) {
                localStorage.setItem("ecmt_session_token", authRes.session_token);
              }
              onAuthSuccess({
                fullName: authRes.user.fullName,
                account: authRes.user.email,
                avatarLetter: authRes.user.avatarLetter,
                provider: "google",
                sub: authRes.user.sub,
              });
            } catch (err: any) {
              setErrorMsg(err.message || "Google authentication verification failed.");
            } finally {
              setLoading(false);
            }
          }
        },
        auto_select: false,
      });
    } catch (err) {
      console.warn("GIS initialization notice:", err);
    }
  }, []);

  const handleSignInSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    const trimmedName = fullName.trim();
    const trimmedAcc = acc.trim();

    if (!trimmedName) {
      setErrorMsg("Please enter your full name.");
      return;
    }
    if (!trimmedAcc) {
      setErrorMsg("Please enter your account (email or research ID).");
      return;
    }
    if (!password || password.length < 4) {
      setErrorMsg("Password must be at least 4 characters.");
      return;
    }

    setLoading(true);
    try {
      const res = await api.loginCredentials({
        account: trimmedAcc,
        password: password,
        full_name: trimmedName,
        mode: "signin",
      });
      if (res.session_token) {
        localStorage.setItem("ecmt_session_token", res.session_token);
      }
      onAuthSuccess({
        fullName: res.user.fullName,
        account: res.user.account,
        avatarLetter: res.user.avatarLetter,
        provider: "email",
        sub: res.user.sub,
      });
    } catch (err: any) {
      setErrorMsg(err.message || "Sign in failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    const trimmedUser = loginAccOrUser.trim();
    if (!trimmedUser) {
      setErrorMsg("Please enter your account or username.");
      return;
    }
    if (!loginPassword) {
      setErrorMsg("Please enter your password.");
      return;
    }

    setLoading(true);
    try {
      const res = await api.loginCredentials({
        account: trimmedUser,
        password: loginPassword,
        mode: "login",
      });
      if (res.session_token) {
        localStorage.setItem("ecmt_session_token", res.session_token);
      }
      onAuthSuccess({
        fullName: res.user.fullName,
        account: res.user.account,
        avatarLetter: res.user.avatarLetter,
        provider: "email",
        sub: res.user.sub,
      });
    } catch (err: any) {
      setErrorMsg(err.message || "Login failed.");
    } finally {
      setLoading(false);
    }
  };

  const initiateOAuthFlow = (clientId: string) => {
    const redirectUri = window.location.origin;
    const oauthUrl = new URL("https://accounts.google.com/o/oauth2/v2/auth");
    oauthUrl.searchParams.set("client_id", clientId);
    oauthUrl.searchParams.set("redirect_uri", redirectUri);
    oauthUrl.searchParams.set("response_type", "id_token");
    oauthUrl.searchParams.set("scope", "openid email profile");
    oauthUrl.searchParams.set("prompt", "select_account"); // Guarantees account selection screen
    oauthUrl.searchParams.set("nonce", Math.random().toString(36).substring(2));

    window.location.href = oauthUrl.toString();
  };

  const handleGoogleAuth = () => {
    setErrorMsg(null);
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;

    if (!clientId) {
      setErrorMsg(
        "Google OAuth Client ID is not configured (VITE_GOOGLE_CLIENT_ID is unset). Please configure your Google Cloud Web Client ID in the environment, or log in with your research credentials."
      );
      return;
    }

    if (window.google?.accounts?.id) {
      setLoading(true);
      try {
        window.google.accounts.id.prompt((notification: any) => {
          setLoading(false);
          if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
            initiateOAuthFlow(clientId);
          }
        });
      } catch {
        setLoading(false);
        initiateOAuthFlow(clientId);
      }
    } else {
      initiateOAuthFlow(clientId);
    }
  };

  const handleGuestEntry = () => {
    onAuthSuccess({
      fullName: "Research Scientist",
      account: "guest@ecmt.ai",
      avatarLetter: "E",
      provider: "guest",
    });
  };

  return (
    <div className="auth-container">
      {/* ====================================================================
          LEFT SIDE PANEL: ECMT Website Logo & ECMT AI Branding
          ==================================================================== */}
      <div className="auth-left-panel">
        {/* Ambient Decorative Light Glows */}
        <div className="auth-glow-top" />
        <div className="auth-glow-bottom" />

        <div className="auth-left-content">
          {/* ECMT Website Logo (High-Tech Crystal Olivine Hex Lattice) */}
          <div className="auth-logo-badge">
            <svg
              className="auth-logo-svg"
              viewBox="0 0 64 64"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <defs>
                <linearGradient id="ecmtGrad1" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse">
                  <stop offset="0%" stopColor="#2563eb" />
                  <stop offset="50%" stopColor="#7c3aed" />
                  <stop offset="100%" stopColor="#06b6d4" />
                </linearGradient>
                <linearGradient id="ecmtGrad2" x1="64" y1="0" x2="0" y2="64" gradientUnits="userSpaceOnUse">
                  <stop offset="0%" stopColor="#38bdf8" />
                  <stop offset="100%" stopColor="#6366f1" />
                </linearGradient>
                <filter id="ecmtGlow" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="3" result="blur" />
                  <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>
              </defs>
              {/* Hexagonal Outer Olivine Lattice Ring */}
              <polygon
                points="32,4 58,18 58,46 32,60 6,46 6,18"
                stroke="url(#ecmtGrad1)"
                strokeWidth="3.5"
                strokeLinejoin="round"
                fill="none"
                filter="url(#ecmtGlow)"
              />
              {/* Inner Atomic Interconnections */}
              <line x1="32" y1="4" x2="32" y2="32" stroke="url(#ecmtGrad2)" strokeWidth="2.5" strokeLinecap="round" />
              <line x1="58" y1="46" x2="32" y2="32" stroke="url(#ecmtGrad2)" strokeWidth="2.5" strokeLinecap="round" />
              <line x1="6" y1="46" x2="32" y2="32" stroke="url(#ecmtGrad2)" strokeWidth="2.5" strokeLinecap="round" />
              <circle cx="32" cy="32" r="7" fill="url(#ecmtGrad1)" />
              <circle cx="32" cy="4" r="3.5" fill="#38bdf8" />
              <circle cx="58" cy="18" r="3.5" fill="#818cf8" />
              <circle cx="58" cy="46" r="3.5" fill="#c084fc" />
              <circle cx="32" cy="60" r="3.5" fill="#38bdf8" />
              <circle cx="6" cy="46" r="3.5" fill="#818cf8" />
              <circle cx="6" cy="18" r="3.5" fill="#c084fc" />
            </svg>
            <div className="auth-logo-text-group">
              <span className="auth-brand-name">ECMT</span>
              <span className="brand-badge-ai" style={{ fontSize: "12px", padding: "3px 9px" }}>
                AI
              </span>
            </div>
          </div>

          {/* Headline & Tagline */}
          <h1 className="auth-hero-title">
            First-Principles LMFP Materials Intelligence
          </h1>
          <p className="auth-hero-subtitle">
            AI-assisted high-entropy cathode design, literature extraction, and electrochemical performance predictions.
          </p>

          {/* Left Panel Footer */}
          <div className="auth-left-footer">
            <span>© 2026 ECMT AI Technologies</span>
            <span>•</span>
            <span>Confidential Research Platform</span>
          </div>
        </div>
      </div>

      {/* ====================================================================
          RIGHT SIDE PANEL: Sign In / Log In & Google Authentication Panel
          ==================================================================== */}
      <div className="auth-right-panel">
        <div className="auth-card">
          {/* Header & Segmented Mode Switch */}
          <div className="auth-header">
            <h2 className="auth-card-title">
              {mode === "signin" ? "Sign in to ECMT AI" : "Log in to ECMT AI"}
            </h2>
            <p className="auth-card-desc">
              {mode === "signin"
                ? "Enter your credentials to initialize your materials research workspace."
                : "Welcome back! Enter your account details to access your cathode projects."}
            </p>
          </div>

          {/* Mode Switcher Tabs */}
          <div className="auth-mode-tabs">
            <button
              type="button"
              className={`auth-mode-tab ${mode === "signin" ? "active" : ""}`}
              onClick={() => {
                setMode("signin");
                setErrorMsg(null);
              }}
            >
              Sign In (New User)
            </button>
            <button
              type="button"
              className={`auth-mode-tab ${mode === "login" ? "active" : ""}`}
              onClick={() => {
                setMode("login");
                setErrorMsg(null);
              }}
            >
              Log In
            </button>
          </div>

          {/* Error Message Alert */}
          {errorMsg && (
            <div className="auth-error-alert">
              <span>⚠</span>
              <span>{errorMsg}</span>
            </div>
          )}

          {/* ================================================================
              FORM 1: SIGN IN (full name, acc, password)
              ================================================================ */}
          {mode === "signin" && (
            <form onSubmit={handleSignInSubmit} className="auth-form">
              <div className="auth-input-group">
                <label className="auth-label">
                  Full Name <span style={{ color: "var(--danger)" }}>*</span>
                </label>
                <input
                  type="text"
                  className="auth-input"
                  placeholder="e.g. Dr. Priyadarshini V"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  autoFocus
                  required
                />
              </div>

              <div className="auth-input-group">
                <label className="auth-label">
                  Account (Email or Research ID) <span style={{ color: "var(--danger)" }}>*</span>
                </label>
                <input
                  type="text"
                  className="auth-input"
                  placeholder="e.g. priyadarshini.v@ecmt.org"
                  value={acc}
                  onChange={(e) => setAcc(e.target.value)}
                  required
                />
              </div>

              <div className="auth-input-group">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <label className="auth-label">
                    Password <span style={{ color: "var(--danger)" }}>*</span>
                  </label>
                  <button
                    type="button"
                    className="auth-toggle-pwd"
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? "Hide" : "Show"}
                  </button>
                </div>
                <input
                  type={showPassword ? "text" : "password"}
                  className="auth-input"
                  placeholder="••••••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>

              <button
                type="submit"
                className="btn-auth-primary"
                disabled={loading}
              >
                {loading ? "Authenticating..." : "Sign In to ECMT AI ➔"}
              </button>
            </form>
          )}

          {/* ================================================================
              FORM 2: LOG IN (acc or username, password)
              ================================================================ */}
          {mode === "login" && (
            <form onSubmit={handleLoginSubmit} className="auth-form">
              <div className="auth-input-group">
                <label className="auth-label">
                  Account or Username <span style={{ color: "var(--danger)" }}>*</span>
                </label>
                <input
                  type="text"
                  className="auth-input"
                  placeholder="e.g. priyadarshini or priya@ecmt.org"
                  value={loginAccOrUser}
                  onChange={(e) => setLoginAccOrUser(e.target.value)}
                  autoFocus
                  required
                />
              </div>

              <div className="auth-input-group">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <label className="auth-label">
                    Password <span style={{ color: "var(--danger)" }}>*</span>
                  </label>
                  <button
                    type="button"
                    className="auth-toggle-pwd"
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? "Hide" : "Show"}
                  </button>
                </div>
                <input
                  type={showPassword ? "text" : "password"}
                  className="auth-input"
                  placeholder="••••••••••••"
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  required
                />
              </div>

              <button
                type="submit"
                className="btn-auth-primary"
                disabled={loading}
              >
                {loading ? "Logging in..." : "Log In to ECMT AI ➔"}
              </button>
            </form>
          )}

          {/* Divider: Or continue with */}
          <div className="auth-divider">
            <span className="auth-divider-line" />
            <span className="auth-divider-text">or continue with</span>
            <span className="auth-divider-line" />
          </div>

          {/* Continue with Google Button */}
          <button
            type="button"
            className="btn-auth-google"
            onClick={handleGoogleAuth}
            disabled={loading}
          >
            {/* Official Google 4-Color Icon */}
            <svg width="18" height="18" viewBox="0 0 24 24" style={{ flexShrink: 0 }}>
              <path
                fill="#4285F4"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="#34A853"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="#FBBC05"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
              />
              <path
                fill="#EA4335"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
              />
            </svg>
            <span>Continue with Google</span>
          </button>

          {/* Quick guest exploration link */}
          <div style={{ textAlign: "center", marginTop: "18px" }}>
            <span
              onClick={handleGuestEntry}
              style={{
                fontSize: "12.5px",
                color: "var(--text-muted)",
                cursor: "pointer",
                textDecoration: "underline",
              }}
            >
              Explore workspace as Guest Scientist ➔
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
