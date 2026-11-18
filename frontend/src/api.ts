/**
 * API client for HE-LMFP-Designer FastAPI Backend.
 * Uses environment variable VITE_API_BASE_URL or defaults to http://127.0.0.1:8000
 */

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL !== undefined
    ? import.meta.env.VITE_API_BASE_URL
    : typeof window !== "undefined" &&
      window.location.hostname !== "localhost" &&
      window.location.hostname !== "127.0.0.1"
    ? window.location.origin
    : "http://127.0.0.1:8000";

export interface Dopant {
  symbol: string;
  fraction: number;
  oxidation_state?: number;
}

export interface DashboardData {
  master_dataset: {
    total_records: number;
    unique_papers: number;
    samples_with_rate_capacity: number;
    samples_with_retention: number;
    top_dopants: [string, number][];
  };
  ml_pipeline: {
    available_models: {
      target_key: string;
      label: string;
      status: string;
      sample_count: number;
      metrics: Record<string, any>;
    }[];
    architecture: string;
  };
  review_queue: {
    total: number;
    pending: number;
    approved: number;
    rejected: number;
  };
  experiments_count: number;
  database_info: {
    mode: string;
    engine: string;
    is_local_sqlite: boolean;
  };
}

export interface ValidationResponse {
  formula: {
    formula_string: string;
    formula_html?: string;
    formula_latex?: string;
    molar_mass: number;
    m2_occupancy: number;
    m2_occupancy_valid: boolean;
    adjusted_li: number;
    li_vacancy_delta: number;
    charge_balanced: boolean;
  };
  charge_balance: {
    status: string;
    total_positive_charge: number;
    total_negative_charge: number;
    net_charge: number;
    m2_cation_charge: number;
    compensation_strategy: string;
    li_compensation_reason: string;
    original_li: number;
    adjusted_li: number;
    li_vacancy_delta: number;
    is_charge_balanced: boolean;
    m2_occupancy: number;
    m2_occupancy_valid: boolean;
    error_message: string;
  };
  entropy: {
    s_config: number;
    s_config_over_r: number;
    classification: string;
    classification_label: string;
    is_provisional: boolean;
    species_fractions: Record<string, number>;
  };
  capacity: {
    project_reference_theoretical: number;
    project_reference_practical: string;
    voltage_window: string;
    formula_calculated_capacity_metric: number;
    disclaimer: string;
  };
  validation: {
    overall_status: string;
    is_valid: boolean;
    errors: string[];
    warnings: string[];
    info_messages: string[];
    details: {
      rule_id: string;
      severity: string;
      message: string;
    }[];
    synthesis_parameters: Record<string, string>;
  };
}

export interface CandidateComposition {
  name: string;
  description: string;
  mn_ratio: number;
  fe_ratio: number;
  dopants: Dopant[];
  carbon_wt: number;
  formula_string: string;
  s_config_over_r: number;
  entropy_class: string;
  m2_occupancy: number;
  li_vacancy_delta: number;
  calculated_capacity: number;
}

// ---------------------------------------------------------------------------
// Stage 5 Phase 4 Research Intelligence & Discovery Interfaces
// ---------------------------------------------------------------------------

export interface TrendReportItem {
  topic: string;
  evidence_type: string;
  sample_count: number;
  paper_count: number;
  data: Record<string, any>;
  key_takeaway: string;
  provenance_notes?: string;
  policy_caveats?: string[];
}

export interface TrendSummaryResponse {
  dataset_overview: {
    total_literature_records: number;
    unique_dois_and_sources: number;
    verified_materials_samples: number;
    scope: string;
  };
  trend_dimensions: {
    dopant_frequencies: TrendReportItem[];
    dopant_cooccurrence: TrendReportItem;
    mn_fe_distributions: TrendReportItem[];
    doping_entropy_tiers: TrendReportItem[];
    composite_modifications: TrendReportItem[];
    synthesis_routes: TrendReportItem[];
    calcination_parameters: TrendReportItem;
    characterization_coverage: TrendReportItem;
    electrochemical_envelopes: TrendReportItem[];
  };
}

