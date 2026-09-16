"""
Validation Engine for High-Entropy Doped LMFP Materials.

Executes modular validation rules across host composition, dopant selections,
occupancy, charge neutrality, oxidation states, material modifications,
and future feature flags.
"""

from typing import Dict, List, Any
from dataclasses import dataclass, field
from .dopants import (
    ALLOWED_DOPANTS,
    EXCLUDED_DOPANTS,
    MIN_DOPANTS,
    MAX_DOPANTS,
    MIN_DOPANT_CONC,
    MAX_DOPANT_CONC,
    DOPANT_DATABASE
)
from .charge_balance import TOLERANCE

MN_MIN = 0.60
MN_MAX = 0.75
FE_MIN = 0.10
FE_MAX = 0.30

CARBON_WT_MIN = 2.0
CARBON_WT_MAX = 3.0
CNT_WT_MIN = 0.5
CNT_WT_MAX = 1.5

@dataclass
class ValidationMessage:
    rule_id: str
    severity: str  # "ERROR", "WARNING", "INFO"
    message: str

@dataclass
class ValidationReport:
    overall_status: str  # "PASS", "WARNING", "INVALID"
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    info_messages: List[str]
    details: List[ValidationMessage]

def validate_composition(
    mn_frac: float,
    fe_frac: float,
    dopants: List[Dict[str, Any]], # list of {"symbol": str, "fraction": float, "oxidation_state": int}
    user_li: float = 1.0,
    is_charge_balanced: bool = True,
    m2_occupancy: float = 1.0,
    carbon_wt_pct: float = 0.0,
    carbon_enabled: bool = False,
    cnt_wt_pct: float = 0.0,
    cnt_enabled: bool = False,
    mgo_enabled: bool = False,
    f_doping_enabled: bool = False
) -> ValidationReport:
    """
    Comprehensive modular validation engine for HE-LMFP candidate.
    """
    messages: List[ValidationMessage] = []
    
    # 1. Host Mn range check
    if mn_frac < MN_MIN or mn_frac > MN_MAX:
        messages.append(ValidationMessage(
            rule_id="RULE_MN_RANGE",
            severity="ERROR",
            message=f"Mn fraction ({mn_frac:.4f}) is outside allowed range [{MN_MIN}, {MN_MAX}]."
        ))
        
    # 2. Host Fe range check
    if fe_frac < FE_MIN or fe_frac > FE_MAX:
        messages.append(ValidationMessage(
            rule_id="RULE_FE_RANGE",
            severity="ERROR",
            message=f"Fe fraction ({fe_frac:.4f}) is outside allowed range [{FE_MIN}, {FE_MAX}]."
        ))
        
    # 3. Dopant count check (must be 3 to 5)
    num_dopants = len(dopants)
    if num_dopants < MIN_DOPANTS or num_dopants > MAX_DOPANTS:
        messages.append(ValidationMessage(
            rule_id="RULE_DOPANT_COUNT",
            severity="ERROR",
            message=f"Number of selected dopants is {num_dopants}. Must select exactly 3, 4, or 5 dopant elements."
        ))
        
    # 4. Individual dopant check
    dopant_symbols = [d["symbol"] for d in dopants]
    for d_dict in dopants:
        sym = d_dict["symbol"]
        conc = d_dict["fraction"]
        ox = d_dict["oxidation_state"]
        
        # Check excluded dopants
        if sym in EXCLUDED_DOPANTS:
            reason = DOPANT_DATABASE.get(sym, {}).get("exclusion_reason", "Excluded element")
            messages.append(ValidationMessage(
                rule_id="RULE_EXCLUDED_DOPANT",
                severity="ERROR",
                message=f"Element '{sym}' is strictly excluded from dopant set: {reason}."
            ))
        elif sym not in ALLOWED_DOPANTS:
            messages.append(ValidationMessage(
                rule_id="RULE_UNRECOGNIZED_DOPANT",
                severity="ERROR",
                message=f"Element '{sym}' is not in the recognized allowed dopant set."
            ))
            
        # Check concentration range [0.005, 0.05]
        if conc < MIN_DOPANT_CONC or conc > MAX_DOPANT_CONC:
            messages.append(ValidationMessage(
                rule_id="RULE_DOPANT_CONC_RANGE",
                severity="ERROR",
                message=f"Dopant '{sym}' concentration ({conc:.4f}) is outside default range [{MIN_DOPANT_CONC}, {MAX_DOPANT_CONC}]."
            ))
            
        # Check oxidation state validity
        if sym in DOPANT_DATABASE:
            valid_ox_states = DOPANT_DATABASE[sym]["allowed_oxidation_states"]
            if ox not in valid_ox_states:
                messages.append(ValidationMessage(
                    rule_id="RULE_OXIDATION_STATE",
                    severity="ERROR",
                    message=f"Oxidation state +{ox} for '{sym}' is invalid. Allowed states: {valid_ox_states}."
                ))

    # Check for duplicate dopants
    if len(set(dopant_symbols)) != len(dopant_symbols):
        messages.append(ValidationMessage(
            rule_id="RULE_DUPLICATE_DOPANT",
            severity="ERROR",
            message="Duplicate dopant elements selected."
        ))

    # 5. M2 Occupancy sum check
    if abs(m2_occupancy - 1.0) > TOLERANCE:
        messages.append(ValidationMessage(
            rule_id="RULE_M2_OCCUPANCY",
            severity="ERROR",
            message=f"M2 total site occupancy sum ({m2_occupancy:.4f}) does not equal 1.0000 (tolerance {TOLERANCE})."
        ))

    # 6. Charge balance & Li stoichiometry check
    if user_li <= 0.0:
        messages.append(ValidationMessage(
            rule_id="RULE_LI_STOICHIOMETRY",
            severity="ERROR",
            message=f"Calculated Li fraction ({user_li:.4f}) is non-positive (<= 0.0). Structure cannot maintain charge balance with active cations."
        ))

    if not is_charge_balanced:
        messages.append(ValidationMessage(
            rule_id="RULE_CHARGE_BALANCE",
            severity="ERROR",
            message="Chemical formula is not charge-balanced under current settings."
        ))

    # 7. Carbon coating range warning/error check
    if carbon_enabled:
        if carbon_wt_pct < CARBON_WT_MIN or carbon_wt_pct > CARBON_WT_MAX:
            messages.append(ValidationMessage(
                rule_id="RULE_CARBON_COATING_RANGE",
                severity="WARNING",
                message=f"Carbon coating ({carbon_wt_pct:.2f} wt%) is outside supervisor recommended range [{CARBON_WT_MIN}, {CARBON_WT_MAX}] wt%."
            ))

    # 8. CNT range warning/error check
    if cnt_enabled:
        if cnt_wt_pct < CNT_WT_MIN or cnt_wt_pct > CNT_WT_MAX:
            messages.append(ValidationMessage(
                rule_id="RULE_CNT_RANGE",
                severity="WARNING",
                message=f"CNT fraction ({cnt_wt_pct:.2f} wt%) is outside supervisor recommended range [{CNT_WT_MIN}, {CNT_WT_MAX}] wt%."
            ))

    # 9. Future / Disabled Features Warnings
    if f_doping_enabled:
        messages.append(ValidationMessage(
            rule_id="RULE_F_DOPING_FUTURE",
            severity="WARNING",
            message="Anion F-doping is flagged as a FUTURE feature and is currently disabled in V1 cation optimization."
        ))

    if mgo_enabled:
        messages.append(ValidationMessage(
            rule_id="RULE_MGO_FUTURE",
            severity="WARNING",
            message="mGO (modified Graphene Oxide) is flagged as a FUTURE feature and is not part of the current active optimization."
        ))

    # Extract lists
    errors = [m.message for m in messages if m.severity == "ERROR"]
    warnings = [m.message for m in messages if m.severity == "WARNING"]
    info_messages = [m.message for m in messages if m.severity == "INFO"]

    if len(errors) > 0:
        overall_status = "INVALID"
        is_valid = False
    elif len(warnings) > 0:
        overall_status = "WARNING"
        is_valid = True
    else:
        overall_status = "PASS"
        is_valid = True

    return ValidationReport(
        overall_status=overall_status,
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
        info_messages=info_messages,
        details=messages
    )
