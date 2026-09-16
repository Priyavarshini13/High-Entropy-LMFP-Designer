"""
Capacity Engine for High-Entropy Doped LMFP Materials.

Computes theoretical capacity based on active Li exchange and formula molar mass.
Displays supervisor benchmark reference values (170 mAh/g theoretical,
150-160 mAh/g practical target, 2.5-4.2 V window) while clearly distinguishing
theoretical reference from formula-calculated values.
"""

from dataclasses import dataclass
from typing import Dict, Any

# Faraday Constant in Coulombs per mole
FARADAY_CONSTANT = 96485.3321

# Supervisor reference constants
REFERENCE_THEORETICAL_CAPACITY = 170.0  # mAh/g
PRACTICAL_CAPACITY_MIN = 150.0          # mAh/g at 0.1C
PRACTICAL_CAPACITY_MAX = 160.0          # mAh/g at 0.1C
VOLTAGE_MIN = 2.5                        # V
VOLTAGE_MAX = 4.2                        # V

# C-rate Reference Duration Table
C_RATE_REFERENCE_TABLE = [
    {"c_rate": "0.02C", "approx_duration": "~20 hours", "notes": "Ultra-low rate / near-equilibrium testing"},
    {"c_rate": "0.1C",  "approx_duration": "~10 hours", "notes": "Standard practical capacity benchmark rate"},
    {"c_rate": "1C",    "approx_duration": "~1 hour",   "notes": "Nominal 1-hour discharge rate"},
    {"c_rate": "2C",    "approx_duration": "~30 minutes", "notes": "Fast discharge rate"},
    {"c_rate": "4C",    "approx_duration": "~15 minutes", "notes": "High power discharge rate"}
]

@dataclass
class CapacityMetrics:
    reference_theoretical_capacity: float  # 170.0 mAh/g (Supervisor Benchmark)
    formula_calculated_capacity_metric: float # Formula-based calculated capacity metric
    practical_target_min: float            # 150.0 mAh/g
    practical_target_max: float            # 160.0 mAh/g
    voltage_window_min: float              # 2.5 V
    voltage_window_max: float              # 4.2 V
    active_li_moles: float                 # (1 - delta)
    molar_mass_g_mol: float
    c_rate_panel: list
    disclaimer: str

def calculate_capacity_metrics(
    li_fraction: float,
    molar_mass: float
) -> CapacityMetrics:
    """
    Calculate capacity reference metrics for the given formula.
    
    Formula-based calculated capacity metric = (n_Li * F) / (3.6 * Molar_Mass) [mAh/g]
    """
    if molar_mass <= 0:
        calc_metric = 0.0
    else:
        # C in mAh/g
        calc_metric = (li_fraction * FARADAY_CONSTANT) / (3.6 * molar_mass)
        
    disclaimer = (
        "Note on Capacity Metrics: The Project Reference Theoretical Capacity (170.0 mAh/g) "
        "is the supervisor-defined reference benchmark. The Formula-Based Calculated Capacity Metric "
        "is derived strictly from stoichiometry ((1-δ) * F / (3.6 * M)). "
        "These are distinct reference metrics and should NOT be interpreted as experimental performance predictions."
    )
    
    return CapacityMetrics(
        reference_theoretical_capacity=REFERENCE_THEORETICAL_CAPACITY,
        formula_calculated_capacity_metric=round(calc_metric, 2),
        practical_target_min=PRACTICAL_CAPACITY_MIN,
        practical_target_max=PRACTICAL_CAPACITY_MAX,
        voltage_window_min=VOLTAGE_MIN,
        voltage_window_max=VOLTAGE_MAX,
        active_li_moles=round(li_fraction, 6),
        molar_mass_g_mol=round(molar_mass, 4),
        c_rate_panel=C_RATE_REFERENCE_TABLE,
        disclaimer=disclaimer
    )
