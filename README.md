# High-Entropy Doped LMFP Formula & Materials Design Platform (HE-LMFP-Designer-AG)

A standalone, computational materials-design application for Lithium Manganese Iron Phosphate (LMFP) cathode materials with multi-element high-entropy cation doping.

---

## 1. Project Purpose & Scientific Scope

The **HE-LMFP Designer** provides a deterministic chemical formula design, site occupancy validation, and charge balancing platform for high-entropy and multi-element doped LMFP cathode compositions. 

Version 1 focuses on deterministic chemical formula generation, charge balance compensation, configurational entropy evaluation, material modification planning, and synthesis workflow structuring.

---

## 2. General Chemical Formula & Site Rules

### General Formula Architecture
$$\text{Li}_{(1-\delta)} \left[ \text{Mn}_m \text{Fe}_f A_{x_1} B_{x_2} C_{x_3} D_{x_4} E_{x_5} \right] \text{P}_{(1-s)} \text{Si}_s \text{O}_{(4-\gamma)} \text{F}_\gamma$$

### Host Composition & M2 Site Rules
- **Host Cations**: Mn²⁺ and Fe²⁺ occupy the M2 transition-metal site. Oxidation states are fixed at +2 for Version 1.
- **Allowed Host Composition Ranges**:
  - $\text{Mn}$: $0.60 \le m \le 0.75$
  - $\text{Fe}$: $0.10 \le f \le 0.30$
- **M2 Site Occupancy Constraint**:
  $$m + f + \sum_{i=1}^N x_i = 1.0000 \quad (\pm 10^{-4})$$

---

## 3. Dopant System & Oxidation States

### Component Count
- Dopant selection requires **3, 4, or 5 dopant elements** in addition to Mn and Fe (yielding 5 to 7 elements on the M2 site).

### Allowed & Excluded Elements
- **Allowed Dopants**: `Mg`, `Zn`, `Ni`, `Cu`, `Al`, `Ti`, `Zr`, `Nb`
- **Excluded Dopants**: 
  - `Cr`: Strictly excluded from active design set.
  - `Co`: Strictly excluded due to high raw material cost.
  - `Nb`: Retained in general formula for high-performance flexibility.

### Concentration Limits & Oxidation States
- Default per-dopant concentration range: $0.005 \le x_i \le 0.05 \text{ mol}$. Individual dopant concentrations can be varied independently.
- **Oxidation States**:
  - `Ti`: $+3$ or $+4$ (user-selected)
  - `Cu`: $+2$ or $+3$ (user-selected)
  - `Al`: $+3$
  - `Nb`: $+5$
  - `Zr`: $+4$
  - `Mg`, `Zn`, `Ni`: $+2$

---

## 4. Deterministic Charge Balance Engine

Charge neutrality is calculated automatically:
$$Q_{\text{net}} = (1-\delta) \cdot z_{\text{Li}} + Q_{\text{M2}} - s + \gamma - 3 = 0$$
where $Q_{\text{M2}} = 2m + 2f + \sum (z_i \cdot x_i)$.

### Charge Balancing Strategy
- Ideal $\text{Li}$ fraction for neutrality: $\text{Li} = 3 + s - \gamma - Q_{\text{M2}}$
- $\text{Li}$ vacancy fraction: $\delta = 1 - \text{Li} = Q_{\text{M2}} - 2$ (for $s=0, \gamma=0$).
- **No Silent Corrections**: Any charge adjustment or stoichiometry calculation is explicitly displayed with original values, adjusted values, reasons, and charge balance outcomes.

---

## 5. Configurational Entropy ($S_{\text{config}}$)

Configurational entropy on the M2 site is calculated as:
$$S_{\text{config}} = -R \sum_{i=1}^N x_i \ln(x_i) \quad \left[\text{J mol}^{-1} \text{K}^{-1}\right]$$
where $R = 8.314 \text{ J mol}^{-1} \text{K}^{-1}$.

### Provisional Entropy Classification
- $S_{\text{config}} / R \ge 1.5$: High-Entropy (Provisional Criterion)
- $0.6 \le S_{\text{config}} / R < 1.5$: Medium-Entropy / Entropy-Assisted (Provisional Criterion)
- $S_{\text{config}} / R < 0.6$: Low-Entropy / Conventional (Provisional Criterion)

> [!NOTE]
> The $\ge 1.5R$ threshold is explicitly labeled as a provisional reference classification requiring experimental confirmation.

---

## 6. Theoretical & Practical Capacity Metrics

- **Project Reference Theoretical Capacity**: $170.0\text{ mAh/g}$ (Supervisor benchmark constant)
- **Formula-Based Calculated Capacity Metric**:
  $$C_{\text{theo}} = \frac{(1-\delta) \cdot F}{3.6 \cdot M_{\text{formula}}} \quad [\text{mAh/g}]$$
  - Default Reference Composition ($\text{Li}_{0.93}[\text{Mn}_{0.65}\text{Fe}_{0.26}\text{Mg}_{0.02}\text{Zn}_{0.02}\text{Nb}_{0.01}\text{Cu}_{0.02}\text{Zr}_{0.02}]\text{PO}_4$): **$158.3\text{ mAh/g}$** (exact deterministic calculation: $158.28\text{ mAh/g}$)
