# V2 Literature Database Data Dictionary (`data/literature_reference.csv`)

## Overview

The `data/literature_reference.csv` dataset is a structured, traceable literature database for Lithium Manganese Iron Phosphate (LMFP) and High-Entropy Doped LMFP cathode materials. It consolidates literature data extracted from research PDFs and verified dataset extracts (`LMFP_Master_Dataset_v2_doped.xlsx`).

---

## Source Priority Rules

1. **Primary Source (Priority 1)**: Original scientific literature PDF document.
2. **Secondary Source (Priority 2)**: Verified extracted dataset (`LMFP_Master_Dataset_v2_doped.xlsx`).
3. **Tertiary Source (Priority 3)**: Supervisor-provided baseline requirements.
4. **Quaternary Source (Priority 4)**: Deterministic software calculations (V1 Chemistry Engine).

> [!IMPORTANT]
> **Data Integrity Rule**: Reported experimental values are NEVER overwritten by calculated values. All calculated metrics are stored in separate, explicitly labeled `Calculated_*` fields. Missing experimental values are preserved as empty `NULL`/`NA` values.

---

## Column Specifications

| Column Name | Category | Reported vs Calculated | Units | Description & Source |
| :--- | :--- | :--- | :--- | :--- |
| `Sample_ID` | Identifier | System Identifier | None | Unique sample variant identifier (e.g. `P1_N-LMFP`, `P1_O-LMFP`). Disaggregates distinct material samples within the same paper. |
| `Paper_ID` | Identifier | Reported Metadata | None | Primary paper key linking sample variants to the source publication (e.g. `P1`, `P2`). |
| `Paper_Title` | Metadata | Reported Metadata | Text | Full title of the academic research paper. Source: Literature PDF / Dataset. |
| `DOI` | Metadata | Reported Metadata | Text | Digital Object Identifier (DOI) of the research paper. Source: Literature PDF. |
| `Year` | Metadata | Reported Metadata | Year (YYYY) | Publication year of the research paper. Source: Literature PDF. |
| `Source_PDF` | Traceability | Traceability Reference | Filename | Exact PDF filename in the `Papers/` repository (e.g. `d2ra04427g.pdf`). |
| `Composition_Formula` | Chemistry | Reported Chemistry | Text | Chemical formula string as reported in the literature source. |
| `Base_LMFP_Composition` | Chemistry | Reported Chemistry | Text | Host matrix stoichiometry before dopant addition (e.g. `LiMn0.8Fe0.2PO4`). |
| `Full_Doped_Composition` | Chemistry | Reported Chemistry | Text | Full chemical formula including dopants and surface coatings. |
| `Mn_Ratio` | Chemistry | Reported Chemistry | Molar fraction | Molar fraction of Mn ($m$) on the M2 transition metal site ($0.0$ to $1.0$). |
| `Fe_Ratio` | Chemistry | Reported Chemistry | Molar fraction | Molar fraction of Fe ($f$) on the M2 transition metal site ($0.0$ to $1.0$). |
| `Dopant_Element` | Chemistry | Reported Chemistry | Text | Element symbol of dopant cation(s) or `None/Undoped`. |
| `Dopant_Count` | Chemistry | Reported Chemistry | Count | Number of distinct dopant elements occupying the M2 site ($0$ to $5$). |
| `Dopant_Molar_Ratio` | Chemistry | Reported Chemistry | Molar ratio | Total dopant molar ratio reported in the material formula. |
| `Dopant_x_per_fu` | Chemistry | Reported Chemistry | Molar fraction | Dopant concentration per formula unit ($x$). |
| `Carbon_wt_percent` | Modification | Reported Chemistry | wt% | Weight percentage of conductive carbon coating. |
| `Synthesis_Method` | Processing | Reported Synthesis | Text | Primary synthesis method (e.g. `Solid-state`, `Co-precipitation`, `Sol-gel`, `Hydrothermal`). |
| `Calcination_Temp_1_C` | Processing | Reported Synthesis | °C | First-stage calcination temperature. |
| `Calcination_Time_1_h` | Processing | Reported Synthesis | Hours (h) | First-stage calcination duration. |
| `Discharge_Capacity_0_05C_mAh_g` | Performance | Reported Experimental | mAh/g | Specific discharge capacity measured at 0.05C rate. |
| `Discharge_Capacity_0_1C_mAh_g` | Performance | Reported Experimental | mAh/g | Specific discharge capacity measured at 0.1C rate. |
| `Discharge_Capacity_1C_mAh_g` | Performance | Reported Experimental | mAh/g | Specific discharge capacity measured at 1C rate. |
| `Discharge_Capacity_2C_mAh_g` | Performance | Reported Experimental | mAh/g | Specific discharge capacity measured at 2C rate. |
| `Discharge_Capacity_5C_mAh_g` | Performance | Reported Experimental | mAh/g | Specific discharge capacity measured at 5C rate. |
| `Initial_Coulombic_Efficiency_percent` | Performance | Reported Experimental | % | Initial Coulombic Efficiency (ICE %) in first cycle. |
| `Cycle_Life_cycles` | Performance | Reported Experimental | Cycles | Total number of charge-discharge cycles tested. |
| `Capacity_Retention_percent` | Performance | Reported Experimental | % | Capacity retention percentage remaining after cycle life testing. |
| `EIS_R_ct_before_Ohm` | Characterization | Reported Experimental | $\Omega$ | Interfacial charge-transfer resistance before cycling. |
| `EIS_R_ct_after_Ohm` | Characterization | Reported Experimental | $\Omega$ | Interfacial charge-transfer resistance after cycling. |
| `Li_Diffusion_Coefficient_cm2_s` | Property | Reported Experimental | $\text{cm}^2/\text{s}$ | Lithium-ion diffusion coefficient ($D_{\text{Li}^+}$). |
| `XRD_Phase_Purity` | Characterization | Reported Characterization| Text | Reported phase purity, space group ($Pnma$), or crystal lattice cell volume. |
| `Remarks` | Observations | Reported Information | Text | Contextual notes, reported limitations, or sample observations. |
| `Impurity_Phase_Identified` | Characterization | Reported Characterization| Text | Secondary impurity phases identified (e.g. `Fe2O3`, `MnPO4`, `Li3PO4`). |
| `Evidence` | Traceability | Traceability Reference | Text | Specific figure, table, or page reference in source paper/dataset. |
| `Calculated_Molar_Mass` | Computation | **CALCULATED** | g/mol | Molecular mass evaluated deterministically from stoichiometry and IUPAC atomic weights. |
| `Calculated_Q_M2` | Computation | **CALCULATED** | Charge ($e$) | Total positive cation charge on the M2 site ($2m + 2f + \sum z_i x_i$). |
| `Calculated_Li_Stoichiometry` | Computation | **CALCULATED** | Molar fraction | Active Lithium stoichiometry required for charge neutrality ($n_{\text{Li}} = 3.00 - Q_{\text{M2}}$). |
| `Calculated_Li_Vacancy_delta` | Computation | **CALCULATED** | Vacancy fraction | Lithium vacancy fraction ($\delta = 1.0 - n_{\text{Li}}$). |
| `Calculated_S_config_over_R` | Computation | **CALCULATED** | Dimensionless ($R$) | M2 site configurational entropy ratio ($S_{\text{config}}/R = -\sum x_i \ln x_i$). |
| `Calculated_Theoretical_Capacity_Metric` | Computation | **CALCULATED** | mAh/g | Theoretical capacity metric derived from active Li and formula molar mass. |
| `Record_Classification` | Taxonomy | System Tag | Enum | Record classification tag (`LITERATURE_REPORTED`). |

---

## Classification Rules

- **`LITERATURE_REPORTED`**: Data extracted from a published scientific paper or verified dataset extract.
- **`CALCULATED_FROM_LITERATURE_COMPOSITION`**: Derived metrics ($S_{\text{config}}$, $C_{\text{theo}}$, $\delta$) calculated deterministically by V1 engine from reported literature stoichiometry.
- **`GENERATED_BY_OUR_SYSTEM`**: Candidate compositions generated by V2 alternative engine (stored separately, not mixed with literature baseline records).
- **`EXPERIMENTALLY_VALIDATED`**: Flag reserved strictly for compositions with direct physical laboratory test confirmation.
