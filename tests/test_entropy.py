"""
Tests for Entropy Engine (Tests 14, 15).
"""

import pytest
import math
from chemistry.entropy import calculate_configurational_entropy, R_GAS_CONSTANT

def test_14_entropy_calculation():
    """TEST 14: Verify exact numerical value of S_config = -R sum(x_i ln x_i)."""
    # 5 species on M2 site: Mn=0.6, Fe=0.2, Mg=0.05, Zn=0.05, Ni=0.10 (Sum = 1.0)
    mn = 0.60
    fe = 0.20
    dopants = [
        {"symbol": "Mg", "fraction": 0.05},
        {"symbol": "Zn", "fraction": 0.05},
        {"symbol": "Ni", "fraction": 0.10}
    ]
    
    ent_res = calculate_configurational_entropy(mn, fe, dopants)
    
    # Expected S_config/R = - (0.6*ln(0.6) + 0.2*ln(0.2) + 0.05*ln(0.05) + 0.05*ln(0.05) + 0.10*ln(0.10))
    expected_sum = (
        0.60 * math.log(0.60) +
        0.20 * math.log(0.20) +
        0.05 * math.log(0.05) +
        0.05 * math.log(0.05) +
        0.10 * math.log(0.10)
    )
    expected_s_over_r = -expected_sum
    expected_s = expected_s_over_r * R_GAS_CONSTANT
    
    assert ent_res.s_config_over_r == pytest.approx(expected_s_over_r, abs=1e-4)
    assert ent_res.s_config_j_mol_k == pytest.approx(expected_s, abs=1e-4)
    assert ent_res.num_m2_species == 5

def test_15_provisional_high_entropy_classification():
    """TEST 15: High-Entropy classification when S_config/R >= 1.5 with provisional label."""
    # 7 equimolar species on M2 site (Mn, Fe + 5 dopants each 1/7 fraction)
    frac = 1.0 / 7.0
    mn = frac
    fe = frac
    dopants = [
        {"symbol": "Mg", "fraction": frac},
        {"symbol": "Zn", "fraction": frac},
        {"symbol": "Ni", "fraction": frac},
        {"symbol": "Cu", "fraction": frac},
        {"symbol": "Al", "fraction": frac}
    ]
    
    ent_res = calculate_configurational_entropy(mn, fe, dopants)
    
    # Expected S_config/R = ln(7) ~ 1.9459 >= 1.5
    assert ent_res.s_config_over_r >= 1.5
    assert ent_res.classification == "High-Entropy"
    assert "Provisional" in ent_res.classification_label
    assert ent_res.is_provisional is True