- **Practical Target Range**: $150–160\text{ mAh/g}$ at 0.1C
- **Voltage Window**: $2.5 – 4.2\text{ V}$


---

## 7. Material Modifications & Synthesis Processing

### Conductive Modifications
- **Carbon Coating**: $2.0 – 3.0\text{ wt}\%$ maximum.
- **Carbon Nanotubes (CNT)**: $0.5 – 1.5\text{ wt}\%$ maximum.
- **Supported Modes**: None, Carbon Coating Only, CNT Only, Carbon Coating + CNT.

### Synthesis Route
- **Primary Method**: **Co-precipitation** (sol-gel is excluded from active V1 workflow).
- **Synthesis Parameters**: Precursors, pH, reaction temperature, and calcination parameters are kept as configurable placeholders labeled `"Not specified by supervisor (Requires experimental input)"` to prevent inventing unverified scientific values.

---

## 8. Material & Electrochemical Characterization Protocols

### Physical Characterization
1. **XRD**: Phase purity & lattice parameter refinement.
2. **SEM**: Morphology, particle size, and CNT distribution.
3. **BET**: Specific surface area ($m^2/g$).
4. **Electrical Conductivity**: Four-point probe / AC impedance ($S/cm$).
5. **Tap Density**: Volumetric tap density ($g/cm^3$).

### Electrochemical Testing Plan
- Galvanostatic charge-discharge cycling ($2.5–4.2\text{ V}$)
- C-rate capability ladder ($0.02\text{C}$, $0.1\text{C}$, $0.5\text{C}$, $1\text{C}$, $2\text{C}$, $4\text{C}$)
- Temperature cycling protocols ($25^\circ\text{C}$ room temp, $55^\circ\text{C}$ high temp, $-20^\circ\text{C}$ low temp)

---

## 9. Feature Categorization & Limitations

| Confirmed Supervisor Requirements | Provisional / Configurable Features | Future / Inactive Features |
| :--- | :--- | :--- |
| Mn range [0.60, 0.75], Fe range [0.10, 0.30] | $S_{\text{config}}/R \ge 1.5$ high-entropy threshold | Anion F-doping |
| 3–5 dopant elements on M2 site | Per-dopant conc [0.005, 0.05] default range | mGO (Graphene Oxide) modification |
| Exclusion of Cr and Co | Synthesis parameters (pH, calcination, etc.) | ML performance prediction module |
| Co-precipitation as primary synthesis route | Li vacancy charge balance strategy | Sol-gel synthesis optimization |
| Carbon [2-3 wt%] and CNT [0.5-1.5 wt%] ranges | | |

---

## 10. System Architecture & Setup Guide

### Environment Requirements
- **Python Version**: Python 3.10, 3.11, or 3.12.
- **Dependencies**: `pip install -r requirements.txt`

### Quick Start
```bash
# Clone repository
git clone https://github.com/your-org/HE-LMFP-Designer-AG.git
cd HE-LMFP-Designer-AG

# Install dependencies
pip install -r requirements.txt

# Run full test suite (54 unit tests)
pytest -v

# Launch Streamlit interactive dashboard
streamlit run app.py
```

---

## 11. Data, Machine Learning & Deployment Architecture

### Literature Dataset
- **File**: `data/literature_reference.csv` (1,215 records, 159 papers, 378 compositions).
- **Data Dictionary**: Documented in `data/literature_data_dictionary.md`.

### Machine Learning Module (`models/ml/`)
- **Trained Artifacts**: Serialized Random Forest models stored in `models/ml/artifacts/`:
  - `model_0_1C_capacity.joblib`
  - `model_1C_capacity.joblib`
  - `model_5C_capacity.joblib`
  - `model_capacity_retention.joblib`
  - `ml_metadata.json`
- **Cross-Validation**: GroupKFold (5-fold) grouped by `Paper_ID` to prevent literature data leakage.

### Database Architecture: Local vs. Cloud

#### LOCAL MODE (Default)
- **Engine**: Local SQLite database stored at `data/lab_experiments.db`.
- **Scope**: Ideal for local testing, single-user research, and offline development.
- **Persistence**: Automatically initializes table `lab_experiments` and commits changes to disk.

#### CLOUD MODE (Production & Multi-User Deployment)
- **Engine**: External PostgreSQL or Supabase cloud database.
- **Configuration**: Set `DATABASE_URL` environment variable in your deployment environment (e.g., Streamlit Community Cloud, AWS App Runner, GCP Cloud Run).
- **Architecture Notice**: SQLite is a single-file local database suitable for local testing. For multi-user cloud deployments with concurrent writes, set `DATABASE_URL` to connect to a managed PostgreSQL instance.