export interface ResearchGapItem {
  gap_id: string;
  category: string;
  title: string;
  description: string;
  scientific_question: string;
  related_compositions: string[];
  related_dopants: string[];
  supporting_paper_ids: string[];
  supporting_sample_ids: string[];
  sample_count: number;
  paper_count: number;
  available_measurements: Record<string, any>;
  missing_measurements: string[];
  relevant_conditions: Record<string, any>;
  confounding_variables: string[];
  evidence_strength: string;
  confidence_limitations: string[];
  why_the_gap_matters: string;
  suggested_investigation: string;
  verification_status: string;
}

export interface ScientificConflictItem {
  conflict_id: string;
  title?: string;
  topic: string;
  classification?: string;
  finding_a: string;
  finding_b: string;
  underlying_cause?: string;
  epistemic_verdict?: string;
  suggested_resolution?: string;
  divergence_description?: string;
  paper_a_id?: string;
  paper_a_doi?: string;
  sample_a_id?: string;
  paper_b_id?: string;
  paper_b_doi?: string;
  sample_b_id?: string;
  reconciliation_hypothesis?: string;
  confounding_variables?: string[];
}

export interface ResearchGapsResponse {
  query_filters: Record<string, any>;
  gaps_count: number;
  conflicts_count: number;
  gaps: ResearchGapItem[];
  conflicts: ScientificConflictItem[];
}

export interface EpistemicStatementItem {
  statement: string;
  epistemic_type: string;
  source: string;
  citation?: string;
}

export interface ExperimentalProtocolItem {
  protocol_id: string;
  candidate_composition: string;
  intended_dopant_concentration: Record<string, number>;
  precursors: string[];
  synthesis_method: string;
  synthesis_variables: Record<string, any>;
  control_and_comparison_samples: { sample_id: string; description: string }[];
  variables_to_hold_constant: string[];
  variables_to_change: string[];
  required_characterization: { technique: string; target: string }[];
  electrochemical_testing_conditions: Record<string, any>;
  expected_observations: string[];
  falsification_criteria: string[];
  researcher_selection_required: string[];
}

export interface ScientificHypothesisItem {
  hypothesis_id: string;
  category: string;
  epistemic_type: string;
  scientific_question: string;
  hypothesis_statement: string;
  epistemic_breakdown: EpistemicStatementItem[];
  supporting_paper_ids: string[];
  supporting_dois: string[];
  supporting_sample_ids: string[];
  related_compositions: string[];
  supporting_measurements: Record<string, any>;
  contradictory_or_limiting_evidence: { finding: string; explanation: string; epistemic_type: string }[];
  proposed_mechanism: string;
  mechanism_evidence_status: string;
  alternative_explanations: string[];
  research_gap_id: string;
  confidence_level: string;
  confidence_explanation: string;
  chemical_validation: {
    is_charge_balanced: boolean;
    is_chemically_plausible: boolean;
    q_m2: number;
    required_li: number;
    delta_li_vacancies: number;
    phi_m2_occupancy: number;
    m2_sum: number;
    explanation: string;
  };
  ml_prediction_context?: any;
  supervisor_policy_context?: any;
  experimental_protocol: ExperimentalProtocolItem;
  expected_outcome: string;
  falsification_criteria: string[];
}

export interface MatrixControlSampleItem {
  sample_id: string;
  label: string;
  formula: string;
  role: string;
  expected_behavior: string;
  epistemic_status: string;
}

export interface VariableSpecificationItem {
  variable_name: string;
  variable_type: string;
  target_value: string;
  tolerance: string;
  rationale: string;
}

export interface SynthesisProtocolStepItem {
  step_number: number;
  operation: string;
  parameters: Record<string, any>;
  atmosphere: string;
  equipment: string;
  safety_notes: string;
}

export interface CharacterizationRequirementItem {
  technique: string;
  instrument: string;
  target_feature: string;
  acceptance_criteria: string;
  epistemic_importance: string;
}

