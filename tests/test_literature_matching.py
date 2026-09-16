"""
Unit tests for V2 Literature Matching Engine (Tests 1 through 12).
Verifies exact match, near match, no match, dopant diffs, missing values,
P1 disaggregation, source traceability, and floating-point tolerance.
"""

import pytest
import os
import numpy as np
from literature.loader import load_literature_database, LiteratureSampleRecord
from literature.parser import parse_composition, ParsedComposition
from literature.matcher import (
    match_composition,
    exact_match,
    calculate_difference,
    MatchStatus,
    MatchResult
)
from literature.evidence import generate_evidence_summary, format_evidence_report

@pytest.fixture
def db_records():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base_dir, "data", "literature_reference.csv")
    return load_literature_database(csv_path)

def test_1_exact_match(db_records):
    """TEST 1: Exact match finds identical stoichiometry in database."""
    # Target: LiMn0.8Fe0.2PO4 (P1_N-LMFP exact stoichiometry)
    target = parse_composition(None, mn_ratio=0.80, fe_ratio=0.20, dopants="None/Undoped")
    
    exact_recs = exact_match(target, db_records, float_tol=1e-4)
    res = match_composition(target, db_records, float_tol=1e-4)
    
    assert len(exact_recs) >= 1
    assert res.status == MatchStatus.LITERATURE_MATCH
    assert any(r.sample_id == "P1_N-LMFP" for r in res.exact_matches)

def test_2_near_match(db_records):
    """TEST 2: Near match detects minor stoichiometry differences within tolerance."""
    # Target: Mn 0.802, Fe 0.198 (within 0.005 of Mn 0.80, Fe 0.20)
    target = parse_composition(None, mn_ratio=0.802, fe_ratio=0.198, dopants="None/Undoped")
    
    res = match_composition(target, db_records, float_tol=1e-4, near_mn_fe_tol=0.005)
    
    assert res.status == MatchStatus.NEAR_LITERATURE_MATCH
    assert len(res.near_matches) >= 1
    assert any(diff.mn_difference == pytest.approx(0.002, abs=1e-4) for diff in res.differences)

def test_3_no_match(db_records):
    """TEST 3: Composition not in database returns NO_MATCH_IN_DATABASE."""
    # Target: Mn 0.6111, Fe 0.1111 with unique dopants
    target = parse_composition(
        None, mn_ratio=0.6111, fe_ratio=0.1111,
        dopants=[{"symbol": "Zr", "fraction": 0.045, "oxidation_state": 4}]
    )
    res = match_composition(target, db_records, float_tol=1e-4, near_mn_fe_tol=0.005)
    
    assert res.status == MatchStatus.NO_MATCH_IN_DATABASE
    assert len(res.exact_matches) == 0
    assert len(res.near_matches) == 0
    assert "No sufficiently matching record was found" in res.explanation

def test_4_different_dopant_set(db_records):
    """TEST 4: Different dopant set prevents exact match and is explicitly reported."""
    # Target has dopant Mg, but literature record P1 has no dopants
    target = parse_composition(None, mn_ratio=0.80, fe_ratio=0.20, dopants=[{"symbol": "Mg", "fraction": 0.02}])
    
    exact_recs = exact_match(target, db_records)
    assert not any(r.sample_id == "P1_N-LMFP" for r in exact_recs)
    
    # Check diff against P1_N-LMFP record
    p1_rec = next(r for r in db_records if r.sample_id == "P1_N-LMFP")
    diff = calculate_difference(target, p1_rec)
    assert diff.dopant_set_status == "NO_OVERLAP"
    assert "Mg" in diff.dopant_differences
    assert diff.dopant_differences["Mg"] == 0.02

def test_5_different_dopant_concentration(db_records):
    """TEST 5: Different dopant concentration exceeds tolerance and reports exact diff."""
    # Sample with Mg=0.05 vs target with Mg=0.01 (diff = 0.04 > 0.002)
    target = parse_composition(None, mn_ratio=0.65, fe_ratio=0.25, dopants=[{"symbol": "Mg", "fraction": 0.01}])
    rec_sample = next((r for r in db_records if r.dopant_element == "Mg" and r.dopant_x_per_fu == 0.05), None)
    
    if rec_sample:
        diff = calculate_difference(target, rec_sample, near_conc_tol=0.002)
        assert diff.is_within_near_tolerance is False
        assert diff.dopant_differences["Mg"] == pytest.approx(0.04, abs=1e-4)

