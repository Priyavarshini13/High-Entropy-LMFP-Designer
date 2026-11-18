# HE-LMFP-Designer — Product Readiness Audit
## Comprehensive Post Stage 5 Phase 4 Scientific & Technical Assessment

**Audit Date:** November 2, 2026  
**Audit Scope:** Full Application (8 Workspaces, 29 API Endpoints, 6 Critical Workflows, Data Repositories, ML Models)  
**Audit Mode:** Read-Only Verification (Zero Code or Data Modifications)  
**Overall Readiness Rating:** **CONDITIONAL PRODUCTION / DEMO READY WITH IDENTIFIED GUARDED DEFECTS**

---

## 1. Executive Summary

A comprehensive post-Stage 5 Phase 4 product readiness audit was conducted across the entire **HE-LMFP-Designer** application. Every workspace, API route, data store, and scientific calculation was evaluated through live execution, static code inspection, and contract reconciliation.

### Key Audit Findings:
1. **Core Scientific Strengths:**
   - **Deterministic Chemistry Engine:** Uncompromising chemical rigor. Charge neutrality ($\sum q_i = 0$), $Q_{M2} = 2.0000\text{ e}$ nominal for undoped $\text{LiMn}_{0.75}\text{Fe}_{0.25}\text{PO}_4$, lithium stoichiometry, and M2 site occupancy ($1.0000 \pm 0.0001$) are strictly enforced across materials design, hypothesis generation, and ML inference.
   - **Data Protection & Corpus Integrity:** The 1,215 × 41 master CSV, 35 literature reviews (Review #6 quarantined, Review #7 export-blocked), and 0-record laboratory database remain 100% intact with zero unauthorized mutations.
   - **Stage 5 Phase 4 Research Discovery Workspace:** The entire 7-step discovery pipeline (Trends → Gaps → Conflicts → Hypotheses → Chemical Validation → Verification Matrix → Experiment Handoff) is fully implemented, verified via automated E2E tests, and visually verified across desktop (1440×900) and mobile (390×844) viewports.
2. **Identified Product Deficiencies & Disconnects:**
   - **Triple Comparison Matrix Unperformed Fallback (Scientific Risk):** In `/api/experiments/compare` ([`backend/main.py#L1103-L1114`](file:///c:/Users/priya/Downloads/ECMT%20Works/HE-LMFP-Designer-AG/backend/main.py#L1103-L1114)), when an experiment has `initial_discharge_cap = None` (e.g. an unperformed `SYNTHESIS_PLANNED` candidate), the backend falls back to hardcoded values (`152.4 mAh/g` and `93.8%` retention). The UI displays these as "Actual Measured", conflating planned experiments with completed empirical measurements.
   - **Property Prediction Baseline Evaluation Contract Mismatch (Functional Disconnect):** The backend `/api/predictions/evaluation` returns target dictionaries at root (`{"0_1C_capacity": {...}, ...}`), but [`PropertyPredictionView.tsx#L265`](file:///c:/Users/priya/Downloads/ECMT%20Works/HE-LMFP-Designer-AG/frontend/src/components/PropertyPredictionView.tsx#L265) expects `evalData.targets`. Consequently, the "GroupKFold Baseline Evaluation" modal renders an empty body.
   - **Research Copilot Static Passage Indexing (Workflow Limitation):** When a new PDF is uploaded, extracted, and staged to `literature_review.db`, the in-memory Copilot passage index does not dynamically hot-reload. Newly uploaded records are not retrievable in Copilot QA until server restart.
   - **Deterministic Fallback Keyword Hardcoding:** When Ollama is offline, `DynamicScientificSynthesizer` in [`copilot/grounding.py`](file:///c:/Users/priya/Downloads/ECMT%20Works/HE-LMFP-Designer-AG/copilot/grounding.py#L311-L620) relies on extensive keyword matching tailored to benchmark papers (`srep26686`, `Reference [79]`, `Reference [29]`). Open-ended questions outside these patterns fall back to structured templates rather than conversational synthesis.
   - **Manual Experiment Form Hardcoded Dopants:** In [`ExperimentManagementView.tsx#L79-L85`](file:///c:/Users/priya/Downloads/ECMT%20Works/HE-LMFP-Designer-AG/frontend/src/components/ExperimentManagementView.tsx#L79-L85), the manual "+ Log New Experiment" form hardcodes a 5-dopant payload (`Mg, Zn, Nb, Cu, Zr`) on submit rather than allowing custom dopant entry.

---

## 2. Workspace-by-Workspace Functionality Matrix

Every feature is classified strictly according to actual execution and contract verification:

| Workspace | Sub-Feature / Capability | Status | Evidence / Verification Notes |
| :--- | :--- | :--- | :--- |
| **1. Dashboard** | Executive Metrics Grid (Corpus, ML, Reviews, Lab) | **FULLY FUNCTIONAL** | Live `/api/dashboard` returns 1,215 records, 4 models, 35 reviews, 0 lab experiments. |
| | Master Dataset Dopant Frequency Bar Chart | **FULLY FUNCTIONAL** | Derived dynamically from master CSV column `Dopant_Element`. |
| | Trained ML Model Performance Cards (GroupKFold $R^2$, MAE) | **FULLY FUNCTIONAL** | Sourced directly from `models/ml/artifacts/ml_metadata.json`. |
| | Module Navigation & Cross-Links | **FULLY FUNCTIONAL** | Navigates via hash routing (`#/discovery`, `#/copilot`, etc.). |
| | Discovery Studio Quick-Launch Banner | **FULLY FUNCTIONAL** | Banner directly routes to Research Discovery workspace. |
| **2. Literature Intelligence** | Literature Review Queue (Status filtering: all/pending/approved) | **FULLY FUNCTIONAL** | Sourced from `data/literature_review.db` (`extraction_reviews`). |
| | Review Detail & Metadata Editing | **FULLY FUNCTIONAL** | `GET/PUT /api/literature/reviews/{id}` updates stoichiometry and citations. |
| | PDF Document Ingestion & Page Extraction | **FULLY FUNCTIONAL** | PyMuPDF (`fitz`) extracts selectable text per page. |
| | Automated Doping Table & Property Extraction | **FULLY FUNCTIONAL** | Regex + section segmentation stages extracted records to `pending`. |
| | Safe Dataset Export Preview & Guardrails | **FULLY FUNCTIONAL** | `GET /api/literature/export/preview` enforces 3 blockers on Review #7, 0 exportable. |
| | Dataset Export Execution (`/api/literature/export`) | **FULLY FUNCTIONAL** | Dry-run enabled by default; blocks export when blockers exist. |
| | Sample Entity Graph Explorer (`/api/literature/samples`) | **FULLY FUNCTIONAL** | Returns 18 resolved sample entities with multi-condition C-rates. |
| | Sample Disambiguation & Resolution Updates | **FULLY FUNCTIONAL** | `POST /api/literature/samples/{id}/resolve` updates sample entity table. |
| **3. Research Copilot** | Intent Classification & Query Decomposition | **FULLY FUNCTIONAL** | `ScientificIntentClassifier` classifies 7 intents; decomposes sub-queries. |
| | Hybrid Literature Retrieval (BM25 + Structured + Entity) | **FULLY FUNCTIONAL** | Queries 1,215 CSV records + 35 review DB records. |
| | Grounded Generation via Qwen3-4B (Ollama) | **FULLY FUNCTIONAL** | Verified live via `/api/copilot/chat` with citation auditing. |
| | Deterministic Fallback Generation | **PARTIALLY FUNCTIONAL** | Uses keyword matching for benchmark papers; template for others. |
| | Dynamic Re-indexing on PDF Upload | **NOT IMPLEMENTED** | In-memory index created at startup; does not hot-reload after upload. |
| | Conversational Context & Multi-Turn Clarification | **FULLY FUNCTIONAL** | `ConversationContextResolver` handles referent ambiguity and pronouns. |
| **4. Materials Designer** | Mn/Fe Stoichiometric Adjustment & Boundaries | **FULLY FUNCTIONAL** | Live reactive sliders (Mn 0.60–0.75, Fe 0.10–0.30). |
| | Dopant Selection, Fraction & Oxidation State Editing | **FULLY FUNCTIONAL** | Supports 8 allowed dopants (Mg, Zn, Ni, Cu, Al, Ti, Zr, Nb). |
| | V1 Charge Neutrality & Lithium Compensation | **FULLY FUNCTIONAL** | $\sum q_i = 0$, adjusts Li vacancy delta ($\delta$). |
| | Configurational Entropy Calculation ($S_{\text{config}}$) | **FULLY FUNCTIONAL** | Classifies Low, Medium, or High-Entropy ($\ge 1.5R$). |
| | Practical & Theoretical Capacity Metrics | **FULLY FUNCTIONAL** | Computes Faraday theoretical capacity and 0.1C practical target. |
| | Preset Candidate Generation (`/api/materials/generate-candidates`) | **MOCK/HARDCODED** | Returns 3 static predefined candidate compositions. |
| **5. Property Prediction** | ML Inference (0.1C, 1C, 5C capacity, retention) | **FULLY FUNCTIONAL** | Random Forest models loaded from `.joblib` artifacts. |
| | Tree-Level Ensemble Standard Deviation Uncertainty | **FULLY FUNCTIONAL** | Evaluates `np.std(tree_preds)` across all estimators. |
| | Domain Coverage Warnings (Multi-doping, zero carbon) | **FULLY FUNCTIONAL** | Warns on $\ge 3$ dopants (only 6 in literature) and 0 wt% carbon. |
| | Chemical Pre-validation Enforcement | **FULLY FUNCTIONAL** | Strictly rejects non-stoichiometric inputs (M2 occupancy $\ne 1.0$) with 400. |
| | Baseline Cross-Validation Modal (`/api/predictions/evaluation`) | **PARTIALLY FUNCTIONAL** | Backend computation works; UI modal broken due to key contract mismatch. |
| **6. Experiment Management** | Experiment List & Filtering | **FULLY FUNCTIONAL** | Reads `data/lab_experiments.db` (currently 0 records). |
| | Manual "+ Log New Experiment" Form | **PARTIALLY FUNCTIONAL** | Saves experiment, but dopant list is hardcoded in submit handler. |
| | Experiment Transfer from Verification Matrix | **FULLY FUNCTIONAL** | Sets `SYNTHESIS_PLANNED`, leaves measurements null. |
| | Triple Comparison Matrix (Performed Experiment) | **FULLY FUNCTIONAL** | Compares Target Design, Literature Baseline, and Actual Lab data. |
| | Triple Comparison Matrix (Unperformed Experiment) | **MOCK/HARDCODED** | Defaults to `152.4 mAh/g` and `93.8%` when measurements are null. |
| **7. Research Discovery** | Topic Presets & Element Search | **FULLY FUNCTIONAL** | 8 presets + custom element/topic text search. |
| | Tab 1: Research Trends & Patterns | **FULLY FUNCTIONAL** | 4 dimensions (overview, dopant frequencies, Mn/Fe, routes). |
| | Tab 2: Research Gaps Explorer | **FULLY FUNCTIONAL** | 7 gap categories, `VERIFIED_LITERATURE_GAP` badging. |
| | Tab 3: Scientific Conflicts Explorer | **FULLY FUNCTIONAL** | Study A vs B findings, root cause categorization, resolution protocol. |
| | Tab 4: Scientific Hypotheses Inspector | **FULLY FUNCTIONAL** | 7 epistemic badges, chemical validation, falsification criteria. |
| | Tab 5: Experimental Verification Matrix Viewer | **FULLY FUNCTIONAL** | 3 controls (Replication, Negative, Target), 4-step synthesis plan. |
| | Matrix Handoff to Experiment Management | **FULLY FUNCTIONAL** | One-click transfer creating `EXP-...` with `SYNTHESIS_PLANNED`. |
| **8. Shared Infrastructure** | Master Literature CSV (`data/literature_reference.csv`) | **FULLY FUNCTIONAL** | Strictly preserved at 1,215 × 41. |
| | Literature Review DB (`data/literature_review.db`) | **FULLY FUNCTIONAL** | 35 reviews, Review #6 quarantined, Review #7 export-blocked. |
| | Lab Experiment DB (`data/lab_experiments.db`) | **FULLY FUNCTIONAL** | 0 experiments, no competing `experiments.db`. |
| | Machine Learning Artifact Inventory | **FULLY FUNCTIONAL** | 4 joblib models + `ml_metadata.json` intact. |
| | FastAPI SPA Static Serving (`/` and `/assets`) | **FULLY FUNCTIONAL** | Single-port full-stack serving tested and visually verified. |

---

## 3. Critical Researcher Workflow Verification

### Workflow A: Upload Paper → Extract Evidence → Review Records → Copilot Retrieval
- **Steps Verified:**
  1. User uploads a PDF via `/api/literature/extract-pdf`: PyMuPDF extracts text per page.
  2. Parser segments sections, identifies LMFP compositions, extracts capacities/retention, and stages records into `data/literature_review.db` with status `pending`.
  3. Reviewer inspects staged records in the Literature Review Queue.
- **Deficiency Identified:** Newly extracted records are written to SQLite, but `LMFPResearchCopilot` caches its passage index in memory. Unless the server is restarted or an explicit re-index endpoint is invoked, the new records are **not immediately retrievable** in Copilot chat.
- **Workflow Status:** **PARTIALLY FUNCTIONAL** (Upload, extraction, and review staging work; live Copilot hot-reindexing is missing).

### Workflow B: Multi-Paper Question → Retrieve Relevant Samples → Cited, Condition-Aware Answer
- **Steps Verified:**
  1. User submits: *"How does Mg doping influence rate capability at 5C?"*
  2. Retrieval planner executes BM25 search over 1,215 master records and review DB.
  3. Pre-generation sufficiency evaluator checks condition parity and policy distinctions.
  4. Response is generated via Qwen3-4B (when Ollama is active) or deterministic fallback.
  5. Citations are audited for verifiable page numbers, DOIs, sample labels, and quotes.
- **Deficiency Identified:** Deterministic fallback works excellently for benchmark-targeted keywords, but open-ended questions outside those keywords receive structured tabular templates rather than natural language synthesis.
- **Workflow Status:** **FULLY FUNCTIONAL (with Qwen3-4B) / PARTIALLY FUNCTIONAL (deterministic fallback)**.

### Workflow C: Design Composition → Validate Stoichiometry → Inspect Oxidation States
- **Steps Verified:**
  1. User adjusts Mn to 0.65, Fe to 0.26, and selects 5 dopants (Mg, Zn, Nb, Cu, Zr).
  2. V1 Chemistry Engine verifies M2 site occupancy $\sum x_{\text{M2}} = 1.0000$.
  3. Charge balance module evaluates total positive cation charge against $\text{PO}_4^{3-}$ ($6.0000\text{ e}$ negative).
  4. Lithium vacancy compensation computes adjusted $\text{Li} = 0.9300$ ($\delta = 0.0700$ vacancies).
  5. Formula is formatted as $\text{Li}_{0.93}[\text{Mn}_{0.65}\text{Fe}_{0.26}\text{Mg}_{0.02}\text{Zn}_{0.02}\text{Nb}_{0.01}\text{Cu}_{0.02}\text{Zr}_{0.02}]\text{PO}_4$.
  6. Configurational entropy is calculated: $S_{\text{config}} = 1.0772\text{ R}$ (Medium-Entropy).
- **Workflow Status:** **FULLY FUNCTIONAL**.

### Workflow D: Property Prediction → Verify Availability, Domain, Limitations & Uncertainty
- **Steps Verified:**
  1. User inputs composition and sintering parameters (650°C, 6.0 h, 2.0 wt% carbon).
  2. Pre-inference guardrail enforces M2 site occupancy (returns 400 if invalid).
  3. Random Forest models infer discharge capacity at 0.1C, 1C, 5C, and cycling retention.
  4. Tree standard deviation is reported: e.g. $146.50 \pm 4.12\text{ mAh/g}$ at 0.1C, $112.40 \pm 6.85\text{ mAh/g}$ at 5C.
  5. Coverage warning alerts researcher when $\ge 3$ dopants are present (noting only 6 such records exist in the literature).
- **Deficiency Identified:** Clicking "GroupKFold Baseline Evaluation" in the UI triggers a modal fetch, but because the backend returns targets at root while the frontend expects `evalData.targets`, the modal body renders blank.
- **Workflow Status:** **FULLY FUNCTIONAL (Prediction & Uncertainty) / PARTIALLY FUNCTIONAL (Baseline Evaluation Modal)**.

### Workflow E: Verification Matrix → Transfer to Experiment Management → Preserve Proposed Status
- **Steps Verified:**
  1. User generates matrix `MAT-LMFP-SYNTH-01` from hypothesis `HYP-LMFP-SYNTH-01`.
  2. Matrix details 3 control samples (`REPLICATION_BASELINE`, `NEGATIVE_CONTROL_UNDOPED`, `TARGET_CANDIDATE`).
  3. Synthesis plan specifies 4 steps; characterization specifies XRD, SEM, XPS, Raman.
  4. User clicks "Transfer to Experiment Management".
  5. Experiment record `EXP-...` is created with status strictly `SYNTHESIS_PLANNED`.
  6. Measured capacities and retention are strictly null (`None` in SQLite).
- **Workflow Status:** **FULLY FUNCTIONAL**.

### Workflow F: Discover Trends → Identify Gaps & Conflicts → Generate Hypotheses → Link Evidence
- **Steps Verified:**
  1. User filters trends by "Spray Drying Precursors (`srep26686`)".
  2. Trend engine reports 1,215 records, synthesis route frequencies, and precursor distribution.
  3. Research Gap engine highlights `GAP-SYNTH-01` (`VERIFIED_LITERATURE_GAP`).
  4. Conflict engine highlights Study A vs Study B findings with suggested reconciliation protocol.
  5. Hypothesis engine synthesizes `HYP-LMFP-SYNTH-01` with 7 epistemic badges, chemical validation ($Q_{M2} = 2.0000\text{ e}$), falsification criteria, and alternative explanations.
  6. Verification matrix `MAT-LMFP-SYNTH-01` provides concrete experimental protocol.
- **Workflow Status:** **FULLY FUNCTIONAL**.

---

## 4. Scientific Reliability & Epistemic Audit

### 4.1 Evidence Provenance and Citations
- **Audit Result:** **HIGH RELIABILITY**. Every passage in the Copilot index contains traceable provenance (`paper_id`, `doi`, `page_number`, `sample_id`, `section_type`, `provenance_type`).
- In Qwen3-4B generation, `audit_citations_and_claims` verifies that any cited paper ID and page number exists in the retrieved evidence before presenting citations to the user.

### 4.2 Primary vs Secondary Literature Distinction
- **Audit Result:** **VERIFIED & ENFORCED**. The system explicitly distinguishes primary experimental studies (e.g. `srep26686`) from secondary review compilations (e.g. `Reference [29]`, `Reference [79]`). Secondary review records are tagged with `is_secondary_review_reference: true` and display distinct badges.

### 4.3 Sample Identity Resolution
- **Audit Result:** **VERIFIED & ENFORCED**. In multi-sample papers (such as `srep26686`), samples `SD_NO3` and `SD_SO4` are maintained as distinct entities with separate synthesis routes, phase purities, and discharge capacities. The system never merges them or attributes `SD_SO4`'s 1,000-cycle retention to `SD_NO3`.

### 4.4 Experimental Condition Parity
- **Audit Result:** **VERIFIED & ENFORCED**. The sufficiency evaluator explicitly flags condition non-parity when comparing:
  - Voltage cutoffs: 2.0–4.2 V vs 2.5–4.5 V (warning that 4.2 V only partially accesses the 4.1 V $\text{Mn}^{2+}/\text{Mn}^{3+}$ plateau).
  - Active mass loadings: $<1.0\text{ mg/cm}^2$ vs $>2.5\text{ mg/cm}^2$ (warning of concentration polarization in thick electrodes).
  - Thermal dwell times and atmospheres: $\text{Ar}$ vs $\text{Ar/H}_2$ vs air.

### 4.5 Chemical Formula & Charge-Balance Validation
- **Audit Result:** **MATHEMATICALLY EXACT**.
  - Nominal undoped $\text{LiMn}_{0.75}\text{Fe}_{0.25}\text{PO}_4$: strictly $Q_{M2} = 2.0000\text{ e}$, $\sum q_i = 0$, $\Delta \text{Li} = 0.0000$.
  - Aliovalent substitution: e.g. $\text{Ti}^{4+}$ ($x = 0.02$) correctly decreases required Li to $1.0000 - 2(0.02) = 0.9600$, creating $\delta = 0.0400$ lithium vacancies for exact electroneutrality.

### 4.6 Dopant Oxidation-State Assumptions
- **Audit Result:** **TRANSPARENTLY COMMUNICATED**.
  - Default oxidation states: $\text{Ti} = +4$, $\text{Mg} = +2$, $\text{Zn} = +2$, $\text{Ni} = +2$, $\text{Cu} = +2$, $\text{Al} = +3$, $\text{Zr} = +4$, $\text{Nb} = +5$.
  - For multi-valent elements ($\text{Ti}^{3+}/\text{Ti}^{4+}$, $\text{Cu}^{2+}/\text{Cu}^{3+}$), the UI and chemical validation report explicitly display the chosen oxidation state and note that reducing calcination atmospheres ($\text{Ar/H}_2$) can stabilize lower oxidation states.

### 4.7 ML Training-Domain Limitations
- **Audit Result:** **PROMINENTLY DISCLOSED**.
  - The model summary notes that out of 1,215 master literature records, only 6 contain 3 or more dopants.
  - The predictor emits an explicit coverage warning whenever $\ge 3$ dopants are requested, stating that predictions are exploratory literature baselines rather than high-confidence interpolations.

### 4.8 Experiment Proposal vs Performed Experiment
- **Audit Result:** **CRITICAL DEFECT DETECTED IN COMPARISON MATRIX**.
  - When experiments are transferred from verification matrices into `data/lab_experiments.db`, they are correctly saved with `status = SYNTHESIS_PLANNED` and measured metrics set to `None`.
  - **However:** When viewing this experiment in the Triple Comparison Matrix (`/api/experiments/compare`), [`backend/main.py#L1103-L1114`](file:///c:/Users/priya/Downloads/ECMT%20Works/HE-LMFP-Designer-AG/backend/main.py#L1103-L1114) substitutes `exp_cap = 152.4` and `exp_ret = 93.8` if measured values are missing, causing the UI to display `Actual Measured: 152.4 mAh/g` for an experiment that has never been performed.

---

## 5. Comprehensive Catalog of Mock / Hardcoded Functionality

The following table documents every mock, simulated, or hardcoded implementation identified in the codebase:

| Location | Description of Mock / Hardcoding | Scientific or Functional Consequence |
| :--- | :--- | :--- |
| [`backend/main.py#L1103-L1114`](file:///c:/Users/priya/Downloads/ECMT%20Works/HE-LMFP-Designer-AG/backend/main.py#L1103-L1114) | Hardcoded fallback values `exp_cap = 152.4` and `exp_ret = 93.8` in `/api/experiments/compare`. | Fabricates "Actual Measured" data in the comparison matrix for unperformed experiments. |
| [`backend/main.py#L401-L441`](file:///c:/Users/priya/Downloads/ECMT%20Works/HE-LMFP-Designer-AG/backend/main.py#L401-L441) | Static candidate list in `/api/materials/generate-candidates` (always returns the same 3 presets). | Limits Materials Designer candidate exploration to 3 hardcoded formulas instead of algorithmic discovery. |
| [`backend/main.py#L385-L392`](file:///c:/Users/priya/Downloads/ECMT%20Works/HE-LMFP-Designer-AG/backend/main.py#L385-L392) | Hardcoded synthesis parameters: `"Not specified by supervisor"`. | Synthesis recommendations in Materials Designer are placeholder strings. |
| [`copilot/grounding.py#L311-L620`](file:///c:/Users/priya/Downloads/ECMT%20Works/HE-LMFP-Designer-AG/copilot/grounding.py#L311-L620) | Hardcoded keyword-matching answers for benchmark queries in deterministic fallback. | Deterministic fallback works well for known benchmark questions, but cannot generalize to unpatterned queries. |
| [`frontend/src/components/ExperimentManagementView.tsx#L79-L85`](file:///c:/Users/priya/Downloads/ECMT%20Works/HE-LMFP-Designer-AG/frontend/src/components/ExperimentManagementView.tsx#L79-L85) | Hardcoded 5-dopant payload (`Mg, Zn, Nb, Cu, Zr`) in manual "+ Log New Experiment" handler. | User cannot specify custom dopants when manually recording a lab experiment via the form. |
| [`frontend/src/components/ExperimentManagementView.tsx#L332`](file:///c:/Users/priya/Downloads/ECMT%20Works/HE-LMFP-Designer-AG/frontend/src/components/ExperimentManagementView.tsx#L332) | Hardcoded green badge class: `className="badge badge-green"`. | Displays green "tested" styling even for unperformed `SYNTHESIS_PLANNED` experiments. |

---

## 6. Broken or Disconnected Integrations

1. **Property Prediction GroupKFold Modal Contract Disconnect:**
   - **Backend Route:** `GET /api/predictions/evaluation` returns `{"0_1C_capacity": {...}, "1C_capacity": {...}, ...}`.
   - **Frontend Consumer:** [`PropertyPredictionView.tsx#L265, L281`](file:///c:/Users/priya/Downloads/ECMT%20Works/HE-LMFP-Designer-AG/frontend/src/components/PropertyPredictionView.tsx#L265) checks `evalData && evalData.targets` and maps over `evalData.targets`.
   - **Failure Mode:** `evalData.targets` is `undefined`, causing the modal to render an empty body.
2. **Dynamic Copilot Index Reload Disconnect (Workflow A):**
   - **Backend Route:** `POST /api/literature/extract-pdf` saves extracted records into SQLite table `extraction_reviews`.
   - **Consumer:** `LMFPResearchCopilot` in [`copilot/engine.py`](file:///c:/Users/priya/Downloads/ECMT%20Works/HE-LMFP-Designer-AG/copilot/engine.py) initializes its `ScientificPassageIndex` once at server boot.
   - **Failure Mode:** Newly extracted records in `literature_review.db` are not retrievable in Copilot QA during the same running process.
3. **Manual Experiment Form vs Data Model Disconnect:**
   - **Frontend UI:** The form has fields for synthesis temperature, time, and carbon wt%, but no dopant selector fields.
   - **Failure Mode:** The form silently submits a default 5-dopant list, overriding whatever dopants the researcher might have intended.

---

## 7. Prioritized Defect Register

### Critical Severity (Must be resolved before founder demonstration)
- **CRIT-1: Unperformed Experiment Data Fabrication in Comparison Matrix**
  - *Location:* [`backend/main.py#L1103-L1114`](file:///c:/Users/priya/Downloads/ECMT%20Works/HE-LMFP-Designer-AG/backend/main.py#L1103-L1114) and [`ExperimentManagementView.tsx#L415-L426`](file:///c:/Users/priya/Downloads/ECMT%20Works/HE-LMFP-Designer-AG/frontend/src/components/ExperimentManagementView.tsx#L415-L426)
  - *Impact:* An unperformed experiment (`status = SYNTHESIS_PLANNED`) displays `Actual Measured: 152.4 mAh/g` in the Triple Comparison Matrix. A founder or scientific advisor inspecting the tool will immediately notice fabricated experimental measurements.

### High Severity (Direct UI breakage or major workflow limitation)
- **HIGH-1: Property Prediction Baseline Evaluation Modal Empty Body**
  - *Location:* [`frontend/src/components/PropertyPredictionView.tsx#L265, L281`](file:///c:/Users/priya/Downloads/ECMT%20Works/HE-LMFP-Designer-AG/frontend/src/components/PropertyPredictionView.tsx#L265)
  - *Impact:* Clicking "GroupKFold Baseline Evaluation" opens a blank modal body.
- **HIGH-2: Missing Dynamic Re-indexing in Copilot after PDF Upload**
  - *Location:* [`backend/main.py#L583-L596`](file:///c:/Users/priya/Downloads/ECMT%20Works/HE-LMFP-Designer-AG/backend/main.py#L583-L596) and [`copilot/index.py#L63`](file:///c:/Users/priya/Downloads/ECMT%20Works/HE-LMFP-Designer-AG/copilot/index.py#L63)
  - *Impact:* Workflow A (Upload → Review → Chat) fails to retrieve newly uploaded paper findings in Copilot without restarting the backend.

### Medium Severity (Functional limitations with workarounds)
- **MED-1: Manual Experiment Form Dopant Hardcoding**
  - *Location:* [`frontend/src/components/ExperimentManagementView.tsx#L79-L85`](file:///c:/Users/priya/Downloads/ECMT%20Works/HE-LMFP-Designer-AG/frontend/src/components/ExperimentManagementView.tsx#L79-L85)
  - *Impact:* User cannot customize dopants when logging an experiment manually. (Workaround: transfer from Verification Matrix works cleanly).
- **MED-2: Experiment Status Badge Visual Ambiguity**
  - *Location:* [`frontend/src/components/ExperimentManagementView.tsx#L332`](file:///c:/Users/priya/Downloads/ECMT%20Works/HE-LMFP-Designer-AG/frontend/src/components/ExperimentManagementView.tsx#L332)
  - *Impact:* `SYNTHESIS_PLANNED` uses `badge-green` (the same color as completed/tested). It should use `badge-amber` or `badge-purple`.
- **MED-3: Static Candidate Presets in Materials Designer**
  - *Location:* [`backend/main.py#L401-L459`](file:///c:/Users/priya/Downloads/ECMT%20Works/HE-LMFP-Designer-AG/backend/main.py#L401-L459)
  - *Impact:* Candidate generation button always loads the exact same 3 preset designs.

### Low Severity (Cosmetic & edge-case improvements)
- **LOW-1: PyMuPDF Deprecation Warning**
  - *Location:* `import fitz` in `literature/pdf_extractor.py` and `copilot/index.py`.
  - *Impact:* Emits a harmless `FutureWarning: The fitz API is deprecated and will be removed in future. Use import pymupdf instead.` during startup.

---

## 8. Recommended Remediation Plan (In Implementation Order)

When authorized to implement fixes, the work should proceed in the following prioritized sequence:

1. **Step 1: Fix Unperformed Experiment Handling in Comparison Matrix (CRIT-1)**
   - Update `/api/experiments/compare` in `backend/main.py`: If `exp.electrochemical_data.initial_discharge_cap is None`, return `measured_discharge_cap: None` and `measured_retention: None` rather than falling back to 152.4 and 93.8.
   - Update `ExperimentManagementView.tsx`: If `actual_experiment.measured_discharge_cap === null`, display `Pending Physical Synthesis / Unperformed` and suppress delta residuals.
2. **Step 2: Reconcile Property Prediction Evaluation Modal Contract (HIGH-1)**
   - Update `backend/main.py:get_prediction_evaluation`: Wrap the returned dictionary in `{"targets": eval_res}` so it satisfies the frontend contract, or update `PropertyPredictionView.tsx` to handle `evalData.targets || evalData`.
3. **Step 3: Implement Copilot Index Hot-Reload on PDF Extraction (HIGH-2)**
   - Add a lightweight index refresh trigger in `backend/main.py` after `save_extraction(...)` finishes, updating `get_research_copilot().retriever.index.build_index()` so uploaded evidence is immediately queryable.
4. **Step 4: Update Experiment Management Status Badges & Form (MED-1, MED-2)**
   - Add conditional badge styling in `ExperimentManagementView.tsx` (`SYNTHESIS_PLANNED` → `badge-amber`; `tested` → `badge-green`).
   - Add a basic dopant selection interface to the manual experiment modal.
5. **Step 5: Dynamic Candidate Exploration in Materials Designer (MED-3)**
   - Enhance `/api/materials/generate-candidates` to accept user constraints (target entropy, preferred dopants) and synthesize diverse stoichiometric candidates dynamically.

---

## 9. Founder Demonstration Readiness Assessment

### Overall Verdict: **READY FOR DEMONSTRATION WITH TARGETED GUARDRAILS**

The platform is remarkably capable, visually compelling, and grounded in rigorous solid-state battery chemistry. It clearly surpasses generic battery chatbots by demonstrating domain-specific thermodynamic calculations, multi-condition literature retrieval, and systematic gap/hypothesis generation.

### Recommended Founder Demonstration Script:
1. **Introduction & Dashboard:** Open on `http://localhost:8000/#dashboard`. Highlight the 1,215 peer-reviewed sample corpus, the 4 GroupKFold-validated Random Forest models, and the protected literature review database.
2. **Research Discovery Studio (The Flagship Workflow):**
   - Navigate to **Discovery Studio** (`#research-discovery`).
   - Select topic preset **"Spray Drying Precursors (`srep26686`)"**.
   - Show Tab 1 (Trends): Explain the distinction between total material samples (1,215) and comparable matched-condition measurements.
   - Show Tab 2 (Gaps): Point out `GAP-SYNTH-01` (`VERIFIED_LITERATURE_GAP`), highlighting missing counter-anion controls and confounding variables.
   - Show Tab 3 (Conflicts): Show the conflict between Study A (sulfate) and Study B (nitrate) with the proposed antioxidant reconciliation protocol.
   - Show Tab 4 (Hypotheses): Formulate `HYP-LMFP-SYNTH-01`, highlight the 7 epistemic breakdown badges, falsification criteria, and chemical validation showing $Q_{M2} = 2.0000\text{ e}$ and zero lithium vacancies.
   - Show Tab 5 (Matrix): Review `MAT-LMFP-SYNTH-01` showing the 3 control samples (`CTRL_SD_SO4`, `CTRL_SD_NO3`, `TEST_SD_NO3_ASC`), the 4-step synthesis plan, characterization battery, and testing protocols.
   - Click **"Transfer to Experiment Management"**: Show that it creates `EXP-...` with status `SYNTHESIS_PLANNED` and completely avoids fabricating test data.
3. **Materials Designer:** Navigate to **Materials Designer** (`#materials-designer`). Adjust Mn/Fe ratios and add $\text{Ti}^{4+}$ or $\text{Nb}^{5+}$. Show how the V1 Chemistry Engine automatically adjusts Li stoichiometry and computes configurational entropy ($S_{\text{config}} \ge 1.5R$).
4. **Property Prediction:** Run ML predictions for a designed composition. Highlight the tree standard deviation uncertainty ($\pm \sigma$) and the data coverage warning for multi-dopant compositions.
5. **Research Copilot QA:** Ask: *"How does Mg doping influence rate capability at 5C?"* Show the cited evidence passages, sample provenance, and condition parity warnings.

### Specific Demonstration Warnings for Presenter:
- **Avoid:** Clicking "+ Log New Experiment" manually without mentioning that manual dopant customization is scheduled for next release (transferring from Discovery Studio works cleanly).
- **Avoid:** Clicking "GroupKFold Baseline Evaluation" modal in Property Prediction until Step 2 of the remediation plan is applied.
- **Avoid:** Viewing an unperformed experiment in the Triple Comparison Matrix until Step 1 of the remediation plan is applied.

---

*Report prepared and validated via live execution audit. All work halted awaiting review.*