export interface ElectrochemicalTestProtocolItem {
  protocol_name: string;
  voltage_window: string;
  c_rates: number[];
  temperature: string;
  cycle_count: number;
  mass_loading_min_mg_cm2: number;
  electrolyte_spec: string;
  target_metrics: Record<string, string>;
}

export interface ExperimentalVerificationMatrixItem {
  matrix_id: string;
  title: string;
  hypothesis_id: string;
  research_gap_id: string;
  scientific_question: string;
  candidate_composition: string;
  intended_dopants: Dopant[];
  supporting_literature: {
    paper_ids: string[];
    dois: string[];
    sample_ids: string[];
    empirical_measurements: Record<string, any>;
    contradictory_evidence: any[];
    epistemic_type: string;
  };
  chemical_validation: {
    is_charge_balanced: boolean;
    is_chemically_plausible: boolean;
    q_m2: number;
    required_li: number;
    delta_li_vacancies: number;
    phi_m2_occupancy: number;
    m2_sum: number;
    explanation: string;
  };
  materials_designer_link: Record<string, any>;
  property_prediction_link: Record<string, any>;
  supervisor_policy_link: Record<string, any>;
  control_samples: MatrixControlSampleItem[];
  variable_specifications: VariableSpecificationItem[];
  synthesis_plan: SynthesisProtocolStepItem[];
  characterization_plan: CharacterizationRequirementItem[];
  electrochemical_plan: ElectrochemicalTestProtocolItem[];
  expected_outcomes: string[];
  falsification_criteria: string[];
  researcher_selection_required: string[];
  status_disclaimers: {
    EXPERIMENT_STATUS: string;
    ML_VALIDATION_STATUS: string;
    SUPERVISOR_POLICY_SEPARATION: string;
  };
}

export interface VerificationMatricesResponse {
  query_filters: Record<string, any>;
  total_matrices: number;
  matrices: ExperimentalVerificationMatrixItem[];
}

export interface PredictionResult {
  formula_string: string;
  molar_mass: number;
  predictions: Record<
    string,
    {
      target_key: string;
      label: string;
      unit: string;
      status: string;
      predicted_value?: number;
      std_uncertainty?: number;
      sample_count?: number;
      paper_count?: number;
      metrics?: Record<string, any>;
      disclaimer?: string;
      message?: string;
    }
  >;
  dopant_count: number;
  coverage_warnings: string[];
  metadata: Record<string, any>;
}

export interface ReviewRecord {
  id: number;
  source_pdf: string;
  page_number: number;
  reference?: string;
  composition?: string;
  evidence_quote?: string;
  status: "pending" | "approved" | "rejected";
  created_at: string;
  reviewed_at?: string;
  extracted_data: Record<string, any>;
}

export interface SavedReviewSummary {
  id: number;
  composition: string;
  page: number;
  reference?: string;
  status: "pending" | "approved" | "rejected";
  is_new: boolean;
}

export interface CandidatePageInfo {
  page: number;
  snippet: string;
  matched_keywords?: string[];
}

export interface PdfExtractionResponse {
  status: "success" | "partial_extraction" | "no_records_found";
  filename: string;
  file_size_bytes: number;
  total_pages: number;
  pages_with_text: number;
  candidate_pages_count: number;
  candidate_pages: CandidatePageInfo[];
  records_extracted: number;
  saved_reviews_count: number;
  saved_review_ids: number[];
  saved_reviews: SavedReviewSummary[];
  warnings: string[];
  message: string;
  suggested_next_action: string;
  detected_sections?: string[];
  background_mentions_count?: number;
  background_mentions?: Array<{
    composition: string;
    page: number;
    section_type: string;
    section_label: string;
    evidence_quote: string;
    is_background: boolean;
  }>;
  structured_measurements?: Array<Record<string, any>>;
  synthesis_profiles?: Array<Record<string, any>>;
  characterization_profiles?: Array<Record<string, any>>;
  property_summary?: {
    total_measurements: number;
    capacities_count: number;
    retentions_count: number;
    synthesis_profiles_count: number;
    characterization_profiles_count: number;
  };
  resolved_samples?: Array<MaterialSampleEntity>;
  resolved_samples_count?: number;
  review_id?: number | null;
  candidates_extracted?: number;
  first_page_snippet?: string;
}

