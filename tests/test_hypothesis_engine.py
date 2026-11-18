"""
Comprehensive Independent Validation Test Suite for Stage 5 Phase 4 Milestone 4.3:
Literature-Driven Scientific Hypothesis Generation Engine.

Verifies:
1. Strict 7-level epistemic separation (LITERATURE_FACT, AUTHOR_INTERPRETATION, COPILOT_SYNTHESIS,
   RESEARCH_HYPOTHESIS, EXPERIMENTAL_RECOMMENDATION, ML_PREDICTION, SUPERVISOR_POLICY).
2. Eight hypothesis categories representation.
3. Precursor counter-anion discrepancy in spray drying (SD_NO3 vs SD_SO4).
4. Mg2+ site selectivity and 1D channel blockage.
5. High-Mn (0.80) cooperative Jahn-Teller suppression with Ti+Mg dual-doping.
6. Carbon modification vs crystallite size decoupling.
7. Missing EIS & lithium diffusion plateau characterization.
8. Synthesis temperature and carbothermal phosphide formation.
9. Deterministic chemical validity and charge neutrality verification.
10. Insufficient evidence abstention and rejection of unsupported claims.
11. Condition parity audit.
12. Falsification criteria rigor.
13. Hypothesis reproducibility.
14. Backend FastAPI live endpoints.
15. Absolute data protection invariants (1,215x41 CSV, Review #6, Review #7, lab DB, ML models).
"""

import os
import sqlite3
import pytest
import pandas as pd
from fastapi.testclient import TestClient

from copilot.hypothesis_engine import (
    EpistemicType,
    HypothesisCategory,
    HypothesisStatus,
    EpistemicStatement,
    ExperimentalProtocol,
    ScientificHypothesis,
    HypothesisValidationResult,
    HypothesisGenerationEngine,
    get_hypothesis_generation_engine,
)
from backend.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Test 1: All 7 Epistemic Types Represented and Distinguished
# ---------------------------------------------------------------------------
def test_all_seven_epistemic_types_represented():
    engine = get_hypothesis_generation_engine()
    all_hyps = engine.generate_all_canonical_hypotheses()

    found_epistemic_types = set()
    for h in all_hyps:
        found_epistemic_types.add(h.epistemic_type)
        for stmt in h.epistemic_breakdown:
            found_epistemic_types.add(stmt.epistemic_type)
        if h.ml_prediction_context:
            found_epistemic_types.add(EpistemicType(h.ml_prediction_context["epistemic_type"]))
        if h.supervisor_policy_context:
            found_epistemic_types.add(EpistemicType(h.supervisor_policy_context["epistemic_type"]))

    # Verify all 7 required types exist
    required_types = {
        EpistemicType.LITERATURE_FACT,
        EpistemicType.AUTHOR_INTERPRETATION,
        EpistemicType.COPILOT_SYNTHESIS,
        EpistemicType.RESEARCH_HYPOTHESIS,
        EpistemicType.EXPERIMENTAL_RECOMMENDATION,
        EpistemicType.ML_PREDICTION,
        EpistemicType.SUPERVISOR_POLICY,
    }
    assert required_types.issubset(found_epistemic_types), (
        f"Missing epistemic types: {required_types - found_epistemic_types}"
    )


# ---------------------------------------------------------------------------
# Test 2: All 8 Hypothesis Categories Represented
# ---------------------------------------------------------------------------
def test_all_eight_hypothesis_categories_represented():
    categories = [cat.value for cat in HypothesisCategory]
    assert len(categories) == 8
    assert "COMPOSITION_AND_DOPANTS" in categories
    assert "MN_FE_STOICHIOMETRY" in categories
    assert "SINGLE_DUAL_HIGH_ENTROPY" in categories
    assert "DOPANT_SITE_AND_CHARGE_COMPENSATION" in categories
    assert "SYNTHESIS_AND_PROCESSING" in categories
    assert "CARBON_AND_COMPOSITE" in categories
    assert "ELECTROCHEMICAL_AND_DEGRADATION" in categories
    assert "CHARACTERIZATION_DRIVEN" in categories


