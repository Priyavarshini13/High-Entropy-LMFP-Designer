import React, { useEffect, useState } from "react";
import {
  api,
  type ReviewRecord,
  type ExportPreview,
  type PdfExtractionResponse,
  type MaterialSampleEntity,
} from "../api";

export const LiteratureIntelligenceView: React.FC = () => {
  const [reviews, setReviews] = useState<ReviewRecord[]>([]);
  const [activeTab, setActiveTab] = useState<"all" | "pending" | "approved" | "rejected">("pending");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Main view toggle: Review Queue vs Sample Entity Graph
  const [mainView, setMainView] = useState<"queue" | "entity_graph">("queue");

  // Stage 4 Sample Entity Graph state
  const [samples, setSamples] = useState<MaterialSampleEntity[]>([]);
  const [samplesLoading, setSamplesLoading] = useState(false);
  const [sampleDopantFilter, setSampleDopantFilter] = useState("");
  const [sampleMinCrateFilter, setSampleMinCrateFilter] = useState("");
  const [selectedSample, setSelectedSample] = useState<MaterialSampleEntity | null>(null);

  // Sample disambiguation edit state
  const [editSampleLabel, setEditSampleLabel] = useState("");
  const [editSampleResStatus, setEditSampleResStatus] = useState("");
  const [editSampleResNotes, setEditSampleResNotes] = useState("");
  const [editSampleIsUnresolved, setEditSampleIsUnresolved] = useState(false);
  const [sampleUpdateLoading, setSampleUpdateLoading] = useState(false);

  // PDF Upload states (7-stage state machine: idle | selected | uploading | processing | completed | partial | error)
  const [uploadStatus, setUploadStatus] = useState<
    "idle" | "selected" | "uploading" | "processing" | "completed" | "partial" | "error"
  >("idle");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadResult, setUploadResult] = useState<PdfExtractionResponse | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadErrorDetails, setUploadErrorDetails] = useState<string | null>(null);

  // Selected review for editing / verification
  const [selectedReview, setSelectedReview] = useState<ReviewRecord | null>(null);
  const [editPaperDoi, setEditPaperDoi] = useState("");
  const [editPaperTitle, setEditPaperTitle] = useState("");
  const [editPaperId, setEditPaperId] = useState("");
  const [editSampleId, setEditSampleId] = useState("");
  const [editTableFigure, setEditTableFigure] = useState("");
  const [editCap01, setEditCap01] = useState("");
  const [editCap1, setEditCap1] = useState("");
  const [editCap5, setEditCap5] = useState("");
  const [editRetention, setEditRetention] = useState("");
  const [editRetentionCycles, setEditRetentionCycles] = useState("");
  const [editRetentionCrate, setEditRetentionCrate] = useState("");
  const [editEvidence, setEditEvidence] = useState("");

  // Export preview drawer state
  const [showExportDrawer, setShowExportDrawer] = useState(false);
  const [exportPreview, setExportPreview] = useState<ExportPreview | null>(null);
  const [exportLoading, setExportLoading] = useState(false);
  const [exportMsg, setExportMsg] = useState<string | null>(null);

  // Supporting Characterization Figure Upload State
  const [showSupportingUpload, setShowSupportingUpload] = useState(false);
  const [suppFile, setSuppFile] = useState<File | null>(null);
  const [suppPaperId, setSuppPaperId] = useState<string>("");
  const [suppDocType, setSuppDocType] = useState<string>("Supporting Characterization / XRD / SEM");
  const [suppUploading, setSuppUploading] = useState<boolean>(false);
  const [suppSuccessMsg, setSuppSuccessMsg] = useState<string | null>(null);

  const fetchReviews = () => {
    setLoading(true);
    api
      .getReviews(activeTab === "all" ? undefined : activeTab)
      .then((data) => {
        setReviews(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "Failed to load literature reviews");
        setLoading(false);
      });
  };

  const handleUploadSupporting = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!suppFile) return;
    setSuppUploading(true);
    setSuppSuccessMsg(null);
    try {
      const res = await api.uploadLiteratureSupporting(suppFile, suppPaperId, suppDocType);
      setSuppSuccessMsg(`Successfully uploaded ${res.original_filename} (${res.doc_type}) to literature repository.`);
      setSuppFile(null);
      setSuppPaperId("");
    } catch (err: any) {
      alert(`Supporting upload error: ${err.message}`);
    } finally {
      setSuppUploading(false);
    }
  };

  useEffect(() => {
    fetchReviews();
  }, [activeTab]);

  const fetchSamples = () => {
    setSamplesLoading(true);
    const minCrateVal = sampleMinCrateFilter ? parseFloat(sampleMinCrateFilter) : undefined;
    api
      .getMaterialSamples({
        dopant: sampleDopantFilter || undefined,
        min_crate: isNaN(minCrateVal as number) ? undefined : minCrateVal,
      })
      .then((data) => {
        setSamples(data);
        setSamplesLoading(false);
      })
      .catch((err) => {
        console.error("Failed to load material samples:", err);
        setSamplesLoading(false);
      });
  };

  useEffect(() => {
    fetchSamples();
  }, [sampleDopantFilter, sampleMinCrateFilter]);

  const handleOpenSampleModal = (sample: MaterialSampleEntity) => {
    setSelectedSample(sample);
    setEditSampleLabel(sample.sample_label);
    setEditSampleResStatus(sample.resolution_status);
    setEditSampleResNotes(sample.resolution_notes || "");
    setEditSampleIsUnresolved(sample.is_unresolved);
  };

  const handleSaveSampleResolution = async () => {
    if (!selectedSample) return;
    setSampleUpdateLoading(true);
    try {
      await api.resolveMaterialSample(selectedSample.sample_id, {
        sample_label: editSampleLabel,
        resolution_status: editSampleResStatus,
        resolution_notes: editSampleResNotes,
        is_unresolved: editSampleIsUnresolved,
      });
      setSelectedSample(null);
      fetchSamples();
    } catch (err: any) {
      alert(`Error updating sample resolution: ${err.message}`);
    } finally {
      setSampleUpdateLoading(false);
    }
  };

  const handleSelectReview = (rev: ReviewRecord) => {
    setSelectedReview(rev);
    const data = rev.extracted_data || {};
    setEditPaperDoi(data.verified_doi || data.doi || "");
    setEditPaperTitle(data.verified_title || data.title || "");
    setEditPaperId(data.verified_paper_id || data.paper_id || "");
    setEditSampleId(data.verified_sample_id || data.sample_id || "");
    setEditTableFigure(data.source_table_figure || "");
    setEditCap01(data.discharge_capacity_0_1c?.toString() || "");
    setEditCap1(data.discharge_capacity_1c?.toString() || "");
    setEditCap5(data.discharge_capacity_5c?.toString() || "");
    setEditRetention(data.capacity_retention_percent?.toString() || "");
    setEditRetentionCycles(data.retention_cycles?.toString() || "");
    setEditRetentionCrate(data.retention_crate?.toString() || "");
    setEditEvidence(rev.evidence_quote || data.evidence_quote || "");
  };

  const handleSaveReviewStatus = async (status: "approved" | "rejected" | "pending") => {
    if (!selectedReview) return;
    try {
      const updatedData = {
        ...selectedReview.extracted_data,
        verified_doi: editPaperDoi,
        verified_title: editPaperTitle,
        verified_paper_id: editPaperId,
        verified_sample_id: editSampleId,
        source_table_figure: editTableFigure,
        discharge_capacity_0_1c: editCap01 ? parseFloat(editCap01) : null,
        discharge_capacity_1c: editCap1 ? parseFloat(editCap1) : null,
        discharge_capacity_5c: editCap5 ? parseFloat(editCap5) : null,
        capacity_retention_percent: editRetention ? parseFloat(editRetention) : null,
        retention_cycles: editRetentionCycles ? parseInt(editRetentionCycles) : null,
        retention_crate: editRetentionCrate ? parseFloat(editRetentionCrate) : null,
        evidence_quote: editEvidence,
      };

      await api.updateReview(selectedReview.id, status, updatedData);
      setSelectedReview(null);
      fetchReviews();
    } catch (err: any) {
      alert(`Error updating review: ${err.message}`);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (!bytes || bytes <= 0) return "0 B";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setUploadStatus("error");
      setUploadError("Unsupported file format.");
      setUploadErrorDetails("Only PDF documents (.pdf) are supported. Please select a valid peer-reviewed paper PDF.");
      setSelectedFile(null);
      return;
    }

    if (file.size === 0) {
      setUploadStatus("error");
      setUploadError("Empty file.");
      setUploadErrorDetails("The selected file is 0 bytes. Please provide a valid PDF document with readable content.");
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
    setUploadStatus("selected");
    setUploadError(null);
    setUploadErrorDetails(null);
    setUploadResult(null);
  };

  const handleStartExtraction = async () => {
    if (!selectedFile) return;
    setUploadStatus("uploading");
    setUploadError(null);
    setUploadErrorDetails(null);

    // Transition to processing state shortly after start
    const timer = setTimeout(() => {
      setUploadStatus((prev) => (prev === "uploading" ? "processing" : prev));
    }, 500);

    try {
      const res = await api.uploadPdf(selectedFile);
      clearTimeout(timer);
      setUploadResult(res);

      if (res.status === "no_records_found") {
        setUploadStatus("error");
        setUploadError(res.message);
        setUploadErrorDetails(res.suggested_next_action);
      } else if (res.status === "partial_extraction") {
        setUploadStatus("partial");
        setActiveTab("pending");
        fetchReviews();
      } else {
        setUploadStatus("completed");
        setActiveTab("pending");
        fetchReviews();
      }
    } catch (err: any) {
      clearTimeout(timer);
      setUploadStatus("error");
      setUploadError(err.message || "Failed to process PDF.");
      setUploadErrorDetails("Check that the PDF is not password protected, corrupted, or scanned without selectable text.");
    }
  };

  const handleResetUpload = () => {
    setSelectedFile(null);
    setUploadStatus("idle");
    setUploadResult(null);
    setUploadError(null);
    setUploadErrorDetails(null);
  };

  const handleInspectSavedReview = async (reviewId: number) => {
    const found = reviews.find((r) => r.id === reviewId);
    if (found) {
      handleSelectReview(found);
      return;
    }
    try {
      const rev = await api.getReview(reviewId);
      if (rev) {
        handleSelectReview(rev);
      }
    } catch (err: any) {
      alert(`Could not open review #${reviewId}: ${err.message}`);
    }
  };

  const handleOpenExportPreview = async () => {
    setShowExportDrawer(true);
    setExportLoading(true);
    setExportMsg(null);
    try {
      const preview = await api.getExportPreview();
      setExportPreview(preview);
    } catch (err: any) {
      setExportMsg(`Failed to load export preview: ${err.message}`);
    } finally {
      setExportLoading(false);
    }
  };

  const handleRunExport = async (dryRun: boolean) => {
    try {
      const res = await api.executeExport(dryRun);
      setExportMsg(res.message);
      // Refresh preview
      const preview = await api.getExportPreview();
      setExportPreview(preview);
    } catch (err: any) {
      setExportMsg(`Export failed: ${err.message}`);
    }
  };

  return (
    <div className="view-container">
      <section className="section-heading" style={{ marginBottom: "16px" }}>
        <div>
          <h2>Literature Evidence</h2>
          <p>Curate extracted LMFP research papers, inspect evidence quotes, and verify data before master corpus integration.</p>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <button
            className="btn-secondary btn-sm"
            onClick={() => setShowSupportingUpload(!showSupportingUpload)}
          >
            {showSupportingUpload ? "✕ Close Supporting Upload" : "📎 Upload Characterization Figures / XRD"}
          </button>
          <button className="btn-secondary btn-sm" onClick={handleOpenExportPreview}>
            🛡️ Export Guardrails Preview
          </button>
        </div>
      </section>

      {/* Optional Supporting Characterization Upload Card */}
      {showSupportingUpload && (
        <div className="card" style={{ marginBottom: 20, padding: "20px 24px", border: "1px solid #bfdbfe", background: "#f8fafc" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
            <div>
              <h3 style={{ margin: 0, fontSize: "16px", color: "var(--text-main)" }}>
                Upload Supporting Characterization Micrograph / XRD Figure
              </h3>
              <p className="card-subtitle" style={{ margin: "2px 0 0" }}>
                Attach supplementary XRD patterns, SEM micrographs, TEM lattice images, or EDS chemical maps to literature corpus.
              </p>
            </div>
            <span className="badge badge-purple">SUPPLEMENTARY DATA</span>
          </div>

          {suppSuccessMsg && (
            <div style={{ padding: "8px 12px", background: "#ecfdf5", border: "1px solid #a7f3d0", color: "#065f46", borderRadius: "6px", fontSize: "13px", marginBottom: "12px" }}>
              ✓ {suppSuccessMsg}
            </div>
          )}

          <form onSubmit={handleUploadSupporting} style={{ display: "flex", flexWrap: "wrap", gap: "12px", alignItems: "flex-end" }}>
            <div style={{ flex: 1, minWidth: "220px" }}>
              <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-muted)", display: "block", marginBottom: "4px" }}>
                Select Image or Document (PNG, JPG, TIFF, PDF - Max 25MB)
              </label>
              <input
                type="file"
                required
                accept=".png,.jpg,.jpeg,.webp,.tiff,.tif,.pdf"
                onChange={(e) => setSuppFile(e.target.files?.[0] || null)}
                style={{ width: "100%", padding: "6px", fontSize: "13px" }}
              />
            </div>

            <div style={{ width: "200px" }}>
              <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-muted)", display: "block", marginBottom: "4px" }}>
                Associated Paper ID / DOI
              </label>
              <input
                type="text"
                placeholder="e.g. srep26686 / 10.1038/..."
                value={suppPaperId}
                onChange={(e) => setSuppPaperId(e.target.value)}
                style={{ width: "100%", padding: "6px", fontSize: "13px", borderRadius: "6px", border: "1px solid var(--border)" }}
              />
            </div>

            <div style={{ width: "220px" }}>
              <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-muted)", display: "block", marginBottom: "4px" }}>
                Figure / Data Category
              </label>
              <select
                value={suppDocType}
                onChange={(e) => setSuppDocType(e.target.value)}
                style={{ width: "100%", padding: "6px", fontSize: "13px", borderRadius: "6px", border: "1px solid var(--border)" }}
              >
                <option value="Supporting Characterization / XRD / SEM">Supporting Characterization (XRD/SEM)</option>
                <option value="High-Resolution TEM Micrograph">High-Resolution TEM Micrograph</option>
                <option value="Electrode Cross-Section SEM">Electrode Cross-Section SEM</option>
                <option value="Supplementary Information PDF">Supplementary Information PDF</option>
              </select>
            </div>

            <div>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={!suppFile || suppUploading}
                style={{ padding: "8px 18px", fontSize: "13px", borderRadius: "6px" }}
              >
                {suppUploading ? "Uploading..." : "Upload Characterization"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* PDF Uploader Card */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <div>
            <h3>Upload Peer-Reviewed PDF for Automated Extraction</h3>
            <p className="card-subtitle">
              Extracts chemical stoichiometry, elemental dopants, discharge capacities, and cycle retention into the review queue.
            </p>
          </div>
          <span className="badge badge-purple">AI / Parser Ingestion</span>
        </div>

        {/* State 1: IDLE */}
        {uploadStatus === "idle" && (
          <div className="upload-dropzone">
            <input
              type="file"
              accept=".pdf"
              id="pdf-upload"
              style={{ display: "none" }}
              onChange={handleFileSelect}
            />
            <label htmlFor="pdf-upload" className="upload-label">
              <span className="upload-icon">📄</span>
              <strong>Choose a Research Paper PDF</strong>
              <span>Click or select a .pdf file (extracts stoichiometry, dopants, capacities, and evidence quotes)</span>
            </label>
          </div>
        )}

        {/* State 2: SELECTED */}
        {uploadStatus === "selected" && selectedFile && (
          <div className="upload-selected-card">
            <div className="upload-selected-info">
              <span className="upload-selected-icon">📄</span>
              <div>
                <span className="upload-selected-name">{selectedFile.name}</span>
                <span className="upload-selected-size">{formatFileSize(selectedFile.size)}</span>
                <div style={{ fontSize: 11, color: "#64748b", marginTop: 4 }}>
                  Ready for automated extraction. Click "Extract LMFP Data" to begin.
                </div>
              </div>
            </div>
            <div className="upload-actions">
              <button className="btn-primary" onClick={handleStartExtraction}>
                🚀 Extract LMFP Data
              </button>
              <button className="btn-secondary" onClick={handleResetUpload}>
                Cancel / Change File
              </button>
            </div>
          </div>
        )}

        {/* State 3: UPLOADING */}
        {uploadStatus === "uploading" && (
          <div className="upload-progress-card">
            <div className="spinner" />
            <div className="upload-progress-title">Uploading Document...</div>
            <div className="upload-progress-desc">
              Transferring <strong>{selectedFile?.name}</strong> ({formatFileSize(selectedFile?.size || 0)}) to the extraction pipeline.
            </div>
          </div>
        )}

        {/* State 4: PROCESSING */}
        {uploadStatus === "processing" && (
          <div className="upload-progress-card">
            <div className="spinner" />
            <div className="upload-progress-title">Analyzing Research Paper...</div>
            <div className="upload-progress-desc">
              Reading PDF pages, locating candidate sections, parsing doping tables, and extracting LMFP electrochemical parameters...
            </div>
          </div>
        )}

        {/* State 5 & 6: COMPLETED or PARTIAL */}
        {(uploadStatus === "completed" || uploadStatus === "partial") && uploadResult && (
          <div className="upload-results-card">
            <div className="upload-results-header">
              <h4>
                {uploadStatus === "completed" ? "✅ Extraction Completed" : "⚠️ Partial Extraction Completed"}
                <span
                  className={`badge ${uploadStatus === "completed" ? "badge-green" : "badge-amber"}`}
                  style={{ marginLeft: 8 }}
                >
                  {uploadResult.status.toUpperCase()}
                </span>
              </h4>
              <button className="btn-secondary btn-sm" onClick={handleResetUpload}>
                Upload Another PDF
              </button>
            </div>

            <div className="upload-metrics-grid">
              <div className="metric-pill">
                <div className="metric-pill-val">{uploadResult.total_pages}</div>
                <div className="metric-pill-lbl">Total Pages</div>
              </div>
              <div className="metric-pill">
                <div className="metric-pill-val">{uploadResult.pages_with_text}</div>
                <div className="metric-pill-lbl">Pages with Text</div>
              </div>
              <div className="metric-pill">
                <div className="metric-pill-val">{uploadResult.candidate_pages_count}</div>
                <div className="metric-pill-lbl">Candidate Pages</div>
              </div>
              <div className="metric-pill">
                <div className="metric-pill-val" style={{ color: "#2563eb" }}>
                  {uploadResult.records_extracted}
                </div>
                <div className="metric-pill-lbl">Records Extracted</div>
              </div>
              <div className="metric-pill">
                <div className="metric-pill-val" style={{ color: "#16a34a" }}>
                  {uploadResult.saved_reviews_count}
                </div>
                <div className="metric-pill-lbl">Staged to Queue</div>
              </div>
            </div>

            {uploadResult.warnings && uploadResult.warnings.length > 0 && (
              <div className="upload-warnings-box">
                <strong>Attention Required:</strong>
                <ul style={{ margin: "4px 0 0 16px", padding: 0 }}>
                  {uploadResult.warnings.map((w, idx) => (
                    <li key={idx}>{w}</li>
                  ))}
                </ul>
              </div>
            )}

            {uploadResult.suggested_next_action && (
              <div className="upload-next-action-box">
                <strong>Suggested Next Action:</strong> {uploadResult.suggested_next_action}
              </div>
            )}

            {uploadResult.saved_reviews && uploadResult.saved_reviews.length > 0 && (
              <div className="upload-reviews-staged">
                <div className="upload-reviews-staged-title">
                  Staged Review Records (Click to inspect and verify in modal):
                </div>
                <div className="review-inspect-chips">
                  {uploadResult.saved_reviews.map((sr) => (
                    <button
                      key={sr.id}
                      className="review-inspect-chip"
                      onClick={() => handleInspectSavedReview(sr.id)}
                      title={`Open Reviewer Disambiguation Modal for Review #${sr.id}`}
                    >
                      🔍 Inspect #{sr.id}: <code>{sr.composition}</code> (p. {sr.page})
                      {sr.is_new ? (
                        <span style={{ fontSize: 10, background: "#10b981", color: "#fff", padding: "1px 5px", borderRadius: 8, marginLeft: 4 }}>
                          NEW
                        </span>
                      ) : (
                        <span style={{ fontSize: 10, background: "#6b7280", color: "#fff", padding: "1px 5px", borderRadius: 8, marginLeft: 4 }}>
                          {sr.status}
                        </span>
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {uploadResult.detected_sections && uploadResult.detected_sections.length > 0 && (
              <div className="candidate-pages-preview" style={{ marginBottom: 8 }}>
                <strong>Document Zones Detected: </strong>
                {uploadResult.detected_sections.map((sec) => (
                  <span
                    key={sec}
                    className="candidate-page-tag"
                    style={{
                      background: sec === "EXPERIMENTAL" || sec === "RESULTS_DISCUSSION" ? "#dcfce7" : "#f1f5f9",
                      borderColor: sec === "EXPERIMENTAL" || sec === "RESULTS_DISCUSSION" ? "#86efac" : "#e2e8f0",
                      color: sec === "EXPERIMENTAL" || sec === "RESULTS_DISCUSSION" ? "#166534" : "#475569",
                      fontWeight: 600,
                    }}
                  >
                    {sec}
                  </span>
                ))}
              </div>
            )}

            {uploadResult.background_mentions_count && uploadResult.background_mentions_count > 0 ? (
              <div
                style={{
                  fontSize: 11,
                  color: "#0369a1",
                  background: "#f0f9ff",
                  padding: "6px 10px",
                  borderRadius: 6,
                  border: "1px solid #bae6fd",
                  marginBottom: 8,
                }}
              >
                ℹ️ <strong>Prior-Work Citations:</strong> Preserved {uploadResult.background_mentions_count} background literature mentions from Introduction/Abstract. Excluded from primary experimental sample creation.
              </div>
            ) : null}

            {uploadResult.property_summary && (
              <div
                style={{
                  background: "#f0fdf4",
                  color: "#166534",
                  fontSize: 12,
                  padding: "6px 10px",
                  borderRadius: 6,
                  border: "1px solid #bbf7d0",
                  marginBottom: 8,
                }}
              >
                🔬 <strong>Extracted Electrochemical Properties:</strong>{" "}
                {uploadResult.property_summary.total_measurements} measurements ({uploadResult.property_summary.capacities_count} capacities, {uploadResult.property_summary.retentions_count} retentions), {uploadResult.property_summary.synthesis_profiles_count} synthesis profiles, {uploadResult.property_summary.characterization_profiles_count} characterization profiles.
              </div>
            )}

            {uploadResult.resolved_samples_count && uploadResult.resolved_samples_count > 0 ? (
              <div
                style={{
                  background: "#eff6ff",
                  color: "#1e40af",
                  fontSize: 12,
                  padding: "6px 10px",
                  borderRadius: 6,
                  border: "1px solid #bfdbfe",
                  marginBottom: 8,
                }}
              >
                🔬 <strong>Material Sample Entities:</strong> Resolved{" "}
                {uploadResult.resolved_samples_count} material samples with explicit author labels, precursor profiles, and linked measurements.
              </div>
            ) : null}

            {uploadResult.candidate_pages && uploadResult.candidate_pages.length > 0 && (
              <div className="candidate-pages-preview">
                <strong>Candidate Pages Detected: </strong>
                {uploadResult.candidate_pages.map((cp) => (
                  <span key={cp.page} className="candidate-page-tag" title={cp.snippet}>
                    Page {cp.page}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {/* State 7: ERROR / REJECTED */}
        {uploadStatus === "error" && (
          <div className="upload-error-box">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <div className="upload-error-title">❌ PDF Processing / Extraction Issue</div>
                <div className="upload-error-desc">{uploadError}</div>
              </div>
              <button className="btn-secondary btn-sm" onClick={handleResetUpload}>
                Try Another PDF
              </button>
            </div>
            {uploadErrorDetails && (
              <div className="upload-error-advice" style={{ marginTop: 8 }}>
                <strong>Advice:</strong> {uploadErrorDetails}
              </div>
            )}
          </div>
        )}
      </div>

      {/* View Switcher: Review Queue vs Sample Entity Graph */}
      <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
        <button
          className={`btn-${mainView === "queue" ? "primary" : "secondary"}`}
          onClick={() => setMainView("queue")}
        >
          📄 Literature Review Queue ({reviews.length})
        </button>
        <button
          className={`btn-${mainView === "entity_graph" ? "primary" : "secondary"}`}
          onClick={() => {
            setMainView("entity_graph");
            fetchSamples();
          }}
        >
          🔬 Sample Entity Graph ({samples.length})
        </button>
      </div>

      {/* View 1: Review Queue Table */}
      {mainView === "queue" && (
        <div className="card">
          <div className="card-header">
            <div className="tab-pills">
              {(["pending", "approved", "rejected", "all"] as const).map((tab) => (
                <button
                  key={tab}
                  className={`tab-pill ${activeTab === tab ? "active" : ""}`}
                  onClick={() => setActiveTab(tab)}
                >
                  {tab.toUpperCase()}
                </button>
              ))}
            </div>
            <span className="badge badge-neutral">{reviews.length} Records</span>
          </div>

          {loading ? (
            <div className="loading-state">
              <div className="spinner" />
              <p>Loading literature review records...</p>
            </div>
          ) : error ? (
            <div className="error-banner">{error}</div>
          ) : reviews.length === 0 ? (
            <div className="empty-state">
              <p>No records found in the "{activeTab}" queue.</p>
            </div>
          ) : (
            <div className="table-responsive">
              <table className="data-table" style={{ width: "100%", tableLayout: "auto" }}>
                <thead>
                  <tr>
                    <th style={{ width: "35%" }}>Paper Title & Source</th>
                    <th style={{ width: "25%" }}>Composition</th>
                    <th style={{ width: "20%" }}>Key Extracted Property</th>
                    <th style={{ width: "10%" }}>Review Status</th>
                    <th style={{ width: "10%", textAlign: "right" }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {reviews.map((rev) => {
                    const ext = rev.extracted_data || {};
                    const cap01 = ext.discharge_capacity_0_1c ?? ext.capacity_0_1c ?? rev.extracted_data?.Discharge_Capacity_0_1C_mAh_g;
                    const cap1 = ext.discharge_capacity_1c ?? ext.capacity_1c;
                    const cap5 = ext.discharge_capacity_5c ?? ext.capacity_5c;
                    const ret = ext.capacity_retention_percent ?? ext.retention_pct;
                    const paperTitle = ext.paper_title || ext.title || rev.source_pdf.replace(/\.pdf$/i, "");

                    return (
                      <tr key={rev.id}>
                        <td>
                          <div style={{ fontWeight: 600, color: "var(--text-main)", fontSize: "12px", lineHeight: "1.3" }}>
                            {paperTitle}
                          </div>
                          <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "2px" }}>
                            {rev.source_pdf} (p. {rev.page_number || "—"})
                          </div>
                        </td>
                        <td>
                          <code
                            style={{
                              fontFamily: "JetBrains Mono, monospace",
                              fontSize: "11px",
                              color: "#38bdf8",
                              background: "rgba(14, 165, 233, 0.12)",
                              padding: "2px 6px",
                              borderRadius: "4px",
                              display: "inline-block",
                            }}
                          >
                            {rev.composition || ext.composition || ext.chemical_formula || "LiMn₁₋ₓFeₓPO₄"}
                          </code>
                          {ext.sample_label && (
                            <span style={{ fontSize: "10px", color: "var(--text-muted)", marginLeft: "6px" }}>
                              [{ext.sample_label}]
                            </span>
                          )}
                        </td>
                        <td>
                          <div style={{ fontSize: "11px" }}>
                            {cap01 ? (
                              <span style={{ fontWeight: 600, color: "#38bdf8" }}>{cap01} mAh/g <span style={{ color: "var(--text-muted)", fontWeight: 400 }}>(0.1C)</span></span>
                            ) : cap1 ? (
                              <span style={{ fontWeight: 600, color: "#38bdf8" }}>{cap1} mAh/g <span style={{ color: "var(--text-muted)", fontWeight: 400 }}>(1C)</span></span>
                            ) : cap5 ? (
                              <span style={{ fontWeight: 600, color: "#60a5fa" }}>{cap5} mAh/g <span style={{ color: "var(--text-muted)", fontWeight: 400 }}>(5C)</span></span>
                            ) : ret ? (
                              <span style={{ color: "#34d399", fontWeight: 600 }}>{ret}% ret</span>
                            ) : (
                              <span style={{ color: "var(--text-muted)" }}>—</span>
                            )}
                          </div>
                        </td>
                        <td>
                          <span
                            className={`badge ${
                              rev.status === "approved"
                                ? "badge-green"
                                : rev.status === "rejected"
                                ? "badge-red"
                                : "badge-amber"
                            }`}
                          >
                            {rev.status.toUpperCase()}
                          </span>
                        </td>
                        <td style={{ textAlign: "right" }}>
                          <button
                            className="btn btn-secondary btn-sm"
                            style={{ padding: "4px 10px", fontSize: "11px" }}
                            onClick={() => handleSelectReview(rev)}
                          >
                            Open / Review ➔
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* View 2: Sample Entity Graph (Stage 4) */}
      {mainView === "entity_graph" && (
        <div className="card">
          <div className="card-header" style={{ flexWrap: "wrap", gap: 12 }}>
            <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
              <span style={{ fontWeight: 600, fontSize: 13 }}>Dopant:</span>
              <select
                className="input-select"
                style={{ padding: "4px 8px", fontSize: 13 }}
                value={sampleDopantFilter}
                onChange={(e) => setSampleDopantFilter(e.target.value)}
              >
                <option value="">All Dopants</option>
                <option value="Mg">Magnesium (Mg)</option>
                <option value="Ti">Titanium (Ti)</option>
                <option value="Co">Cobalt (Co)</option>
                <option value="Ni">Nickel (Ni)</option>
                <option value="V">Vanadium (V)</option>
                <option value="Zn">Zinc (Zn)</option>
                <option value="Zr">Zirconium (Zr)</option>
                <option value="Al">Aluminum (Al)</option>
              </select>

              <span style={{ fontWeight: 600, fontSize: 13, marginLeft: 8 }}>Min Rate:</span>
              <select
                className="input-select"
                style={{ padding: "4px 8px", fontSize: 13 }}
                value={sampleMinCrateFilter}
                onChange={(e) => setSampleMinCrateFilter(e.target.value)}
              >
                <option value="">All Rates</option>
                <option value="0.1">≥ 0.1 C</option>
                <option value="0.5">≥ 0.5 C</option>
                <option value="1.0">≥ 1.0 C</option>
                <option value="2.0">≥ 2.0 C</option>
                <option value="5.0">≥ 5.0 C</option>
              </select>

              <button className="btn-secondary btn-sm" onClick={fetchSamples} disabled={samplesLoading}>
                {samplesLoading ? "Refreshing..." : "↻ Refresh"}
              </button>
            </div>
            <span className="badge badge-neutral">{samples.length} Resolved Samples</span>
          </div>

          {samplesLoading ? (
            <div className="loading-state">
              <div className="spinner" />
              <p>Loading resolved MaterialSample entity graphs...</p>
            </div>
          ) : samples.length === 0 ? (
            <div className="empty-state">
              <p>No material samples match the selected criteria.</p>
            </div>
          ) : (
            <div className="table-responsive">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Sample Identity</th>
                    <th>Resolution Status</th>
                    <th>Formula & Substitutions</th>
                    <th>Precursors & Synthesis</th>
                    <th>Characterization</th>
                    <th>Linked Measurements</th>
                    <th>Provenance</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {samples.map((s) => (
                    <tr key={s.sample_id}>
                      <td>
                        <strong>{s.sample_label}</strong>
                        <div style={{ fontSize: 11, color: "#64748b" }}>{s.paper_id}</div>
                      </td>
                      <td>
                        <span
                          className={`badge ${
                            s.resolution_status === "CONFIRMED_EXPLICIT"
                              ? "badge-green"
                              : s.resolution_status === "SECONDARY_CITATION"
                              ? "badge-purple"
                              : s.resolution_status === "AMBIGUOUS"
                              ? "badge-amber"
                              : s.resolution_status === "UNRESOLVED"
                              ? "badge-red"
                              : "badge-blue"
                          }`}
                        >
                          {s.resolution_status.replace("CONFIRMED_", "")}
                        </span>
                        {s.is_unresolved && (
                          <span className="badge badge-red" style={{ marginLeft: 4 }}>
                            UNRESOLVED
                          </span>
                        )}
                      </td>
                      <td>
                        <code>{s.base_lmfp_formula}</code>
                        {s.dopants && s.dopants.length > 0 && (
                          <div style={{ fontSize: 11, color: "#2563eb", marginTop: 2 }}>
                            {s.dopants.map((d) => `${d.element} (${d.molar_ratio})`).join(", ")}
                          </div>
                        )}
                        {s.modifications && s.modifications.length > 0 && (
                          <div style={{ fontSize: 11, color: "#0d9488", marginTop: 2 }}>
                            {s.modifications.map((m) => m.modification_type).join(", ")}
                          </div>
                        )}
                      </td>
                      <td style={{ fontSize: 12 }}>
                        <div><strong>{s.synthesis_method || "Unspecified"}</strong></div>
                        {s.calcination_temp_c && (
                          <div style={{ color: "#64748b" }}>{s.calcination_temp_c} °C ({s.atmosphere || "Ar"})</div>
                        )}
                        {s.precursor_salts && s.precursor_salts.length > 0 && (
                          <div style={{ fontSize: 11, color: "#475569", marginTop: 2 }}>
                            Precursors: {s.precursor_salts.slice(0, 2).join(", ")}
                            {s.precursor_salts.length > 2 ? "..." : ""}
                          </div>
                        )}
                      </td>
                      <td style={{ fontSize: 12 }}>
                        <div>{s.space_group || "Pnma"} ({s.crystal_structure || "olivine"})</div>
                        {s.xrd_phase_purity && (
                          <div style={{ fontSize: 11, color: s.xrd_phase_purity.includes("trace") ? "#b45309" : "#16a34a" }}>
                            {s.xrd_phase_purity}
                          </div>
                        )}
                      </td>
                      <td>
                        {s.measurements && s.measurements.length > 0 ? (
                          <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                            {s.measurements.slice(0, 3).map((m) => (
                              <span
                                key={m.measurement_id}
                                className="candidate-page-tag"
                                style={{
                                  fontSize: 11,
                                  background: m.measurement_type.includes("capacity") ? "#ecfdf5" : "#eff6ff",
                                  borderColor: m.measurement_type.includes("capacity") ? "#a7f3d0" : "#bfdbfe",
                                  color: m.measurement_type.includes("capacity") ? "#065f46" : "#1e40af",
                                }}
                              >
                                {m.c_rate !== undefined && m.c_rate !== null ? `${m.c_rate}C: ` : ""}
                                {m.normalized_value} {m.normalized_unit}
                                {m.cycle_count ? ` (${m.cycle_count} cyc)` : ""}
                              </span>
                            ))}
                            {s.measurements.length > 3 && (
                              <span style={{ fontSize: 10, color: "#64748b" }}>
                                +{s.measurements.length - 3} more condition(s)
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="text-muted" style={{ fontSize: 11 }}>No measurements</span>
                        )}
                      </td>
                      <td style={{ fontSize: 11 }}>
                        <span
                          className={`badge ${s.provenance_type === "PRIMARY_EXPERIMENTAL" ? "badge-green" : "badge-purple"}`}
                        >
                          {s.provenance_type === "PRIMARY_EXPERIMENTAL" ? "PRIMARY" : "REVIEW"}
                        </span>
                        {s.secondary_citation_key && (
                          <div style={{ marginTop: 4, color: "#7c3aed" }}>
                            Ref: <strong>{s.secondary_citation_key}</strong>
                            <div style={{ fontSize: 10, color: "#64748b" }}>(Unverified primary)</div>
                          </div>
                        )}
                      </td>
                      <td>
                        <button className="btn-sm" onClick={() => handleOpenSampleModal(s)}>
                          Inspect Graph
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Review & Disambiguation Modal */}
      {selectedReview && (
        <div className="modal-backdrop">
          <div className="modal-card">
            <div className="modal-header">
              <div>
                <h3>Reviewer Disambiguation — Record #{selectedReview.id}</h3>
                <span className="text-muted">Source: {selectedReview.source_pdf} (p. {selectedReview.page_number})</span>
              </div>
              <button className="btn-close" onClick={() => setSelectedReview(null)}>
                ✕
              </button>
            </div>

            <div className="modal-body">
              {/* Evidence Banner */}
              <div className="evidence-box">
                <span className="evidence-label">DOCUMENT EVIDENCE QUOTE</span>
                <p>"{editEvidence || selectedReview.evidence_quote || "No quote extracted"}"</p>
              </div>

              <div className="form-grid">
                <div className="form-group">
                  <label>Verified Paper DOI</label>
                  <input
                    type="text"
                    value={editPaperDoi}
                    onChange={(e) => setEditPaperDoi(e.target.value)}
                    placeholder="e.g. 10.1016/j.electacta.2023..."
                  />
                </div>

                <div className="form-group">
                  <label>Verified Paper ID</label>
                  <input
                    type="text"
                    value={editPaperId}
                    onChange={(e) => setEditPaperId(e.target.value)}
                    placeholder="e.g. P142"
                  />
                </div>

                <div className="form-group span-2">
                  <label>Verified Paper Title</label>
                  <input
                    type="text"
                    value={editPaperTitle}
                    onChange={(e) => setEditPaperTitle(e.target.value)}
                    placeholder="Full article title"
                  />
                </div>

                <div className="form-group">
                  <label>Verified Sample ID</label>
                  <input
                    type="text"
                    value={editSampleId}
                    onChange={(e) => setEditSampleId(e.target.value)}
                    placeholder="e.g. LMFP-Mg02"
                  />
                </div>

                <div className="form-group">
                  <label>Source Table / Figure</label>
                  <input
                    type="text"
                    value={editTableFigure}
                    onChange={(e) => setEditTableFigure(e.target.value)}
                    placeholder="e.g. Table 2, Fig 4b"
                  />
                </div>

                <div className="form-group">
                  <label>0.1C Discharge Cap (mAh/g)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={editCap01}
                    onChange={(e) => setEditCap01(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label>1C Discharge Cap (mAh/g)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={editCap1}
                    onChange={(e) => setEditCap1(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label>5C Discharge Cap (mAh/g)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={editCap5}
                    onChange={(e) => setEditCap5(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label>Benchmark Capacity Retention (%)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={editRetention}
                    onChange={(e) => setEditRetention(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label>Retention Cycles</label>
                  <input
                    type="number"
                    value={editRetentionCycles}
                    onChange={(e) => setEditRetentionCycles(e.target.value)}
                    placeholder="e.g. 100"
                  />
                </div>

                <div className="form-group">
                  <label>Retention C-rate</label>
                  <input
                    type="number"
                    step="0.1"
                    value={editRetentionCrate}
                    onChange={(e) => setEditRetentionCrate(e.target.value)}
                    placeholder="e.g. 1.0"
                  />
                </div>
              </div>

              {/* Multi-condition retention warning if detected */}
              {selectedReview.extracted_data?.retention_conditions &&
                selectedReview.extracted_data.retention_conditions.length > 1 && (
                  <div className="alert alert-warning" style={{ marginTop: 12 }}>
                    <strong>Multi-Condition Retention Detected:</strong> Multiple cycle/rate conditions were found in the text.
                    Ensure you explicitly confirm one benchmark condition before approving for export.
                  </div>
                )}

              {/* Structured Measurements & Provenance */}
              {selectedReview.extracted_data?.structured_measurements &&
                selectedReview.extracted_data.structured_measurements.length > 0 && (
                  <div style={{ marginTop: 16, borderTop: "1px solid #e2e8f0", paddingTop: 12 }}>
                    <h4 style={{ fontSize: 13, textTransform: "uppercase", letterSpacing: "0.05em", color: "#475569", marginBottom: 8 }}>
                      Extracted Property Measurements & Provenance
                    </h4>
                    <div style={{ maxHeight: 220, overflowY: "auto", border: "1px solid #e2e8f0", borderRadius: 6 }}>
                      <table style={{ width: "100%", fontSize: 11, borderCollapse: "collapse", textAlign: "left" }}>
                        <thead style={{ background: "#f8fafc", borderBottom: "1px solid #e2e8f0" }}>
                          <tr>
                            <th style={{ padding: "6px 8px" }}>Type</th>
                            <th style={{ padding: "6px 8px" }}>Sample</th>
                            <th style={{ padding: "6px 8px" }}>Value (Rep → Norm)</th>
                            <th style={{ padding: "6px 8px" }}>Conditions</th>
                            <th style={{ padding: "6px 8px" }}>Location</th>
                            <th style={{ padding: "6px 8px" }}>Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {selectedReview.extracted_data.structured_measurements.map((m: any, idx: number) => {
                            const conds = [];
                            if (m.conditions?.c_rate !== undefined && m.conditions?.c_rate !== null) conds.push(`${m.conditions.c_rate} C`);
                            if (m.conditions?.cycle_count) conds.push(`${m.conditions.cycle_count} cyc`);
                            if (m.conditions?.temperature_c) conds.push(`${m.conditions.temperature_c} °C`);
                            if (m.conditions?.voltage_window) conds.push(m.conditions.voltage_window);

                            return (
                              <tr key={idx} style={{ borderBottom: "1px solid #f1f5f9" }} title={`Evidence: ${m.evidence_quote || "N/A"}`}>
                                <td style={{ padding: "6px 8px", fontWeight: 600 }}>{m.measurement_type}</td>
                                <td style={{ padding: "6px 8px", color: "#2563eb" }}>{m.sample_label || "Host"}</td>
                                <td style={{ padding: "6px 8px" }}>
                                  {m.reported_value} {m.reported_unit || ""} → <strong>{m.normalized_value ?? "—"} {m.normalized_unit || ""}</strong>
                                </td>
                                <td style={{ padding: "6px 8px", color: "#64748b" }}>{conds.join(", ") || "Ambient"}</td>
                                <td style={{ padding: "6px 8px", color: "#64748b" }}>p. {m.page_number} ({m.section_type})</td>
                                <td style={{ padding: "6px 8px" }}>
                                  <span
                                    style={{
                                      fontSize: 10,
                                      padding: "2px 5px",
                                      borderRadius: 4,
                                      background: m.validation_status === "VERIFIED" ? "#dcfce7" : "#fef3c7",
                                      color: m.validation_status === "VERIFIED" ? "#166534" : "#92400e",
                                    }}
                                  >
                                    {m.validation_status}
                                  </span>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

              {/* Stage 3 Synthesis & Characterization Profiles */}
              {(selectedReview.extracted_data?.synthesis_profile || selectedReview.extracted_data?.characterization_profile) && (
                <div style={{ marginTop: 12, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                  {selectedReview.extracted_data?.synthesis_profile && (
                    <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 6, padding: 8, fontSize: 11 }}>
                      <strong style={{ color: "#334155" }}>⚗️ Synthesis Profile</strong>
                      <div style={{ marginTop: 4, color: "#64748b" }}>
                        Route: <strong>{selectedReview.extracted_data.synthesis_profile.route || "Not specified"}</strong><br />
                        Calcination: {selectedReview.extracted_data.synthesis_profile.calcination_temperature_c ? `${selectedReview.extracted_data.synthesis_profile.calcination_temperature_c} °C` : "—"}{selectedReview.extracted_data.synthesis_profile.calcination_duration_hours ? ` (${selectedReview.extracted_data.synthesis_profile.calcination_duration_hours} h)` : ""}<br />
                        Atmosphere: {selectedReview.extracted_data.synthesis_profile.atmosphere || "—"}
                      </div>
                    </div>
                  )}
                  {selectedReview.extracted_data?.characterization_profile && (
                    <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 6, padding: 8, fontSize: 11 }}>
                      <strong style={{ color: "#334155" }}>🔬 Characterization Profile</strong>
                      <div style={{ marginTop: 4, color: "#64748b" }}>
                        Space Group: <strong>{selectedReview.extracted_data.characterization_profile.space_group || "—"}</strong><br />
                        Lattice Vol: {selectedReview.extracted_data.characterization_profile.unit_cell_volume_angstrom3 ? `${selectedReview.extracted_data.characterization_profile.unit_cell_volume_angstrom3} Å³` : "—"}<br />
                        EIS Rct: {selectedReview.extracted_data.characterization_profile.eis_rct_ohm ? `${selectedReview.extracted_data.characterization_profile.eis_rct_ohm} Ω` : "—"}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="modal-footer">
              <button className="btn-secondary" onClick={() => handleSaveReviewStatus("rejected")}>
                Reject Record
              </button>
              <button className="btn-secondary" onClick={() => handleSaveReviewStatus("pending")}>
                Save as Pending
              </button>
              <button className="btn-primary" onClick={() => handleSaveReviewStatus("approved")}>
                ✓ Approve for Export
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Sample Entity Graph Inspection & Disambiguation Modal */}
      {selectedSample && (
        <div className="modal-backdrop">
          <div className="modal-card" style={{ maxWidth: 820 }}>
            <div className="modal-header">
              <div>
                <h3>Sample Entity Graph — {selectedSample.sample_label}</h3>
                <span className="text-muted">
                  Paper: {selectedSample.paper_id} | Sample ID: {selectedSample.sample_id}
                </span>
              </div>
              <button className="btn-close" onClick={() => setSelectedSample(null)}>
                ✕
              </button>
            </div>

            <div className="modal-body">
              {/* Provenance Alert */}
              {selectedSample.provenance_type === "SECONDARY_REVIEW" ? (
                <div
                  style={{
                    background: "#faf5ff",
                    color: "#6b21a8",
                    padding: 10,
                    borderRadius: 6,
                    border: "1px solid #e9d5ff",
                    fontSize: 12,
                    marginBottom: 12,
                  }}
                >
                  ⚠️ <strong>Secondary Review Citation:</strong> Extracted from a review paper citing reference{" "}
                  <strong>{selectedSample.secondary_citation_key || "unspecified"}</strong>. Primary paper identity has not been independently verified; primary DOI fabrication is strictly prevented.
                </div>
              ) : (
                <div
                  style={{
                    background: "#f0fdf4",
                    color: "#166534",
                    padding: 10,
                    borderRadius: 6,
                    border: "1px solid #bbf7d0",
                    fontSize: 12,
                    marginBottom: 12,
                  }}
                >
                  ✅ <strong>Primary Experimental Sample:</strong> Directly synthesized and characterized in paper{" "}
                  <strong>{selectedSample.paper_id}</strong>.
                </div>
              )}

              {/* Composition & Synthesis Grid */}
              <div className="form-grid" style={{ marginBottom: 16 }}>
                <div className="form-group">
                  <label>Base Formula</label>
                  <input type="text" readOnly value={selectedSample.base_lmfp_formula} />
                </div>
                <div className="form-group">
                  <label>Mn / Fe Ratios</label>
                  <input
                    type="text"
                    readOnly
                    value={`Mn: ${selectedSample.mn_ratio} | Fe: ${selectedSample.fe_ratio}`}
                  />
                </div>
                <div className="form-group">
                  <label>Synthesis Method & Precursors</label>
                  <input
                    type="text"
                    readOnly
                    value={`${selectedSample.synthesis_method || "Solid-state"} (${(selectedSample.precursor_salts || []).join(", ") || "Unspecified"})`}
                  />
                </div>
                <div className="form-group">
                  <label>Calcination & Atmosphere</label>
                  <input
                    type="text"
                    readOnly
                    value={`${selectedSample.calcination_temp_c ? `${selectedSample.calcination_temp_c} °C` : "—"} | ${selectedSample.atmosphere || "Ar/H2"}`}
                  />
                </div>
              </div>

              {/* Linked Measurements with Condition Preservation */}
              <div style={{ marginBottom: 16 }}>
                <h4 style={{ fontSize: 13, marginBottom: 8, color: "#334155" }}>
                  Linked Electrochemical Measurements ({selectedSample.measurements?.length || 0})
                </h4>
                {selectedSample.measurements && selectedSample.measurements.length > 0 ? (
                  <div className="table-responsive">
                    <table className="data-table" style={{ fontSize: 12 }}>
                      <thead>
                        <tr>
                          <th>Measurement</th>
                          <th>Value & Unit</th>
                          <th>C-Rate</th>
                          <th>Cycle Count</th>
                          <th>Temp (°C)</th>
                          <th>Voltage Window</th>
                          <th>Page</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selectedSample.measurements.map((m) => (
                          <tr key={m.measurement_id}>
                            <td><code>{m.measurement_type}</code></td>
                            <td><strong>{m.normalized_value} {m.normalized_unit}</strong></td>
                            <td>{m.c_rate !== undefined && m.c_rate !== null ? `${m.c_rate} C` : "—"}</td>
                            <td>{m.cycle_count !== undefined && m.cycle_count !== null ? m.cycle_count : "—"}</td>
                            <td>{m.temperature_c ?? 25.0} °C</td>
                            <td>
                              {m.voltage_window_lower_v && m.voltage_window_upper_v
                                ? `${m.voltage_window_lower_v}–${m.voltage_window_upper_v} V`
                                : "2.5–4.5 V"}
                            </td>
                            <td>p. {m.source_page}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-muted" style={{ fontSize: 12 }}>No linked measurements.</p>
                )}
              </div>

              {/* Reviewer Disambiguation Controls */}
              <div style={{ background: "#f8fafc", padding: 12, borderRadius: 8, border: "1px solid #e2e8f0" }}>
                <h4 style={{ fontSize: 13, marginBottom: 8, color: "#1e293b" }}>
                  Reviewer Disambiguation & Identity Overrides
                </h4>
                <div className="form-grid">
                  <div className="form-group">
                    <label>Author Sample Label</label>
                    <input
                      type="text"
                      value={editSampleLabel}
                      onChange={(e) => setEditSampleLabel(e.target.value)}
                    />
                  </div>
                  <div className="form-group">
                    <label>Resolution Status</label>
                    <select
                      className="input-select"
                      value={editSampleResStatus}
                      onChange={(e) => setEditSampleResStatus(e.target.value)}
                    >
                      <option value="CONFIRMED_EXPLICIT">CONFIRMED_EXPLICIT (Author designation)</option>
                      <option value="CONFIRMED_MODIFICATION">CONFIRMED_MODIFICATION (Distinct coating/composite)</option>
                      <option value="CONFIRMED_FORMULA">CONFIRMED_FORMULA (Stoichiometry)</option>
                      <option value="SECONDARY_CITATION">SECONDARY_CITATION (Review paper reference)</option>
                      <option value="AMBIGUOUS">AMBIGUOUS (Suspected duplicate / conflicting)</option>
                      <option value="UNRESOLVED">UNRESOLVED (Cannot isolate identity)</option>
                    </select>
                  </div>
                </div>

                <div className="form-group" style={{ marginTop: 8 }}>
                  <label>Resolution Notes / Scientific Provenance</label>
                  <textarea
                    rows={2}
                    value={editSampleResNotes}
                    onChange={(e) => setEditSampleResNotes(e.target.value)}
                    placeholder="Enter scientific justification for sample grouping or separation..."
                  />
                </div>

                <div style={{ marginTop: 8 }}>
                  <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, cursor: "pointer" }}>
                    <input
                      type="checkbox"
                      checked={editSampleIsUnresolved}
                      onChange={(e) => setEditSampleIsUnresolved(e.target.checked)}
                    />
                    Flag as Unresolved Sample (Prevents downstream auto-association in copilot and dataset export)
                  </label>
                </div>
              </div>
            </div>

            <div className="modal-footer">
              <button className="btn-secondary" onClick={() => setSelectedSample(null)}>
                Cancel
              </button>
              <button
                className="btn-primary"
                onClick={handleSaveSampleResolution}
                disabled={sampleUpdateLoading}
              >
                {sampleUpdateLoading ? "Saving..." : "Save Sample Resolution"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Safe Export Preview Drawer */}
      {showExportDrawer && (
        <div className="modal-backdrop">
          <div className="modal-card" style={{ maxWidth: 750 }}>
            <div className="modal-header">
              <div>
                <h3>Master Corpus Safe Export Preview</h3>
                <span className="text-muted">Protects the 1,215 × 41 literature master dataset with strict integrity checks</span>
              </div>
              <button className="btn-close" onClick={() => setShowExportDrawer(false)}>
                ✕
              </button>
            </div>

            <div className="modal-body">
              {exportLoading ? (
                <div className="loading-state">
                  <div className="spinner" />
                  <p>Inspecting approved records and validation blockers...</p>
                </div>
              ) : exportPreview ? (
                <>
                  <div className="metrics-grid" style={{ gridTemplateColumns: "repeat(4, 1fr)", marginBottom: 16 }}>
                    <div className="metric-box">
                      <span className="metric-label">MASTER RECORDS</span>
                      <div className="metric-box-value">{exportPreview.master_records}</div>
                    </div>
                    <div className="metric-box">
                      <span className="metric-label">APPROVED REVIEWS</span>
                      <div className="metric-box-value">{exportPreview.approved_reviews}</div>
                    </div>
                    <div className="metric-box">
                      <span className="metric-label">EXPORTABLE</span>
                      <div className="metric-box-value" style={{ color: "#32b881" }}>
                        {exportPreview.exportable_records}
                      </div>
                    </div>
                    <div className="metric-box">
                      <span className="metric-label">BLOCKED</span>
                      <div className="metric-box-value" style={{ color: "#e55353" }}>
                        {exportPreview.blocked_records}
                      </div>
                    </div>
                  </div>

                  {exportMsg && (
                    <div className="alert alert-info" style={{ marginBottom: 12 }}>
                      {exportMsg}
                    </div>
                  )}

                  <div className="table-responsive">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Review ID</th>
                          <th>Composition</th>
                          <th>Integrity Status</th>
                          <th>Validation / Blocker Details</th>
                        </tr>
                      </thead>
                      <tbody>
                        {exportPreview.records.map((r) => (
                          <tr key={r.review_id}>
                            <td>#{r.review_id}</td>
                            <td>
                              <code>{r.composition}</code>
                            </td>
                            <td>
                              {r.errors.length === 0 ? (
                                <span className="badge badge-green">Ready</span>
                              ) : (
                                <span className="badge badge-red">Blocked</span>
                              )}
                            </td>
                            <td>
                              {r.errors.length === 0 ? (
                                <span className="text-muted">All 41 schema fields and constraints verified</span>
                              ) : (
                                <ul className="error-list">
                                  {r.errors.map((e, idx) => (
                                    <li key={idx}>{e}</li>
                                  ))}
                                </ul>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <div className="notice-box" style={{ marginTop: 16 }}>
                    <p>
                      <strong>Safety Guarantee:</strong> Records with unverified Paper_ID, missing Sample_ID, or
                      unbenchmarked multi-condition retention are permanently blocked from altering the master CSV.
                    </p>
                  </div>
                </>
              ) : null}
            </div>

            <div className="modal-footer">
              <button
                className="btn-secondary"
                onClick={() => handleRunExport(true)}
                disabled={exportLoading}
              >
                Simulate Dry Run
              </button>
              <button
                className="btn-primary"
                onClick={() => handleRunExport(false)}
                disabled={exportLoading || exportPreview?.exportable_records === 0}
              >
                Execute Safe Export ({exportPreview?.exportable_records || 0} Records)
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