export interface MaterialSampleEntity {
  sample_id: string;
  paper_id: string;
  sample_label: string;
  provenance_type: string;
  resolution_status: string;
  resolution_confidence: number;
  resolution_notes?: string;
  is_unresolved: boolean;
  raw_formula: string;
  base_lmfp_formula: string;
  mn_ratio: number;
  fe_ratio: number;
  dopants: Array<{
    element: string;
    molar_ratio: number;
    substitution_site?: string;
  }>;
  modifications: Array<{
    modification_type: string;
    carbon_source?: string;
    weight_percentage?: number;
  }>;
  synthesis_method?: string;
  calcination_temp_c?: number;
  atmosphere?: string;
  precursor_salts: string[];
  crystal_structure?: string;
  space_group?: string;
  xrd_phase_purity?: string;
  morphology?: string;
  secondary_citation_key?: string;
  secondary_primary_doi?: string;
  measurements: Array<{
    measurement_id: string;
    measurement_type: string;
    reported_value: string;
    normalized_value?: number;
    normalized_unit?: string;
    c_rate?: number;
    cycle_count?: number;
    temperature_c?: number;
    voltage_window_lower_v?: number;
    voltage_window_upper_v?: number;
    source_page: number;
    table_or_figure_ref?: string;
    evidence_quote?: string;
    validation_status: string;
  }>;
}

export interface ExportPreview {
  master_records: number;
  approved_reviews: number;
  exportable_records: number;
  blocked_records: number;
  records: {
    review_id: number;
    source_pdf: string;
    page_number: number;
    composition: string;
    errors: string[];
  }[];
}

export interface CopilotResponse {
  response: string;
  direct_answer?: string;
  explanation?: string;
  comparison_table?: Array<{
    paper_id: string;
    sample: string;
    composition: string;
    dopant: string;
    capacity_0_1c: string;
    capacity_1c: string;
    capacity_5c: string;
    retention: string;
    synthesis: string;
  }>;
  sourced_facts: { source: string; doi: string; finding: string }[];
  engine_facts: { rule: string; detail: string }[];
  citations?: Array<{
    paper_id: string;
    page_number: number;
    doi?: string;
    sample_label?: string;
    evidence_quote: string;
    is_verified: boolean;
  }>;
  conflicts_and_limitations?: string;
  inference_source?: string;
  predictions_note?: string;
  disclaimer: string;
  sample_profiles?: any[];
  attached_image_url?: string;
  attached_image_name?: string;
}

export interface ExperimentImageRecord {
  url: string;
  filename: string;
  original_filename: string;
  image_type?: string;
  notes?: string;
  size_bytes?: number;
  uploaded_at?: string;
}

export interface ExperimentRecord {
  experiment_id: string;
  sample_id: string;
  created_at: string;
  updated_at: string;
  operator: string;
  batch_id: string;
  status: string;
  generated_formula: string;
  mn_frac: number;
  fe_frac: number;
  dopants: Dopant[];
  carbon_wt_pct: number;
  synthesis_route: string;
  synthesis_data?: {
    calcination_temp_c?: number;
    calcination_duration_h?: number;
    observations?: string;
  };
  electrochemical_data?: {
    initial_discharge_cap?: number;
    capacity_retention_pct?: number;
    cycle_life_cycles?: number;
  };
  characterization_data?: {
    impurity_phases?: string;
  };
  characterization_images?: ExperimentImageRecord[];
}

// ---------------------------------------------------------------------------
// API Methods
// ---------------------------------------------------------------------------

