"""
Evidence module for V2 literature reference engine.
Extracts, formats, and exposes evidence reports for literature records,
maintaining strict traceability between reported experimental values and calculated metrics.
"""

from typing import Dict, List, Any, Optional
from .loader import LiteratureSampleRecord
from .matcher import MatchResult, MatchStatus

def _fmt_val(val: Any, suffix: str = "", default: str = "N/A") -> str:
    if val is None or val == "" or str(val).lower() == "nan":
        return default
    if isinstance(val, float):
        if val.is_integer():
            return f"{int(val)}{suffix}"
        return f"{val:.4g}{suffix}"
    return f"{str(val)}{suffix}"

def generate_evidence_summary(rec: LiteratureSampleRecord) -> Dict[str, Any]:
    """
    Generate a structured dictionary summarizing verified evidence for a literature record.
    Preserves missing values as N/A and strictly separates reported vs calculated values.
    """
    return {
        "Sample_ID": rec.sample_id,
        "Paper_ID": rec.paper_id,
        "Paper_Title": rec.paper_title or "N/A",
        "DOI": rec.doi or "N/A",
        "Year": _fmt_val(rec.year),
        "Source_PDF": rec.source_pdf or "UNVERIFIED_PDF_NOT_FOUND",
        
        # Composition Information
        "Composition_Formula": rec.composition_formula or "N/A",
        "Base_LMFP_Composition": rec.base_lmfp_composition or "N/A",
        "Full_Doped_Composition": rec.full_doped_composition or "N/A",
        "Mn_Ratio": _fmt_val(rec.mn_ratio),
        "Fe_Ratio": _fmt_val(rec.fe_ratio),
        "Dopant_Element": rec.dopant_element or "None/Undoped",
        "Dopant_Count": rec.dopant_count,
        "Dopant_Molar_Ratio": _fmt_val(rec.dopant_molar_ratio),
        "Dopant_x_per_fu": _fmt_val(rec.dopant_x_per_fu),
        "Carbon_wt_percent": _fmt_val(rec.carbon_wt_percent, suffix=" wt%"),
        
        # Synthesis & Calcination
        "Synthesis_Method": rec.synthesis_method or "N/A",
        "Calcination_Temp_1_C": _fmt_val(rec.calcination_temp_1_c, suffix=" °C"),
        "Calcination_Time_1_h": _fmt_val(rec.calcination_time_1_h, suffix=" h"),
        
        # Reported Experimental Performance (LITERATURE_REPORTED)
        "Discharge_Capacity_0_05C_mAh_g": _fmt_val(rec.discharge_capacity_0_05c_mah_g, suffix=" mAh/g"),
        "Discharge_Capacity_0_1C_mAh_g": _fmt_val(rec.discharge_capacity_0_1c_mah_g, suffix=" mAh/g"),
        "Discharge_Capacity_1C_mAh_g": _fmt_val(rec.discharge_capacity_1c_mah_g, suffix=" mAh/g"),
        "Discharge_Capacity_2C_mAh_g": _fmt_val(rec.discharge_capacity_2c_mah_g, suffix=" mAh/g"),
        "Discharge_Capacity_5C_mAh_g": _fmt_val(rec.discharge_capacity_5c_mah_g, suffix=" mAh/g"),
        "Initial_Coulombic_Efficiency_percent": _fmt_val(rec.initial_coulombic_efficiency_percent, suffix=" %"),
        "Cycle_Life_cycles": _fmt_val(rec.cycle_life_cycles, suffix=" cycles"),
        "Capacity_Retention_percent": _fmt_val(rec.capacity_retention_percent, suffix=" %"),
        
        # Characterization & Measurements (LITERATURE_REPORTED)
        "EIS_R_ct_before_Ohm": _fmt_val(rec.eis_r_ct_before_ohm, suffix=" Ω"),
        "EIS_R_ct_after_Ohm": _fmt_val(rec.eis_r_ct_after_ohm, suffix=" Ω"),
        "Li_Diffusion_Coefficient_cm2_s": _fmt_val(rec.li_diffusion_coefficient_cm2_s, suffix=" cm²/s"),
        "XRD_Phase_Purity": rec.xrd_phase_purity or "N/A",
        "Remarks": rec.remarks or "N/A",
        "Impurity_Phase_Identified": rec.impurity_phase_identified or "N/A",
        "Evidence": rec.evidence or "N/A",
        
        # Software Calculated Chemistry Metrics (CALCULATED_FROM_LITERATURE_COMPOSITION)
        "Calculated_Molar_Mass": _fmt_val(rec.calculated_molar_mass, suffix=" g/mol"),
        "Calculated_Q_M2": _fmt_val(rec.calculated_q_m2, suffix=" e"),
        "Calculated_Li_Stoichiometry": _fmt_val(rec.calculated_li_stoichiometry),
        "Calculated_Li_Vacancy_delta": _fmt_val(rec.calculated_li_vacancy_delta),
        "Calculated_S_config_over_R": _fmt_val(rec.calculated_s_config_over_r, suffix=" R"),
        "Calculated_Theoretical_Capacity_Metric": _fmt_val(rec.calculated_theoretical_capacity_metric, suffix=" mAh/g"),
        
        "Record_Classification": rec.record_classification or "LITERATURE_REPORTED"
    }

