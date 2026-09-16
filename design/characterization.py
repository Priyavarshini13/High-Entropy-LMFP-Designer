"""
Material Characterization Module for HE-LMFP.

Defines the required 5 physical & structural characterization techniques per supervisor:
1. XRD (X-ray Diffraction)
2. SEM (Scanning Electron Microscopy)
3. BET (Surface Area Analysis)
4. Electrical Conductivity
5. Tap Density
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any

REQUIRED_CHARACTERIZATION_TECHNIQUES = [
    {
        "technique": "XRD",
        "full_name": "X-Ray Diffraction",
        "purpose": "Phase purity analysis, lattice parameter refinement (a, b, c volume), M1/M2 cation anti-site defect estimation.",
        "status": "Planned / Standard Protocol"
    },
    {
        "technique": "SEM",
        "full_name": "Scanning Electron Microscopy",
        "purpose": "Primary particle morphology, secondary agglomerate size, carbon coating distribution, CNT networking visualization.",
        "status": "Planned / Standard Protocol"
    },
    {
        "technique": "BET",
        "full_name": "Brunauer-Emmett-Teller Surface Area Analysis",
        "purpose": "Specific surface area (m²/g) measurement and N2 adsorption-desorption porosity profile.",
        "status": "Planned / Standard Protocol"
    },
    {
        "technique": "Electrical Conductivity",
        "full_name": "Four-Probe / AC Impedance Powder Conductivity",
        "purpose": "Electronic conductivity (S/cm) measurement of pelletized powder to evaluate carbon coating & dopant percolation.",
        "status": "Planned / Standard Protocol"
    },
    {
        "technique": "Tap Density",
        "full_name": "Powder Tap Density Measurement",
        "purpose": "Volumetric tap density (g/cm³) assessment for electrode packing density evaluation.",
        "status": "Planned / Standard Protocol"
    }
]

@dataclass
class CharacterizationPlan:
    techniques: List[Dict[str, Any]]
    total_techniques_count: int
    notes: str

def get_characterization_plan() -> CharacterizationPlan:
    """Return mandatory physical characterization plan."""
    return CharacterizationPlan(
        techniques=REQUIRED_CHARACTERIZATION_TECHNIQUES,
        total_techniques_count=len(REQUIRED_CHARACTERIZATION_TECHNIQUES),
        notes="Physical characterization protocol includes exactly the 5 supervisor-specified techniques. No invented values reported without experimental measurement."
    )
