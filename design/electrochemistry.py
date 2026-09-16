"""
Electrochemical Characterization Design Module for HE-LMFP.

Defines electrochemical evaluation protocols:
- Charge-discharge cycling
- C-rate testing (0.02C, 0.1C, 1C, 2C, 4C)
- Voltage window (2.5 - 4.2 V)
- Temperature cycling protocols (Room Temperature, High Temperature, Low Temperature)
"""

from dataclasses import dataclass
from typing import List, Dict, Any

VOLTAGE_LOWER_LIMIT = 2.5  # V
VOLTAGE_UPPER_LIMIT = 4.2  # V

ELECTROCHEMICAL_TEST_ITEMS = [
    {
        "test_name": "Galvanostatic Charge-Discharge Cycling",
        "description": "Standard constant current charge-discharge cycling to establish reversible discharge capacity (mAh/g) and initial coulombic efficiency (ICE %).",
        "voltage_range": "2.5 V - 4.2 V"
    },
    {
        "test_name": "C-Rate Capability Test",
        "description": "Ladder rate discharge test at 0.02C, 0.1C, 0.5C, 1C, 2C, and 4C to determine rate retention and kinetic performance.",
        "rates": ["0.02C", "0.1C", "0.5C", "1.0C", "2.0C", "4.0C"]
    },
    {
        "test_name": "Room-Temperature Cycling (25°C)",
        "description": "Long-term capacity retention cycling at 25°C (1C/1C rate) to evaluate structural stability.",
        "temperature": "25°C"
    },
    {
        "test_name": "High-Temperature Cycling (55°C)",
        "description": "Accelerated degradation cycling at elevated temperature (55°C) to assess Mn dissolution and interface stability.",
        "temperature": "55°C"
    },
    {
        "test_name": "Low-Temperature Cycling (-20°C)",
        "description": "Low-temperature capacity retention cycling and discharge performance at -20°C (0.1C rate) to evaluate ion diffusion kinetics.",
        "temperature": "-20°C"
    }
]

@dataclass
class ElectrochemicalPlan:
    voltage_min: float
    voltage_max: float
    test_items: List[Dict[str, Any]]
    disclaimer: str

def get_electrochemical_plan(
    v_min: float = VOLTAGE_LOWER_LIMIT,
    v_max: float = VOLTAGE_UPPER_LIMIT
) -> ElectrochemicalPlan:
    """Return electrochemical testing plan configuration."""
    disclaimer = (
        "Electrochemical test profiles are design specifications. "
        "Measured capacity, retention, and rate capabilities require experimental cell assembly "
        "(e.g., coin cell / pouch cell) and battery testing."
    )
    
    return ElectrochemicalPlan(
        voltage_min=v_min,
        voltage_max=v_max,
        test_items=ELECTROCHEMICAL_TEST_ITEMS,
        disclaimer=disclaimer
    )