def format_evidence_report(match_result: MatchResult) -> str:
    """
    Format a complete human-readable Markdown evidence report from a MatchResult.
    """
    lines = []
    lines.append(f"## Literature Match Report: {match_result.status.value}")
    lines.append(f"**Explanation**: {match_result.explanation}\n")
    
    records_to_show = match_result.exact_matches if match_result.exact_matches else match_result.near_matches
    
    if not records_to_show:
        lines.append("> [!NOTE]")
        lines.append("> No matching record was found in the current literature reference database.")
        return "\n".join(lines)
        
    lines.append(f"### Matched Literature Sample Records ({len(records_to_show)} record(s))\n")
    
    for idx, rec in enumerate(records_to_show):
        ev = generate_evidence_summary(rec)
        diff_text = match_result.differences[idx].summary_text if idx < len(match_result.differences) else ""
        
        lines.append(f"#### Sample Record #{idx+1}: `{ev['Sample_ID']}` (Paper: `{ev['Paper_ID']}`)")
        if diff_text:
            lines.append(f"- ** stoichiometric Differences**: `{diff_text}`")
        lines.append(f"- **Paper Title**: {ev['Paper_Title']}")
        lines.append(f"- **Citation / DOI**: `{ev['DOI']}` (Year: {ev['Year']})")
        lines.append(f"- **Source PDF**: `{ev['Source_PDF']}`")
        lines.append(f"- **Reported Formula**: `{ev['Composition_Formula']}`")
        lines.append(f"- **Synthesis Method**: `{ev['Synthesis_Method']}` (Calcination: {ev['Calcination_Temp_1_C']} for {ev['Calcination_Time_1_h']})")
        lines.append(f"- **Carbon Coating**: `{ev['Carbon_wt_percent']}`")
        
        lines.append("\n**Reported Experimental Performance (LITERATURE_REPORTED)**:")
        lines.append(f"- 0.1C Discharge Capacity: `{ev['Discharge_Capacity_0_1C_mAh_g']}`")
        lines.append(f"- 1C Discharge Capacity: `{ev['Discharge_Capacity_1C_mAh_g']}`")
        lines.append(f"- 2C Discharge Capacity: `{ev['Discharge_Capacity_2C_mAh_g']}`")
        lines.append(f"- 5C Discharge Capacity: `{ev['Discharge_Capacity_5C_mAh_g']}`")
        lines.append(f"- Capacity Retention: `{ev['Capacity_Retention_percent']}` after `{ev['Cycle_Life_cycles']}`")
        lines.append(f"- Initial Coulombic Efficiency (ICE): `{ev['Initial_Coulombic_Efficiency_percent']}`")
        
        lines.append("\n**Software Calculated Metrics (CALCULATED_FROM_LITERATURE_COMPOSITION)**:")
        lines.append(f"- Molar Mass: `{ev['Calculated_Molar_Mass']}`")
        lines.append(f"- Derived Li Stoichiometry (1-δ): `{ev['Calculated_Li_Stoichiometry']}` (δ = `{ev['Calculated_Li_Vacancy_delta']}`)")
        lines.append(f"- Configurational Entropy (S_config/R): `{ev['Calculated_S_config_over_R']}`")
        lines.append(f"- Theoretical Capacity Metric: `{ev['Calculated_Theoretical_Capacity_Metric']}`")
        
        lines.append(f"\n**Remarks & Evidence**: {ev['Remarks']}")
        lines.append(f"- Evidence Source: `{ev['Evidence']}`\n")
        lines.append("---")
        
    return "\n".join(lines)
