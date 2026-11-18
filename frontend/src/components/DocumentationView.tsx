import React, { useState } from "react";

export const DocumentationView: React.FC = () => {
  const [activeDoc, setActiveDoc] = useState<"methodology" | "chemistry" | "ml" | "integrity">("methodology");

  return (
    <div className="view-container">
      <section className="section-heading">
        <div>
          <h2>Platform Documentation & Scientific Methodology</h2>
          <p>Technical reference, deterministic chemistry formulation rules, ML validation standards, and data protection policies.</p>
        </div>
        <div style={{ display: "flex", gap: "8px" }}>
          <span className="badge badge-blue">Reference v1.0</span>
          <span className="badge badge-green">OpenAPI Verified</span>
        </div>
      </section>

      {/* Doc Navigation Tabs */}
      <div style={{ display: "flex", gap: "8px", marginBottom: "20px", borderBottom: "1px solid var(--border)", paddingBottom: "10px" }}>
        <button
          className={`tab-pill ${activeDoc === "methodology" ? "active" : ""}`}
          onClick={() => setActiveDoc("methodology")}
        >
          🔬 Discovery Methodology
        </button>
        <button
          className={`tab-pill ${activeDoc === "chemistry" ? "active" : ""}`}
          onClick={() => setActiveDoc("chemistry")}
        >
          ⚗ First-Principles Chemistry
        </button>
        <button
          className={`tab-pill ${activeDoc === "ml" ? "active" : ""}`}
          onClick={() => setActiveDoc("ml")}
        >
          📊 Machine Learning Architecture
        </button>
        <button
          className={`tab-pill ${activeDoc === "integrity" ? "active" : ""}`}
          onClick={() => setActiveDoc("integrity")}
        >
          🛡 Data Protection & Integrity
        </button>
      </div>

      {/* Doc 1: Discovery Methodology */}
      {activeDoc === "methodology" && (
        <div className="card" style={{ padding: "24px" }}>
          <h3 style={{ color: "var(--text-main)", marginBottom: "12px", fontSize: "16px" }}>
            High-Entropy LMFP Discovery Framework
          </h3>
          <p style={{ color: "var(--text-secondary)", lineHeight: 1.6, marginBottom: "16px", fontSize: "13px" }}>
            The ECMT AI platform bridges the gap between quantum mechanical constraints, peer-reviewed literature evidence, and wet-lab physical synthesis. It addresses the commercial bottleneck of lithium manganese iron phosphate cathodes—namely, the Jahn-Teller distortion in high-spin Mn³⁺—by guiding researchers through high-entropy transition metal co-doping.
          </p>

          <div className="grid-two-col" style={{ gap: "20px", marginTop: "16px" }}>
            <div style={{ background: "var(--bg-subtle)", padding: "16px", borderRadius: "8px", border: "1px solid var(--border)" }}>
              <h4 style={{ color: "var(--text-main)", margin: "0 0 8px", fontSize: "14px" }}>The Seven-Step Discovery Lifecycle</h4>
              <ol style={{ color: "var(--text-secondary)", paddingLeft: "18px", margin: 0, lineHeight: 1.8, fontSize: "12px" }}>
                <li><strong>Literature Trend Extraction:</strong> Statistical analysis across 1,215 curated cathode samples.</li>
                <li><strong>Research Gap Identification:</strong> Automated detection of uninvestigated compositional and thermal spaces.</li>
                <li><strong>Scientific Conflict Reconciliation:</strong> Highlighting divergent literature claims and underlying variables.</li>
                <li><strong>Hypothesis Formulation:</strong> Synthesis of evidence-backed mechanistic hypotheses.</li>
                <li><strong>First-Principles Chemical Validation:</strong> Rigorous charge neutrality and Shannon radii matching.</li>
                <li><strong>Experimental Verification Matrix:</strong> Formulation scoring, control sample planning, and protocol generation.</li>
                <li><strong>Laboratory Handoff:</strong> Seamless transition to physical synthesis tracking with zero data fabrication.</li>
              </ol>
            </div>

            <div style={{ background: "var(--bg-subtle)", padding: "16px", borderRadius: "8px", border: "1px solid var(--border)" }}>
              <h4 style={{ color: "var(--text-main)", margin: "0 0 8px", fontSize: "14px" }}>The Jahn-Teller Mitigation Strategy</h4>
              <p style={{ color: "var(--text-secondary)", fontSize: "12px", lineHeight: 1.6, margin: "0 0 12px" }}>
                In trivalent manganese (Mn³⁺, 3d⁴, t₂g³ eg¹), the single electron in the degenerate eg orbital causes spontaneous tetragonal distortion of the MnO₆ octahedra. During charge/discharge cycling above 4.1 V, this distortion triggers lattice cracking and Mn dissolution into the electrolyte.
              </p>
              <div style={{ background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: "6px", padding: "10px", fontSize: "12px", color: "#166534" }}>
                <strong>High-Entropy Stabilization:</strong> Doping 3 to 5 multi-valent cations into the M2 site introduces configurational entropy (ΔS_config &gt; 0.8 R), relieving local lattice strain and suppressing phase separation.
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Doc 2: First-Principles Chemistry */}
      {activeDoc === "chemistry" && (
        <div className="card" style={{ padding: "24px" }}>
          <h3 style={{ color: "var(--text-main)", marginBottom: "12px", fontSize: "16px" }}>
            Deterministic Crystallography & Electroneutrality
          </h3>
          <p style={{ color: "var(--text-secondary)", lineHeight: 1.6, marginBottom: "20px", fontSize: "13px" }}>
            The Materials Designer engine enforces physical and crystallographic laws deterministically. No candidate is passed to machine learning surrogates or laboratory protocols without passing rigorous stoichiometric and charge-balance checks.
          </p>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "16px" }}>
            <div style={{ background: "var(--bg-subtle)", padding: "16px", borderRadius: "8px", border: "1px solid var(--border)" }}>
              <div style={{ fontSize: "11px", color: "var(--primary)", fontWeight: 700, marginBottom: "4px" }}>RULE 1</div>
              <h4 style={{ color: "var(--text-main)", margin: "0 0 8px", fontSize: "14px" }}>M2 Octahedral Site Occupancy</h4>
              <p style={{ color: "var(--text-secondary)", fontSize: "12px", lineHeight: 1.5, margin: 0 }}>
                In the ordered olivine Pnma lattice, transition metals occupy the 4c Wyckoff site (M2 octahedra). The sum of all M2 cations must satisfy:
              </p>
              <div style={{ background: "rgba(15, 23, 42, 0.8)", border: "1px solid var(--border)", padding: "8px 12px", borderRadius: "4px", margin: "8px 0", fontFamily: "JetBrains Mono, monospace", color: "#38bdf8", fontSize: "12px" }}>
                Mn_frac + Fe_frac + ∑(Dopant_frac) = 1.0000 ± 0.005
              </div>
            </div>

            <div style={{ background: "var(--bg-subtle)", padding: "16px", borderRadius: "8px", border: "1px solid var(--border)" }}>
              <div style={{ fontSize: "11px", color: "var(--primary)", fontWeight: 700, marginBottom: "4px" }}>RULE 2</div>
              <h4 style={{ color: "var(--text-main)", margin: "0 0 8px", fontSize: "14px" }}>Charge Neutrality & Li Vacancy Compensation</h4>
              <p style={{ color: "var(--text-secondary)", fontSize: "12px", lineHeight: 1.5, margin: 0 }}>
                When dopants with oxidation states &gt; +2 (such as Al³⁺, Ti⁴⁺, Nb⁵⁺) substitute into M2, electroneutrality is maintained by creating lithium vacancies:
              </p>
              <div style={{ background: "rgba(15, 23, 42, 0.8)", border: "1px solid var(--border)", padding: "8px 12px", borderRadius: "4px", margin: "8px 0", fontFamily: "JetBrains Mono, monospace", color: "#38bdf8", fontSize: "12px" }}>
                Li = 1.0 - δ, where δ = Q_M2 - 2.0000
              </div>
            </div>

            <div style={{ background: "var(--bg-subtle)", padding: "16px", borderRadius: "8px", border: "1px solid var(--border)" }}>
              <div style={{ fontSize: "11px", color: "var(--primary)", fontWeight: 700, marginBottom: "4px" }}>RULE 3</div>
              <h4 style={{ color: "var(--text-main)", margin: "0 0 8px", fontSize: "14px" }}>Configurational Entropy (ΔS_config)</h4>
              <p style={{ color: "var(--text-secondary)", fontSize: "12px", lineHeight: 1.5, margin: 0 }}>
                Configurational entropy in the transition metal sublattice is calculated using the Boltzmann-Gibbs relation:
              </p>
              <div style={{ background: "rgba(15, 23, 42, 0.8)", border: "1px solid var(--border)", padding: "8px 12px", borderRadius: "4px", margin: "8px 0", fontFamily: "JetBrains Mono, monospace", color: "#38bdf8", fontSize: "12px" }}>
                ΔS_config = -R * ∑(x_i * ln(x_i))
              </div>
              <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>Low (&lt;0.6R), Medium (0.6–0.8R), High (&gt;0.8R)</span>
            </div>
          </div>
        </div>
      )}

      {/* Doc 3: Machine Learning Architecture */}
      {activeDoc === "ml" && (
        <div className="card" style={{ padding: "24px" }}>
          <h3 style={{ color: "var(--text-main)", marginBottom: "12px", fontSize: "16px" }}>
            Machine Learning Surrogate Models
          </h3>
          <p style={{ color: "var(--text-secondary)", lineHeight: 1.6, marginBottom: "20px", fontSize: "13px" }}>
            The platform utilizes Random Forest regressors validated under GroupKFold cross-validation grouped strictly by publication DOI to prevent data leakage across identical synthesis batches.
          </p>

          <table className="data-table" style={{ width: "100%", marginBottom: "20px" }}>
            <thead>
              <tr>
                <th>Target Metric</th>
                <th>Model Type</th>
                <th>Cross-Validation</th>
                <th>Training Samples</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>0.1C Discharge Capacity</strong></td>
                <td>Random Forest Regressor (100 estimators)</td>
                <td>GroupKFold (grouped by DOI)</td>
                <td>182 samples</td>
                <td><span className="badge badge-green">Production Ready</span></td>
              </tr>
              <tr>
                <td><strong>1C Discharge Capacity</strong></td>
                <td>Random Forest Regressor (100 estimators)</td>
                <td>GroupKFold (grouped by DOI)</td>
                <td>182 samples</td>
                <td><span className="badge badge-green">Production Ready</span></td>
              </tr>
              <tr>
                <td><strong>5C High-Rate Capacity</strong></td>
                <td>Random Forest Regressor (100 estimators)</td>
                <td>GroupKFold (grouped by DOI)</td>
                <td>182 samples</td>
                <td><span className="badge badge-green">Production Ready</span></td>
              </tr>
              <tr>
                <td><strong>Capacity Retention (100 cyc)</strong></td>
                <td>Random Forest Regressor (100 estimators)</td>
                <td>GroupKFold (grouped by DOI)</td>
                <td>192 samples</td>
                <td><span className="badge badge-green">Production Ready</span></td>
              </tr>
              <tr>
                <td><strong>0.05C Discharge Capacity</strong></td>
                <td>—</td>
                <td>Insufficient data threshold (&lt;50 pts)</td>
                <td>38 samples</td>
                <td><span className="badge badge-neutral">Insufficient Data</span></td>
              </tr>
              <tr>
                <td><strong>Initial Coulombic Efficiency (ICE)</strong></td>
                <td>—</td>
                <td>Insufficient data threshold (&lt;50 pts)</td>
                <td>42 samples</td>
                <td><span className="badge badge-neutral">Insufficient Data</span></td>
              </tr>
            </tbody>
          </table>

          <div style={{ background: "#fffbeb", border: "1px solid #fde68a", borderRadius: "6px", padding: "12px", fontSize: "12px", color: "#b45309" }}>
            <strong>Domain Coverage Policy:</strong> Published literature predominantly investigates binary or ternary systems. For high-entropy formulations (≥ 3 dopants), the platform generates explicit domain coverage warnings and displays 95% tree-dispersion intervals to honestly reflect model uncertainty.
          </div>
        </div>
      )}

      {/* Doc 4: Data Protection & Integrity */}
      {activeDoc === "integrity" && (
        <div className="card" style={{ padding: "24px" }}>
          <h3 style={{ color: "var(--text-main)", marginBottom: "12px", fontSize: "16px" }}>
            Scientific Integrity & Safe Export Guardrails
          </h3>
          <p style={{ color: "var(--text-secondary)", lineHeight: 1.6, marginBottom: "20px", fontSize: "13px" }}>
            ECMT AI is built on an unwavering commitment to scientific honesty. The platform strictly forbids fabricated placeholder values or ungrounded claims.
          </p>

          <div className="grid-two-col" style={{ gap: "20px" }}>
            <div style={{ background: "var(--bg-subtle)", padding: "16px", borderRadius: "8px", border: "1px solid var(--border)" }}>
              <h4 style={{ color: "var(--text-main)", margin: "0 0 8px", fontSize: "14px" }}>Zero Fabrication in Laboratory Tracking</h4>
              <p style={{ color: "var(--text-secondary)", fontSize: "12px", lineHeight: 1.6, margin: 0 }}>
                Unperformed experiments strictly return <code>null</code> measurements for discharge capacity and retention. The UI renders <code>--</code> with status <code>SYNTHESIS_PLANNED</code>. Under no circumstances are mock or default numbers substituted for actual physical measurements.
              </p>
            </div>

            <div style={{ background: "var(--bg-subtle)", padding: "16px", borderRadius: "8px", border: "1px solid var(--border)" }}>
              <h4 style={{ color: "var(--text-main)", margin: "0 0 8px", fontSize: "14px" }}>Safe Export Defense-in-Depth</h4>
              <p style={{ color: "var(--text-secondary)", fontSize: "12px", lineHeight: 1.6, margin: 0 }}>
                Extracted literature records must pass human review staging before integration into the master corpus. The safe export engine blocks records that have unresolved sample IDs, missing paper DOIs, or multi-condition retention strings that cannot be cleanly mapped to single scalars.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
