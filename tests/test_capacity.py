"""
Tests for Theoretical & Practical Capacity Metrics.
"""

import pytest
from chemistry.capacity import calculate_capacity_metrics, REFERENCE_THEORETICAL_CAPACITY

def test_project_reference_theoretical_capacity_remains_170():
    """Unit test confirming that the displayed project reference theoretical capacity remains 170 mAh/g."""
    cap_res = calculate_capacity_metrics(li_fraction=1.0, molar_mass=157.75)
    
    # Requirement: Displayed project reference theoretical capacity must remain 170 mAh/g
    assert cap_res.reference_theoretical_capacity == 170.0
    assert REFERENCE_THEORETICAL_CAPACITY == 170.0

def test_capacity_metrics_differentiation():
    """Test that Formula-Based Calculated Capacity Metric is distinct from the 170 mAh/g reference."""
    # Pristine LiFePO4: Li1.0 Fe1.0 P1.0 O4.0, Molar mass ~ 157.75 g/mol
    cap_res = calculate_capacity_metrics(li_fraction=1.0, molar_mass=157.75)
    
    assert cap_res.reference_theoretical_capacity == 170.0
    assert cap_res.formula_calculated_capacity_metric == pytest.approx(169.89, abs=0.5)
    assert cap_res.practical_target_min == 150.0
    assert cap_res.practical_target_max == 160.0
    assert cap_res.voltage_window_min == 2.5
    assert cap_res.voltage_window_max == 4.2
    assert "distinct reference metrics" in cap_res.disclaimer
    assert len(cap_res.c_rate_panel) == 5

def test_default_reference_composition_capacity():
    """Verify deterministic calculated capacity for default reference composition (Li0.93, Molar mass 157.4725 g/mol) is 158.28 mAh/g (158.3 mAh/g)."""
    # Default composition: Li0.93[Mn0.65 Fe0.26 Mg0.02 Zn0.02 Nb0.01 Cu0.02 Zr0.02]PO4
    # li_fraction = 0.93, molar_mass = 157.4725 g/mol
    cap_res = calculate_capacity_metrics(li_fraction=0.93, molar_mass=157.4725)
    
    assert cap_res.reference_theoretical_capacity == 170.0
    assert cap_res.formula_calculated_capacity_metric == 158.28
    assert round(cap_res.formula_calculated_capacity_metric, 1) == 158.3