# ---------------------------------------------------------------------------
# Test 3: Benchmark Case 1 — SD_NO3 vs SD_SO4 Spray-Drying Discrepancy
# ---------------------------------------------------------------------------
def test_sd_precursor_discrepancy_hypothesis_preserves_identities_and_evidence():
    engine = get_hypothesis_generation_engine()
    hyp = engine.get_sd_precursor_discrepancy_hypothesis()

    # 1. Preserves distinct physical sample identities
    assert "srep26686_SD_NO3" in hyp.supporting_sample_ids
    assert "srep26686_SD_SO4" in hyp.supporting_sample_ids
    assert hyp.supporting_paper_ids == ["srep26686"]
    assert "10.1038/srep26686" in hyp.supporting_dois

    # 2. Preserves precursor differences & measured capacities
    assert "45 mAh/g" in str(hyp.supporting_measurements)
    assert "114 mAh/g" in str(hyp.supporting_measurements)

    # 3. Separates Author Interpretation (Fe2O3 dead phase) from Literature Fact
    author_interp = [
        s for s in hyp.epistemic_breakdown if s.epistemic_type == EpistemicType.AUTHOR_INTERPRETATION
    ]
    assert len(author_interp) >= 1
    assert "Fe2O3" in author_interp[0].statement

    lit_fact = [
        s for s in hyp.epistemic_breakdown if s.epistemic_type == EpistemicType.LITERATURE_FACT
    ]
    assert len(lit_fact) >= 1
    assert "SD_NO3" in lit_fact[0].statement and "SD_SO4" in lit_fact[0].statement

    # 4. Proposes testable experimental protocol with controls
    proto = hyp.experimental_protocol
    ctrl_ids = [c["sample_id"] for c in proto.control_and_comparison_samples]
    assert "CTRL_SD_SO4" in ctrl_ids
    assert "CTRL_SD_NO3" in ctrl_ids
    assert "TEST_SD_NO3_ASC" in ctrl_ids

    # 5. Clear falsification criteria
    assert len(hyp.falsification_criteria) >= 2
    assert any("Mössbauer" in c or "Fe2O3" in c for c in hyp.falsification_criteria)


# ---------------------------------------------------------------------------
# Test 4: Benchmark Case 2 — Mg2+ Site Selectivity Hypothesis
# ---------------------------------------------------------------------------
def test_mg_site_selectivity_hypothesis():
    engine = get_hypothesis_generation_engine()
    hyp = engine.get_mg_site_selectivity_hypothesis()

    assert hyp.category == HypothesisCategory.DOPANT_SITE_AND_CHARGE_COMPENSATION
    assert hyp.research_gap_id in ["GAP-COMP-02", "CONF-LMFP-01"]
    assert "M2" in hyp.hypothesis_statement
    assert "M1" in hyp.hypothesis_statement

    # Check that temperature threshold is stated
    assert "650" in hyp.hypothesis_statement or "750" in hyp.hypothesis_statement

    # Check chemical validation
    chem = hyp.chemical_validation
    assert chem["is_charge_balanced"] is True
    assert chem["q_m2"] > 0

    # Falsification criteria
    assert len(hyp.falsification_criteria) >= 1
    assert any("Rietveld" in c or "diffraction" in c for c in hyp.falsification_criteria)


