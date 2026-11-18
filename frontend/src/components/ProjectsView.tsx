import React, { useEffect, useState } from "react";
import { api, type CandidateComposition } from "../api";

interface ProjectsViewProps {
  onNavigate: (section: string) => void;
}

export const ProjectsView: React.FC<ProjectsViewProps> = ({ onNavigate }) => {
  const [candidates, setCandidates] = useState<CandidateComposition[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    api
      .generateCandidates()
      .then((res) => {
        if (mounted) {
          setCandidates(res.candidates || []);
          setLoading(false);
        }
      })
      .catch(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div className="view-container" style={{ maxWidth: "880px", margin: "0 auto", padding: "32px 24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
        <div>
          <h1 style={{ fontSize: "22px", fontWeight: 700, color: "var(--text-main)", margin: 0 }}>
            Projects &amp; Material Candidates
          </h1>
          <p style={{ fontSize: "13px", color: "var(--text-muted)", margin: "4px 0 0" }}>
            First-principles verified olivine cathode compositions
          </p>
        </div>
        <button
          className="btn btn-primary btn-sm"
          onClick={() => onNavigate("Materials Designer")}
          style={{ borderRadius: "9999px", padding: "8px 16px" }}
        >
          + Design New Material
        </button>
      </div>

      {loading ? (
        <div style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)" }}>
          <div className="spinner" style={{ margin: "0 auto 12px" }} />
          Loading candidates...
        </div>
      ) : candidates.length === 0 ? (
        <div className="card" style={{ padding: "40px", textAlign: "center" }}>
          <div style={{ fontSize: "28px", marginBottom: "8px" }}>⚗</div>
          <h3 style={{ fontSize: "15px", color: "var(--text-main)", marginBottom: "4px" }}>No projects yet</h3>
          <p style={{ fontSize: "13px", color: "var(--text-muted)", marginBottom: "16px" }}>
            Design your first high-entropy LMFP cathode composition to get started.
          </p>
          <button className="btn btn-primary btn-sm" onClick={() => onNavigate("Materials Designer")}>
            Open Materials Designer
          </button>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          {candidates.map((c, idx) => (
            <div
              key={idx}
              className="card"
              style={{
                padding: "18px 20px",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                flexWrap: "wrap",
                gap: "14px",
                borderRadius: "12px",
              }}
            >
              <div>
                <strong style={{ fontSize: "15px", color: "var(--text-main)", display: "block", marginBottom: "3px" }}>
                  {c.name}
                </strong>
                <code
                  style={{
                    fontSize: "12px",
                    color: "var(--accent-blue, #0284c7)",
                    fontFamily: "JetBrains Mono, monospace",
                  }}
                >
                  {c.formula_string}
                </code>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
                <div style={{ textAlign: "right" }}>
                  <div style={{ fontSize: "10px", color: "var(--text-muted)", textTransform: "uppercase" }}>
                    Capacity
                  </div>
                  <span style={{ fontSize: "14px", fontWeight: 700, color: "#10b981" }}>
                    {c.calculated_capacity.toFixed(1)} mAh/g
                  </span>
                </div>

                <div style={{ display: "flex", gap: "8px" }}>
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={() => onNavigate("Property Prediction")}
                    style={{ fontSize: "12px" }}
                  >
                    Simulate
                  </button>
                  <button
                    className="btn btn-primary btn-sm"
                    onClick={() => onNavigate("Materials Designer")}
                    style={{ fontSize: "12px" }}
                  >
                    Inspect
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
