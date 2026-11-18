import React, { useState, useEffect } from "react";
import { api, type ExperimentRecord, type Dopant } from "../api";

const ALLOWED_DOPANTS = [
  { symbol: "Mg", oxidation_state: 2, label: "Magnesium (Mg²⁺)" },
  { symbol: "Zn", oxidation_state: 2, label: "Zinc (Zn²⁺)" },
  { symbol: "Ni", oxidation_state: 2, label: "Nickel (Ni²⁺)" },
  { symbol: "Cu", oxidation_state: 2, label: "Copper (Cu²⁺)" },
  { symbol: "Al", oxidation_state: 3, label: "Aluminum (Al³⁺)" },
  { symbol: "Ti", oxidation_state: 4, label: "Titanium (Ti⁴⁺)" },
  { symbol: "Zr", oxidation_state: 4, label: "Zirconium (Zr⁴⁺)" },
  { symbol: "Nb", oxidation_state: 5, label: "Niobium (Nb⁵⁺)" },
];

interface ExperimentManagementViewProps {
  onNavigate?: (section: string) => void;
}

export const ExperimentManagementView: React.FC<ExperimentManagementViewProps> = ({ onNavigate }) => {
  const [experiments, setExperiments] = useState<ExperimentRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Database info & save confirmation banner
  const [dbInfo, setDbInfo] = useState<any>(null);
  const [saveSuccessBanner, setSaveSuccessBanner] = useState<{
    experimentId: string;
    sampleId: string;
    message: string;
    timestamp: string;
  } | null>(null);

  // New experiment form state
  const [showForm, setShowForm] = useState<boolean>(false);
  const [sampleId, setSampleId] = useState<string>("HE-LMFP-EXP-01");
  const [operator, setOperator] = useState<string>("Lab Researcher");
  const [batchId, setBatchId] = useState<string>("B-2026-01");
  const [synthesisRoute, setSynthesisRoute] = useState<string>("sol-gel");
  const [calcTemp, setCalcTemp] = useState<number>(650);
  const [calcDuration, setCalcDuration] = useState<number>(6.0);
  const [mnFrac, setMnFrac] = useState<number>(0.70);
  const [feFrac, setFeFrac] = useState<number>(0.30);
  const [dopants, setDopants] = useState<Dopant[]>([]);
  const [selectedDopantSymbol, setSelectedDopantSymbol] = useState<string>("Mg");
  const [dopantFractionInput, setDopantFractionInput] = useState<number>(0.02);
  const [carbonWt, setCarbonWt] = useState<number>(2.0);

  // Status and measurement toggle
  const [isPlannedOnly, setIsPlannedOnly] = useState<boolean>(false);
  const [dischargeCap, setDischargeCap] = useState<number>(152.4);
  const [retentionPct, setRetentionPct] = useState<number>(93.8);
  const [cycleCount, setCycleCount] = useState<number>(100);
  const [impurityPhases, setImpurityPhases] = useState<string>("None detected (pure olivine)");
  const [observations, setObservations] = useState<string>("Uniform black powder, high tap density");

  // Comparison matrix state
  const [selectedExp, setSelectedExp] = useState<ExperimentRecord | null>(null);
  const [comparisonData, setComparisonData] = useState<any>(null);
  const [loadingComp, setLoadingComp] = useState<boolean>(false);

  // Characterization Images State
  const [enlargedImage, setEnlargedImage] = useState<string | null>(null);
  const [showAttachModal, setShowAttachModal] = useState<boolean>(false);
  const [attachFile, setAttachFile] = useState<File | null>(null);
  const [attachType, setAttachType] = useState<string>("SEM Micrograph");
  const [attachNotes, setAttachNotes] = useState<string>("");
  const [uploadingImage, setUploadingImage] = useState<boolean>(false);

  // Stoichiometry calculations
  const dopantSum = dopants.reduce((acc, d) => acc + (Number(d.fraction) || 0), 0);
  const m2Sum = Number((mnFrac + feFrac + dopantSum).toFixed(4));
  const isM2Valid = Math.abs(m2Sum - 1.0) <= 0.005;

  const fetchExperiments = () => {
    setLoading(true);
    api
      .getExperiments()
      .then((data) => {
        setExperiments(data);
        if (data.length > 0 && !selectedExp) {
          handleSelectExperiment(data[0]);
        }
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "Failed to load experiments");
        setLoading(false);
      });
  };

  const fetchDbInfo = () => {
    api
      .getExperimentDatabaseInfo()
      .then((info) => setDbInfo(info))
      .catch(() => {
        setDbInfo({
          mode: "LOCAL_MODE",
          engine: "SQLite File Database",
          db_filename: "lab_experiments.db",
          table_name: "lab_experiments",
          sqlite_db_abs_path: "data/lab_experiments.db",
        });
      });
  };

  useEffect(() => {
    fetchExperiments();
    fetchDbInfo();
  }, []);

  const handleSelectExperiment = async (exp: ExperimentRecord) => {
    setSelectedExp(exp);
    setLoadingComp(true);
    try {
      const comp = await api.compareExperiment({
        mn_ratio: exp.mn_frac,
        fe_ratio: exp.fe_frac,
        experiment_id: exp.experiment_id,
      });
      setComparisonData(comp);
    } catch (err: any) {
      console.error("Comparison load error:", err);
    } finally {
      setLoadingComp(false);
    }
  };

  const handleDeleteExperiment = async (expId: string, sampleLabel: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm(`Delete experiment ${sampleLabel} (${expId}) from data/lab_experiments.db?`)) {
      return;
    }
    try {
      await api.deleteExperiment(expId);
      if (selectedExp?.experiment_id === expId) {
        setSelectedExp(null);
        setComparisonData(null);
      }
      fetchExperiments();
      fetchDbInfo();
    } catch (err: any) {
      alert(`Failed to delete experiment: ${err.message}`);
    }
  };

  const handleUploadImageToExperiment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedExp || !attachFile) return;
    setUploadingImage(true);
    try {
      const res = await api.uploadExperimentImage(
        attachFile,
        selectedExp.experiment_id,
        attachType,
        attachNotes
      );
      const updatedImages = [...(selectedExp.characterization_images || []), res.image_record];
      const updatedExp = { ...selectedExp, characterization_images: updatedImages };
      setSelectedExp(updatedExp);
      setExperiments(experiments.map((x) => (x.experiment_id === selectedExp.experiment_id ? updatedExp : x)));
      setShowAttachModal(false);
      setAttachFile(null);
      setAttachNotes("");
    } catch (err: any) {
      alert(`Failed to attach image: ${err.message}`);
    } finally {
      setUploadingImage(false);
    }
  };

  const handleDeleteExpImage = async (imgUrl: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!selectedExp) return;
    if (!window.confirm("Remove this characterization image from the experiment record?")) return;
    try {
      await api.deleteExperimentImage(selectedExp.experiment_id, imgUrl);
      const updatedImages = (selectedExp.characterization_images || []).filter((x) => x.url !== imgUrl);
      const updatedExp = { ...selectedExp, characterization_images: updatedImages };
      setSelectedExp(updatedExp);
      setExperiments(experiments.map((x) => (x.experiment_id === selectedExp.experiment_id ? updatedExp : x)));
    } catch (err: any) {
      alert(`Failed to delete image: ${err.message}`);
    }
  };

  const handleAddDopant = () => {
    if (dopants.some((d) => d.symbol === selectedDopantSymbol)) {
      alert(`Dopant ${selectedDopantSymbol} is already added. Edit its fraction or remove it.`);
      return;
    }
    const catalogItem = ALLOWED_DOPANTS.find((d) => d.symbol === selectedDopantSymbol);
    const oxState = catalogItem ? catalogItem.oxidation_state : 2;
    setDopants([
      ...dopants,
      { symbol: selectedDopantSymbol, fraction: Number(dopantFractionInput), oxidation_state: oxState },
    ]);
  };

  const handleRemoveDopant = (symbol: string) => {
    setDopants(dopants.filter((d) => d.symbol !== symbol));
  };

  const handleUpdateDopantFraction = (symbol: string, newFrac: number) => {
    setDopants(
      dopants.map((d) => (d.symbol === symbol ? { ...d, fraction: Number(newFrac) } : d))
    );
  };

  const handleCreateExperiment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isM2Valid) {
      alert(
        `Chemical stoichiometry constraint violated: M2 site cation sum must equal 1.0000 ± 0.005.\nCurrent sum: Mn(${mnFrac}) + Fe(${feFrac}) + Dopants(${dopantSum.toFixed(4)}) = ${m2Sum.toFixed(4)}.`
      );
      return;
    }

    try {
      const payload: any = {
        sample_id: sampleId,
        operator: operator,
        batch_id: batchId,
        synthesis_route: synthesisRoute,
        mn_frac: mnFrac,
        fe_frac: feFrac,
        dopants: dopants.map((d) => ({
          symbol: d.symbol,
          fraction: Number(d.fraction),
          oxidation_state: d.oxidation_state,
        })),
        carbon_wt_pct: carbonWt,
        status: isPlannedOnly ? "SYNTHESIS_PLANNED" : "ELECTROCHEMICAL_TESTED",
        synthesis_data: {
          calcination_temp_c: calcTemp,
          calcination_duration_h: calcDuration,
          observations: observations,
        },
        characterization_data: {
          impurity_phases: impurityPhases || "None detected (pure olivine)",
        },
      };

      if (!isPlannedOnly) {
        payload.electrochemical_data = {
          initial_discharge_cap: Number(dischargeCap),
          capacity_retention_pct: Number(retentionPct),
          cycle_life_cycles: Number(cycleCount),
        };
        payload.measured_cap_0_1c = Number(dischargeCap);
        payload.measured_retention = Number(retentionPct);
        payload.measured_cycles = Number(cycleCount);
      } else {
        payload.electrochemical_data = null;
      }

      const res = await api.createExperiment(payload);
      setSaveSuccessBanner({
        experimentId: res.experiment_id,
        sampleId: payload.sample_id,
        message: res.message || "Experiment successfully saved to database.",
        timestamp: new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit", hour12: true }),
      });
      setShowForm(false);
      fetchExperiments();
      fetchDbInfo();
    } catch (err: any) {
      alert(`Failed to save experiment: ${err.message}`);
    }
  };

  return (
    <div className="view-container">
      <section className="section-heading">
        <div>
          <h2>Experimental Laboratory Management</h2>
          <p>
            Track synthesis routes, XRD phase characterization, and electrochemical cycling with triple comparison analytics.
          </p>
        </div>
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          {onNavigate && (
            <button className="btn btn-secondary btn-sm" onClick={() => onNavigate("Property Prediction")}>
              ⌁ Back to Simulation
            </button>
          )}
          <button className="btn-primary" onClick={() => setShowForm(!showForm)}>
            {showForm ? "✕ Cancel" : "+ Log New Experiment"}
          </button>
        </div>
      </section>

      {/* Database Connection & File Location Banner */}
      <div
        className="card"
        style={{
          padding: "14px 20px",
          marginBottom: "18px",
          background: "var(--bg-subtle)",
          border: "1px solid var(--border)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "12px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div
            style={{
              width: "36px",
              height: "36px",
              borderRadius: "8px",
              background: "rgba(37, 99, 235, 0.1)",
              color: "var(--primary)",
              display: "grid",
              placeItems: "center",
              fontSize: "18px",
            }}
          >
            💾
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <strong style={{ fontSize: "13.5px", color: "var(--text-main)" }}>
                Database Storage: SQLite File Database
              </strong>
              <span className="badge badge-success">ACTIVE & PERSISTENT</span>
            </div>
            <div
              style={{
                fontSize: "12px",
                color: "var(--text-muted)",
                marginTop: "2px",
                fontFamily: "JetBrains Mono, monospace",
              }}
            >
              File: <strong style={{ color: "var(--text-main)" }}>{dbInfo?.db_path || "data/lab_experiments.db"}</strong> · Table:{" "}
              <strong style={{ color: "var(--text-main)" }}>{dbInfo?.table_name || "lab_experiments"}</strong>
            </div>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "12px", fontSize: "12px" }}>
          <div>
            <span style={{ color: "var(--text-muted)" }}>Saved Trials in DB: </span>
            <strong style={{ color: "var(--primary)", fontSize: "14px" }}>
              {experiments.length}
            </strong>
          </div>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => {
              fetchExperiments();
              fetchDbInfo();
            }}
            title="Refresh experiments from data/lab_experiments.db"
          >
            ↻ Refresh DB
          </button>
        </div>
      </div>

      {/* Save Success Confirmation Banner */}
      {saveSuccessBanner && (
        <div
          style={{
            background: "rgba(16, 185, 129, 0.1)",
            border: "1px solid rgba(16, 185, 129, 0.35)",
            borderRadius: "10px",
            padding: "16px 20px",
            marginBottom: "20px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: "12px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <span style={{ fontSize: "24px" }}>✅</span>
            <div>
              <strong style={{ fontSize: "14px", color: "#065f46", display: "block" }}>
                Experiment Successfully Saved to Database!
              </strong>
              <div style={{ fontSize: "12.5px", color: "#047857", marginTop: "2px" }}>
                Assigned ID: <code style={{ fontWeight: 700 }}>{saveSuccessBanner.experimentId}</code> · Sample:{" "}
                <code style={{ fontWeight: 700 }}>{saveSuccessBanner.sampleId}</code> · Saved to{" "}
                <strong>data/lab_experiments.db</strong> at {saveSuccessBanner.timestamp}
              </div>
            </div>
          </div>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => setSaveSuccessBanner(null)}
          >
            ✕ Dismiss
          </button>
        </div>
      )}

      {/* New Experiment Form */}
      {showForm && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-header">
            <div>
              <h3>Log Laboratory Synthesis & Electrochemical Test</h3>
              <p className="card-subtitle">Record physical synthesis parameters and measured battery performance</p>
            </div>
            <span className="badge badge-purple">Lab Record Ingestion</span>
          </div>

          <form onSubmit={handleCreateExperiment}>
            <div className="form-grid">
              <div className="form-group">
                <label>Sample ID</label>
                <input
                  type="text"
                  required
                  value={sampleId}
                  onChange={(e) => setSampleId(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>Batch ID</label>
                <input
                  type="text"
                  value={batchId}
                  onChange={(e) => setBatchId(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>Operator</label>
                <input
                  type="text"
                  value={operator}
                  onChange={(e) => setOperator(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>Synthesis Route</label>
                <select
                  value={synthesisRoute}
                  onChange={(e) => setSynthesisRoute(e.target.value)}
                >
                  <option value="sol-gel">Sol-Gel Synthesis</option>
                  <option value="solid-state">Solid-State Reaction</option>
                  <option value="co-precipitation">Co-Precipitation</option>
                  <option value="hydrothermal">Hydrothermal / Solvothermal</option>
                </select>
              </div>

              <div className="form-group">
                <label>Calcination Temp (°C)</label>
                <input
                  type="number"
                  value={calcTemp}
                  onChange={(e) => setCalcTemp(parseInt(e.target.value) || 0)}
                />
              </div>

              <div className="form-group">
                <label>Calcination Duration (h)</label>
                <input
                  type="number"
                  step="0.5"
                  value={calcDuration}
                  onChange={(e) => setCalcDuration(parseFloat(e.target.value) || 0)}
                />
              </div>

              <div className="form-group">
                <label>Mn Cation Ratio</label>
                <input
                  type="number"
                  step="0.01"
                  min="0.40"
                  max="0.90"
                  value={mnFrac}
                  onChange={(e) => setMnFrac(parseFloat(e.target.value) || 0)}
                />
              </div>

              <div className="form-group">
                <label>Fe Cation Ratio</label>
                <input
                  type="number"
                  step="0.01"
                  min="0.05"
                  max="0.50"
                  value={feFrac}
                  onChange={(e) => setFeFrac(parseFloat(e.target.value) || 0)}
                />
              </div>

              <div className="form-group">
                <label>Carbon Coating (wt%)</label>
                <input
                  type="number"
                  step="0.1"
                  min="0.0"
                  max="10.0"
                  value={carbonWt}
                  onChange={(e) => setCarbonWt(parseFloat(e.target.value) || 0)}
                />
              </div>

              {/* Dopants Control Box */}
              <div className="form-group span-3" style={{ background: "var(--card-hover-bg, #1a2234)", padding: 14, borderRadius: 8 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                  <label style={{ margin: 0, fontWeight: 600 }}>Cation Dopants (M2 Site Substitution)</label>
                  <span className={`badge ${isM2Valid ? "badge-green" : "badge-amber"}`}>
                    M2 Sum: {m2Sum.toFixed(4)} {isM2Valid ? "(Valid 1.0000 ± 0.005)" : "(Must = 1.0000 ± 0.005)"}
                  </span>
                </div>

                <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 12 }}>
                  <select
                    value={selectedDopantSymbol}
                    onChange={(e) => setSelectedDopantSymbol(e.target.value)}
                    style={{ flex: 1 }}
                  >
                    {ALLOWED_DOPANTS.map((ad) => (
                      <option key={ad.symbol} value={ad.symbol}>
                        {ad.label}
                      </option>
                    ))}
                  </select>
                  <input
                    type="number"
                    step="0.005"
                    min="0.001"
                    max="0.10"
                    placeholder="Fraction (e.g. 0.02)"
                    value={dopantFractionInput}
                    onChange={(e) => setDopantFractionInput(parseFloat(e.target.value) || 0)}
                    style={{ width: 140 }}
                  />
                  <button type="button" className="btn-secondary" onClick={handleAddDopant}>
                    + Add Dopant
                  </button>
                </div>

                {dopants.length === 0 ? (
                  <p className="text-muted" style={{ margin: 0, fontSize: "0.85rem" }}>
                    No dopants configured (undoped baseline composition Li(Mn{mnFrac}Fe{feFrac})PO4).
                  </p>
                ) : (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                    {dopants.map((d) => (
                      <div
                        key={d.symbol}
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 6,
                          background: "var(--bg-card, #232d42)",
                          padding: "4px 10px",
                          borderRadius: 6,
                          fontSize: "0.85rem",
                          border: "1px solid var(--border-color, #334155)",
                        }}
                      >
                        <strong>{d.symbol}</strong>
                        <span>(+{d.oxidation_state}):</span>
                        <input
                          type="number"
                          step="0.005"
                          min="0.001"
                          max="0.10"
                          value={d.fraction}
                          onChange={(e) => handleUpdateDopantFraction(d.symbol, parseFloat(e.target.value) || 0)}
                          style={{ width: 65, padding: "2px 4px", fontSize: "0.8rem" }}
                        />
                        <button
                          type="button"
                          onClick={() => handleRemoveDopant(d.symbol)}
                          style={{ background: "transparent", border: "none", color: "#f87171", cursor: "pointer", fontWeight: "bold" }}
                          title="Remove dopant"
                        >
                          ✕
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Status toggle for planned vs tested */}
              <div className="form-group span-3" style={{ marginTop: 4 }}>
                <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={isPlannedOnly}
                    onChange={(e) => setIsPlannedOnly(e.target.checked)}
                  />
                  <strong>Log as Planned Experiment (Testing Pending / Unperformed)</strong>
                </label>
                <span className="text-muted" style={{ fontSize: "0.85rem", marginLeft: 24, display: "block" }}>
                  When checked, the experiment will be registered with status <code>SYNTHESIS_PLANNED</code> and no electrochemical measurements will be fabricated.
                </span>
              </div>

              {/* Electrochemical Testing Inputs (Only when not planned-only) */}
              {!isPlannedOnly ? (
                <>
                  <div className="form-group">
                    <label>0.1C Discharge Capacity (mAh/g)</label>
                    <input
                      type="number"
                      step="0.1"
                      required={!isPlannedOnly}
                      value={dischargeCap}
                      onChange={(e) => setDischargeCap(parseFloat(e.target.value) || 0)}
                    />
                  </div>

                  <div className="form-group">
                    <label>Capacity Retention (%)</label>
                    <input
                      type="number"
                      step="0.1"
                      required={!isPlannedOnly}
                      value={retentionPct}
                      onChange={(e) => setRetentionPct(parseFloat(e.target.value) || 0)}
                    />
                  </div>

                  <div className="form-group">
                    <label>Cycles Tested</label>
                    <input
                      type="number"
                      value={cycleCount}
                      onChange={(e) => setCycleCount(parseInt(e.target.value) || 0)}
                    />
                  </div>
                </>
              ) : null}

              <div className="form-group span-2">
                <label>XRD Impurity Phases</label>
                <input
                  type="text"
                  value={impurityPhases}
                  onChange={(e) => setImpurityPhases(e.target.value)}
                  placeholder="e.g. None detected / Trace Fe2O3"
                />
              </div>

              <div className="form-group span-3">
                <label>Synthesis Observations</label>
                <input
                  type="text"
                  value={observations}
                  onChange={(e) => setObservations(e.target.value)}
                  placeholder="Physical morphology, tap density, color"
                />
              </div>
            </div>

            <div style={{ marginTop: 16, display: "flex", justifyContent: "flex-end", gap: 10 }}>
              <button type="button" className="btn-secondary" onClick={() => setShowForm(false)}>
                Cancel
              </button>
              <button type="submit" className="btn-primary" disabled={!isM2Valid}>
                Save Experiment
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Onboarding & Empty State when 0 experiments and form is closed */}
      {experiments.length === 0 && !showForm && (
        <div
          className="card"
          style={{
            padding: "32px 36px",
            background: "var(--bg-card)",
            borderRadius: "8px",
            border: "1px solid var(--border)",
            marginBottom: "20px",
          }}
        >
          <div style={{ maxWidth: "750px", marginBottom: "24px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
              <span className="badge badge-purple">LABORATORY STAGING</span>
              <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>Zero-Fabrication Data Protection</span>
            </div>
            <h2 style={{ fontSize: "20px", fontWeight: 700, color: "#ffffff", margin: "0 0 6px" }}>
              Connect In-Silico Cathode Models to Physical Battery Trials
            </h2>
            <p style={{ fontSize: "13px", color: "var(--text-secondary)", margin: 0, lineHeight: "1.5" }}>
              The Experiment Lab tracks synthesis protocols (calcination temperatures, heating durations, precursor salts) and coin-cell electrochemical testing. Your actual physical lab measurements are triangulated against 1,215 curated literature records and ML surrogate predictions to compute capacity residuals.
            </p>
          </div>

          {/* Planned vs Tested Distinction Guide */}
          <div className="grid-2col" style={{ gap: "14px", marginBottom: "24px" }}>
            <div style={{ background: "var(--bg-subtle)", padding: "16px 20px", borderRadius: "10px", border: "1px solid var(--border)" }}>
              <strong style={{ fontSize: "13px", color: "var(--primary)", display: "block", marginBottom: "4px" }}>
                1. Synthesis Planning (Pre-Lab Registration)
              </strong>
              <p style={{ margin: 0, fontSize: "12px", color: "var(--text-secondary)", lineHeight: "1.4" }}>
                Log target stoichiometry, precursor weights, and furnace profiles before synthesis. Registered with status <code>SYNTHESIS_PLANNED</code>; capacity and retention metrics remain strictly <code>Pending (--)</code> with no fabricated values.
              </p>
            </div>

            <div style={{ background: "var(--bg-subtle)", padding: "16px 20px", borderRadius: "10px", border: "1px solid var(--border)" }}>
              <strong style={{ fontSize: "13px", color: "var(--success)", display: "block", marginBottom: "4px" }}>
                2. Electrochemical Validation (Post-Cycling)
              </strong>
              <p style={{ margin: 0, fontSize: "12px", color: "var(--text-secondary)", lineHeight: "1.4" }}>
                Record physical coin-cell cycling data (0.1C discharge capacity, 100-cycle retention, XRD impurity phases) after testing. Automatically updates the Triple Comparison Matrix to reveal model residuals.
              </p>
            </div>
          </div>

          {/* Quick Start Buttons from Pre-Screened Candidates */}
          <div>
            <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-muted)", letterSpacing: "0.5px", display: "block", marginBottom: "10px" }}>
              PLAN AN EXPERIMENTAL BATCH FROM PRE-SCREENED CANDIDATES:
            </span>
            <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => {
                  setShowForm(true);
                  setIsPlannedOnly(true);
                  setSampleId("HE-LMFP-EXP-01");
                  setMnFrac(0.65);
                  setFeFrac(0.26);
                  setDopants([
                    { symbol: "Mg", fraction: 0.02, oxidation_state: 2 },
                    { symbol: "Zn", fraction: 0.02, oxidation_state: 2 },
                    { symbol: "Nb", fraction: 0.01, oxidation_state: 5 },
                    { symbol: "Cu", fraction: 0.02, oxidation_state: 2 },
                    { symbol: "Zr", fraction: 0.02, oxidation_state: 4 },
                  ]);
                }}
              >
                ⚗ Plan 5-Dopant High-Entropy Batch (Mg/Zn/Nb/Cu/Zr) ➔
              </button>

              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => {
                  setShowForm(true);
                  setIsPlannedOnly(true);
                  setSampleId("RATE-LMFP-EXP-02");
                  setMnFrac(0.70);
                  setFeFrac(0.26);
                  setDopants([
                    { symbol: "Mg", fraction: 0.02, oxidation_state: 2 },
                    { symbol: "Ti", fraction: 0.02, oxidation_state: 4 },
                  ]);
                }}
              >
                ⚗ Plan High-Rate Batch (Dual Mg/Ti) ➔
              </button>

              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => {
                  setShowForm(true);
                  setIsPlannedOnly(true);
                  setSampleId("CUSTOM-LMFP-EXP-03");
                  setMnFrac(0.70);
                  setFeFrac(0.30);
                  setDopants([]);
                }}
              >
                + Custom Blank Synthesis Plan
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main Content: Experiment List and Triple Comparison Matrix (Shown when experiments exist) */}
      {experiments.length > 0 && (
      <div className="grid-two-col">
        {/* Left: Logged Experiments */}
        <div className="card">
          <div className="card-header">
            <div>
              <h3>Logged Lab Batches</h3>
              <p className="card-subtitle">Select an experiment to trigger triple comparison</p>
            </div>
            <span className="badge badge-neutral">{experiments.length} Records</span>
          </div>

          {loading ? (
            <div className="loading-state">
              <div className="spinner" />
              <p>Loading experiments...</p>
            </div>
          ) : error ? (
            <div className="error-banner">{error}</div>
          ) : experiments.length === 0 ? (
            <div className="empty-state" style={{ padding: "30px 20px", textAlign: "center" }}>
              <p style={{ color: "var(--muted)", margin: "0 0 12px" }}>
                No laboratory experiments logged in the active database.
              </p>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => {
                  setShowForm(true);
                  setIsPlannedOnly(true);
                  setSampleId("HE-LMFP-EXP-01");
                  setMnFrac(0.65);
                  setFeFrac(0.26);
                  setDopants([
                    { symbol: "Mg", fraction: 0.02, oxidation_state: 2 },
                    { symbol: "Zn", fraction: 0.02, oxidation_state: 2 },
                    { symbol: "Nb", fraction: 0.01, oxidation_state: 5 },
                    { symbol: "Cu", fraction: 0.02, oxidation_state: 2 },
                    { symbol: "Zr", fraction: 0.02, oxidation_state: 4 },
                  ]);
                }}
              >
                + Plan High-Entropy Synthesis Trial
              </button>
            </div>
          ) : (
            <div className="experiment-list">
              {experiments.map((exp) => {
                const isPlanned = exp.status === "SYNTHESIS_PLANNED";
                const capVal = exp.electrochemical_data?.initial_discharge_cap;
                const retVal = exp.electrochemical_data?.capacity_retention_pct;
                return (
                  <div
                    key={exp.experiment_id}
                    className={`experiment-list-item ${
                      selectedExp?.experiment_id === exp.experiment_id ? "active" : ""
                    }`}
                    onClick={() => handleSelectExperiment(exp)}
                  >
                    <div className="exp-item-header">
                      <strong>{exp.sample_id}</strong>
                      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        <span className={`badge ${isPlanned ? "badge-amber" : "badge-green"}`}>
                          {isPlanned ? "Planned (Unperformed)" : exp.status || "Completed"}
                        </span>
                        <button
                          type="button"
                          onClick={(e) => handleDeleteExperiment(exp.experiment_id, exp.sample_id, e)}
                          title="Delete experiment from database"
                          style={{
                            background: "rgba(239, 68, 68, 0.08)",
                            border: "1px solid rgba(239, 68, 68, 0.2)",
                            color: "var(--danger)",
                            cursor: "pointer",
                            fontSize: "11px",
                            padding: "2px 6px",
                            borderRadius: "4px",
                          }}
                        >
                          🗑
                        </button>
                      </div>
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                      <code className="exp-item-formula" style={{ margin: 0 }}>{exp.generated_formula}</code>
                      <span style={{ fontSize: "10.5px", color: "var(--text-muted)", fontFamily: "JetBrains Mono, monospace" }}>
                        {exp.experiment_id}
                      </span>
                    </div>
                    <div className="exp-item-meta">
                      <span>Route: {exp.synthesis_route}</span>
                      <span>
                        0.1C:{" "}
                        <strong>
                          {capVal !== null && capVal !== undefined ? `${capVal} mAh/g` : "Pending"}
                        </strong>
                      </span>
                      <span>
                        Ret:{" "}
                        <strong>
                          {retVal !== null && retVal !== undefined ? `${retVal}%` : "Pending"}
                        </strong>
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right: Triple Comparison Matrix */}
        <div className="card">
          <div className="card-header">
            <div>
              <h3>Triple Comparison Matrix</h3>
              <p className="card-subtitle">Target Design vs. Literature Master vs. Actual Lab Experiment</p>
            </div>
            <span className="badge badge-blue">Triangulation</span>
          </div>

          {loadingComp ? (
            <div className="loading-state">
              <div className="spinner" />
              <p>Computing residuals against 1,215 literature records...</p>
            </div>
          ) : comparisonData ? (
            <div className="comparison-content">
              {/* Formula & Sample info */}
              <div className="comparison-hero">
                <span className="metric-label">ACTIVE SAMPLE UNDER TEST</span>
                <h4>{comparisonData.sample_id}</h4>
                <code>{comparisonData.formula}</code>
              </div>

              {/* Comparison Grid */}
              <div className="matrix-grid">
                <div className="matrix-col target-col">
                  <div className="matrix-col-header">
                    <span className="badge badge-purple">Target Design</span>
                    <h4>Theoretical / In Silico</h4>
                  </div>
                  <div className="matrix-stat">
                    <span>Theoretical Metric</span>
                    <strong>{comparisonData.target_design.theoretical_capacity.toFixed(1)} mAh/g</strong>
                  </div>
                  {comparisonData.target_design.ml_predicted_capacity_0_1c !== null &&
                    comparisonData.target_design.ml_predicted_capacity_0_1c !== undefined && (
                      <div className="matrix-stat">
                        <span>ML Predicted (0.1C)</span>
                        <strong>{comparisonData.target_design.ml_predicted_capacity_0_1c.toFixed(1)} mAh/g</strong>
                      </div>
                    )}
                  {comparisonData.target_design.ml_predicted_retention !== null &&
                    comparisonData.target_design.ml_predicted_retention !== undefined && (
                      <div className="matrix-stat">
                        <span>ML Predicted Ret</span>
                        <strong>{comparisonData.target_design.ml_predicted_retention.toFixed(1)}%</strong>
                      </div>
                    )}
                  <div className="matrix-stat">
                    <span>Target Retention</span>
                    <strong>{comparisonData.target_design.target_retention.toFixed(1)}%</strong>
                  </div>
                </div>

                <div className="matrix-col lit-col">
                  <div className="matrix-col-header">
                    <span className="badge badge-blue">Literature Master</span>
                    <h4>Corpus Baseline (N={comparisonData.literature_baseline.sample_count})</h4>
                  </div>
                  <div className="matrix-stat">
                    <span>Avg Discharge Cap</span>
                    <strong>{comparisonData.literature_baseline.avg_discharge_cap.toFixed(1)} mAh/g</strong>
                  </div>
                  <div className="matrix-stat">
                    <span>Avg Retention</span>
                    <strong>{comparisonData.literature_baseline.avg_retention.toFixed(1)}%</strong>
                  </div>
                  <div className="matrix-stat">
                    <span>Reference Scope</span>
                    <strong>Similar Mn/Fe ratio</strong>
                  </div>
                </div>

                {(() => {
                  const isPerformed =
                    comparisonData.actual_experiment?.is_performed &&
                    comparisonData.status !== "SYNTHESIS_PLANNED";
                  const measCap = comparisonData.actual_experiment?.measured_discharge_cap;
                  const measRet = comparisonData.actual_experiment?.measured_retention;
                  const phases = comparisonData.actual_experiment?.impurity_phases;

                  return (
                    <div className="matrix-col lab-col">
                      <div className="matrix-col-header">
                        <span className={`badge ${isPerformed ? "badge-green" : "badge-amber"}`}>
                          {isPerformed ? "Lab Experiment" : "Proposed / Pending"}
                        </span>
                        <h4>{isPerformed ? "Actual Measured" : "Pending Physical Synthesis"}</h4>
                      </div>
                      <div className="matrix-stat">
                        <span>Measured Capacity</span>
                        {measCap !== null && measCap !== undefined ? (
                          <strong>{measCap.toFixed(1)} mAh/g</strong>
                        ) : (
                          <span className="text-muted">Pending Physical Synthesis</span>
                        )}
                      </div>
                      <div className="matrix-stat">
                        <span>Measured Retention</span>
                        {measRet !== null && measRet !== undefined ? (
                          <strong>{measRet.toFixed(1)}%</strong>
                        ) : (
                          <span className="text-muted">Pending Battery Cycling</span>
                        )}
                      </div>
                      <div className="matrix-stat">
                        <span>XRD Phases</span>
                        {phases ? (
                          <strong>{phases}</strong>
                        ) : (
                          <span className="text-muted">Awaiting Characterization</span>
                        )}
                      </div>
                    </div>
                  );
                })()}
              </div>

              {/* Residuals Summary */}
              {(() => {
                const capDelta = comparisonData.residuals?.capacity_vs_lit_delta;
                const retDelta = comparisonData.residuals?.retention_vs_lit_delta;

                if (capDelta !== null && capDelta !== undefined && retDelta !== null && retDelta !== undefined) {
                  return (
                    <div className="residuals-box" style={{ marginTop: 18 }}>
                      <span className="metric-label">RESIDUAL ANALYSIS (MEASURED VS. LITERATURE BASELINE)</span>
                      <div className="residual-item">
                        <span>Capacity Residual:</span>
                        <strong className={capDelta >= 0 ? "text-success" : "text-danger"}>
                          {capDelta >= 0 ? "+" : ""}
                          {capDelta.toFixed(1)} mAh/g
                        </strong>
                      </div>
                      <div className="residual-item">
                        <span>Retention Residual:</span>
                        <strong className={retDelta >= 0 ? "text-success" : "text-danger"}>
                          {retDelta >= 0 ? "+" : ""}
                          {retDelta.toFixed(1)}%
                        </strong>
                      </div>
                    </div>
                  );
                }

                return (
                  <div className="residuals-box" style={{ marginTop: 18 }}>
                    <span className="metric-label">RESIDUAL ANALYSIS</span>
                    <div className="notice-box" style={{ marginTop: 8 }}>
                      <p style={{ margin: 0 }}>
                        <strong>Residuals Pending:</strong> Physical experimental measurements have not yet been recorded for this experiment batch (status: <code>{comparisonData.status || "SYNTHESIS_PLANNED"}</code>). Residual analysis will be calculated upon entry of actual experimental battery cycling data.
                      </p>
                    </div>
                  </div>
                );
              })()}

              {/* Characterization Gallery (XRD / SEM / TEM) */}
              <div style={{ marginTop: 24, paddingTop: 18, borderTop: "1px solid var(--border)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
                  <div>
                    <span className="metric-label">CHARACTERIZATION MICROGRAPHS &amp; XRD</span>
                    <h4 style={{ margin: "2px 0 0", fontSize: "15px", color: "var(--text-main)" }}>
                      Physical Evidence &amp; Characterization ({selectedExp?.characterization_images?.length || 0})
                    </h4>
                  </div>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => setShowAttachModal(true)}
                    style={{ fontSize: "12.5px", borderRadius: "9999px" }}
                  >
                    + Attach Micrograph / XRD
                  </button>
                </div>

                {(!selectedExp?.characterization_images || selectedExp.characterization_images.length === 0) ? (
                  <div
                    style={{
                      padding: "18px 20px",
                      background: "var(--bg-subtle)",
                      borderRadius: "8px",
                      border: "1px dashed var(--border)",
                      textAlign: "center",
                      color: "var(--text-muted)",
                      fontSize: "13px",
                    }}
                  >
                    No characterization images attached yet. Attach SEM/TEM micrographs or XRD diffraction patterns to verify particle morphology and phase purity.
                  </div>
                ) : (
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 12 }}>
                    {selectedExp.characterization_images.map((img, idx) => (
                      <div
                        key={idx}
                        className="card"
                        style={{
                          padding: "8px",
                          borderRadius: "8px",
                          border: "1px solid var(--border)",
                          overflow: "hidden",
                          position: "relative",
                        }}
                      >
                        <div
                          style={{
                            height: "120px",
                            borderRadius: "6px",
                            overflow: "hidden",
                            background: "#0f172a",
                            cursor: "pointer",
                            marginBottom: "8px",
                          }}
                          onClick={() => setEnlargedImage(img.url)}
                          title="Click to enlarge"
                        >
                          <img
                            src={img.url}
                            alt={img.original_filename || "Micrograph"}
                            style={{ width: "100%", height: "100%", objectFit: "cover" }}
                          />
                        </div>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <span
                            className="badge badge-purple"
                            style={{ fontSize: "10.5px", padding: "1px 6px" }}
                          >
                            {img.image_type || "Micrograph"}
                          </span>
                          <button
                            type="button"
                            onClick={(e) => handleDeleteExpImage(img.url, e)}
                            title="Remove image"
                            style={{
                              background: "none",
                              border: "none",
                              color: "#ef4444",
                              cursor: "pointer",
                              fontSize: "12px",
                              padding: "2px",
                            }}
                          >
                            ✕
                          </button>
                        </div>
                        <div
                          style={{
                            fontSize: "11px",
                            color: "var(--text-muted)",
                            marginTop: "4px",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                          }}
                          title={img.original_filename}
                        >
                          {img.original_filename}
                        </div>
                        {img.notes && (
                          <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "2px" }}>
                            {img.notes}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="empty-state">
              <p>Select an experiment to inspect the triple comparison matrix.</p>
            </div>
          )}
        </div>
      </div>
      )}

      {/* Attach Micrograph Modal */}
      {showAttachModal && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(0, 0, 0, 0.6)",
            zIndex: 9999,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "20px",
          }}
          onClick={() => setShowAttachModal(false)}
        >
          <div
            className="card"
            style={{
              maxWidth: "460px",
              width: "100%",
              padding: "24px",
              borderRadius: "12px",
              backgroundColor: "#ffffff",
              boxShadow: "0 20px 40px rgba(0,0,0,0.2)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <h3 style={{ margin: 0, fontSize: "18px", color: "#0f172a" }}>Attach Characterization Image</h3>
              <button
                type="button"
                onClick={() => setShowAttachModal(false)}
                style={{ background: "none", border: "none", fontSize: "18px", cursor: "pointer", color: "var(--text-muted)" }}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleUploadImageToExperiment}>
              <div className="form-group" style={{ marginBottom: "14px" }}>
                <label style={{ fontSize: "13px", fontWeight: 600, color: "#0f172a" }}>Select Image File (Max 25MB)</label>
                <input
                  type="file"
                  required
                  accept=".png,.jpg,.jpeg,.webp,.tiff,.tif"
                  onChange={(e) => setAttachFile(e.target.files?.[0] || null)}
                  style={{ width: "100%", padding: "8px", fontSize: "13px" }}
                />
              </div>

              <div className="form-group" style={{ marginBottom: "14px" }}>
                <label style={{ fontSize: "13px", fontWeight: 600, color: "#0f172a" }}>Image Category</label>
                <select
                  value={attachType}
                  onChange={(e) => setAttachType(e.target.value)}
                  style={{ width: "100%", padding: "8px", fontSize: "13px", borderRadius: "6px", border: "1px solid var(--border)" }}
                >
                  <option value="SEM Micrograph">SEM Micrograph (Particle Morphology)</option>
                  <option value="XRD Pattern">XRD Pattern (Phase Purity)</option>
                  <option value="TEM Analysis">TEM Analysis (Atomic Resolution / Lattice Fringes)</option>
                  <option value="Electrode Photo">Electrode / Calendered Foil Photo</option>
                  <option value="EIS Nyquist Plot">EIS Nyquist Plot</option>
                </select>
              </div>

              <div className="form-group" style={{ marginBottom: "18px" }}>
                <label style={{ fontSize: "13px", fontWeight: 600, color: "#0f172a" }}>Notes / Instrument Conditions</label>
                <input
                  type="text"
                  placeholder="e.g. 5kV accelerating voltage, 20k magnification, spherical morphology"
                  value={attachNotes}
                  onChange={(e) => setAttachNotes(e.target.value)}
                  style={{ width: "100%", padding: "8px", fontSize: "13px", borderRadius: "6px", border: "1px solid var(--border)" }}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowAttachModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={!attachFile || uploadingImage}
                >
                  {uploadingImage ? "Uploading..." : "Upload & Attach"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Enlarged Image Modal */}
      {enlargedImage && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(0, 0, 0, 0.8)",
            zIndex: 10000,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "24px",
          }}
          onClick={() => setEnlargedImage(null)}
        >
          <div
            style={{
              position: "relative",
              maxWidth: "90vw",
              maxHeight: "90vh",
              backgroundColor: "#ffffff",
              borderRadius: "12px",
              padding: "16px",
              boxShadow: "0 25px 60px rgba(0,0,0,0.5)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <button
              type="button"
              onClick={() => setEnlargedImage(null)}
              style={{
                position: "absolute",
                top: "-12px",
                right: "-12px",
                width: "32px",
                height: "32px",
                borderRadius: "50%",
                backgroundColor: "#0f172a",
                color: "#ffffff",
                fontSize: "16px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                cursor: "pointer",
                border: "2px solid #ffffff",
              }}
            >
              ✕
            </button>
            <img
              src={enlargedImage}
              alt="Enlarged characterization micrograph"
              style={{ maxWidth: "85vw", maxHeight: "80vh", objectFit: "contain", borderRadius: "8px", display: "block" }}
            />
          </div>
        </div>
      )}
    </div>
  );
};
