"""
Tests for Charge Balance Engine (Tests 5, 6, 7).
"""

import pytest
from chemistry.charge_balance import calculate_charge_balance

def test_supervisor_example_charge_balance_derivation():
    """Verify supervisor reference composition is NOT assumed balanced at Li=0.95. Required Li must be independently derived as 0.93."""
    mn = 0.65
    fe = 0.26
    dopants = [
        {"symbol": "Mg", "fraction": 0.02, "oxidation_state": 2},
        {"symbol": "Zn", "fraction": 0.02, "oxidation_state": 2},
        {"symbol": "Nb", "fraction": 0.01, "oxidation_state": 5},
        {"symbol": "Cu", "fraction": 0.02, "oxidation_state": 2},
        {"symbol": "Zr", "fraction": 0.02, "oxidation_state": 4}
    ]
    # In CHECK_ONLY mode with Li=0.95, engine reports net charge imbalance of +0.02 e
    cb_manual = calculate_charge_balance(mn, fe, dopants, user_li=0.95, strategy="CHECK_ONLY")
    assert cb_manual.is_balanced is False
    assert cb_manual.net_charge_before == pytest.approx(0.02, abs=1e-4)
    
    # In ADJUST_LI mode, engine independently derives neutral Li = 0.93 (delta = 0.07)
    cb_auto = calculate_charge_balance(mn, fe, dopants, user_li=1.0, strategy="ADJUST_LI")
    assert cb_auto.is_balanced is True
    assert cb_auto.adjusted_li == pytest.approx(0.93, abs=1e-4)
    assert cb_auto.delta_li == pytest.approx(0.07, abs=1e-4)

def test_5_charge_imbalance_detection():
    """TEST 5: Manual / CHECK_ONLY mode detects net charge imbalance when user Li is fixed to 1.0."""
    mn = 0.65
    fe = 0.25
    dopants = [
        {"symbol": "Mg", "fraction": 0.03, "oxidation_state": 2},
        {"symbol": "Zn", "fraction": 0.04, "oxidation_state": 2},
        {"symbol": "Al", "fraction": 0.03, "oxidation_state": 3}  # Al3+ increases Q_M2 to 2.03
    ]
    
    # In CHECK_ONLY mode with fixed user_li = 1.0, net charge = 1.0 + 2.03 - 3.0 = +0.03 (imbalanced)
    cb_res = calculate_charge_balance(mn, fe, dopants, user_li=1.0, strategy="CHECK_ONLY")
    
    assert cb_res.is_balanced is False
    assert cb_res.net_charge_before == pytest.approx(0.03, abs=1e-4)
    assert cb_res.required_li == pytest.approx(0.97, abs=1e-4)

def test_6_ti3_versus_ti4_charge_balance_change():
    """TEST 6: Ti3+ versus Ti4+ changes total cation charge and required Li stoichiometry."""
    mn = 0.70
    fe = 0.20
    
    dopants_ti3 = [
        {"symbol": "Mg", "fraction": 0.04, "oxidation_state": 2},
        {"symbol": "Zn", "fraction": 0.04, "oxidation_state": 2},
        {"symbol": "Ti", "fraction": 0.02, "oxidation_state": 3}  # Ti3+
    ]
    
    dopants_ti4 = [
        {"symbol": "Mg", "fraction": 0.04, "oxidation_state": 2},
        {"symbol": "Zn", "fraction": 0.04, "oxidation_state": 2},
        {"symbol": "Ti", "fraction": 0.02, "oxidation_state": 4}  # Ti4+
    ]
    
    cb_ti3 = calculate_charge_balance(mn, fe, dopants_ti3)
    cb_ti4 = calculate_charge_balance(mn, fe, dopants_ti4)
    
    # Q_M2 for Ti3+ = 0.70*2 + 0.20*2 + 0.04*2 + 0.04*2 + 0.02*3 = 1.4 + 0.4 + 0.08 + 0.08 + 0.06 = 2.02
    # Q_M2 for Ti4+ = 1.4 + 0.4 + 0.08 + 0.08 + 0.08 = 2.04
    assert cb_ti3.q_m2 == pytest.approx(2.02, abs=1e-4)
    assert cb_ti4.q_m2 == pytest.approx(2.04, abs=1e-4)
    assert cb_ti3.required_li == pytest.approx(0.98, abs=1e-4)
    assert cb_ti4.required_li == pytest.approx(0.96, abs=1e-4)
    assert cb_ti3.required_li != cb_ti4.required_li

def test_7_cu2_versus_cu3_charge_balance_change():
    """TEST 7: Cu2+ versus Cu3+ changes total cation charge and required Li stoichiometry."""
    mn = 0.70
    fe = 0.20
    
    dopants_cu2 = [
        {"symbol": "Mg", "fraction": 0.04, "oxidation_state": 2},
        {"symbol": "Zn", "fraction": 0.04, "oxidation_state": 2},
        {"symbol": "Cu", "fraction": 0.02, "oxidation_state": 2}  # Cu2+
    ]
    
    dopants_cu3 = [
        {"symbol": "Mg", "fraction": 0.04, "oxidation_state": 2},
        {"symbol": "Zn", "fraction": 0.04, "oxidation_state": 2},
        {"symbol": "Cu", "fraction": 0.02, "oxidation_state": 3}  # Cu3+
    ]
    
    cb_cu2 = calculate_charge_balance(mn, fe, dopants_cu2)
    cb_cu3 = calculate_charge_balance(mn, fe, dopants_cu3)
    
    assert cb_cu2.q_m2 == pytest.approx(2.00, abs=1e-4)
    assert cb_cu3.q_m2 == pytest.approx(2.02, abs=1e-4)
    assert cb_cu2.required_li == pytest.approx(1.00, abs=1e-4)
    assert cb_cu3.required_li == pytest.approx(0.98, abs=1e-4)
    assert cb_cu2.required_li != cb_cu3.required_li

def test_impossible_composition_rejected_when_required_li_non_positive():
    """Verify that compositions requiring Li <= 0 are rejected as invalid/imbalanced."""
    mn = 0.60
    fe = 0.10
    dopants = [
        {"symbol": "Nb", "fraction": 0.20, "oxidation_state": 5}, # Q_M2 = 0.6*2 + 0.1*2 + 0.2*5 = 2.4
        {"symbol": "Zr", "fraction": 0.10, "oxidation_state": 4}  # Q_M2 = 2.4 + 0.4 = 2.8
    ] # Total Q_M2 = 2.8 -> If dopant charge pushes Q_M2 >= 3.0, required Li <= 0
    dopants_high = [
        {"symbol": "Nb", "fraction": 0.25, "oxidation_state": 5},
        {"symbol": "Zr", "fraction": 0.05, "oxidation_state": 4}
    ] # Q_M2 = 0.6*2 + 0.1*2 + 0.25*5 + 0.05*4 = 1.2 + 0.2 + 1.25 + 0.2 = 2.85 (still 0.15 Li)
    
    dopants_extreme = [
        {"symbol": "Nb", "fraction": 0.30, "oxidation_state": 5} # Q_M2 = 1.2 + 0.2 + 1.5 = 2.9 (0.10 Li)
    ]
    # Extreme hypothetical: Q_M2 = 3.05 -> required Li = -0.05 <= 0
    dopants_over = [
        {"symbol": "Nb", "fraction": 0.35, "oxidation_state": 5} # Q_M2 = 1.2 + 0.2 + 1.75 = 3.15 -> required Li = -0.15
    ]
    cb_over = calculate_charge_balance(mn, fe, dopants_over)
    assert cb_over.is_balanced is False
    assert cb_over.required_li < 0.0
