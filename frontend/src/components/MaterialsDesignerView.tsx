import React, { useState, useEffect } from "react";
import { api, type Dopant, type ValidationResponse, type CandidateComposition } from "../api";

interface AllowedDopantInfo {
  symbol: string;
  name: string;
  allowed_oxidation_states: number[];
  default_oxidation_state: number;
}

interface MaterialsDesignerViewProps {
  onNavigate?: (section: string) => void;
}

export const MaterialsDesignerView: React.FC<MaterialsDesignerViewProps> = ({ onNavigate }) => {
  // Primary cation concentrations
  const [mnFrac, setMnFrac] = useState<number>(0.65);
  const [feFrac, setFeFrac] = useState<number>(0.26);

  // Active dopants
  const [dopants, setDopants] = useState<Dopant[]>([
    { symbol: "Mg", fraction: 0.02, oxidation_state: 2 },
    { symbol: "Zn", fraction: 0.02, oxidation_state: 2 },
    { symbol: "Nb", fraction: 0.01, oxidation_state: 5 },
    { symbol: "Cu", fraction: 0.02, oxidation_state: 2 },
    { symbol: "Zr", fraction: 0.02, oxidation_state: 4 },
  ]);

  // Advanced section toggle
  const [showAdvanced, setShowAdvanced] = useState<boolean>(false);
  const [carbonWt, setCarbonWt] = useState<number>(2.0);
  const [cntWt, setCntWt] = useState<number>(0.0);

  // Validation state
  const [validation, setValidation] = useState<ValidationResponse | null>(null);
  const [validating, setValidating] = useState<boolean>(false);

  // Pre-screened candidates
  const [candidates, setCandidates] = useState<CandidateComposition[]>([]);

  const allowedDopants: AllowedDopantInfo[] = [
    { symbol: "Mg", name: "Magnesium", allowed_oxidation_states: [2], default_oxidation_state: 2 },
    { symbol: "Zn", name: "Zinc", allowed_oxidation_states: [2], default_oxidation_state: 2 },
    { symbol: "Ni", name: "Nickel", allowed_oxidation_states: [2], default_oxidation_state: 2 },
    { symbol: "Cu", name: "Copper", allowed_oxidation_states: [2, 3], default_oxidation_state: 2 },
    { symbol: "Al", name: "Aluminum", allowed_oxidation_states: [3], default_oxidation_state: 3 },
    { symbol: "Ti", name: "Titanium", allowed_oxidation_states: [3, 4], default_oxidation_state: 4 },
    { symbol: "Zr", name: "Zirconium", allowed_oxidation_states: [4], default_oxidation_state: 4 },
    { symbol: "Nb", name: "Niobium", allowed_oxidation_states: [5], default_oxidation_state: 5 },
  ];

  const handleValidate = () => {
    setValidating(true);
    api
      .validateComposition({
        mn_ratio: mnFrac,
        fe_ratio: feFrac,
        dopants: dopants,
        carbon_wt_percent: carbonWt,
        cnt_wt_percent: cntWt,
      })
      .then((res) => {
        setValidation(res);
        setValidating(false);
      })
      .catch((err) => {
        console.error("Validation error:", err);
        setValidating(false);
      });
  };

  useEffect(() => {
    handleValidate();
  }, [mnFrac, feFrac, dopants, carbonWt, cntWt]);

  useEffect(() => {
    api
      .generateCandidates()
      .then((res) => setCandidates(res.candidates || []))
      .catch(() => {});
  }, []);

  const totalDopantFrac = dopants.reduce((sum, d) => sum + d.fraction, 0);
  const m2Occupancy = mnFrac + feFrac + totalDopantFrac;
  const isM2Valid = Math.abs(m2Occupancy - 1.0) <= 0.005;

  const handleAddDopant = (symbol: string) => {
    if (dopants.some((d) => d.symbol === symbol) || dopants.length >= 5) return;
    const elem = allowedDopants.find((e) => e.symbol === symbol);
    if (!elem) return;
    setDopants([...dopants, { symbol, fraction: 0.01, oxidation_state: elem.default_oxidation_state }]);
  };

  const handleRemoveDopant = (symbol: string) => {
    setDopants(dopants.filter((d) => d.symbol !== symbol));
  };

  const handleUpdateDopantFrac = (index: number, newFrac: number) => {
    const updated = [...dopants];
    updated[index] = { ...updated[index], fraction: newFrac };
    setDopants(updated);
  };

  const handleUpdateDopantOxState = (index: number, newOx: number) => {
    const updated = [...dopants];
    updated[index] = { ...updated[index], oxidation_state: newOx };
    setDopants(updated);
  };

  const handleLoadPreset = (c: CandidateComposition) => {
    setMnFrac(c.mn_ratio);
    setFeFrac(c.fe_ratio);
    setDopants(c.dopants);
  };

  return (
    <div className="view-container">
      {/* 1. Short Header */}
      <section className="section-heading" style={{ marginBottom: "16px" }}>
        <div>
          <h2>Materials Designer</h2>
          <p>Formulate stoichiometric LMFP compositions with real-time charge balance and site occupancy validation.</p>
        </div>
        <div style={{ display: "flex", gap: "6px" }}>
          {candidates.slice(0, 2).map((c, idx) => (
            <button
              key={idx}
              type="button"
              className="btn btn-secondary btn-sm"
              style={{ fontSize: "11px", padding: "4px 8px" }}
              onClick={() => handleLoadPreset(c)}
            >
              Preset: {c.name.split(" ")[0]}
            </button>
          ))}
        </div>
      </section>

      <div className="grid-2col" style={{ gap: "16px", alignItems: "flex-start" }}>
        {/* Left: Primary Formulation Inputs */}
        <div className="card" style={{ padding: "20px 22px" }}>
          <h3 style={{ margin: "0 0 14px", fontSize: "14px", color: "var(--text-main)" }}>
            Primary Stoichiometry Inputs
          </h3>

          {/* Mn Concentration */}
          <div style={{ marginBottom: "14px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", marginBottom: "4px" }}>
              <label style={{ fontWeight: 600 }}>Manganese Fraction (Mn):</label>
              <strong style={{ fontFamily: "monospace" }}>{mnFrac.toFixed(3)}</strong>
            </div>
            <input
              type="range"
              min="0.40"
              max="0.85"
              step="0.01"
              value={mnFrac}
              onChange={(e) => setMnFrac(parseFloat(e.target.value))}
              style={{ width: "100%" }}
            />
          </div>

          {/* Fe Concentration */}
          <div style={{ marginBottom: "16px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", marginBottom: "4px" }}>
              <label style={{ fontWeight: 600 }}>Iron Fraction (Fe):</label>
              <strong style={{ fontFamily: "monospace" }}>{feFrac.toFixed(3)}</strong>
            </div>
            <input
              type="range"
              min="0.10"
              max="0.50"
              step="0.01"
              value={feFrac}
              onChange={(e) => setFeFrac(parseFloat(e.target.value))}
              style={{ width: "100%" }}
            />
          </div>

          {/* Add Dopants Bar */}
          <div style={{ marginBottom: "14px" }}>
            <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-muted)", display: "block", marginBottom: "6px" }}>
              ADD DOPANT:
            </span>
            <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
              {allowedDopants.map((elem) => {
                const isAdded = dopants.some((d) => d.symbol === elem.symbol);
                return (
                  <button
                    key={elem.symbol}
                    type="button"
                    className={`btn btn-sm ${isAdded ? "btn-primary" : "btn-secondary"}`}
                    style={{ fontSize: "11px", padding: "3px 8px" }}
                    onClick={() => (isAdded ? handleRemoveDopant(elem.symbol) : handleAddDopant(elem.symbol))}
                  >
                    {isAdded ? `✓ ${elem.symbol}` : `+ ${elem.symbol}`}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Added Dopants Concentrations */}
          {dopants.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginBottom: "16px" }}>
              <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-muted)" }}>
                DOPANT CONCENTRATIONS:
              </span>
              {dopants.map((d, idx) => (
                <div
                  key={d.symbol}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: "8px",
                    padding: "6px 10px",
                    background: "var(--bg-subtle)",
                    borderRadius: "6px",
                    border: "1px solid var(--border)",
                  }}
                >
                  <strong style={{ fontSize: "12px", minWidth: "30px" }}>{d.symbol}</strong>
                  <input
                    type="range"
                    min="0.005"
                    max="0.05"
                    step="0.005"
                    value={d.fraction}
                    onChange={(e) => handleUpdateDopantFrac(idx, parseFloat(e.target.value))}
                    style={{ flex: 1 }}
                  />
                  <span style={{ fontFamily: "monospace", fontSize: "11px", minWidth: "40px", textAlign: "right" }}>
                    {d.fraction.toFixed(3)}
                  </span>
                  <button
                    type="button"
                    style={{ border: "none", background: "transparent", color: "#dc2626", cursor: "pointer", fontSize: "12px" }}
                    onClick={() => handleRemoveDopant(d.symbol)}
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Primary Action Button */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span
              style={{
                fontSize: "11px",
                fontWeight: 600,
                color: isM2Valid ? "#16a34a" : "#d97706",
              }}
            >
              M2 Sum: {m2Occupancy.toFixed(4)} {isM2Valid ? "✓" : "(Target: 1.000)"}
            </span>
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={handleValidate}
              disabled={validating}
            >
              {validating ? "Validating..." : "Validate Chemistry ➔"}
            </button>
          </div>

          {/* Advanced Chemistry Accordion (Collapsed) */}
          <div style={{ marginTop: "16px", paddingTop: "12px", borderTop: "1px solid #e2e8f0" }}>
            <div
              style={{ display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer" }}
              onClick={() => setShowAdvanced(!showAdvanced)}
            >
              <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-secondary)" }}>
                {showAdvanced ? "▼ HIDE ADVANCED CHEMISTRY" : "▶ ADVANCED CHEMISTRY & COATINGS"}
              </span>
              <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>{showAdvanced ? "Collapse" : "Expand"}</span>
            </div>

            {showAdvanced && (
              <div style={{ marginTop: "12px", display: "flex", flexDirection: "column", gap: "10px", fontSize: "11px" }}>
                {/* Dopant Oxidation States */}
                {dopants.map((d, idx) => {
                  const elem = allowedDopants.find((e) => e.symbol === d.symbol);
                  return (
                    <div key={d.symbol} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span>{d.symbol} Oxidation State:</span>
                      <select
                        value={d.oxidation_state}
                        onChange={(e) => handleUpdateDopantOxState(idx, parseInt(e.target.value))}
                        style={{ padding: "2px 6px", fontSize: "11px" }}
                      >
                        {elem?.allowed_oxidation_states.map((ox) => (
                          <option key={ox} value={ox}>
                            +{ox}
                          </option>
                        ))}
                      </select>
                    </div>
                  );
                })}

                {/* Carbon & CNT Coatings */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span>Carbon Coating (wt%):</span>
                  <input
                    type="number"
                    step="0.5"
                    min="0"
                    max="5"
                    value={carbonWt}
                    onChange={(e) => setCarbonWt(parseFloat(e.target.value) || 0)}
                    style={{ width: "60px", padding: "2px 4px", fontSize: "11px" }}
                  />
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span>CNT Network (wt%):</span>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    max="2"
                    value={cntWt}
                    onChange={(e) => setCntWt(parseFloat(e.target.value) || 0)}
                    style={{ width: "60px", padding: "2px 4px", fontSize: "11px" }}
                  />
                </div>

                {validation && (
                  <div style={{ background: "#f8fafc", padding: "8px 10px", borderRadius: "4px", color: "#64748b" }}>
                    <div>Lithium vacancy delta (δ): <code>{validation.formula.li_vacancy_delta.toFixed(4)}</code></div>
                    <div>Crystallographic net charge: <code>{validation.charge_balance.net_charge.toFixed(3)}</code></div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right: Validation Result & Next Action */}
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          {validation && (
            <div className="card" style={{ padding: "20px 22px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                <span className="badge badge-purple">FORMULATED CANDIDATE</span>
                <span className={`badge ${validation.charge_balance.is_charge_balanced ? "badge-green" : "badge-red"}`}>
                  {validation.charge_balance.is_charge_balanced ? "✓ Balanced" : "Unbalanced"}
                </span>
              </div>

              {/* Formula String */}
              <div style={{ background: "#eff6ff", padding: "10px 12px", borderRadius: "6px", marginBottom: "14px" }}>
                <span style={{ fontSize: "10px", fontWeight: 700, color: "#1e40af", display: "block" }}>
                  IUPAC CHEMICAL FORMULA:
                </span>
                <code style={{ fontSize: "13px", fontWeight: 700, color: "#1e3a8a", wordBreak: "break-all" }}>
                  {validation.formula.formula_string}
                </code>
              </div>

              {/* Essential Metrics */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", marginBottom: "16px", fontSize: "12px" }}>
                <div style={{ background: "var(--bg-subtle)", padding: "10px 12px", borderRadius: "8px", border: "1px solid var(--border)" }}>
                  <span style={{ color: "var(--text-muted)", fontSize: "11px", display: "block", marginBottom: "2px" }}>Theoretical Capacity</span>
                  <strong style={{ fontSize: "15px", color: "var(--success)" }}>
                    {validation.capacity.project_reference_theoretical.toFixed(1)} mAh/g
                  </strong>
                </div>

                <div style={{ background: "var(--bg-subtle)", padding: "10px 12px", borderRadius: "8px", border: "1px solid var(--border)" }}>
                  <span style={{ color: "var(--text-muted)", fontSize: "11px", display: "block", marginBottom: "2px" }}>Entropy Classification</span>
                  <strong style={{ fontSize: "13px", color: "var(--primary)" }}>
                    {validation.entropy.classification.replace(/_/g, " ")} ({validation.entropy.s_config_over_r.toFixed(3)})
                  </strong>
                </div>
              </div>

              {/* Next Action Buttons */}
              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                {onNavigate && (
                  <>
                    <button
                      type="button"
                      className="btn btn-primary"
                      style={{ padding: "8px 14px", justifyContent: "center" }}
                      onClick={() => onNavigate("Property Prediction")}
                    >
                      ⌁ Run Property Simulation (ML) ➔
                    </button>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      style={{ padding: "8px 14px", justifyContent: "center" }}
                      onClick={() => onNavigate("Experiment Management")}
                    >
                      ⌘ Plan Experiment in Lab ➔
                    </button>
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