async function request<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const token = typeof window !== "undefined" ? localStorage.getItem("ecmt_session_token") : null;
  const authHeader = token ? { Authorization: `Bearer ${token}` } : {};

  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...authHeader,
      ...options?.headers,
    },
  });

  if (!response.ok) {
    let errMessage = `HTTP ${response.status}: ${response.statusText}`;
    try {
      const errJson = await response.json();
      if (errJson.detail) {
        errMessage = typeof errJson.detail === "string" ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // fallback to status text
    }
    throw new Error(errMessage);
  }

  return response.json();
}

export const api = {
  getHealth: () => request<{ status: string }>("/api/health"),

  getDashboard: () => request<DashboardData>("/api/dashboard"),

  getAllowedDopants: () => request<any>("/api/materials/dopants"),

  validateComposition: (payload: {
    mn_ratio: number;
    fe_ratio: number;
    dopants: Dopant[];
    carbon_wt_percent: number;
    cnt_wt_percent: number;
  }) => request<ValidationResponse>("/api/materials/validate", {
    method: "POST",
    body: JSON.stringify(payload),
  }),

  generateCandidates: () =>
    request<{ candidates: CandidateComposition[] }>(
      "/api/materials/generate-candidates",
      { method: "POST" }
    ),

  predictProperties: (payload: {
    mn_ratio: number;
    fe_ratio: number;
    dopants: Dopant[];
    carbon_wt: number;
    calc_temp?: number;
    calc_time?: number;
  }) =>
    request<PredictionResult>("/api/predictions/predict", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getPredictionEvaluation: () =>
    request<any>("/api/predictions/evaluation"),

  getReviews: (status?: string) =>
    request<ReviewRecord[]>(
      status ? `/api/literature/reviews?status=${status}` : "/api/literature/reviews"
    ),

  getReview: (id: number) => request<ReviewRecord>(`/api/literature/reviews/${id}`),

  updateReview: (id: number, status: string, record: Record<string, any>) =>
    request<{ review_id: number; status: string; message: string }>(
      `/api/literature/reviews/${id}`,
      {
        method: "POST",
        body: JSON.stringify({ status, record }),
      }
    ),

  uploadPdf: async (file: File): Promise<PdfExtractionResponse> => {
    const formData = new FormData();
    formData.append("file", file);
    const response = await fetch(`${API_BASE_URL}/api/literature/extract-pdf`, {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      let errMessage = `HTTP ${response.status}: ${response.statusText}`;
      try {
        const errJson = await response.json();
        if (errJson.detail) {
          errMessage = typeof errJson.detail === "string" ? errJson.detail : JSON.stringify(errJson.detail);
        }
      } catch {
        // fallback
      }
      throw new Error(errMessage);
    }
    return response.json();
  },

  getExportPreview: () =>
    request<ExportPreview>("/api/literature/export/preview"),

  executeExport: (dryRun: boolean = true) =>
    request<any>(`/api/literature/export?dry_run=${dryRun}`, {
      method: "POST",
    }),

  getMaterialSamples: (params?: { paper_id?: string; dopant?: string; min_crate?: number }) => {
    const query = new URLSearchParams();
    if (params?.paper_id) query.append("paper_id", params.paper_id);
    if (params?.dopant) query.append("dopant", params.dopant);
    if (params?.min_crate !== undefined) query.append("min_crate", params.min_crate.toString());
    const qs = query.toString();
    return request<MaterialSampleEntity[]>(`/api/literature/samples${qs ? `?${qs}` : ""}`);
  },

  getMaterialSample: (sampleId: string) =>
    request<MaterialSampleEntity>(`/api/literature/samples/${encodeURIComponent(sampleId)}`),

  resolveMaterialSample: (
    sampleId: string,
    payload: {
      sample_label?: string;
      resolution_status?: string;
      resolution_notes?: string;
      is_unresolved?: boolean;
    }
  ) =>
    request<{ sample_id: string; updated: boolean; sample: MaterialSampleEntity }>(
      `/api/literature/samples/${encodeURIComponent(sampleId)}/resolve`,
      {
        method: "POST",
        body: JSON.stringify(payload),
      }
    ),

  chatCopilot: (
    message: string,
    currentComposition?: any,
    recentHistory?: any[],
    attachedImageUrl?: string,
    attachedImageName?: string
  ) =>
    request<CopilotResponse>("/api/copilot/chat", {
      method: "POST",
      body: JSON.stringify({
        message,
        current_composition: currentComposition,
        recent_history: recentHistory,
        attached_image_url: attachedImageUrl,
        attached_image_name: attachedImageName,
      }),
    }),

  uploadImage: async (
    file: File,
    category: string = "copilot"
  ): Promise<{
    status: string;
    url: string;
    filename: string;
    original_filename: string;
    size_bytes: number;
    content_type: string;
    category: string;
  }> => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("category", category);
    const res = await fetch(`${API_BASE_URL}/api/upload/image`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Image upload failed" }));
      throw new Error(err.detail || `Upload failed with HTTP ${res.status}`);
    }
    return res.json();
  },

  uploadExperimentImage: async (
    file: File,
    experimentId: string,
    imageType: string = "SEM Micrograph",
    notes: string = ""
  ): Promise<{
    status: string;
    image_record: ExperimentImageRecord;
    experiment_id: string;
    message: string;
  }> => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("experiment_id", experimentId);
    formData.append("image_type", imageType);
    formData.append("notes", notes);
    const res = await fetch(`${API_BASE_URL}/api/upload/experiment-image`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Experiment image upload failed" }));
      throw new Error(err.detail || `Upload failed with HTTP ${res.status}`);
    }
    return res.json();
  },

  deleteExperimentImage: async (experimentId: string, imageUrl: string) =>
    request<{ status: string; removed: number; remaining_images: number }>(
      "/api/upload/experiment-image",
      {
        method: "DELETE",
        body: JSON.stringify({ experiment_id: experimentId, image_url: imageUrl }),
      }
    ),

  uploadLiteratureSupporting: async (
    file: File,
    paperId: string = "",
    docType: string = "Supporting Characterization / XRD / SEM"
  ): Promise<{
    status: string;
    url: string;
    filename: string;
    original_filename: string;
    paper_id: string;
    doc_type: string;
    size_bytes: number;
  }> => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("paper_id", paperId);
    formData.append("doc_type", docType);
    const res = await fetch(`${API_BASE_URL}/api/upload/literature-supporting`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Upload failed" }));
      throw new Error(err.detail || `Upload failed with HTTP ${res.status}`);
    }
    return res.json();
  },

  getExperiments: () => request<ExperimentRecord[]>("/api/experiments"),

  getExperimentDatabaseInfo: () =>
    request<{
      mode: string;
      engine: string;
      db_path?: string;
      sqlite_db_abs_path?: string;
      db_filename: string;
      table_name: string;
      total_experiments: number;
      is_local_sqlite: boolean;
    }>("/api/experiments/database-info"),

  deleteExperiment: (experimentId: string) =>
    request<{ status: string; message: string }>(`/api/experiments/${experimentId}`, {
      method: "DELETE",
    }),

  createExperiment: (payload: any) =>
    request<{ experiment_id: string; sample_id: string; message: string; status?: string }>(
      "/api/experiments",
      {
        method: "POST",
        body: JSON.stringify(payload),
      }
    ),

  compareExperiment: (payload: {
    mn_ratio: number;
    fe_ratio: number;
    experiment_id?: string;
  }) =>
    request<any>(
      `/api/experiments/compare?mn_ratio=${payload.mn_ratio}&fe_ratio=${payload.fe_ratio}${
        payload.experiment_id ? `&experiment_id=${payload.experiment_id}` : ""
      }`,
      { method: "POST" }
    ),

  // Stage 5 Phase 4 - Research Intelligence & Scientific Discovery APIs
  getLiteratureTrends: (params?: { topic?: string; dopant?: string }) => {
    const qs = new URLSearchParams();
    if (params?.topic) qs.append("topic", params.topic);
    if (params?.dopant) qs.append("dopant", params.dopant);
    const query = qs.toString();
    return request<TrendSummaryResponse>(`/api/copilot/trends${query ? `?${query}` : ""}`);
  },

  getResearchGaps: (params?: { category?: string; verification_status?: string; dopant?: string }) => {
    const qs = new URLSearchParams();
    if (params?.category) qs.append("category", params.category);
    if (params?.verification_status) qs.append("verification_status", params.verification_status);
    if (params?.dopant) qs.append("dopant", params.dopant);
    const query = qs.toString();
    return request<ResearchGapsResponse>(`/api/copilot/gaps${query ? `?${query}` : ""}`);
  },

  getScientificConflicts: (params?: { dopant?: string }) => {
    const qs = new URLSearchParams();
    if (params?.dopant) qs.append("dopant", params.dopant);
    const query = qs.toString();
    return request<{ conflicts_count: number; conflicts: ScientificConflictItem[] }>(
      `/api/copilot/conflicts${query ? `?${query}` : ""}`
    ).then((res) => res.conflicts || []);
  },

  getScientificHypotheses: (params?: { category?: string; epistemic_type?: string; dopant?: string }) => {
    const qs = new URLSearchParams();
    if (params?.category) qs.append("category", params.category);
    if (params?.epistemic_type) qs.append("epistemic_type", params.epistemic_type);
    if (params?.dopant) qs.append("dopant", params.dopant);
    const query = qs.toString();
    return request<{ query_filters: any; total_hypotheses: number; hypotheses: ScientificHypothesisItem[] }>(
      `/api/copilot/hypotheses${query ? `?${query}` : ""}`
    );
  },

  getHypothesisById: (id: string) =>
    request<ScientificHypothesisItem>(`/api/copilot/hypotheses/${encodeURIComponent(id)}`),

  generateHypothesis: (payload: { gap_id?: string; topic?: string; category?: string }) =>
    request<ScientificHypothesisItem>("/api/copilot/hypotheses/generate", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  validateHypothesis: (payload: {
    candidate_formula: string;
    mn_frac: number;
    fe_frac: number;
    dopants?: any[];
  }) =>
    request<any>("/api/copilot/hypotheses/validate", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getVerificationMatrices: (params?: { hypothesis_id?: string; gap_id?: string; dopant?: string }) => {
    const qs = new URLSearchParams();
    if (params?.hypothesis_id) qs.append("hypothesis_id", params.hypothesis_id);
    if (params?.gap_id) qs.append("gap_id", params.gap_id);
    if (params?.dopant) qs.append("dopant", params.dopant);
    const query = qs.toString();
    return request<VerificationMatricesResponse>(`/api/copilot/verification-matrices${query ? `?${query}` : ""}`);
  },

  getVerificationMatrixById: (matrixId: string) =>
    request<ExperimentalVerificationMatrixItem>(`/api/copilot/verification-matrices/${encodeURIComponent(matrixId)}`),

  generateVerificationMatrix: (payload: { hypothesis_id?: string; gap_id?: string }) =>
    request<ExperimentalVerificationMatrixItem>("/api/copilot/verification-matrices/generate", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  // Authentication & Identity Verification APIs
  verifyGoogleToken: (credential: string) =>
    request<{
      status: string;
      session_token: string;
      user: {
        sub: string;
        email: string;
        fullName: string;
        account: string;
        avatarLetter: string;
        picture?: string;
        provider: string;
      };
    }>("/api/auth/google/verify", {
      method: "POST",
      body: JSON.stringify({ credential }),
    }),

  getCurrentUser: () =>
    request<{
      authenticated: boolean;
      user: {
        sub: string;
        email: string;
        fullName: string;
        account: string;
        avatarLetter: string;
        picture?: string;
        provider: string;
      };
    }>("/api/auth/me"),

  loginCredentials: (payload: { account: string; password: string; full_name?: string; mode?: string }) =>
    request<{
      status: string;
      session_token: string;
      user: {
        sub: string;
        email: string;
        fullName: string;
        account: string;
        avatarLetter: string;
        provider: string;
      };
    }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
