"""
Triple Comparison Matrix Engine for HE-LMFP Materials.

Compares:
1. COMPUTATIONAL DESIGN (CALCULATED - V1 Chemistry Engine)
2. LITERATURE REFERENCE (LITERATURE_REPORTED - V2 Verified Database Match)
3. ACTUAL EXPERIMENT (EXPERIMENTAL - Laboratory Entry)

Computes explicit residuals (Residual = Experimental - Reference) strictly
when both data points exist, preserving source integrity without data fabrication.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from chemistry.formula import ChemicalFormula
from chemistry.capacity import CapacityMetrics
from literature.matcher import MatchResult, MatchStatus
from .models import LabExperiment


@dataclass
class ComparisonRow:
    property_name: str
    unit: str
    calculated_val: Optional[float]
    calculated_label: str
    literature_val: Optional[float]
    literature_label: str
    experimental_val: Optional[float]
    experimental_label: str
    residual_vs_calculated: Optional[float]
    residual_vs_literature: Optional[float]
    notes: str


@dataclass
class ComparisonMatrix:
    formula_string: str
    experiment_id: Optional[str]
    literature_match_status: str
    rows: List[ComparisonRow]
    summary_notes: str


def generate_comparison_matrix(
    formula: Optional[ChemicalFormula],
    cap_metrics: Optional[CapacityMetrics],
    match_res: Optional[MatchResult],
    experiment: Optional[LabExperiment]
) -> ComparisonMatrix:
    """Generate a structured triple comparison matrix across Calculated, Literature, and Experimental data."""
    rows: List[ComparisonRow] = []

    # Helper function to format residual
    def _calc_res(exp_val: Optional[float], ref_val: Optional[float]) -> Optional[float]:
        if exp_val is not None and ref_val is not None:
            return round(exp_val - ref_val, 4)
        return None

    # Get matched literature record if available
    best_lit = None
    if match_res:
        if match_res.exact_matches:
            best_lit = match_res.exact_matches[0]
        elif match_res.near_matches:
            best_lit = match_res.near_matches[0]

    # Extract Experimental Values
    exp_elec = experiment.electrochemical_data if experiment else None
    exp_char = experiment.characterization_data if experiment else None

    # 1. Theoretical / Calculated Capacity Metric (0.1C)
    calc_cap = cap_metrics.formula_calculated_capacity_metric if cap_metrics else None
    lit_cap_01c = best_lit.cap_0_1c if best_lit else None
    exp_cap_01c = exp_elec.cap_0_1c if exp_elec else None

    rows.append(ComparisonRow(
        property_name="0.1C Capacity",
        unit="mAh/g",
        calculated_val=round(calc_cap, 1) if calc_cap is not None else None,
        calculated_label="CALCULATED",
        literature_val=round(lit_cap_01c, 1) if lit_cap_01c is not None else None,
        literature_label="LITERATURE_REPORTED",
        experimental_val=round(exp_cap_01c, 1) if exp_cap_01c is not None else None,
        experimental_label="EXPERIMENTAL",
        residual_vs_calculated=_calc_res(exp_cap_01c, calc_cap),
        residual_vs_literature=_calc_res(exp_cap_01c, lit_cap_01c),
        notes="Discharge capacity measured at 0.1C rate."
    ))

    # 2. 1C Rate Capacity
    calc_1c = None  # V1 formula engine calculates 0.1C reference metric; 1C is rate performance
    lit_cap_1c = best_lit.cap_1c if best_lit else None
    exp_cap_1c = exp_elec.cap_1c if exp_elec else None

    rows.append(ComparisonRow(
        property_name="1C Rate Capacity",
        unit="mAh/g",
        calculated_val=None,
        calculated_label="CALCULATED",
        literature_val=round(lit_cap_1c, 1) if lit_cap_1c is not None else None,
        literature_label="LITERATURE_REPORTED",
        experimental_val=round(exp_cap_1c, 1) if exp_cap_1c is not None else None,
        experimental_label="EXPERIMENTAL",
        residual_vs_calculated=None,
        residual_vs_literature=_calc_res(exp_cap_1c, lit_cap_1c),
        notes="High-rate capacity at 1.0C rate."
    ))

    # 3. Initial Coulombic Efficiency (ICE)
    lit_ice = best_lit.ice_pct if best_lit else None
    exp_ice = exp_elec.initial_coulombic_efficiency if exp_elec else None

    rows.append(ComparisonRow(
        property_name="Initial Coulombic Efficiency (ICE)",
        unit="%",
        calculated_val=None,
        calculated_label="CALCULATED",
        literature_val=round(lit_ice, 1) if lit_ice is not None else None,
        literature_label="LITERATURE_REPORTED",
        experimental_val=round(exp_ice, 1) if exp_ice is not None else None,
        experimental_label="EXPERIMENTAL",
        residual_vs_calculated=None,
        residual_vs_literature=_calc_res(exp_ice, lit_ice),
        notes="First cycle efficiency."
    ))

    # 4. Capacity Retention (25°C)
    lit_ret_25 = best_lit.retention_pct if best_lit else None
    exp_ret_25 = exp_elec.retention_25c_pct if exp_elec else (exp_elec.capacity_retention_pct if exp_elec else None)

    rows.append(ComparisonRow(
        property_name="25°C Cycling Retention",
        unit="%",
        calculated_val=None,
        calculated_label="CALCULATED",
        literature_val=round(lit_ret_25, 1) if lit_ret_25 is not None else None,
        literature_label="LITERATURE_REPORTED",
        experimental_val=round(exp_ret_25, 1) if exp_ret_25 is not None else None,
        experimental_label="EXPERIMENTAL",
        residual_vs_calculated=None,
        residual_vs_literature=_calc_res(exp_ret_25, lit_ret_25),
        notes="Room temperature long-term capacity retention."
    ))

    # 5. High-Temperature Retention (55°C)
    exp_ret_55 = exp_elec.retention_55c_pct if exp_elec else None
    rows.append(ComparisonRow(
        property_name="55°C Cycling Retention",
        unit="%",
        calculated_val=None,
        calculated_label="CALCULATED",
        literature_val=None,
        literature_label="LITERATURE_REPORTED",
        experimental_val=round(exp_ret_55, 1) if exp_ret_55 is not None else None,
        experimental_label="EXPERIMENTAL",
        residual_vs_calculated=None,
        residual_vs_literature=None,
        notes="Elevated temperature stability assessment."
    ))

    # 6. Low-Temperature Retention (-20°C)
    exp_ret_minus20 = exp_elec.retention_minus20c_pct if exp_elec else None
    rows.append(ComparisonRow(
        property_name="-20°C Cycling Retention",
        unit="%",
        calculated_val=None,
        calculated_label="CALCULATED",
        literature_val=None,
        literature_label="LITERATURE_REPORTED",
        experimental_val=round(exp_ret_minus20, 1) if exp_ret_minus20 is not None else None,
        experimental_label="EXPERIMENTAL",
        residual_vs_calculated=None,
        residual_vs_literature=None,
        notes="Low temperature performance."
    ))

    # 7. BET Surface Area
    exp_bet = exp_char.bet_surface_area_m2g if exp_char else None
    rows.append(ComparisonRow(
        property_name="BET Surface Area",
        unit="m²/g",
        calculated_val=None,
        calculated_label="CALCULATED",
        literature_val=None,
        literature_label="LITERATURE_REPORTED",
        experimental_val=round(exp_bet, 2) if exp_bet is not None else None,
        experimental_label="EXPERIMENTAL",
        residual_vs_calculated=None,
        residual_vs_literature=None,
        notes="Physical specific surface area measurement."
    ))

    # 8. Electrical Conductivity
    exp_cond = exp_char.electrical_conductivity_scm if exp_char else None
    rows.append(ComparisonRow(
        property_name="Electrical Conductivity",
        unit="S/cm",
        calculated_val=None,
        calculated_label="CALCULATED",
        literature_val=None,
        literature_label="LITERATURE_REPORTED",
        experimental_val=exp_cond,
        experimental_label="EXPERIMENTAL",
        residual_vs_calculated=None,
        residual_vs_literature=None,
        notes="Electronic conductivity measurement."
    ))

    formula_str = formula.formula_string if formula else "Unspecified"
    exp_id = experiment.experiment_id if experiment else None
    lit_status = match_res.status.value if match_res else "NOT_AUDITED"

    summary_notes = (
        "Triple Comparison Matrix generated. Source designations strictly separated "
        "(CALCULATED = V1 engine, LITERATURE_REPORTED = V2 reference database, EXPERIMENTAL = Lab measurement). "
        "Residuals are computed strictly when both experimental and reference data points exist."
    )

    return ComparisonMatrix(
        formula_string=formula_str,
        experiment_id=exp_id,
        literature_match_status=lit_status,
        rows=rows,
        summary_notes=summary_notes
    )