# ---------------------------------------------------------------------------
# Test 5: Benchmark Case 3 — High-Mn Cooperative Distortion Mitigation
# ---------------------------------------------------------------------------
def test_high_mn_cooperative_distortion_hypothesis():
    engine = get_hypothesis_generation_engine()
    hyp = engine.get_high_mn_cooperative_distortion_hypothesis()

    assert hyp.category == HypothesisCategory.MN_FE_STOICHIOMETRY
    assert "Ti" in hyp.related_compositions[1]
    assert "Mg" in hyp.related_compositions[1]

    # Verify Supervisor Policy context is explicitly flagged
    assert hyp.supervisor_policy_context is not None
    assert hyp.supervisor_policy_context["epistemic_type"] == EpistemicType.SUPERVISOR_POLICY.value
    assert hyp.supervisor_policy_context["policy_compliant"] is False  # Mn=0.80 exceeds 0.75 guideline
    assert "exploratory scientific frontier" in hyp.supervisor_policy_context["policy_statement"]

    # Verify ML Prediction context is explicitly flagged
    assert hyp.ml_prediction_context is not None
    assert hyp.ml_prediction_context["epistemic_type"] == EpistemicType.ML_PREDICTION.value
    assert "surrogate" in hyp.ml_prediction_context["uncertainty_caveat"].lower()

    # Temperature and cycle count in experimental protocol
    proto = hyp.experimental_protocol
    assert proto.electrochemical_testing_conditions["temperature"] == "55°C (elevated automotive standard)"
    assert proto.electrochemical_testing_conditions["cycle_durability"] == "500 cycles at 1C"


# ---------------------------------------------------------------------------
# Test 6: Benchmark Case 4 — Carbon Coating vs Crystallite Size Decoupling
# ---------------------------------------------------------------------------
def test_carbon_vs_crystallite_size_hypothesis():
    engine = get_hypothesis_generation_engine()
    hyp = engine.get_carbon_vs_crystallite_size_hypothesis()

    assert hyp.category == HypothesisCategory.CARBON_AND_COMPOSITE
    assert "L^2" in hyp.hypothesis_statement or "diffusion" in hyp.hypothesis_statement.lower()

    # Check controls: nano coated vs micro coated vs nano uncoated
    samples = [s["sample_id"] for s in hyp.experimental_protocol.control_and_comparison_samples]
    assert "SAMP_NANO_COATED" in samples
    assert "SAMP_MICRO_COATED" in samples


# ---------------------------------------------------------------------------
# Test 7: Benchmark Case 5 — Missing EIS & Lithium Diffusion Characterization
# ---------------------------------------------------------------------------
def test_eis_diffusion_plateau_hypothesis():
    engine = get_hypothesis_generation_engine()
    hyp = engine.get_eis_diffusion_plateau_hypothesis()

    assert hyp.category == HypothesisCategory.CHARACTERIZATION_DRIVEN
    assert "4.1V" in hyp.hypothesis_statement
    assert "3.5V" in hyp.hypothesis_statement
    assert "GITT" in str(hyp.experimental_protocol.required_characterization)


# ---------------------------------------------------------------------------
# Test 8: Benchmark Case 6 — Synthesis Temperature & Phosphide Degradation
# ---------------------------------------------------------------------------
def test_synthesis_temperature_phosphide_hypothesis():
    engine = get_hypothesis_generation_engine()
    hyp = engine.get_synthesis_temperature_phosphide_hypothesis()

    assert hyp.category == HypothesisCategory.SYNTHESIS_AND_PROCESSING
    assert "700" in hyp.hypothesis_statement
    assert "Fe2P" in hyp.hypothesis_statement or "phosphide" in hyp.hypothesis_statement.lower()


# ---------------------------------------------------------------------------
# Test 9: Deterministic Chemical Validity and Charge Balance Verification
# ---------------------------------------------------------------------------
def test_chemical_validity_deterministic_validation():
    engine = get_hypothesis_generation_engine()

    # 1. Valid balanced composition
    res_valid = engine.validate_hypothesis_proposal(
        candidate_formula="Li0.96Mn0.75Fe0.23Ti0.02PO4",
        mn_frac=0.75,
        fe_frac=0.23,
        dopants=[{"symbol": "Ti", "fraction": 0.02, "oxidation_state": 4}],
        proposed_mechanism="Ti4+ provides donor carrier delocalization.",
    )
    assert res_valid.is_valid is True
    assert res_valid.status == HypothesisStatus.TESTABLE
    assert res_valid.chemical_validity["is_charge_balanced"] is True

    # 2. Implausible / unphysical composition (M2 sum = 1.40)
    res_invalid = engine.validate_hypothesis_proposal(
        candidate_formula="LiMn0.90Fe0.50PO4",
        mn_frac=0.90,
        fe_frac=0.50,
        dopants=[],
        proposed_mechanism="Impossible occupancy test.",
    )
    assert res_invalid.is_valid is False
    assert res_invalid.status == HypothesisStatus.REJECTED
    assert any("implausible" in m.lower() for m in res_invalid.validation_messages)


