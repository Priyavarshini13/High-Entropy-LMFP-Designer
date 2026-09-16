"""
Loader module for V2 literature reference database.
Reads data/literature_reference.csv and constructs LiteratureSampleRecord objects.
"""

import os
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

@dataclass
class LiteratureSampleRecord:
    # System & Paper Identifiers
    sample_id: str
    paper_id: str
    paper_title: str
    doi: str
    year: Optional[float]
    source_pdf: str
    
    # Reported Composition & Chemistry
    composition_formula: str
    base_lmfp_composition: str
    full_doped_composition: str
    mn_ratio: Optional[float]
    fe_ratio: Optional[float]
    dopant_element: str
    dopant_count: int
    dopant_molar_ratio: Optional[float]
    dopant_x_per_fu: Optional[float]
    carbon_wt_percent: Optional[float]
    
    # Reported Synthesis Parameters
    synthesis_method: str
    calcination_temp_1_c: Optional[float]
    calcination_time_1_h: Optional[float]
    
    # Reported Experimental Performance Values
    discharge_capacity_0_05c_mah_g: Optional[float]
    discharge_capacity_0_1c_mah_g: Optional[float]
    discharge_capacity_1c_mah_g: Optional[float]
    discharge_capacity_2c_mah_g: Optional[float]
    discharge_capacity_5c_mah_g: Optional[float]
    initial_coulombic_efficiency_percent: Optional[float]
    cycle_life_cycles: Optional[float]
    capacity_retention_percent: Optional[float]
    
    # Reported Experimental Characterization & Measurements
    eis_r_ct_before_ohm: Optional[float]
    eis_r_ct_after_ohm: Optional[float]
    li_diffusion_coefficient_cm2_s: Optional[float]
    xrd_phase_purity: str
    remarks: str
    impurity_phase_identified: str
    evidence: str
    
    # Software Calculated Chemistry Engine Metrics (Separated from Reported Data)
    calculated_molar_mass: Optional[float]
    calculated_q_m2: Optional[float]
    calculated_li_stoichiometry: Optional[float]
    calculated_li_vacancy_delta: Optional[float]
    calculated_s_config_over_r: Optional[float]
    calculated_theoretical_capacity_metric: Optional[float]
    record_classification: str = "LITERATURE_REPORTED"

def _clean_val(val, val_type=float):
    if pd.isnull(val) or val is None:
        return None
    try:
        if val_type == int:
            return int(val)
        elif val_type == float:
            f = float(val)
            return f if not np.isnan(f) else None
        elif val_type == str:
            s = str(val).strip()
            return s if s != "nan" else ""
    except Exception:
        return None
    return val

