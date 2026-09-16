"""
Validation Engine for Laboratory Experiment Data Entries.

Validates ranges and physical consistency for user-entered laboratory measurements:
- Synthesis parameters (pH, temperature, duration, yield)
- Characterization metrics (lattice constants, purity %, surface area, density)
- Electrochemical metrics (discharge capacity, ICE %, retention %, temperature cycling)
"""

from typing import List, Dict, Any
from dataclasses import dataclass
from .models import LabExperiment


@dataclass
class LabValidationMessage:
    severity: str  # "ERROR", "WARNING", "INFO"
    field: str
    message: str


@dataclass
class LabValidationReport:
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    details: List[LabValidationMessage]


def validate_lab_experiment(exp: LabExperiment) -> LabValidationReport:
    """Validate experimental data entries for physical consistency and plausibility."""
    messages: List[LabValidationMessage] = []

    # 1. Synthesis Validation
    if exp.synthesis_data:
        syn = exp.synthesis_data
        if syn.reaction_ph is not None:
            if syn.reaction_ph < 0.0 or syn.reaction_ph > 14.0:
                messages.append(LabValidationMessage("ERROR", "reaction_ph", f"Reaction pH ({syn.reaction_ph}) must be between 0.0 and 14.0."))

        if syn.yield_pct is not None:
            if syn.yield_pct < 0.0 or syn.yield_pct > 100.0:
                messages.append(LabValidationMessage("ERROR", "yield_pct", f"Synthesis yield ({syn.yield_pct:.1f}%) must be between 0% and 100%."))

        if syn.calcination_temp_c is not None:
            if syn.calcination_temp_c < 300.0 or syn.calcination_temp_c > 1100.0:
                messages.append(LabValidationMessage("WARNING", "calcination_temp_c", f"Calcination temperature ({syn.calcination_temp_c}°C) is outside typical range [300°C, 1100°C]."))

    # 2. Characterization Validation
    if exp.characterization_data:
        char = exp.characterization_data
        if char.xrd_phase_purity_pct is not None:
            if char.xrd_phase_purity_pct < 0.0 or char.xrd_phase_purity_pct > 100.0:
                messages.append(LabValidationMessage("ERROR", "xrd_phase_purity_pct", f"Phase purity ({char.xrd_phase_purity_pct:.1f}%) must be between 0% and 100%."))

        if char.antisite_defects_pct is not None:
            if char.antisite_defects_pct < 0.0 or char.antisite_defects_pct > 30.0:
                messages.append(LabValidationMessage("WARNING", "antisite_defects_pct", f"Antisite defect fraction ({char.antisite_defects_pct:.1f}%) is unusually high (>30%)."))

        if char.bet_surface_area_m2g is not None and char.bet_surface_area_m2g < 0.0:
            messages.append(LabValidationMessage("ERROR", "bet_surface_area_m2g", "BET surface area cannot be negative."))

    # 3. Electrochemical Validation
    if exp.electrochemical_data:
        elec = exp.electrochemical_data
        for c_field, c_name in [
            (elec.cap_0_02c, "0.02C capacity"),
            (elec.cap_0_1c, "0.1C capacity"),
            (elec.cap_1c, "1C capacity"),
            (elec.cap_2c, "2C capacity"),
            (elec.cap_4c, "4C capacity")
        ]:
            if c_field is not None:
                if c_field < 0.0:
                    messages.append(LabValidationMessage("ERROR", c_name, f"{c_name} cannot be negative ({c_field:.1f} mAh/g)."))
                elif c_field > 200.0:
                    messages.append(LabValidationMessage("WARNING", c_name, f"{c_name} ({c_field:.1f} mAh/g) exceeds theoretical maximum (~170 mAh/g)."))

        if elec.initial_coulombic_efficiency is not None:
            if elec.initial_coulombic_efficiency < 0.0 or elec.initial_coulombic_efficiency > 100.0:
                messages.append(LabValidationMessage("ERROR", "initial_coulombic_efficiency", f"ICE ({elec.initial_coulombic_efficiency:.1f}%) must be between 0% and 100%."))

        for ret_val, ret_label in [
            (elec.capacity_retention_pct, "General retention"),
            (elec.retention_25c_pct, "25°C retention"),
            (elec.retention_55c_pct, "55°C retention"),
            (elec.retention_minus20c_pct, "-20°C retention")
        ]:
            if ret_val is not None:
                if ret_val < 0.0 or ret_val > 100.0:
                    messages.append(LabValidationMessage("ERROR", ret_label, f"{ret_label} ({ret_val:.1f}%) must be between 0% and 100%."))

    errors = [m.message for m in messages if m.severity == "ERROR"]
    warnings = [m.message for m in messages if m.severity == "WARNING"]
    is_valid = len(errors) == 0

    return LabValidationReport(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
        details=messages
    )
