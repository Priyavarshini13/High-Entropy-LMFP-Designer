"""
Tests for Dopant Constraints & Validation Engine (Tests 8, 9, 10, 11, 12, 13, 16, 17, 18, 19).
"""

import pytest
from chemistry.validation import validate_composition
from chemistry.dopants import validate_dopant_selection

def test_8_dopant_conc_below_minimum():
    """TEST 8: Dopant concentration below 0.005 -> Invalid."""
    mn = 0.65
    fe = 0.25
    dopants = [
        {"symbol": "Mg", "fraction": 0.002, "oxidation_state": 2}, # Below 0.005
        {"symbol": "Zn", "fraction": 0.048, "oxidation_state": 2},
        {"symbol": "Ni", "fraction": 0.050, "oxidation_state": 2}
    ]
    val_res = validate_composition(mn, fe, dopants)
    assert val_res.is_valid is False
    assert any("outside default range [0.005, 0.05]" in err for err in val_res.errors)

def test_9_dopant_conc_above_maximum():
    """TEST 9: Dopant concentration above 0.05 -> Invalid."""
    mn = 0.65
    fe = 0.20
    dopants = [
        {"symbol": "Mg", "fraction": 0.07, "oxidation_state": 2}, # Above 0.05
        {"symbol": "Zn", "fraction": 0.04, "oxidation_state": 2},
        {"symbol": "Ni", "fraction": 0.04, "oxidation_state": 2}
    ]
    val_res = validate_composition(mn, fe, dopants)
    assert val_res.is_valid is False
    assert any("outside default range [0.005, 0.05]" in err for err in val_res.errors)

def test_10_only_2_dopants_selected():
    """TEST 10: Only 2 dopants selected -> Invalid."""
    dopants_list = ["Mg", "Zn"]
    is_valid, errors = validate_dopant_selection(dopants_list)
    assert is_valid is False
    assert any("3, 4, or 5 dopant elements" in err for err in errors)

def test_11_6_dopants_selected():
    """TEST 11: 6 dopants selected -> Invalid."""
    dopants_list = ["Mg", "Zn", "Ni", "Cu", "Al", "Ti"]
    is_valid, errors = validate_dopant_selection(dopants_list)
    assert is_valid is False
    assert any("3, 4, or 5 dopant elements" in err for err in errors)

def test_12_cr_selected():
    """TEST 12: Cr selected -> Invalid (Cr is strictly excluded)."""
    dopants_list = ["Mg", "Zn", "Cr"]
    is_valid, errors = validate_dopant_selection(dopants_list)
    assert is_valid is False
    assert any("Cr" in err and "excluded" in err for err in errors)

def test_13_co_selected():
    """TEST 13: Co selected -> Invalid (Co is strictly excluded)."""
    dopants_list = ["Mg", "Zn", "Co"]
    is_valid, errors = validate_dopant_selection(dopants_list)
    assert is_valid is False
    assert any("Co" in err and "excluded" in err for err in errors)

def test_16_carbon_coating_outside_recommended_range():
    """TEST 16: Carbon coating outside 2–3 wt% maximum produces validation warning."""
    mn = 0.65
    fe = 0.25
    dopants = [
        {"symbol": "Mg", "fraction": 0.03, "oxidation_state": 2},
        {"symbol": "Zn", "fraction": 0.04, "oxidation_state": 2},
        {"symbol": "Ni", "fraction": 0.03, "oxidation_state": 2}
    ]
    val_res = validate_composition(
        mn, fe, dopants, carbon_wt_pct=4.0, carbon_enabled=True
    )
    assert val_res.overall_status == "WARNING"
    assert any("Carbon coating (4.00 wt%) is outside supervisor recommended range" in warn for warn in val_res.warnings)

def test_17_cnt_outside_recommended_range():
    """TEST 17: CNT outside 0.5–1.5% maximum produces validation warning."""
    mn = 0.65
    fe = 0.25
    dopants = [
        {"symbol": "Mg", "fraction": 0.03, "oxidation_state": 2},
        {"symbol": "Zn", "fraction": 0.04, "oxidation_state": 2},
        {"symbol": "Ni", "fraction": 0.03, "oxidation_state": 2}
    ]
    val_res = validate_composition(
        mn, fe, dopants, cnt_wt_pct=2.0, cnt_enabled=True
    )
    assert val_res.overall_status == "WARNING"
    assert any("CNT fraction (2.00 wt%) is outside supervisor recommended range" in warn for warn in val_res.warnings)

def test_18_f_doping_flagged_as_future():
    """TEST 18: F doping flagged as future feature."""
    mn = 0.65
    fe = 0.25
    dopants = [
        {"symbol": "Mg", "fraction": 0.03, "oxidation_state": 2},
        {"symbol": "Zn", "fraction": 0.04, "oxidation_state": 2},
        {"symbol": "Ni", "fraction": 0.03, "oxidation_state": 2}
    ]
    val_res = validate_composition(mn, fe, dopants, f_doping_enabled=True)
    assert any("FUTURE" in warn and "F-doping" in warn for warn in val_res.warnings)

def test_19_mgo_flagged_as_future():
    """TEST 19: mGO flagged as future / currently not optimized."""
    mn = 0.65
    fe = 0.25
    dopants = [
        {"symbol": "Mg", "fraction": 0.03, "oxidation_state": 2},
        {"symbol": "Zn", "fraction": 0.04, "oxidation_state": 2},
        {"symbol": "Ni", "fraction": 0.03, "oxidation_state": 2}
    ]
    val_res = validate_composition(mn, fe, dopants, mgo_enabled=True)
    assert any("FUTURE" in warn and "mGO" in warn for warn in val_res.warnings)
