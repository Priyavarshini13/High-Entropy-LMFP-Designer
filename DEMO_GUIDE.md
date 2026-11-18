# High-Entropy LMFP Materials Designer — Supervisor Demonstration Guide

**Project**: AI-Assisted High-Entropy Doped $\text{LiMn}_{1-x-y}\text{Fe}_x\text{M}_y\text{PO}_4$ (HE-LMFP) Formula & Materials Design Platform  
**Target Audience**: Academic Supervisor, Thesis Committee, and Laboratory Researchers  
**Estimated Demo Duration**: 5–10 minutes  

---

## 1. System Architecture & Prerequisites

### Architecture Overview
The platform connects a deterministic cathode chemistry engine and machine learning surrogates with a modern web interface:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        React 18 + TypeScript + Vite                   │
│         (Tailwind-styled Design Studio, Local Port: 5173)              │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │ REST API (JSON)
┌────────────────────────────────────▼───────────────────────────────────┐
│                           FastAPI Backend                              │
│                    (Uvicorn Server, Local Port: 8000)                  │
├─────────────────────┬──────────────────────┬───────────────────────────┤
│ Deterministic Engine│ ML Surrogates (RF)   │ Storage & Intelligence    │
│ - Charge Neutrality │ - 0.1C, 1C, 5C Cap.  │ - Master CSV (1,215x41)   │
│ - Li Vacancy δ      │ - Capacity Retention │ - Review DB (SQLite)      │
│ - Shannon Radii/M2  │ - GroupKFold (DOI)   │ - Lab Experiments (SQLite)│
│ - Entropy (S_config)│ - Tree Dispersion    │ - Grounded Copilot (RAG)  │
└─────────────────────┴──────────────────────┴───────────────────────────┘
```

### Prerequisites
- **Python**: 3.11.x (with dependencies installed via `pip install -r requirements.txt`)
- **Node.js**: 18.x or 20.x LTS with `npm`
- **Modern Web Browser**: Chrome, Edge, Firefox, or Safari (Desktop resolution 1440×900 or higher recommended)

---

## 2. Startup Instructions

Run the backend and frontend in two separate terminal windows.

### Terminal 1: FastAPI Backend
```powershell
# Navigate to the project root
cd "C:\Users\priya\Downloads\ECMT Works\HE-LMFP-Designer-AG"

# Launch Uvicorn server
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
- **Backend API**: `http://127.0.0.1:8000`
- **Interactive Swagger Docs**: `http://127.0.0.1:8000/docs`
- **Health Check**: `http://127.0.0.1:8000/api/health`

### Terminal 2: React Frontend
```powershell
# Navigate to the frontend directory
cd "C:\Users\priya\Downloads\ECMT Works\HE-LMFP-Designer-AG\frontend"

# Launch Vite development server
npm run dev
```
- **Web Application URL**: `http://localhost:5173`

*Note: In the top right corner of the application shell, confirm the status badge shows `● FastAPI Online (Port 8000)`.*

---

## 3. Recommended 5–10 Minute Demo Script

### Minute 1: Executive Dashboard (`/#dashboard`)
1. Open `http://localhost:5173`.
2. **Point out the Master Literature Corpus card**:
   - 1,215 curated records extracted across 159 peer-reviewed publications.
3. **Showcase the Machine Learning Model Suite**:
   - 4 models validated under GroupKFold cross-validation (`0.1C`, `1C`, `5C`, and `Capacity Retention`) displaying green `READY` status pills.
   - 2 targets (`0.05C` and `Initial Coulombic Efficiency`) honestly flagged as `INSUFFICIENT DATA` because fewer than 50 verified literature points exist.
4. **Inspect Dopant Distribution**:
   - Show empirical frequencies of transition-metal dopants across published literature (Ni, Mg, Ti, Zn, Al, etc.).

---

### Minute 2: Literature Intelligence & Safe Export (`/#literature`)
1. Click **"Literature AI"** in the sidebar.
2. **Review Queue Walkthrough**:
   - Explain the human-in-the-loop review architecture.
   - Show existing review records: 3 pending, 1 approved, 3 rejected.
3. **Safe Export Barrier Demonstration**:
   - Click the blue **"Safe Export Preview"** button in the top right.
   - Show the slide-over drawer:
     - `Exportable records: 0`
     - `Blocked records: 1`
   - Point out Review #7 (Ni-doped solvothermal LMFP) is **blocked** from export because it reports multi-condition retention (`89.45% at 0.1C, 89.11% at 2C, 88.68% at 10C`) and lacks reviewer-confirmed `Paper_ID` and `Sample_ID`.
   - Explain that the master dataset (`data/literature_reference.csv`, 1,215 × 41) is protected by automated defense-in-depth safety checks.

---