def test_6_different_mn_fe_ratio(db_records):
    """TEST 6: Different Mn/Fe ratio (> 0.005 diff) prevents match."""
    # Target: Mn 0.75, Fe 0.15 vs P1 (Mn 0.80, Fe 0.20)
    target = parse_composition(None, mn_ratio=0.75, fe_ratio=0.15, dopants="None/Undoped")
    p1_rec = next(r for r in db_records if r.sample_id == "P1_N-LMFP")
    
    diff = calculate_difference(target, p1_rec, near_mn_fe_tol=0.005)
    assert diff.mn_difference == pytest.approx(0.05, abs=1e-4)
    assert diff.is_within_near_tolerance is False

def test_7_missing_literature_performance_values(db_records):
    """TEST 7: Missing literature performance values are preserved as N/A."""
    p1_c = next(r for r in db_records if r.sample_id == "P1_C-LMFP")
    ev = generate_evidence_summary(p1_c)
    
    # P1_C-LMFP has no reported 1C capacity or ICE in paper
    assert ev["Discharge_Capacity_1C_mAh_g"] == "N/A"
    assert ev["Initial_Coulombic_Efficiency_percent"] == "N/A"
    # But reports 0.1C capacity 126 mAh/g
    assert "126" in ev["Discharge_Capacity_0_1C_mAh_g"]

def test_8_multiple_samples_from_same_paper(db_records):
    """TEST 8: Multiple sample records from Paper P1 exist in database."""
    p1_samples = [r for r in db_records if r.paper_id == "P1"]
    assert len(p1_samples) == 4
    sample_ids = {r.sample_id for r in p1_samples}
    assert sample_ids == {"P1_N-LMFP", "P1_C-LMFP", "P1_O-LMFP", "P1_LMP-C"}

def test_9_p1_sample_separation(db_records):
    """TEST 9: P1 sample variants retain distinct, unmerged experimental performance."""
    p1_n = next(r for r in db_records if r.sample_id == "P1_N-LMFP")
    p1_o = next(r for r in db_records if r.sample_id == "P1_O-LMFP")
    
    # N-LMFP: 136 mAh/g 0.1C, 98.9% retention
    assert p1_n.discharge_capacity_0_1c_mah_g == 136.0
    assert p1_n.capacity_retention_percent == 98.9
    
    # O-LMFP: 120 mAh/g 0.1C, 55.1% retention
    assert p1_o.discharge_capacity_0_1c_mah_g == 120.0
    assert p1_o.capacity_retention_percent == 55.1
    
    # They are distinct records and NOT merged
    assert p1_n.discharge_capacity_0_1c_mah_g != p1_o.discharge_capacity_0_1c_mah_g

def test_10_no_novelty_claim(db_records):
    """TEST 10: System never uses 'NOVEL' status for unindexed compositions."""
    target = parse_composition(None, mn_ratio=0.61, fe_ratio=0.11, dopants="None/Undoped")
    res = match_composition(target, db_records)
    
    assert res.status != "NOVEL"
    assert res.status == MatchStatus.NO_MATCH_IN_DATABASE
    assert "No sufficiently matching record was found" in res.explanation

def test_11_source_traceability(db_records):
    """TEST 11: Reported experimental values and calculated metrics remain strictly separated."""
    p1_n = next(r for r in db_records if r.sample_id == "P1_N-LMFP")
    ev = generate_evidence_summary(p1_n)
    
    # Reported capacity is 136 mAh/g
    assert "136" in ev["Discharge_Capacity_0_1C_mAh_g"]
    # Calculated capacity metric is distinct (~170.7 mAh/g for Li1.0 Mn0.8 Fe0.2 PO4)
    assert "170.7" in ev["Calculated_Theoretical_Capacity_Metric"] or "170.68" in ev["Calculated_Theoretical_Capacity_Metric"]
    assert ev["Discharge_Capacity_0_1C_mAh_g"] != ev["Calculated_Theoretical_Capacity_Metric"]


def test_12_floating_point_tolerance(db_records):
    """TEST 12: Exact match respects floating point representation tolerance (1e-4)."""
    # Target: Mn 0.8000000001, Fe 0.1999999999
    target = parse_composition(None, mn_ratio=0.8000000001, fe_ratio=0.1999999999, dopants="None/Undoped")
    
    exact_recs = exact_match(target, db_records, float_tol=1e-4)
    assert len(exact_recs) >= 1
    assert any(r.sample_id == "P1_N-LMFP" for r in exact_recs)