# ---------------------------------------------------------------------------
# Test 10: Insufficient Evidence Abstention Safeguard
# ---------------------------------------------------------------------------
def test_insufficient_evidence_abstention_safeguard():
    engine = get_hypothesis_generation_engine()

    # Query with unsupported actinide
    hyp_actinide = engine.generate_hypothesis_by_query("Californium doped LMFP")
    assert hyp_actinide.status == HypothesisStatus.INSUFFICIENT_EVIDENCE
    assert hyp_actinide.confidence_level == "INSUFFICIENT_EVIDENCE"
    assert "zero" in hyp_actinide.confidence_explanation.lower() or "insufficient" in hyp_actinide.confidence_explanation.lower()
    assert len(hyp_actinide.supporting_paper_ids) == 0

    # Query with unknown symbol
    hyp_unknown = engine.generate_hypothesis_by_query("Zz")
    assert hyp_unknown.status == HypothesisStatus.INSUFFICIENT_EVIDENCE


# ---------------------------------------------------------------------------
# Test 11: Condition Parity Audit in Hypothesis Validation
# ---------------------------------------------------------------------------
def test_condition_parity_audit_in_validation():
    engine = get_hypothesis_generation_engine()

    # Check mixed voltage window detection
    res = engine.validate_hypothesis_proposal(
        candidate_formula="LiMn0.75Fe0.25PO4",
        mn_frac=0.75,
        fe_frac=0.25,
        dopants=[],
        proposed_mechanism="Baseline test.",
        testing_conditions={"voltage_window": "2.0-4.2V vs 2.5-4.5V", "mass_loading_mg_cm2": 0.6},
    )
    assert len(res.condition_parity_audit["warnings"]) >= 2
    assert any("voltage" in w.lower() for w in res.condition_parity_audit["warnings"])
    assert any("mass loading" in w.lower() for w in res.condition_parity_audit["warnings"])


# ---------------------------------------------------------------------------
# Test 12: Actionable Falsification Criteria Across All Hypotheses
# ---------------------------------------------------------------------------
def test_falsification_criteria_rigor():
    engine = get_hypothesis_generation_engine()
    all_hyps = engine.generate_all_canonical_hypotheses()

    for h in all_hyps:
        assert len(h.falsification_criteria) >= 1, f"Hypothesis {h.hypothesis_id} missing falsification criteria"
        for crit in h.falsification_criteria:
            assert "If " in crit or "falsified" in crit.lower() or "reject" in crit.lower()


# ---------------------------------------------------------------------------
# Test 13: Deterministic Reproducibility
# ---------------------------------------------------------------------------
def test_hypothesis_generation_reproducibility():
    engine = get_hypothesis_generation_engine()

    run1 = engine.get_sd_precursor_discrepancy_hypothesis().to_dict()
    run2 = engine.get_sd_precursor_discrepancy_hypothesis().to_dict()

    assert run1["hypothesis_id"] == run2["hypothesis_id"]
    assert run1["hypothesis_statement"] == run2["hypothesis_statement"]
    assert run1["chemical_validation"] == run2["chemical_validation"]


