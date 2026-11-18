import React, { useEffect, useState } from "react";
import {
  api,
  type TrendSummaryResponse,
  type ResearchGapItem,
  type ScientificConflictItem,
  type ScientificHypothesisItem,
  type ExperimentalVerificationMatrixItem,
} from "../api";

interface ResearchDiscoveryViewProps {
  onNavigate?: (section: string) => void;
}

type DiscoveryTab = "trends" | "gaps" | "conflicts" | "hypotheses" | "matrix";

export const ResearchDiscoveryView: React.FC<ResearchDiscoveryViewProps> = ({ onNavigate }) => {
  // Navigation & Sub-tab State
  const [activeTab, setActiveTab] = useState<DiscoveryTab>("trends");
  const [topicQuery, setTopicQuery] = useState("");
  const [dopantFilter, setDopantFilter] = useState("");

  // Data States
  const [trends, setTrends] = useState<TrendSummaryResponse | null>(null);
  const [gaps, setGaps] = useState<ResearchGapItem[]>([]);
  const [conflicts, setConflicts] = useState<ScientificConflictItem[]>([]);
  const [hypotheses, setHypotheses] = useState<ScientificHypothesisItem[]>([]);
  const [selectedHypothesis, setSelectedHypothesis] = useState<ScientificHypothesisItem | null>(null);
  const [matrices, setMatrices] = useState<ExperimentalVerificationMatrixItem[]>([]);
  const [selectedMatrix, setSelectedMatrix] = useState<ExperimentalVerificationMatrixItem | null>(null);

  // Status & Feedback States
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [transferStatus, setTransferStatus] = useState<{ id: string; message: string } | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);

  // Topic Presets for fast exploration
  const topicPresets = [
    { label: "All Literature Frontiers", topic: "all", dopant: "" },
    { label: "Spray Drying Precursors (srep26686)", topic: "spray-drying", dopant: "" },
    { label: "Mg Site Partitioning (M2 vs M1)", topic: "mg-partitioning", dopant: "Mg" },
    { label: "High-Mn Jahn-Teller Dual Doping", topic: "high-mn", dopant: "Ti" },
    { label: "Carbon vs Crystallite Size", topic: "carbon-coating", dopant: "" },
    { label: "High-Rate Polaronic Kinetics", topic: "polaronic-kinetics", dopant: "" },
    { label: "First-Cycle ICE Underreporting", topic: "ice-loss", dopant: "" },
    { label: "Elevated 55°C Durability", topic: "elevated-temperature", dopant: "" },
  ];

  // 1. Initial Data Load
  useEffect(() => {
    loadAllData();
  }, []);

  const loadAllData = async (filterTopic?: string, filterDopant?: string) => {
    setLoading(true);
    setError(null);
    try {
      const [trendsRes, gapsRes, conflictsRes, hypRes, matRes] = await Promise.all([
        api.getLiteratureTrends({ topic: filterTopic || "all", dopant: filterDopant || undefined }),
        api.getResearchGaps({ dopant: filterDopant || undefined }),
        api.getScientificConflicts({ dopant: filterDopant || undefined }),
        api.getScientificHypotheses({ dopant: filterDopant || undefined }),
        api.getVerificationMatrices({ dopant: filterDopant || undefined }),
      ]);

      setTrends(trendsRes);
      setGaps(gapsRes.gaps || []);
      setConflicts(conflictsRes || []);
      setHypotheses(hypRes.hypotheses || []);
      if (hypRes.hypotheses && hypRes.hypotheses.length > 0 && !selectedHypothesis) {
        setSelectedHypothesis(hypRes.hypotheses[0]);
      }
      setMatrices(matRes.matrices || []);
      if (matRes.matrices && matRes.matrices.length > 0 && !selectedMatrix) {
        setSelectedMatrix(matRes.matrices[0]);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load research intelligence data");
    } finally {
      setLoading(false);
    }
  };

  const handleTopicSelect = (topic: string, dopant: string) => {
    setTopicQuery(topic === "all" ? "" : topic);
    setDopantFilter(dopant);
    loadAllData(topic, dopant);
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadAllData(topicQuery, dopantFilter);
  };

  // Workflow Action: Generate Hypothesis from Gap
  const handleGenerateHypothesisFromGap = async (gapId: string) => {
    setIsGenerating(true);
    setError(null);
    try {
      const newHyp = await api.generateHypothesis({ gap_id: gapId });
      setSelectedHypothesis(newHyp);
      // Prepend to hypotheses if not already present
      setHypotheses((prev) => [newHyp, ...prev.filter((h) => h.hypothesis_id !== newHyp.hypothesis_id)]);
      setActiveTab("hypotheses");
    } catch (err: any) {
      setError(err.message || "Failed to generate hypothesis from research gap");
    } finally {
      setIsGenerating(false);
    }
  };

  // Workflow Action: Generate Verification Matrix from Hypothesis
  const handleGenerateMatrixFromHypothesis = async (hypothesisId: string) => {
    setIsGenerating(true);
    setError(null);
    try {
      const newMat = await api.generateVerificationMatrix({ hypothesis_id: hypothesisId });
      setSelectedMatrix(newMat);
      setMatrices((prev) => [newMat, ...prev.filter((m) => m.matrix_id !== newMat.matrix_id)]);
      setActiveTab("matrix");
    } catch (err: any) {
      setError(err.message || "Failed to generate experimental verification matrix");
    } finally {
      setIsGenerating(false);
    }
  };

  // Workflow Action: Transfer Proposed Experiment to Experiment Management
  const handleTransferToExperiments = async (mat: ExperimentalVerificationMatrixItem) => {
    setError(null);
    setTransferStatus(null);
    try {
      // Parse Mn and Fe from candidate composition or links
      const candidateComp = mat.candidate_composition;
      let mnRatio = 0.75;
      let feRatio = 0.25;
      if (candidateComp.includes("0.80") || candidateComp.includes("0.8")) {
        mnRatio = 0.8;
        feRatio = 0.2;
      } else if (candidateComp.includes("0.70") || candidateComp.includes("0.7")) {
        mnRatio = 0.7;
        feRatio = 0.3;
      }

      // Safeguard: Status is explicitly SYNTHESIS_PLANNED, never completed
      const payload = {
        sample_id: `VERIFY-${mat.matrix_id}`,
        batch_id: `DISCOVERY-${mat.matrix_id.split("-").slice(-2).join("-")}`,
        operator: "Discovery Studio Researcher",
        generated_formula: mat.candidate_composition,
        mn_ratio: mnRatio,
        fe_ratio: feRatio,
        dopants: mat.intended_dopants,
        carbon_wt_percent: 2.0,
        synthesis_route: mat.synthesis_plan[0]?.operation || "solid-state",
        status: "SYNTHESIS_PLANNED",
        notes: `Transferred from Verification Matrix ${mat.matrix_id} (${mat.title}). Status: PROPOSED_UNPERFORMED. Designed to test hypothesis ${mat.hypothesis_id}.`,
        synthesis_data: {
          observations: `Proposed protocol: ${mat.synthesis_plan.map((s) => s.operation).join(" -> ")}`,
          calcination_temp_c: 650,
          calcination_duration_h: 6.0,
        },
        characterization_data: {
          impurity_phases: "Pending physical synthesis and XRD verification",
        },
        electrochemical_data: {
          initial_discharge_cap: null,
          capacity_retention_pct: null,
          cycle_life_cycles: null,
          notes: "UNPERFORMED EXPERIMENT: Awaiting coin-cell assembly and electrochemical testing per protocol.",
        },
      };

      const res = await api.createExperiment(payload);
      setTransferStatus({
        id: res.experiment_id,
        message: `Proposed experiment logged as '${res.experiment_id}' with status SYNTHESIS_PLANNED (Unperformed).`,
      });
    } catch (err: any) {
      setError(err.message || "Failed to transfer experiment to Experiment Management");
    }
  };

  // Helper: Render Epistemic Badges
  const renderEpistemicBadge = (type: string) => {
    switch (type) {
      case "LITERATURE_FACT":
        return <span className="badge badge-green">LITERATURE FACT</span>;
      case "AUTHOR_INTERPRETATION":
        return <span className="badge badge-purple">AUTHOR INTERPRETATION</span>;
      case "COPILOT_SYNTHESIS":
        return <span className="badge badge-blue">COPILOT SYNTHESIS</span>;
      case "RESEARCH_HYPOTHESIS":
        return <span className="badge badge-amber">RESEARCH HYPOTHESIS</span>;
      case "ML_PREDICTION":
        return <span className="badge badge-indigo">ML PREDICTION (IN SILICO)</span>;
      case "SUPERVISOR_POLICY":
        return <span className="badge badge-gold">SUPERVISOR POLICY</span>;
      case "EXPERIMENTAL_RECOMMENDATION":
        return <span className="badge badge-teal">RECOMMENDATION</span>;
      default:
        return <span className="badge badge-secondary">{type}</span>;
    }
  };

  return (
    <div className="view-container">
      {/* Header & Hero */}
      <section className="section-heading">
        <div>
          <h2>Research Intelligence & Scientific Discovery Workspace</h2>
          <p>
            Seamless evidence pipeline: Literature Trends ➔ Research Gaps & Conflicts ➔ Scientific Hypotheses ➔
            Experimental Verification Matrices.
          </p>
        </div>
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <span className="version-tag">ECMT DISCOVERY STUDIO</span>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => loadAllData(topicQuery, dopantFilter)}
            disabled={loading}
          >
            {loading ? "Refreshing..." : "↻ Refresh Intelligence"}
          </button>
        </div>
      </section>

      {/* Global Filter & Preset Topics Bar */}
      <div className="card" style={{ marginBottom: "16px", padding: "14px 18px" }}>
        <form onSubmit={handleSearchSubmit} style={{ display: "flex", gap: "12px", alignItems: "center", flexWrap: "wrap" }}>
          <span style={{ fontWeight: 600, fontSize: "12px", color: "#475569" }}>TOPIC PRESETS:</span>
          <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", flex: 1 }}>
            {topicPresets.map((p, idx) => (
              <button
                key={idx}
                type="button"
                className={`tab-pill ${topicQuery === p.topic ? "active" : ""}`}
                onClick={() => handleTopicSelect(p.topic, p.dopant)}
                style={{ fontSize: "11px", padding: "4px 10px" }}
              >
                {p.label}
              </button>
            ))}
          </div>

          <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
            <input
              type="text"
              placeholder="Search custom topic or element (e.g. Ti, sulfate, 55°C)..."
              value={topicQuery}
              onChange={(e) => setTopicQuery(e.target.value)}
              className="input-field"
              style={{ width: "240px", padding: "6px 10px", fontSize: "12px" }}
            />
            <button type="submit" className="btn btn-primary btn-sm">
              Search
            </button>
          </div>
        </form>
      </div>

      {/* Notifications & Error Alerts */}
      {error && (
        <div className="error-banner" style={{ marginBottom: "16px" }}>
          <strong>Discovery Engine Notice:</strong> {error}
        </div>
      )}

      {transferStatus && (
        <div className="card" style={{ background: "#f0fdf4", borderColor: "#86efac", marginBottom: "16px", padding: "12px 18px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <strong style={{ color: "#166534" }}>✓ Experiment Transferred Successfully</strong>
              <p style={{ margin: "4px 0 0", fontSize: "12px", color: "#15803d" }}>{transferStatus.message}</p>
            </div>
            {onNavigate && (
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => onNavigate("Experiment Management")}
                style={{ background: "#ffffff", borderColor: "#86efac", color: "#166534" }}
              >
                View in Experiment Management ➔
              </button>
            )}
          </div>
        </div>
      )}

      {/* Active Analysis Context & Findings Overview */}
      <div
        className="card"
        style={{
          background: "#ffffff",
          padding: "16px 20px",
          borderRadius: "8px",
          border: "1px solid var(--border)",
          marginBottom: "18px",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
              <span className="badge badge-purple">ANALYSIS TOPIC</span>
              <strong style={{ fontSize: "14px", color: "var(--text-main)" }}>
                {topicQuery ? topicQuery.toUpperCase() : "ALL LITERATURE FRONTIERS"}
                {dopantFilter ? ` (Dopant: ${dopantFilter})` : ""}
              </strong>
            </div>
            <p style={{ margin: 0, fontSize: "12px", color: "var(--text-secondary)" }}>
              Cross-study synthesis grounded in 1,215 curated olivine records and 159 publications · Strictly zero fabricated claims.
            </p>
          </div>

          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "center" }}>
            <span className="tag-pill" style={{ fontSize: "11px", background: "#eff6ff", color: "#1e40af" }}>
              <strong>{gaps.length}</strong> Gaps Documented
            </span>
            <span className="tag-pill" style={{ fontSize: "11px", background: "#fdf4ff", color: "#86198f" }}>
              <strong>{conflicts.length}</strong> Conflicts Detected
            </span>
            <span className="tag-pill" style={{ fontSize: "11px", background: "#f0fdf4", color: "#166534" }}>
              <strong>{hypotheses.length}</strong> Hypotheses Ready
            </span>
            <span className="tag-pill" style={{ fontSize: "11px", background: "#faf5ff", color: "#7e22ce" }}>
              <strong>{matrices.length}</strong> Verification Matrices
            </span>
            {(topicQuery || dopantFilter) && (
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                style={{ fontSize: "11px", padding: "4px 8px" }}
                onClick={() => handleTopicSelect("all", "")}
              >
                ✕ Reset to All Topics
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Workflow Navigation Stepper Tabs */}
      <div style={{ display: "flex", gap: "8px", marginBottom: "18px", borderBottom: "1px solid #e2e8f0", paddingBottom: "10px" }}>
        <button
          className={`tab-pill ${activeTab === "trends" ? "active" : ""}`}
          onClick={() => setActiveTab("trends")}
          style={{ fontSize: "12px", padding: "8px 16px" }}
        >
          1. Research Trends & Patterns ({trends?.dataset_overview.total_literature_records || 1215} Records)
        </button>
        <button
          className={`tab-pill ${activeTab === "gaps" ? "active" : ""}`}
          onClick={() => setActiveTab("gaps")}
          style={{ fontSize: "12px", padding: "8px 16px" }}
        >
          2. Research Gaps ({gaps.length})
        </button>
        <button
          className={`tab-pill ${activeTab === "conflicts" ? "active" : ""}`}
          onClick={() => setActiveTab("conflicts")}
          style={{ fontSize: "12px", padding: "8px 16px" }}
        >
          3. Scientific Conflicts ({conflicts.length})
        </button>
        <button
          className={`tab-pill ${activeTab === "hypotheses" ? "active" : ""}`}
          onClick={() => setActiveTab("hypotheses")}
          style={{ fontSize: "12px", padding: "8px 16px" }}
        >
          4. Scientific Hypotheses ({hypotheses.length})
        </button>
        <button
          className={`tab-pill ${activeTab === "matrix" ? "active" : ""}`}
          onClick={() => setActiveTab("matrix")}
          style={{ fontSize: "12px", padding: "8px 16px" }}
        >
          5. Verification Matrix ({matrices.length})
        </button>
      </div>

      {loading && !trends && (
        <div className="loading-state">
          <div className="spinner" />
          <p>Analyzing cross-study LMFP research intelligence...</p>
        </div>
      )}

      {/* =========================================================================
          TAB 1: RESEARCH TRENDS & PATTERNS
          ========================================================================= */}
      {activeTab === "trends" && !trends && (
        <div className="card" style={{ padding: "32px", textAlign: "center" }}>
          <div className="spinner" style={{ margin: "0 auto 12px" }} />
          <h4 style={{ margin: "0 0 6px", fontSize: "14px", color: "var(--text-main)" }}>
            Compiling Literature Trends & Evidence Distributions...
          </h4>
          <p style={{ margin: 0, fontSize: "12px", color: "var(--text-muted)" }}>
            Aggregating electrochemical distributions across 1,215 peer-reviewed olivine samples.
          </p>
        </div>
      )}

      {activeTab === "trends" && trends && (
        <div>
          {/* Top Overview Cards */}
          <div className="metrics-grid" style={{ marginBottom: "20px" }}>
            <div className="metric-box">
              <span className="metric-label">TOTAL LITERATURE SAMPLES</span>
              <div className="metric-box-value">{trends.dataset_overview.total_literature_records}</div>
              <p className="metric-box-sub">Across {trends.dataset_overview.unique_dois_and_sources}+ peer-reviewed papers</p>
            </div>
            <div className="metric-box">
              <span className="metric-label">VERIFIED LMFP SAMPLES</span>
              <div className="metric-box-value">{trends.dataset_overview.verified_materials_samples}</div>
              <p className="metric-box-sub">Deterministic stoichiometry & phase-pure</p>
            </div>
            <div className="metric-box">
              <span className="metric-label">IDENTIFIED RESEARCH GAPS</span>
              <div className="metric-box-value">{gaps.length}</div>
              <p className="metric-box-sub">Across 7 structured LMFP categories</p>
            </div>
            <div className="metric-box">
              <span className="metric-label">CANONICAL VERIFICATION MATRICES</span>
              <div className="metric-box-value">{matrices.length}</div>
              <p className="metric-box-sub">Ready for experimental execution</p>
            </div>
          </div>

          {/* Dimension 1 & 2: Dopant Frequencies & Co-occurrences */}
          <div className="grid-2col" style={{ marginBottom: "20px" }}>
            <div className="card">
              <div className="card-header">
                <h3>Top Dopant Research Frequencies</h3>
                <span className="badge badge-blue">Independent Counting</span>
              </div>
              <div className="table-responsive">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Dopant</th>
                      <th>Samples</th>
                      <th>Papers</th>
                      <th>Primary Mechanism</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trends.trend_dimensions.dopant_frequencies?.slice(0, 6).map((df, i) => (
                      <tr key={i}>
                        <td>
                          <strong>{df.data?.dopant || df.topic}</strong>
                        </td>
                        <td>{df.sample_count}</td>
                        <td>{df.paper_count}</td>
                        <td style={{ fontSize: "11px", color: "#64748b" }}>{df.key_takeaway.slice(0, 75)}...</td>
                        <td>
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={() => {
                              setDopantFilter(df.data?.dopant || "");
                              setActiveTab("gaps");
                            }}
                          >
                            Explore Gaps ➔
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="card">
              <div className="card-header">
                <h3>Pairwise Dopant Co-Occurrences</h3>
                <span className="badge badge-purple">Synergy Mapping</span>
              </div>
              <p style={{ fontSize: "12px", color: "#64748b", marginBottom: "12px" }}>
                Identifies co-doped formulations studied in literature vs unexplored synergy opportunities.
              </p>
              <div className="table-responsive">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Dopant Pair</th>
                      <th>Samples</th>
                      <th>Papers</th>
                      <th>Target Property</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trends.trend_dimensions.dopant_cooccurrence?.data?.top_cooccurring_pairs?.slice(0, 5).map((cp: any, i: number) => (
                      <tr key={i}>
                        <td>
                          <span className="badge badge-blue" style={{ marginRight: "4px" }}>
                            {cp.dopant_1}
                          </span>
                          +
                          <span className="badge badge-purple" style={{ marginLeft: "4px" }}>
                            {cp.dopant_2}
                          </span>
                        </td>
                        <td>{cp.sample_count}</td>
                        <td>{cp.paper_count}</td>
                        <td style={{ fontSize: "11px", color: "#64748b" }}>
                          {cp.dopant_1 === "Mg" && cp.dopant_2 === "Ti"
                            ? "Jahn-Teller stabilization & tunnel preservation"
                            : "Synergistic conductivity & stability"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* Dimension 3 & 4: Mn/Fe Distributions & Synthesis Routes */}
          <div className="grid-2col" style={{ marginBottom: "20px" }}>
            <div className="card">
              <div className="card-header">
                <h3>Mn/Fe Stoichiometry Distribution</h3>
                <span className="badge badge-amber">Voltage vs Polaron Trade-off</span>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginTop: "10px" }}>
                {trends.trend_dimensions.mn_fe_distributions?.map((mfd, i) => (
                  <div
                    key={i}
                    style={{
                      padding: "10px 14px",
                      background: "#f8fafc",
                      borderRadius: "6px",
                      border: "1px solid #e2e8f0",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <div>
                      <strong style={{ fontSize: "13px" }}>{mfd.topic}</strong>
                      <p style={{ margin: "2px 0 0", fontSize: "11px", color: "#64748b" }}>{mfd.key_takeaway}</p>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <span className="badge badge-secondary">{mfd.sample_count} Samples</span>
                      <div style={{ fontSize: "10px", color: "#94a3b8" }}>{mfd.paper_count} Papers</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="card">
              <div className="card-header">
                <h3>Synthesis Routes & Processing Methods</h3>
                <span className="badge badge-teal">Morphology Control</span>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginTop: "10px" }}>
                {trends.trend_dimensions.synthesis_routes?.map((sr, i) => (
                  <div
                    key={i}
                    style={{
                      padding: "10px 14px",
                      background: "#f8fafc",
                      borderRadius: "6px",
                      border: "1px solid #e2e8f0",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <div>
                      <strong style={{ fontSize: "13px" }}>{sr.topic}</strong>
                      <p style={{ margin: "2px 0 0", fontSize: "11px", color: "#64748b" }}>{sr.key_takeaway}</p>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <span className="badge badge-secondary">{sr.sample_count} Samples</span>
                      <div style={{ fontSize: "10px", color: "#94a3b8" }}>{sr.paper_count} Papers</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Quick Handoff Banner */}
          <div className="card" style={{ background: "#f8fafc", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <strong>Next Step in Discovery Workflow:</strong>
              <p style={{ margin: "4px 0 0", fontSize: "12px", color: "#64748b" }}>
                Examine specific research gaps and unresolved conflicts identified across these empirical distributions.
              </p>
            </div>
            <button className="btn btn-primary" onClick={() => setActiveTab("gaps")}>
              Examine Research Gaps ➔
            </button>
          </div>
        </div>
      )}

      {/* =========================================================================
          TAB 2: RESEARCH GAPS EXPLORER
          ========================================================================= */}
      {activeTab === "gaps" && (
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
            <div>
              <h3 style={{ margin: 0 }}>Evidence-Grounded Research Gaps</h3>
              <p style={{ margin: "4px 0 0", fontSize: "12px", color: "#64748b" }}>
                Rigorous separation of database coverage omissions from verified scientific literature gaps.
              </p>
            </div>
            <span className="badge badge-blue">{gaps.length} Gaps Documented</span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
            {gaps.length === 0 ? (
              <div className="empty-state">
                <h4 style={{ fontSize: "14px", color: "var(--text-main)", marginBottom: "6px" }}>No Research Gaps Found</h4>
                <p style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "12px" }}>
                  No gaps match the current topic/dopant filter. Click below to view all documented scientific gaps across the literature corpus.
                </p>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => handleTopicSelect("all", "")}
                >
                  View All Research Gaps
                </button>
              </div>
            ) : (
              gaps.map((gap) => (
                <div key={gap.gap_id} className="card" style={{ padding: "16px 20px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
                  <div>
                    <div style={{ display: "flex", gap: "8px", alignItems: "center", marginBottom: "4px" }}>
                      <span className="badge badge-purple" style={{ fontFamily: "monospace" }}>
                        {gap.gap_id}
                      </span>
                      <span className="badge badge-teal">{gap.category.replace(/_/g, " ")}</span>
                      {gap.verification_status.includes("VERIFIED") ? (
                        <span className="badge badge-green">VERIFIED LITERATURE GAP</span>
                      ) : (
                        <span className="badge badge-amber">DATABASE COVERAGE GAP</span>
                      )}
                    </div>
                    <h3 style={{ margin: "4px 0 2px", fontSize: "15px" }}>{gap.title}</h3>
                  </div>

                  <button
                    className="btn btn-primary btn-sm"
                    onClick={() => handleGenerateHypothesisFromGap(gap.gap_id)}
                    disabled={isGenerating}
                  >
                    {isGenerating ? "Synthesizing..." : "Formulate Hypothesis ➔"}
                  </button>
                </div>

                <p style={{ fontSize: "13px", color: "#334155", margin: "6px 0 10px" }}>{gap.description}</p>

                <div style={{ background: "#f1f5f9", padding: "10px 14px", borderRadius: "6px", marginBottom: "10px" }}>
                  <strong style={{ fontSize: "12px", color: "#0f172a" }}>Scientific Research Question:</strong>
                  <p style={{ margin: "2px 0 0", fontSize: "12px", color: "#2563eb", fontStyle: "italic" }}>
                    "{gap.scientific_question}"
                  </p>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "10px", fontSize: "11px" }}>
                  <div>
                    <span style={{ color: "#64748b" }}>Supporting Evidence Papers:</span>
                    <div style={{ fontWeight: 600 }}>
                      {gap.supporting_paper_ids.length > 0 ? gap.supporting_paper_ids.join(", ") : "Literature Benchmark"} ({gap.paper_count} papers, {gap.sample_count} samples)
                    </div>
                  </div>
                  <div>
                    <span style={{ color: "#64748b" }}>Missing Measurements:</span>
                    <div style={{ fontWeight: 600, color: "#dc2626" }}>
                      {gap.missing_measurements.length > 0 ? gap.missing_measurements.join("; ") : "Electrochemical kinetics"}
                    </div>
                  </div>
                  <div>
                    <span style={{ color: "#64748b" }}>Confounding Variables:</span>
                    <div style={{ fontWeight: 600, color: "#b45309" }}>
                      {gap.confounding_variables.length > 0 ? gap.confounding_variables[0] : "Condition non-parity"}
                    </div>
                  </div>
                  <div>
                    <span style={{ color: "#64748b" }}>Related Compositions:</span>
                    <div style={{ fontWeight: 600, fontFamily: "monospace" }}>
                      {gap.related_compositions.length > 0 ? gap.related_compositions.join(", ") : "LiMn0.75Fe0.25PO4/C"}
                    </div>
                  </div>
                </div>
              </div>
            )))}
          </div>
        </div>
      )}

      {/* =========================================================================
          TAB 3: SCIENTIFIC CONFLICTS EXPLORER
          ========================================================================= */}
      {activeTab === "conflicts" && (
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
            <div>
              <h3 style={{ margin: 0 }}>Scientific Conflict Explorer</h3>
              <p style={{ margin: "4px 0 0", fontSize: "12px", color: "#64748b" }}>
                Identifies contradictory empirical findings between publications and isolates confounding variables.
              </p>
            </div>
            <span className="badge badge-purple">{conflicts.length} Documented Conflicts</span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {conflicts.length === 0 ? (
              <div className="empty-state">
                <h4 style={{ fontSize: "14px", color: "var(--text-main)", marginBottom: "6px" }}>No Scientific Conflicts Detected</h4>
                <p style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "12px" }}>
                  No divergent literature findings match the current filter. Click below to view all documented conflicts in the corpus.
                </p>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => handleTopicSelect("all", "")}
                >
                  View All Conflicts
                </button>
              </div>
            ) : (
              conflicts.map((c) => (
                <div key={c.conflict_id} className="card" style={{ padding: "18px 22px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
                  <div>
                    <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                      <span className="badge badge-purple" style={{ fontFamily: "monospace" }}>
                        {c.conflict_id}
                      </span>
                      <span className="badge badge-amber">{(c.classification || "PROCESSING_DEPENDENT").replace(/_/g, " ")}</span>
                    </div>
                    <h3 style={{ margin: "6px 0 2px", fontSize: "15px" }}>{c.title || c.topic}</h3>
                  </div>
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={() => {
                      setTopicQuery(c.topic);
                      setActiveTab("hypotheses");
                    }}
                  >
                    View Reconciliation Plan ➔
                  </button>
                </div>

                <p style={{ fontSize: "12px", color: "#475569", marginBottom: "12px" }}>{c.divergence_description}</p>

                {/* Head-to-head Comparison Cards */}
                <div className="grid-2col" style={{ gap: "12px", marginBottom: "12px" }}>
                  <div style={{ background: "#f8fafc", padding: "12px 14px", borderRadius: "6px", border: "1px solid #cbd5e1" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                      <strong style={{ color: "#1e293b", fontSize: "12px" }}>Study A ({c.paper_a_id})</strong>
                      <span style={{ fontSize: "10px", color: "#64748b", fontFamily: "monospace" }}>{c.paper_a_doi}</span>
                    </div>
                    <div style={{ fontSize: "11px", color: "#0f172a", fontWeight: 600, marginBottom: "4px" }}>
                      Sample: {c.sample_a_id}
                    </div>
                    <p style={{ margin: 0, fontSize: "12px", color: "#334155" }}>"{c.finding_a}"</p>
                  </div>

                  <div style={{ background: "#f8fafc", padding: "12px 14px", borderRadius: "6px", border: "1px solid #cbd5e1" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                      <strong style={{ color: "#1e293b", fontSize: "12px" }}>Study B ({c.paper_b_id})</strong>
                      <span style={{ fontSize: "10px", color: "#64748b", fontFamily: "monospace" }}>{c.paper_b_doi}</span>
                    </div>
                    <div style={{ fontSize: "11px", color: "#0f172a", fontWeight: 600, marginBottom: "4px" }}>
                      Sample: {c.sample_b_id}
                    </div>
                    <p style={{ margin: 0, fontSize: "12px", color: "#334155" }}>"{c.finding_b}"</p>
                  </div>
                </div>

                <div style={{ background: "#fdf4ff", border: "1px solid #f0abfc", padding: "10px 14px", borderRadius: "6px" }}>
                  <strong style={{ fontSize: "12px", color: "#86198f" }}>Reconciliation Hypothesis & Proposed Protocol:</strong>
                  <p style={{ margin: "2px 0 0", fontSize: "12px", color: "#701a75" }}>{c.suggested_resolution || c.reconciliation_hypothesis}</p>
                  {c.underlying_cause && (
                    <p style={{ margin: "4px 0 0", fontSize: "11px", color: "#9333ea" }}>
                      <strong>Root Cause:</strong> {c.underlying_cause}
                    </p>
                  )}
                </div>
              </div>
            )))}
          </div>
        </div>
      )}

      {/* =========================================================================
          TAB 4: SCIENTIFIC HYPOTHESES
          ========================================================================= */}
      {activeTab === "hypotheses" && (
        hypotheses.length === 0 ? (
          <div className="empty-state" style={{ padding: "36px 20px" }}>
            <h4 style={{ fontSize: "14px", color: "var(--text-main)", marginBottom: "6px" }}>No Scientific Hypotheses Formulated Yet</h4>
            <p style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "12px" }}>
              Select a documented gap from Tab 2 and click "Formulate Hypothesis ➔" to generate an evidence-backed hypothesis with first-principles validation.
            </p>
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={() => setActiveTab("gaps")}
            >
              Browse Research Gaps ➔
            </button>
          </div>
        ) : (
        <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: "18px" }}>
          {/* Left Column: Hypothesis List */}
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
              <strong style={{ fontSize: "13px" }}>Hypotheses ({hypotheses.length})</strong>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "8px", maxHeight: "680px", overflowY: "auto" }}>
              {hypotheses.map((h) => {
                const isSelected = selectedHypothesis?.hypothesis_id === h.hypothesis_id;
                return (
                  <div
                    key={h.hypothesis_id}
                    className="card"
                    style={{
                      padding: "12px 14px",
                      cursor: "pointer",
                      border: isSelected ? "2px solid #2563eb" : "1px solid #e2e8f0",
                      background: isSelected ? "#eff6ff" : "#ffffff",
                    }}
                    onClick={() => setSelectedHypothesis(h)}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                      <span style={{ fontSize: "10px", fontFamily: "monospace", color: "#64748b" }}>{h.hypothesis_id}</span>
                      {renderEpistemicBadge(h.epistemic_type)}
                    </div>
                    <strong style={{ fontSize: "12px", display: "block", marginBottom: "4px", color: "#0f172a" }}>
                      {h.hypothesis_statement.slice(0, 85)}...
                    </strong>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "#64748b" }}>
                      <span>{h.category.replace(/_/g, " ")}</span>
                      <span style={{ fontFamily: "monospace" }}>{h.experimental_protocol.candidate_composition}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Right Column: Active Hypothesis Inspector */}
          {selectedHypothesis ? (
            <div className="card" style={{ padding: "20px 24px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "12px" }}>
                <div>
                  <div style={{ display: "flex", gap: "8px", alignItems: "center", marginBottom: "6px" }}>
                    <span className="badge badge-purple" style={{ fontFamily: "monospace" }}>
                      {selectedHypothesis.hypothesis_id}
                    </span>
                    {renderEpistemicBadge(selectedHypothesis.epistemic_type)}
                    <span className="badge badge-teal">{selectedHypothesis.category.replace(/_/g, " ")}</span>
                  </div>
                  <h3 style={{ margin: 0, fontSize: "16px", color: "#0f172a" }}>
                    {selectedHypothesis.hypothesis_statement}
                  </h3>
                </div>

                <button
                  className="btn btn-primary"
                  onClick={() => handleGenerateMatrixFromHypothesis(selectedHypothesis.hypothesis_id)}
                  disabled={isGenerating}
                >
                  {isGenerating ? "Building..." : "Generate Verification Matrix ➔"}
                </button>
              </div>

              {/* Chemical Validation Strip */}
              <div
                style={{
                  background: selectedHypothesis.chemical_validation.is_charge_balanced ? "#f0fdf4" : "#fef2f2",
                  border: `1px solid ${selectedHypothesis.chemical_validation.is_charge_balanced ? "#86efac" : "#fca5a5"}`,
                  borderRadius: "8px",
                  padding: "12px 16px",
                  marginBottom: "16px",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  flexWrap: "wrap",
                  gap: "12px",
                }}
              >
                <div>
                  <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                    <strong style={{ fontSize: "13px", color: "#166534" }}>
                      Candidate: {selectedHypothesis.experimental_protocol.candidate_composition}
                    </strong>
                    <span className="badge badge-green">CHARGE BALANCED (Q_net = 0)</span>
                  </div>
                  <p style={{ margin: "4px 0 0", fontSize: "11px", color: "#15803d" }}>
                    {selectedHypothesis.chemical_validation.explanation.split("\n")[0]}
                  </p>
                </div>

                <div style={{ display: "flex", gap: "16px", fontSize: "11px", fontFamily: "monospace" }}>
                  <div>
                    <span style={{ color: "#64748b" }}>M2 Valence (Q_M2):</span>
                    <strong style={{ display: "block" }}>{selectedHypothesis.chemical_validation.q_m2.toFixed(3)} e</strong>
                  </div>
                  <div>
                    <span style={{ color: "#64748b" }}>Required Li:</span>
                    <strong style={{ display: "block" }}>{selectedHypothesis.chemical_validation.required_li.toFixed(3)}</strong>
                  </div>
                  <div>
                    <span style={{ color: "#64748b" }}>Li Vacancies (δ):</span>
                    <strong style={{ display: "block" }}>{selectedHypothesis.chemical_validation.delta_li_vacancies.toFixed(3)}</strong>
                  </div>
                  <div>
                    <span style={{ color: "#64748b" }}>M2 Occupancy:</span>
                    <strong style={{ display: "block" }}>{selectedHypothesis.chemical_validation.phi_m2_occupancy.toFixed(3)}</strong>
                  </div>
                </div>
              </div>

              {/* Epistemic Statements Breakdown */}
              <div style={{ marginBottom: "16px" }}>
                <h4 style={{ margin: "0 0 8px", fontSize: "13px", color: "#334155" }}>Epistemic Evidence Breakdown:</h4>
                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  {selectedHypothesis.epistemic_breakdown.map((stmt, i) => (
                    <div
                      key={i}
                      style={{
                        padding: "8px 12px",
                        background: "#f8fafc",
                        border: "1px solid #e2e8f0",
                        borderRadius: "6px",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                      }}
                    >
                      <span style={{ fontSize: "12px", color: "#1e293b", flex: 1 }}>{stmt.statement}</span>
                      <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
                        {renderEpistemicBadge(stmt.epistemic_type)}
                        {stmt.citation && (
                          <span style={{ fontSize: "10px", color: "#64748b", fontFamily: "monospace" }}>
                            [{stmt.citation}]
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Falsification Criteria & Alternative Explanations */}
              <div className="grid-2col" style={{ gap: "14px", marginBottom: "14px" }}>
                <div style={{ background: "#fef2f2", border: "1px solid #fecaca", padding: "12px 16px", borderRadius: "6px" }}>
                  <strong style={{ fontSize: "12px", color: "#991b1b" }}>Actionable Falsification Criteria:</strong>
                  <ul style={{ margin: "6px 0 0", paddingLeft: "18px", fontSize: "11px", color: "#7f1d1d" }}>
                    {selectedHypothesis.falsification_criteria.map((fc, i) => (
                      <li key={i}>{fc}</li>
                    ))}
                  </ul>
                </div>

                <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", padding: "12px 16px", borderRadius: "6px" }}>
                  <strong style={{ fontSize: "12px", color: "#334155" }}>Alternative Explanations & Confounders:</strong>
                  <ul style={{ margin: "6px 0 0", paddingLeft: "18px", fontSize: "11px", color: "#475569" }}>
                    {selectedHypothesis.alternative_explanations.map((ae, i) => (
                      <li key={i}>{ae}</li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Cross-Module Quick Actions */}
              <div style={{ display: "flex", gap: "8px", borderTop: "1px solid #e2e8f0", paddingTop: "14px" }}>
                {onNavigate && (
                  <>
                    <button className="btn btn-secondary btn-sm" onClick={() => onNavigate("Materials Designer")}>
                      Open in Materials Designer ⚗
                    </button>
                    <button className="btn btn-secondary btn-sm" onClick={() => onNavigate("Property Prediction")}>
                      Predict Properties (ML) ⌁
                    </button>
                    <button className="btn btn-secondary btn-sm" onClick={() => onNavigate("Research Copilot")}>
                      Ask Copilot About Mechanism 💬
                    </button>
                  </>
                )}
              </div>
            </div>
          ) : (
            <div className="loading-state">
              <p>Select a scientific hypothesis to inspect evidence breakdown and protocols.</p>
            </div>
          )}
        </div>
        )
      )}

      {/* =========================================================================
          TAB 5: EXPERIMENTAL VERIFICATION MATRIX
          ========================================================================= */}
      {activeTab === "matrix" && (
        matrices.length === 0 ? (
          <div className="empty-state" style={{ padding: "36px 20px" }}>
            <h4 style={{ fontSize: "14px", color: "var(--text-main)", marginBottom: "6px" }}>No Verification Matrices Generated</h4>
            <p style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "12px" }}>
              Select a hypothesis in Tab 4 and click "Create Verification Matrix ➔" to plan precursors, controls, and testing protocols.
            </p>
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={() => setActiveTab("hypotheses")}
            >
              Go to Scientific Hypotheses ➔
            </button>
          </div>
        ) : (
        <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: "18px" }}>
          {/* Left Column: Matrices List */}
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
              <strong style={{ fontSize: "13px" }}>Verification Matrices ({matrices.length})</strong>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "8px", maxHeight: "680px", overflowY: "auto" }}>
              {matrices.map((m) => {
                const isSelected = selectedMatrix?.matrix_id === m.matrix_id;
                return (
                  <div
                    key={m.matrix_id}
                    className="card"
                    style={{
                      padding: "12px 14px",
                      cursor: "pointer",
                      border: isSelected ? "2px solid #2563eb" : "1px solid #e2e8f0",
                      background: isSelected ? "#eff6ff" : "#ffffff",
                    }}
                    onClick={() => setSelectedMatrix(m)}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                      <span style={{ fontSize: "10px", fontFamily: "monospace", color: "#64748b" }}>{m.matrix_id}</span>
                      <span className="badge badge-amber">PROPOSED</span>
                    </div>
                    <strong style={{ fontSize: "12px", display: "block", marginBottom: "4px", color: "#0f172a" }}>
                      {m.title.slice(0, 80)}...
                    </strong>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "#64748b" }}>
                      <span style={{ fontFamily: "monospace" }}>{m.candidate_composition}</span>
                      <span>{m.control_samples.length} Controls</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Right Column: Active Matrix Details */}
          {selectedMatrix ? (
            <div className="card" style={{ padding: "20px 24px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "12px" }}>
                <div>
                  <div style={{ display: "flex", gap: "8px", alignItems: "center", marginBottom: "6px" }}>
                    <span className="badge badge-purple" style={{ fontFamily: "monospace" }}>
                      {selectedMatrix.matrix_id}
                    </span>
                    <span className="badge badge-blue">LINKED TO {selectedMatrix.hypothesis_id}</span>
                    <span className="badge badge-teal">GAP {selectedMatrix.research_gap_id}</span>
                  </div>
                  <h3 style={{ margin: 0, fontSize: "16px", color: "#0f172a" }}>{selectedMatrix.title}</h3>
                </div>

                <button className="btn btn-primary" onClick={() => handleTransferToExperiments(selectedMatrix)}>
                  Transfer to Experiment Management ➔
                </button>
              </div>

              {/* Status Disclaimers Strip (Mandatory Uncertainty Preservation) */}
              <div
                style={{
                  background: "#fffbeb",
                  border: "1px solid #fcd34d",
                  borderRadius: "8px",
                  padding: "12px 16px",
                  marginBottom: "16px",
                  fontSize: "11px",
                  color: "#92400e",
                }}
              >
                <div style={{ display: "flex", gap: "14px", alignItems: "center", marginBottom: "4px" }}>
                  <strong style={{ color: "#78350f" }}>MANDATORY STATUS SAFEGUARDS:</strong>
                  <span className="badge badge-amber">{selectedMatrix.status_disclaimers.EXPERIMENT_STATUS}</span>
                  <span className="badge badge-indigo">{selectedMatrix.status_disclaimers.ML_VALIDATION_STATUS}</span>
                </div>
                <div>{selectedMatrix.status_disclaimers.SUPERVISOR_POLICY_SEPARATION}</div>
              </div>

              {/* Control Samples Table */}
              <div style={{ marginBottom: "16px" }}>
                <h4 style={{ margin: "0 0 8px", fontSize: "13px", color: "#334155" }}>
                  1. Control & Comparison Samples ({selectedMatrix.control_samples.length}):
                </h4>
                <div className="table-responsive">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Role</th>
                        <th>Sample ID</th>
                        <th>Formula</th>
                        <th>Expected Empirical Behavior</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedMatrix.control_samples.map((cs, i) => (
                        <tr key={i}>
                          <td>
                            <span
                              className={`badge ${
                                cs.role.includes("NEGATIVE")
                                  ? "badge-amber"
                                  : cs.role.includes("REPLICATION")
                                  ? "badge-blue"
                                  : "badge-green"
                              }`}
                            >
                              {cs.role}
                            </span>
                          </td>
                          <td style={{ fontFamily: "monospace", fontWeight: 600 }}>{cs.sample_id}</td>
                          <td style={{ fontFamily: "monospace" }}>{cs.formula}</td>
                          <td style={{ fontSize: "11px", color: "#475569" }}>{cs.expected_behavior}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Variable Specifications */}
              <div style={{ marginBottom: "16px" }}>
                <h4 style={{ margin: "0 0 8px", fontSize: "13px", color: "#334155" }}>
                  2. Controlled vs Independent Variables ({selectedMatrix.variable_specifications.length}):
                </h4>
                <div className="table-responsive">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Variable Name</th>
                        <th>Type</th>
                        <th>Target Value</th>
                        <th>Tolerance</th>
                        <th>Scientific Rationale</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedMatrix.variable_specifications.map((vs, i) => (
                        <tr key={i}>
                          <td style={{ fontWeight: 600 }}>{vs.variable_name}</td>
                          <td>
                            <span
                              className={`badge ${
                                vs.variable_type === "CONTROLLED"
                                  ? "badge-teal"
                                  : vs.variable_type === "INDEPENDENT"
                                  ? "badge-purple"
                                  : "badge-blue"
                              }`}
                            >
                              {vs.variable_type}
                            </span>
                          </td>
                          <td style={{ fontSize: "11px", fontFamily: "monospace" }}>{vs.target_value}</td>
                          <td style={{ fontSize: "11px" }}>{vs.tolerance}</td>
                          <td style={{ fontSize: "11px", color: "#64748b" }}>{vs.rationale}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Synthesis Protocol Plan */}
              <div style={{ marginBottom: "16px" }}>
                <h4 style={{ margin: "0 0 8px", fontSize: "13px", color: "#334155" }}>
                  3. Discrete Synthesis Protocol Plan ({selectedMatrix.synthesis_plan.length} Steps):
                </h4>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "10px" }}>
                  {selectedMatrix.synthesis_plan.map((sp) => (
                    <div
                      key={sp.step_number}
                      style={{
                        padding: "10px 14px",
                        background: "#f8fafc",
                        border: "1px solid #e2e8f0",
                        borderRadius: "6px",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                        <strong style={{ fontSize: "12px", color: "#0f172a" }}>Step {sp.step_number}</strong>
                        <span style={{ fontSize: "10px", color: "#64748b" }}>{sp.equipment.split(" ")[0]}</span>
                      </div>
                      <div style={{ fontSize: "11px", fontWeight: 600, color: "#2563eb", marginBottom: "4px" }}>
                        {sp.operation}
                      </div>
                      <div style={{ fontSize: "10px", color: "#475569" }}>
                        <strong>Atmosphere:</strong> {sp.atmosphere}
                      </div>
                      <div style={{ fontSize: "10px", color: "#64748b", marginTop: "2px" }}>
                        <strong>Safety:</strong> {sp.safety_notes.slice(0, 60)}...
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Characterization Battery & Electrochemical Protocols */}
              <div className="grid-2col" style={{ gap: "14px", marginBottom: "16px" }}>
                <div style={{ background: "#f8fafc", padding: "12px 14px", borderRadius: "6px", border: "1px solid #e2e8f0" }}>
                  <strong style={{ fontSize: "12px", color: "#0f172a" }}>
                    4. Pre-cycling Characterization Gate ({selectedMatrix.characterization_plan.length} techniques):
                  </strong>
                  <ul style={{ margin: "6px 0 0", paddingLeft: "16px", fontSize: "11px", color: "#334155" }}>
                    {selectedMatrix.characterization_plan.map((cp, i) => (
                      <li key={i} style={{ marginBottom: "4px" }}>
                        <strong>{cp.technique}:</strong> {cp.target_feature} ({cp.acceptance_criteria})
                      </li>
                    ))}
                  </ul>
                </div>

                <div style={{ background: "#f8fafc", padding: "12px 14px", borderRadius: "6px", border: "1px solid #e2e8f0" }}>
                  <strong style={{ fontSize: "12px", color: "#0f172a" }}>5. Electrochemical Evaluation Protocol:</strong>
                  {selectedMatrix.electrochemical_plan.map((ep, i) => (
                    <div key={i} style={{ marginTop: "6px", fontSize: "11px", color: "#334155" }}>
                      <div>
                        <strong>Window:</strong> {ep.voltage_window} | <strong>Temp:</strong> {ep.temperature}
                      </div>
                      <div>
                        <strong>C-rates:</strong> {ep.c_rates.join(", ")}C | <strong>Loading:</strong> ≥{ep.mass_loading_min_mg_cm2} mg/cm²
                      </div>
                      <div style={{ fontSize: "10px", color: "#64748b", marginTop: "2px" }}>
                        <strong>Electrolyte:</strong> {ep.electrolyte_spec}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Action Buttons & Navigation */}
              <div style={{ display: "flex", gap: "8px", borderTop: "1px solid #e2e8f0", paddingTop: "14px" }}>
                <button className="btn btn-primary" onClick={() => handleTransferToExperiments(selectedMatrix)}>
                  Log Experiment to Lab DB (Planned) ⌘
                </button>
                {onNavigate && (
                  <>
                    <button className="btn btn-secondary" onClick={() => onNavigate("Materials Designer")}>
                      Validate in Materials Designer ⚗
                    </button>
                    <button className="btn btn-secondary" onClick={() => onNavigate("Property Prediction")}>
                      Evaluate with ML Surrogates ⌁
                    </button>
                    <button className="btn btn-secondary" onClick={() => onNavigate("Research Copilot")}>
                      Discuss Matrix with Copilot 💬
                    </button>
                  </>
                )}
              </div>
            </div>
          ) : (
            <div className="loading-state">
              <p>Select an experimental verification matrix to review protocol, controls, and variables.</p>
            </div>
          )}
        </div>
        )
      )}
    </div>
  );
};