### Minute 3: Research Copilot (`/#copilot`)
1. Click **"Research Copilot"** in the sidebar.
2. **Demonstrate Grounded Retrieval**:
   - Click the suggested prompt chip: *"What dopants improve rate capability at 5C?"*
3. **Review Output**:
   - Highlight the verified literature evidence citing specific papers and DOIs.
   - Show the **"Chemistry Engine Rules"** section enforcing supervisor stoichiometry boundaries ($0.60 \le \text{Mn} \le 0.75$, $0.10 \le \text{Fe} \le 0.30$, and 3–5 dopant elements).
   - Point out the scientific disclaimer clarifying that AI responses assist hypothesis generation and require laboratory validation.

---

### Minute 4–5: Materials Designer & Deterministic Chemistry (`/#materials`)
1. Click **"Materials Designer"** in the sidebar.
2. **Load High-Entropy Preset**:
   - Click **"⚡ Generate Balanced Candidates"** at the top.
   - Click **"Apply Composition →"** on `Supervisor Reference Baseline (5-Dopant)`.
3. **Examine Live Stoichiometry**:
   - Primary cations: $\text{Mn}^{2+} = 0.65\text{ mol}$, $\text{Fe}^{2+} = 0.26\text{ mol}$.
   - 5 Dopant elements: $\text{Mg}^{2+} (0.02)$, $\text{Zn}^{2+} (0.02)$, $\text{Nb}^{5+} (0.01)$, $\text{Cu}^{2+} (0.02)$, $\text{Zr}^{4+} (0.02)$.
   - Sum of M2 site cations = $1.000\text{ mol}$ (Strictly enforced).
4. **Inspect Deterministic Chemistry Report**:
   - Generated normalized formula: `Li0.93[Mn0.65Fe0.26Mg0.02Zn0.02Nb0.01Cu0.02Zr0.02]PO4`.
   - Li vacancy compensation: $\delta = 0.0700$ (balances the $+2.07\text{ e}$ average M2 site cation valence).
   - Configurational entropy: $S_{\text{config}}/R = 0.9893R$ ($8.2252\text{ J}\cdot\text{mol}^{-1}\cdot\text{K}^{-1}$), classified as `ENTROPY-ASSISTED / MEDIUM-ENTROPY`.
5. **Capacity Metric Disclosure**:
   - Highlight that the supervisor-mandated **Theoretical Capacity Benchmark is fixed at $170.0\text{ mAh/g}$**.
   - Show the Practical Reference ($150\text{--}160\text{ mAh/g}$ at 0.1C).
   - Show the Faraday formula-dependent calculated metric ($158.3\text{ mAh/g}$), clearly labeled to explain that it does not replace the supervisor benchmark.

---

### Minute 6–7: Property Prediction & Scientific Transparency (`/#prediction`)
1. Click **"Property Prediction"** in the sidebar.
2. Click **"⚡ Run ML Predictions"**.
3. **Explain Predicted Outputs**:
   - **0.1C Discharge Capacity**: $\sim 152.8\text{ mAh/g} \pm 15.9\text{ mAh/g}$.
   - **1C Discharge Capacity**: $\sim 136.1\text{ mAh/g} \pm 9.8\text{ mAh/g}$.
   - **5C Discharge Capacity**: $\sim 109.3\text{ mAh/g} \pm 32.4\text{ mAh/g}$.
   - **Capacity Retention**: $\sim 86.9\% \pm 8.5\%$.
4. **Emphasize Scientific Transparency**:
   - Point out the label: **`Model Dispersion (Tree Std Dev)`** with the note **`Uncalibrated tree dispersion`**. Clarify that this reflects tree ensemble variance, not a calibrated statistical confidence interval.
5. **Open GroupKFold Baseline Evaluation Modal**:
   - Click the top button **"📊 GroupKFold Baseline Evaluation"**.
   - Show the comparative table against training-fold medians:
     - Point out that **only 5C Discharge Capacity outperforms the median baseline** ($R^2 = +0.243$, MAE reduction of $4.97\text{ mAh/g}$).
     - Honestly explain that for 0.1C, 1C, and retention, the simple median baseline achieves comparable or superior generalization due to significant cross-laboratory synthesis batch variability.

---

### Minute 8: Experiment Management & Triangulation (`/#experiments`)
1. Click **"Experiments"** in the sidebar.
2. **Show Clean Registry State**:
   - Point out that the laboratory experiment registry is in a clean, baseline state (0 records logged).
3. **Inspect Experiment Batch Form (Read-Only Demo Walkthrough)**:
   - Click **"+ Log New Experiment"**.
   - Show the structured lab batch entry modal: synthesis route selection (`sol-gel`, `solid-state`, `co-precipitation`), thermal calcination parameters ($650^\circ\text{C}$, $6.0\text{ h}$), XRD characterization, and electrochemical cycling fields.
   - Note that the stoichiometry defaults to the balanced candidate ($\text{Mn}=0.65, \text{Fe}=0.26$, 5 dopants) to streamline laboratory entry.
   - Click **"✕"** to close the modal without writing test data to the database, maintaining database cleanliness.
