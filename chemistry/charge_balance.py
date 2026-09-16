"""
Charge Balance Engine for High-Entropy Doped LMFP Materials.

Implements deterministic charge calculations based on site occupancy
and species oxidation states.

General Formula:
Li_(1-delta) [ Mn_m Fe_f A_x1 B_x2 C_x3 D_x4 E_x5 ] P_(1-s) Si_s O_(4-gamma) F_gamma

Charge Neutrality Equation:
Q_net = (1 - delta)*z_Li + Q_M2 + (1-s)*z_P + s*z_Si + (4-gamma)*z_O + gamma*z_F
Where:
- z_Li = +1
- z_P  = +5
- z_Si = +4
- z_O  = -2
- z_F  = -1
- Q_M2 = m*z_Mn + f*z_Fe + sum(x_i * z_i)
- z_Mn = +2 (fixed V1)
- z_Fe = +2 (fixed V1)

Simplifying:
Q_net = (1 - delta) + Q_M2 - s + gamma - 3

For balance (Q_net = 0):
Ideal (1 - delta) = 3 + s - gamma - Q_M2
"""

from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, field

# Numerical tolerance for floating point comparisons
TOLERANCE = 1e-4

@dataclass
class ChargeBalanceResult:
    is_balanced: bool
    net_charge_before: float
    net_charge_after: float
    q_m2: float
    q_total_positive: float
    q_total_negative: float
    required_li: float
    delta_li: float  # Li vacancy fraction (1 - required_li)
    phi_m2: float    # M2 vacancy fraction (1 - m - f - sum(x_i))
    m2_occupancy: float
    m2_occupancy_valid: bool
    user_li: float
    adjusted_li: float
    adjustment_strategy: str
    adjustment_details: List[Dict[str, Any]]
    explanation: str

def calculate_charge_balance(
    mn_frac: float,
    fe_frac: float,
    dopants: List[Dict[str, Any]],  # list of {"symbol": str, "fraction": float, "oxidation_state": int}
    user_li: float = 1.0,
    strategy: str = "ADJUST_LI",
    s_si: float = 0.0,
    gamma_f: float = 0.0,
    phi_m2: float = 0.0
) -> ChargeBalanceResult:
    """
    Calculate charge balance for an HE-LMFP composition.
    
    Mn and Fe oxidation states are fixed at +2.
    
    dopants item format:
    {"symbol": "Mg", "fraction": 0.02, "oxidation_state": 2}
    """
    # 1. M2 Occupancy calculation
    dopant_frac_sum = sum(d["fraction"] for d in dopants)
    m2_occupancy = mn_frac + fe_frac + dopant_frac_sum + phi_m2
    m2_occupancy_valid = abs(m2_occupancy - 1.0) <= TOLERANCE
    
    # 2. M2 Cation Charge calculation (Mn=2+, Fe=2+)
    q_mn = mn_frac * 2.0
    q_fe = fe_frac * 2.0
    q_dopants = sum(d["fraction"] * d["oxidation_state"] for d in dopants)
    
    # If M2 vacancies exist, vacancies carry 0 charge
    q_m2 = q_mn + q_fe + q_dopants
    
    # 3. Required Li for exact charge balance (Q_net = 0)
    # (1 - delta) + Q_m2 - s_si + gamma_f - 3 = 0
    # Required Li = 3 + s_si - gamma_f - Q_m2
    required_li = 3.0 + s_si - gamma_f - q_m2
    delta_li = 1.0 - required_li
    
    # Net charge with user-specified Li fraction
    net_charge_before = user_li + q_m2 - s_si + gamma_f - 3.0
    
    adjustment_details = []
    adjusted_li = user_li
    net_charge_after = net_charge_before
    
    if strategy == "ADJUST_LI":
        adjusted_li = required_li
        net_charge_after = adjusted_li + q_m2 - s_si + gamma_f - 3.0
        if required_li <= 0.0:
            is_balanced = False
            adjustment_details.append({
                "parameter": "Li fraction",
                "original": round(user_li, 5),
                "adjusted": round(required_li, 5),
                "reason": f"Impossible stoichiometry: Calculated Li fraction is non-positive ({required_li:.4f}). Composition cannot be charge balanced under active cations.",
                "net_charge_result": round(net_charge_after, 6)
            })
        elif abs(user_li - adjusted_li) > TOLERANCE:
            adjustment_details.append({
                "parameter": "Li fraction",
                "original": round(user_li, 5),
                "adjusted": round(adjusted_li, 5),
                "reason": f"Automatic Li balancing to compensate M2 site cation charge (Q_M2 = {q_m2:.4f}). Li vacancy delta = {delta_li:.4f}.",
                "net_charge_result": round(net_charge_after, 6)
            })
    elif strategy == "CHECK_ONLY":
        adjusted_li = user_li
        net_charge_after = net_charge_before
        if abs(net_charge_before) > TOLERANCE:
            adjustment_details.append({
                "parameter": "Charge Balance",
                "original": round(user_li, 5),
                "adjusted": round(user_li, 5),
                "reason": f"Manual mode: Net charge imbalance of {net_charge_before:+.4f} detected. Neutral balance requires Li = {required_li:.4f}.",
                "net_charge_result": round(net_charge_before, 6)
            })

    is_balanced = abs(net_charge_after) <= TOLERANCE and adjusted_li > 0.0
    
    # Total positive and negative charge
    q_total_positive = adjusted_li * 1.0 + q_m2 + 5.0 * (1.0 - s_si) + 4.0 * s_si
    q_total_negative = -2.0 * (4.0 - gamma_f) - 1.0 * gamma_f
    
    # Build explanation string
    expl_lines = [
        f"M2 Site Charge (Q_M2): {q_m2:.4f} (Mn2+: {q_mn:.4f}, Fe2+: {q_fe:.4f}, Dopants: {q_dopants:.4f})",
        f"Total Positive Charge: {q_total_positive:+.4f} e, Total Negative Charge: {q_total_negative:+.4f} e",
        f"Required Li fraction for neutrality: {required_li:.4f} (Li vacancy delta = {delta_li:.4f})."
    ]
    if adjustment_details:
        expl_lines.append(f"Adjustment Action ({strategy}): {adjustment_details[0]['reason']}")
    else:
        expl_lines.append("Composition is naturally charge-balanced under current settings.")

    return ChargeBalanceResult(
        is_balanced=is_balanced,
        net_charge_before=round(net_charge_before, 6),
        net_charge_after=round(net_charge_after, 6),
        q_m2=round(q_m2, 6),
        q_total_positive=round(q_total_positive, 6),
        q_total_negative=round(q_total_negative, 6),
        required_li=round(required_li, 6),
        delta_li=round(delta_li, 6),
        phi_m2=round(phi_m2, 6),
        m2_occupancy=round(m2_occupancy, 6),
        m2_occupancy_valid=m2_occupancy_valid,
        user_li=round(user_li, 6),
        adjusted_li=round(adjusted_li, 6),
        adjustment_strategy=strategy,
        adjustment_details=adjustment_details,
        explanation="\n".join(expl_lines)
    )
