"""
Tests for Chemical Formula Generation & M2 Occupancy (Tests 1, 2, 3, 4).
"""

import pytest
from chemistry.formula import generate_formula
from chemistry.validation import validate_composition
from chemistry.charge_balance import calculate_charge_balance

def test_1_valid_3_dopant_composition():
    """TEST 1: A valid Mn/Fe + 3-dopant composition."""
    # Mn=0.65, Fe=0.25, Mg=0.03, Zn=0.04, Ni=0.03 -> Total M2 = 1.00
    mn = 0.65
    fe = 0.25
    dopants = [
        {"symbol": "Mg", "fraction": 0.03, "oxidation_state": 2},
        {"symbol": "Zn", "fraction": 0.04, "oxidation_state": 2},
        {"symbol": "Ni", "fraction": 0.03, "oxidation_state": 2}
    ]
    
    cb_res = calculate_charge_balance(mn, fe, dopants)
    formula = generate_formula(cb_res.adjusted_li, mn, fe, dopants)
    val_res = validate_composition(mn, fe, dopants, cb_res.adjusted_li, cb_res.is_balanced, cb_res.m2_occupancy)
    
    assert formula.m2_occupancy == pytest.approx(1.0, abs=1e-4)
    assert cb_res.m2_occupancy_valid is True
    assert val_res.is_valid is True
    assert "Li" in formula.formula_string
    assert "Mn0.65" in formula.formula_string
    assert "Fe0.25" in formula.formula_string

def test_2_valid_5_dopant_composition():
    """TEST 2: A valid Mn/Fe + 5-dopant composition (matching supervisor reference example)."""
    # Li(Mn0.65 Fe0.26 Mg0.02 Zn0.02 Nb0.01 Cu0.02 Zr0.02)PO4
    mn = 0.65
    fe = 0.26
    dopants = [
        {"symbol": "Mg", "fraction": 0.02, "oxidation_state": 2},
        {"symbol": "Zn", "fraction": 0.02, "oxidation_state": 2},
        {"symbol": "Nb", "fraction": 0.01, "oxidation_state": 5},
        {"symbol": "Cu", "fraction": 0.02, "oxidation_state": 2},
        {"symbol": "Zr", "fraction": 0.02, "oxidation_state": 4}
    ]
    
    cb_res = calculate_charge_balance(mn, fe, dopants)
    formula = generate_formula(cb_res.adjusted_li, mn, fe, dopants)
    val_res = validate_composition(mn, fe, dopants, cb_res.adjusted_li, cb_res.is_balanced, cb_res.m2_occupancy)
    
    assert formula.m2_occupancy == pytest.approx(1.0, abs=1e-4)
    assert val_res.is_valid is True
    assert len(formula.dopants) == 5
    # M2 cation charge = 0.65*2 + 0.26*2 + 0.02*2 + 0.02*2 + 0.01*5 + 0.02*2 + 0.02*4
    # = 1.3 + 0.52 + 0.04 + 0.04 + 0.05 + 0.04 + 0.08 = 2.07
    # Required Li = 3 - 2.07 = 0.93
    assert cb_res.required_li == pytest.approx(0.93, abs=1e-4)

def test_3_different_dopant_concentrations():
    """TEST 3: Support non-equal, individual dopant concentrations."""
    mn = 0.70
    fe = 0.25
    dopants = [
        {"symbol": "Mg", "fraction": 0.02, "oxidation_state": 2},
        {"symbol": "Zn", "fraction": 0.01, "oxidation_state": 2},
        {"symbol": "Zr", "fraction": 0.02, "oxidation_state": 4}
    ]
    
    cb_res = calculate_charge_balance(mn, fe, dopants)
    formula = generate_formula(cb_res.adjusted_li, mn, fe, dopants)
    
    assert formula.m2_occupancy == pytest.approx(1.0, abs=1e-4)
    assert formula.dopants[0].fraction == 0.02
    assert formula.dopants[1].fraction == 0.01
    assert formula.dopants[2].fraction == 0.02

def test_4_m2_occupancy_failure():
    """TEST 4: M2 occupancy sum not equal to 1.0 -> Invalid status."""
    mn = 0.70
    fe = 0.20
    dopants = [
        {"symbol": "Mg", "fraction": 0.02, "oxidation_state": 2},
        {"symbol": "Zn", "fraction": 0.01, "oxidation_state": 2},
        {"symbol": "Zr", "fraction": 0.02, "oxidation_state": 4}
    ]
    # Sum = 0.70 + 0.20 + 0.05 = 0.95 != 1.0
    
    cb_res = calculate_charge_balance(mn, fe, dopants)
    val_res = validate_composition(mn, fe, dopants, cb_res.adjusted_li, cb_res.is_balanced, cb_res.m2_occupancy)
    
    assert cb_res.m2_occupancy == pytest.approx(0.95, abs=1e-4)
    assert cb_res.m2_occupancy_valid is False
    assert val_res.is_valid is False
    assert val_res.overall_status == "INVALID"
    assert any("M2 total site occupancy sum" in err for err in val_res.errors)

def test_m2_occupancy_1_0100_rejected():
    """Test specifically that an M2 site occupancy of 1.0100 is rejected and fails validation."""
    mn = 0.65
    fe = 0.26
    dopants = [
        {"symbol": "Mg", "fraction": 0.02, "oxidation_state": 2},
        {"symbol": "Zn", "fraction": 0.02, "oxidation_state": 2},
        {"symbol": "Nb", "fraction": 0.01, "oxidation_state": 5},
        {"symbol": "Cu", "fraction": 0.02, "oxidation_state": 2},
        {"symbol": "Zr", "fraction": 0.03, "oxidation_state": 4}  # 0.03 instead of 0.02 -> Sum = 1.0100
    ]
    
    cb_res = calculate_charge_balance(mn, fe, dopants)
    val_res = validate_composition(mn, fe, dopants, cb_res.adjusted_li, cb_res.is_balanced, cb_res.m2_occupancy)
    
    assert cb_res.m2_occupancy == pytest.approx(1.0100, abs=1e-4)
    assert cb_res.m2_occupancy_valid is False
    assert val_res.is_valid is False
    assert val_res.overall_status == "INVALID"
    assert any("M2 total site occupancy sum" in err for err in val_res.errors)

def test_electrochemical_temperature_cycling_protocols():
    """Verify that electrochemical plan explicitly includes room-temp, high-temp, and low-temp cycling."""
    from design.electrochemistry import get_electrochemical_plan
    plan = get_electrochemical_plan()
    
    test_names = [item["test_name"] for item in plan.test_items]
    assert any("Room-Temperature Cycling" in name for name in test_names)
    assert any("High-Temperature Cycling" in name for name in test_names)
    assert any("Low-Temperature Cycling" in name for name in test_names)

