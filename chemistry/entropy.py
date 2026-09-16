"""
Configurational Entropy Engine for High-Entropy Doped LMFP Materials.

Implements S_config = -R * sum(x_i * ln(x_i)) for M2-site species.
Provides provisional entropy tier classification.
"""

import math
from typing import Dict, List, Any
from dataclasses import dataclass

# Universal Gas Constant R in J / (mol * K)
R_GAS_CONSTANT = 8.314462618

PROVISIONAL_HIGH_ENTROPY_THRESHOLD = 1.5  # S_config / R >= 1.5
PROVISIONAL_MEDIUM_ENTROPY_THRESHOLD = 0.6 # 0.6 <= S_config / R < 1.5

@dataclass
class EntropyResult:
    s_config_j_mol_k: float   # S_config in J mol^-1 K^-1
    s_config_over_r: float    # S_config / R
    num_m2_species: int       # Total distinct species on M2 site (Mn, Fe + dopants)
    species_fractions: Dict[str, float]  # Normalized fractions used in calculation
    classification: str       # High-Entropy, Medium-Entropy / Entropy-Assisted, Low-Entropy
    classification_label: str # Full label with provisional disclaimer
    is_provisional: bool

def calculate_configurational_entropy(
    mn_frac: float,
    fe_frac: float,
    dopants: List[Dict[str, Any]], # list of {"symbol": str, "fraction": float}
    phi_m2_vacancy: float = 0.0
) -> EntropyResult:
    """
    Calculate configurational entropy S_config for M2 transition-metal site species.
    
    S_config = -R * sum( x_i * ln(x_i) )
    where x_i are species mole fractions on M2 site.
    """
    raw_fractions = {}
    if mn_frac > 0:
        raw_fractions["Mn"] = mn_frac
    if fe_frac > 0:
        raw_fractions["Fe"] = fe_frac
        
    for d in dopants:
        sym = d["symbol"]
        frac = d["fraction"]
        if frac > 0:
            raw_fractions[sym] = raw_fractions.get(sym, 0.0) + frac
            
    if phi_m2_vacancy > 0:
        raw_fractions["Vacancy_M2"] = phi_m2_vacancy
        
    total_occ = sum(raw_fractions.values())
    if total_occ <= 0:
        return EntropyResult(
            s_config_j_mol_k=0.0,
            s_config_over_r=0.0,
            num_m2_species=0,
            species_fractions={},
            classification="Undefined",
            classification_label="Undefined (Zero M2 occupancy)",
            is_provisional=True
        )
        
    # Normalize fractions over M2 site
    norm_fractions = {k: v / total_occ for k, v in raw_fractions.items()}
    
    # Calculate sum(x_i * ln(x_i))
    entropy_sum = 0.0
    for frac in norm_fractions.values():
        if frac > 0:
            entropy_sum += frac * math.log(frac)
            
    s_config_over_r = -entropy_sum
    s_config_j_mol_k = s_config_over_r * R_GAS_CONSTANT
    
    # Classification logic based on supervisor criteria
    if s_config_over_r >= PROVISIONAL_HIGH_ENTROPY_THRESHOLD:
        classification = "High-Entropy"
        classification_label = "High-Entropy (Provisional Criterion: S_config/R >= 1.5)"
    elif s_config_over_r >= PROVISIONAL_MEDIUM_ENTROPY_THRESHOLD:
        classification = "Entropy-Assisted / Medium-Entropy"
        classification_label = "Entropy-Assisted / Medium-Entropy (Provisional Criterion: 0.6 <= S_config/R < 1.5)"
    else:
        classification = "Low-Entropy / Conventional"
        classification_label = "Low-Entropy / Conventional (Provisional Criterion: S_config/R < 0.6)"

    return EntropyResult(
        s_config_j_mol_k=round(s_config_j_mol_k, 4),
        s_config_over_r=round(s_config_over_r, 4),
        num_m2_species=len(norm_fractions),
        species_fractions={k: round(v, 6) for k, v in norm_fractions.items()},
        classification=classification,
        classification_label=classification_label,
        is_provisional=True
    )