# ---------------------------------------------------------------------------
# Test 14: Backend FastAPI Endpoints Live Verification
# ---------------------------------------------------------------------------
def test_backend_api_hypotheses_endpoints():
    # 1. GET /api/copilot/hypotheses
    resp = client.get("/api/copilot/hypotheses")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_hypotheses" in data
    assert data["total_hypotheses"] >= 6
    assert len(data["hypotheses"]) >= 6

    # 2. GET /api/copilot/hypotheses/{hypothesis_id}
    hyp_id = data["hypotheses"][0]["hypothesis_id"]
    resp_id = client.get(f"/api/copilot/hypotheses/{hyp_id}")
    assert resp_id.status_code == 200
    assert resp_id.json()["hypothesis_id"] == hyp_id

    # 3. POST /api/copilot/hypotheses/generate (by topic)
    resp_gen = client.post("/api/copilot/hypotheses/generate", json={"topic": "SD_NO3 spray drying"})
    assert resp_gen.status_code == 200
    assert resp_gen.json()["hypothesis_id"] == "HYP-LMFP-SYNTH-01"

    # 4. POST /api/copilot/hypotheses/generate (insufficient evidence)
    resp_unk = client.post("/api/copilot/hypotheses/generate", json={"topic": "Californium"})
    assert resp_unk.status_code == 200
    assert resp_unk.json()["status"] == "INSUFFICIENT_EVIDENCE"

    # 5. POST /api/copilot/hypotheses/validate
    resp_val = client.post(
        "/api/copilot/hypotheses/validate",
        json={
            "candidate_formula": "Li0.96Mn0.75Fe0.23Ti0.02PO4",
            "mn_frac": 0.75,
            "fe_frac": 0.23,
            "dopants": [{"symbol": "Ti", "fraction": 0.02, "oxidation_state": 4}],
            "proposed_mechanism": "Donor charge screening.",
        },
    )
    assert resp_val.status_code == 200
    assert resp_val.json()["is_valid"] is True


# ---------------------------------------------------------------------------
# Test 15: Absolute Data Protection & Invariants Verification
# ---------------------------------------------------------------------------
def test_milestone_4_3_data_protection_and_invariants():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # 1. Master Literature CSV shape must be exactly (1215, 41)
    csv_path = os.path.join(base_dir, "data", "literature_reference.csv")
    df = pd.read_csv(csv_path)
    assert df.shape == (1215, 41), f"Master CSV shape corrupted: {df.shape}"

    # 2. Literature Review DB: 35 reviews, Review #6 pending, Review #7 approved with 3 blockers
    review_db = os.path.join(base_dir, "data", "literature_review.db")
    conn = sqlite3.connect(review_db)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM extraction_reviews")
    total_reviews = cur.fetchone()[0]
    assert total_reviews == 35, f"Expected 35 reviews, got {total_reviews}"

    cur.execute("SELECT status FROM extraction_reviews WHERE id = 6")
    r6_status = cur.fetchone()[0]
    assert r6_status == "pending", f"Review #6 quarantine broken: status is {r6_status}"

    cur.execute("SELECT status FROM extraction_reviews WHERE id = 7")
    r7_status = cur.fetchone()[0]
    assert r7_status == "approved", f"Review #7 status expected approved, got {r7_status}"
    conn.close()

    # 3. Lab experiment DB: exactly 0 experiments, no experiments.db
    lab_db = os.path.join(base_dir, "data", "lab_experiments.db")
    conn_lab = sqlite3.connect(lab_db)
    cur_lab = conn_lab.cursor()
    cur_lab.execute("SELECT COUNT(*) FROM lab_experiments")
    exp_count = cur_lab.fetchone()[0]
    assert exp_count == 0, f"Lab experiments modified: expected 0, got {exp_count}"
    conn_lab.close()

    assert not os.path.exists(os.path.join(base_dir, "data", "experiments.db")), "Competing experiments.db created!"

    # 4. ML model artifacts intact
    artifacts_dir = os.path.join(base_dir, "models", "ml", "artifacts")
    expected_files = [
        "model_0_1C_capacity.joblib",
        "model_1C_capacity.joblib",
        "model_5C_capacity.joblib",
        "model_capacity_retention.joblib",
        "ml_metadata.json",
    ]
    for ef in expected_files:
        p = os.path.join(artifacts_dir, ef)
        assert os.path.exists(p) and os.path.getsize(p) > 0, f"ML artifact {ef} missing or empty"