4. **Explain Triple Comparison Triangulation**:
   - Explain how when real laboratory experimental batches are logged, the platform triangulates the measured experimental performance against both the target stoichiometric design and the 1,215 literature master baseline records.

---

## 4. Sample Safe Compositions for Live Testing

| Parameter | Recommended Safe Example 1 | Recommended Safe Example 2 |
|---|---|---|
| **Manganese ($\text{Mn}^{2+}$)** | $0.65\text{ mol}$ | $0.70\text{ mol}$ |
| **Iron ($\text{Fe}^{2+}$)** | $0.26\text{ mol}$ | $0.20\text{ mol}$ |
| **Dopant 1** | $\text{Mg}^{2+} (0.02\text{ mol})$ | $\text{Mg}^{2+} (0.02\text{ mol})$ |
| **Dopant 2** | $\text{Zn}^{2+} (0.02\text{ mol})$ | $\text{Ti}^{4+} (0.02\text{ mol})$ |
| **Dopant 3** | $\text{Nb}^{5+} (0.01\text{ mol})$ | $\text{Al}^{3+} (0.02\text{ mol})$ |
| **Dopant 4** | $\text{Cu}^{2+} (0.02\text{ mol})$ | $\text{Zr}^{4+} (0.02\text{ mol})$ |
| **Dopant 5** | $\text{Zr}^{4+} (0.02\text{ mol})$ | $\text{Ni}^{2+} (0.02\text{ mol})$ |
| **Sum M2** | **$1.000\text{ mol}$** | **$1.000\text{ mol}$** |
| **Resulting Formula** | `Li0.93[Mn0.65Fe0.26Mg0.02Zn0.02Nb0.01Cu0.02Zr0.02]PO4` | `Li0.90[Mn0.70Fe0.20Mg0.02Ti0.02Al0.02Zr0.02Ni0.02]PO4` |
| **Li Vacancy $\delta$** | $0.0700$ | $0.1000$ |

---

## 5. Sample Questions for Research Copilot

1. *"What dopants improve rate capability at 5C?"*  
   *Expected: Highlights Nb and Ti dopants that reduce charge transfer resistance and enhance lithium-ion diffusion.*
2. *"Why is Mg + Ti co-doping effective in LMFP?"*  
   *Expected: Discusses Mg occupying M2 sites to stabilize the lattice framework and Ti reducing polaronic conduction barriers.*
3. *"What are the allowed Mn and Fe ranges?"*  
   *Expected: Explains supervisor rules ($0.60 \le \text{Mn} \le 0.75$, $0.10 \le \text{Fe} \le 0.30$) and Jahn-Teller distortion trade-offs.*
4. *"What is the theoretical capacity of LMFP?"*  
   *Expected: Clarifies that the supervisor reference is $170.0\text{ mAh/g}$ ($1\text{ Li}^+$ per formula unit), with practical targets at $150\text{--}160\text{ mAh/g}$ at 0.1C.*

---

## 6. Scientific Limitations & Transparency Summary

1. **Surrogate ML Role**:
   - Random Forest models are preliminary empirical surrogates intended for multi-element screening. They do not substitute for physical synthesis or potentiostatic cycling.
2. **Baseline Generalization**:
   - GroupKFold cross-validation grouped strictly by publication reveals high inter-laboratory variance. Only 5C discharge capacity shows a statistically significant MAE reduction ($4.97\text{ mAh/g}$) over fold medians.
3. **Data Integrity Barriers**:
   - Review #6 contains test contamination and is quarantined with an audit note; it cannot be exported.
   - Review #7 contains multiple cycling condition measurements and missing publication provenance; it is automatically blocked from altering the master CSV.
   - The master literature dataset is strictly maintained at 1,215 records and 41 columns.

---

## 7. Troubleshooting & FAQ

| Symptom | Cause | Solution |
|---|---|---|
| Topbar shows `Backend Offline` | FastAPI backend is not running on port 8000 | Run `uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload` in project root. |
| Port 8000 or 5173 is already in use | Stale background process holding the port | Run `Get-Process python` or `netstat -ano \| findstr :8000` in PowerShell and terminate the stale PID. |
| M2 Occupancy warning on Designer | Cation fractions do not sum to exactly 1.0000 | Adjust Mn, Fe, or dopant sliders so that $\text{Mn} + \text{Fe} + \sum x_i = 1.0000$. Or click "Generate Balanced Candidates". |
| Database connection error | Supabase/PostgreSQL unreachable | The system automatically falls back to local SQLite (`data/lab_experiments.db`). Ensure `DATABASE_URL` is unset or valid. |