def load_literature_database(csv_path: Optional[str] = None) -> List[LiteratureSampleRecord]:
    """
    Load the verified literature reference database from data/literature_reference.csv.
    Returns a list of LiteratureSampleRecord objects with strict preservation of reported vs calculated data.
    """
    if csv_path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        csv_path = os.path.join(base_dir, "data", "literature_reference.csv")
        
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Literature reference database not found at {csv_path}")
        
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    records = []
    
    for _, row in df.iterrows():
        rec = LiteratureSampleRecord(
            sample_id=str(row.get("Sample_ID", "")).strip(),
            paper_id=str(row.get("Paper_ID", "")).strip(),
            paper_title=str(row.get("Paper_Title", "")).strip() if pd.notnull(row.get("Paper_Title")) else "",
            doi=str(row.get("DOI", "")).strip() if pd.notnull(row.get("DOI")) else "",
            year=_clean_val(row.get("Year"), float),
            source_pdf=str(row.get("Source_PDF", "")).strip() if pd.notnull(row.get("Source_PDF")) else "UNVERIFIED_PDF_NOT_FOUND",
            
            composition_formula=str(row.get("Composition_Formula", "")).strip() if pd.notnull(row.get("Composition_Formula")) else "",
            base_lmfp_composition=str(row.get("Base_LMFP_Composition", "")).strip() if pd.notnull(row.get("Base_LMFP_Composition")) else "",
            full_doped_composition=str(row.get("Full_Doped_Composition", "")).strip() if pd.notnull(row.get("Full_Doped_Composition")) else "",
            mn_ratio=_clean_val(row.get("Mn_Ratio"), float),
            fe_ratio=_clean_val(row.get("Fe_Ratio"), float),
            dopant_element=str(row.get("Dopant_Element", "None/Undoped")).strip() if pd.notnull(row.get("Dopant_Element")) else "None/Undoped",
            dopant_count=int(_clean_val(row.get("Dopant_Count"), int) or 0),
            dopant_molar_ratio=_clean_val(row.get("Dopant_Molar_Ratio"), float),
            dopant_x_per_fu=_clean_val(row.get("Dopant_x_per_fu"), float),
            carbon_wt_percent=_clean_val(row.get("Carbon_wt_percent"), float),
            
            synthesis_method=str(row.get("Synthesis_Method", "")).strip() if pd.notnull(row.get("Synthesis_Method")) else "",
            calcination_temp_1_c=_clean_val(row.get("Calcination_Temp_1_C"), float),
            calcination_time_1_h=_clean_val(row.get("Calcination_Time_1_h"), float),
            
            discharge_capacity_0_05c_mah_g=_clean_val(row.get("Discharge_Capacity_0_05C_mAh_g"), float),
            discharge_capacity_0_1c_mah_g=_clean_val(row.get("Discharge_Capacity_0_1C_mAh_g"), float),
            discharge_capacity_1c_mah_g=_clean_val(row.get("Discharge_Capacity_1C_mAh_g"), float),
            discharge_capacity_2c_mah_g=_clean_val(row.get("Discharge_Capacity_2C_mAh_g"), float),
            discharge_capacity_5c_mah_g=_clean_val(row.get("Discharge_Capacity_5C_mAh_g"), float),
            initial_coulombic_efficiency_percent=_clean_val(row.get("Initial_Coulombic_Efficiency_percent"), float),
            cycle_life_cycles=_clean_val(row.get("Cycle_Life_cycles"), float),
            capacity_retention_percent=_clean_val(row.get("Capacity_Retention_percent"), float),
            
            eis_r_ct_before_ohm=_clean_val(row.get("EIS_R_ct_before_Ohm"), float),
            eis_r_ct_after_ohm=_clean_val(row.get("EIS_R_ct_after_Ohm"), float),
            li_diffusion_coefficient_cm2_s=_clean_val(row.get("Li_Diffusion_Coefficient_cm2_s"), float),
            xrd_phase_purity=str(row.get("XRD_Phase_Purity", "")).strip() if pd.notnull(row.get("XRD_Phase_Purity")) else "",
            remarks=str(row.get("Remarks", "")).strip() if pd.notnull(row.get("Remarks")) else "",
            impurity_phase_identified=str(row.get("Impurity_Phase_Identified", "")).strip() if pd.notnull(row.get("Impurity_Phase_Identified")) else "",
            evidence=str(row.get("Evidence", "")).strip() if pd.notnull(row.get("Evidence")) else "",
            
            calculated_molar_mass=_clean_val(row.get("Calculated_Molar_Mass"), float),
            calculated_q_m2=_clean_val(row.get("Calculated_Q_M2"), float),
            calculated_li_stoichiometry=_clean_val(row.get("Calculated_Li_Stoichiometry"), float),
            calculated_li_vacancy_delta=_clean_val(row.get("Calculated_Li_Vacancy_delta"), float),
            calculated_s_config_over_r=_clean_val(row.get("Calculated_S_config_over_R"), float),
            calculated_theoretical_capacity_metric=_clean_val(row.get("Calculated_Theoretical_Capacity_Metric"), float),
            record_classification=str(row.get("Record_Classification", "LITERATURE_REPORTED")).strip() if pd.notnull(row.get("Record_Classification")) else "LITERATURE_REPORTED"
        )
        records.append(rec)
        
    return records
