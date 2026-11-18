"""
Comprehensive Independent Validation Test Suite for Stage 5 Phase 4 Milestone 4.4:
Cross-Study Hypothesis Synthesis & Experimental Verification Matrix.

Verifies:
1. End-to-end linking of Research Gap -> Scientific Hypothesis -> Materials Designer -> ML Predictor -> Lab Plan.
2. Unperformed experiment status preservation ("EXPERIMENT_STATUS": "PROPOSED_UNPERFORMED").
3. ML prediction disclaimer preservation ("ML_VALIDATION_STATUS": "IN_SILICO_PREDICTION_NOT_EXPERIMENTAL_PROOF").
4. Strict epistemic separation across all matrix components (literature facts, hypotheses, supervisor policies).
5. Control samples, variable specifications (INDEPENDENT, DEPENDENT, CONTROLLED).
6. Synthesis protocol steps and characterization battery.
7. Standardized electrochemical testing protocols.
8. Actionable falsification criteria in every matrix.
9. SD_NO3 vs SD_SO4 precursor verification matrix.
10. Mg site selectivity verification matrix.
11. High-Mn (0.80) cooperative distortion verification matrix.
12. Dynamic matrix generation for arbitrary research gaps.
13. Chemical charge balance and vacancy consistency ($Q_{net} = 0$).
14. Live FastAPI backend endpoints execution.
15. Absolute data protection invariants (1,215x41 CSV, Review #6, Review #7, lab DB, ML models).
"""

import os
import sqlite3
import pytest
import pandas as pd
from fastapi.testclient import TestClient

from copilot.verification_matrix import (
    VariableType,
    VariableSpecification,
    MatrixControlSample,
    SynthesisProtocolStep,
    CharacterizationRequirement,
    ElectrochemicalTestProtocol,
    ExperimentalVerificationMatrix,
    VerificationMatrixEngine,
    get_verification_matrix_engine,
)
from backend.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Test 1: Complete Cross-Module Linking
# ---------------------------------------------------------------------------
def test_verification_matrix_linking_gap_hypothesis_designer_ml_plan():
    engine = get_verification_matrix_engine()
    mat = engine.generate_matrix_for_hypothesis("HYP-LMFP-SYNTH-01")

    # 1. Hypothesis & Gap links
    assert mat.hypothesis_id == "HYP-LMFP-SYNTH-01"
    assert "GAP-SYNTH-01" in mat.research_gap_id
    assert len(mat.scientific_question) > 10

    # 2. Supporting literature link
    lit = mat.supporting_literature
    assert "srep26686" in lit["paper_ids"]
    assert "srep26686_SD_NO3" in lit["sample_ids"]
    assert "srep26686_SD_SO4" in lit["sample_ids"]

    # 3. Chemical validation link
    chem = mat.chemical_validation
    assert chem["is_charge_balanced"] is True
    assert chem["q_m2"] > 0

    # 4. Materials Designer link
    mat_des = mat.materials_designer_link
    assert mat_des["reference_theoretical_capacity_mAh_g"] == 170.0
    assert mat_des["molar_mass_g_mol"] > 150.0
    assert mat_des["formula_theoretical_capacity_mAh_g"] > 150.0

    # 5. Property prediction link
    prop = mat.property_prediction_link
    assert "disclaimer" in prop
    assert "surrogate" in prop["disclaimer"].lower()

    # 6. Supervisor policy link
    sup = mat.supervisor_policy_link
    assert "policy_compliant" in sup
    assert "policy_statement" in sup


# ---------------------------------------------------------------------------
# Test 2: Unperformed Status & Uncertainty Disclaimers
# ---------------------------------------------------------------------------
def test_unperformed_status_and_uncertainty_disclaimers():
    engine = get_verification_matrix_engine()
    mat = engine.generate_matrix_for_hypothesis("HYP-LMFP-MN-01")

    disclaimers = mat.status_disclaimers
    assert disclaimers["EXPERIMENT_STATUS"] == "PROPOSED_UNPERFORMED"
    assert "No physical synthesis" in disclaimers["EXPERIMENT_STATUS_EXPLANATION"]
    assert disclaimers["ML_VALIDATION_STATUS"] == "IN_SILICO_PREDICTION_NOT_EXPERIMENTAL_PROOF"
    assert "do NOT substitute" in disclaimers["ML_VALIDATION_EXPLANATION"]
    assert "SUPERVISOR_POLICY_SEPARATION" in disclaimers


# ---------------------------------------------------------------------------
# Test 3: Control Samples & Variable Specifications
# ---------------------------------------------------------------------------
def test_control_samples_and_variable_specifications():
    engine = get_verification_matrix_engine()
    mat = engine.generate_matrix_for_hypothesis("HYP-LMFP-DOP-01")

    # Verify control samples
    assert len(mat.control_samples) >= 2
    roles = [s.role for s in mat.control_samples]
    assert any("CONTROL" in r or "BASELINE" in r for r in roles)

    # Verify variables
    var_types = {v.variable_type for v in mat.variable_specifications}
    assert VariableType.INDEPENDENT in var_types
    assert VariableType.DEPENDENT in var_types
    assert VariableType.CONTROLLED in var_types


# ---------------------------------------------------------------------------
# Test 4: Synthesis Plan Steps
# ---------------------------------------------------------------------------
def test_synthesis_plan_steps():
    engine = get_verification_matrix_engine()
    mat = engine.generate_matrix_for_hypothesis("HYP-LMFP-CARB-01")

    assert len(mat.synthesis_plan) >= 3
    step_nums = [s.step_number for s in mat.synthesis_plan]
    assert step_nums == sorted(step_nums)
    for s in mat.synthesis_plan:
        assert len(s.atmosphere) > 0
        assert len(s.equipment) > 0
        assert len(s.safety_notes) > 0


# ---------------------------------------------------------------------------
# Test 5: Characterization Battery
# ---------------------------------------------------------------------------
def test_characterization_battery():
    engine = get_verification_matrix_engine()
    mat = engine.generate_matrix_for_hypothesis("HYP-LMFP-CHAR-01")

    assert len(mat.characterization_plan) >= 2
    for c in mat.characterization_plan:
        assert len(c.technique) > 0
        assert len(c.instrument) > 0
        assert len(c.acceptance_criteria) > 0


# ---------------------------------------------------------------------------
# Test 6: Electrochemical Testing Protocols
# ---------------------------------------------------------------------------
def test_electrochemical_testing_protocols():
    engine = get_verification_matrix_engine()
    mat = engine.generate_matrix_for_hypothesis("HYP-LMFP-TEMP-01")

    assert len(mat.electrochemical_plan) >= 1
    for ep in mat.electrochemical_plan:
        assert "V" in ep.voltage_window
        assert len(ep.c_rates) >= 2
        assert ep.mass_loading_min_mg_cm2 >= 1.5
        assert "LiPF6" in ep.electrolyte_spec


# ---------------------------------------------------------------------------
# Test 7: Actionable Falsification Criteria
# ---------------------------------------------------------------------------
def test_actionable_falsification_criteria_in_matrix():
    engine = get_verification_matrix_engine()
    all_mats = engine.get_canonical_verification_matrices()

    for m in all_mats:
        assert len(m.falsification_criteria) >= 1, f"Matrix {m.matrix_id} missing falsification criteria"
        for fc in m.falsification_criteria:
            assert "If " in fc or "falsified" in fc.lower()


# ---------------------------------------------------------------------------
# Test 8: SD_NO3 vs SD_SO4 Precursor Verification Matrix
# ---------------------------------------------------------------------------
def test_sd_spray_drying_verification_matrix():
    engine = get_verification_matrix_engine()
    mat = engine.generate_matrix_for_hypothesis("HYP-LMFP-SYNTH-01")

    assert "srep26686_SD_NO3" in mat.supporting_literature["sample_ids"]
    assert "srep26686_SD_SO4" in mat.supporting_literature["sample_ids"]

    # Verify control samples include both nitrate and sulfate baseline replication
    ctrl_ids = [c.sample_id for c in mat.control_samples]
    assert "CTRL_SD_SO4" in ctrl_ids
    assert "CTRL_SD_NO3" in ctrl_ids
    assert "TEST_SD_NO3_ASC" in ctrl_ids


# ---------------------------------------------------------------------------
# Test 9: Mg Site Selectivity Verification Matrix
# ---------------------------------------------------------------------------
def test_mg_site_selectivity_verification_matrix():
    engine = get_verification_matrix_engine()
    mat = engine.generate_matrix_for_hypothesis("HYP-LMFP-DOP-01")

    assert mat.hypothesis_id == "HYP-LMFP-DOP-01"
    assert "Mg" in mat.candidate_composition
    # Verify independent variable includes temperature matrix
    ind_vars = [v for v in mat.variable_specifications if v.variable_type == VariableType.INDEPENDENT]
    assert any("temperature" in v.variable_name.lower() or "calcination" in v.variable_name.lower() for v in ind_vars)


# ---------------------------------------------------------------------------
# Test 10: High-Mn Cooperative Distortion Matrix
# ---------------------------------------------------------------------------
def test_high_mn_cooperative_distortion_verification_matrix():
    engine = get_verification_matrix_engine()
    mat = engine.generate_matrix_for_hypothesis("HYP-LMFP-MN-01")

    # High temperature testing protocol
    assert any("55°C" in ep.temperature for ep in mat.electrochemical_plan)
    # Characterization targets Mn dissolution and volume contraction
    targets = [c.target_feature for c in mat.characterization_plan]
    assert any("Mn" in t or "volume" in t.lower() or "dissolution" in t.lower() for t in targets)


# ---------------------------------------------------------------------------
# Test 11: Dynamic Matrix Generation for Arbitrary Gap
# ---------------------------------------------------------------------------
def test_dynamic_matrix_generation_for_arbitrary_gap():
    engine = get_verification_matrix_engine()
    # Generate directly from Milestone 4.2 gap
    mat = engine.generate_matrix_for_gap("GAP-ELEC-01")

    assert mat.research_gap_id == "GAP-ELEC-01"
    assert "GAP-ELEC-01" in mat.matrix_id
    assert len(mat.candidate_composition) > 5
    assert mat.chemical_validation["is_charge_balanced"] is True
    assert len(mat.control_samples) >= 2


# ---------------------------------------------------------------------------
# Test 12: Chemical Charge Neutrality Across All Canonical Matrices
# ---------------------------------------------------------------------------
def test_chemical_charge_neutrality_across_matrices():
    engine = get_verification_matrix_engine()
    matrices = engine.get_canonical_verification_matrices()

    for m in matrices:
        chem = m.chemical_validation
        assert chem["is_charge_balanced"] is True, f"Matrix {m.matrix_id} is not charge-balanced"
        assert chem["phi_m2_occupancy"] >= 0.95, f"Matrix {m.matrix_id} M2 occupancy implausible"


# ---------------------------------------------------------------------------
# Test 13: Query Verification Matrices
# ---------------------------------------------------------------------------
def test_query_verification_matrices():
    engine = get_verification_matrix_engine()

    # Query by gap_id
    res_gap = engine.query_matrices(gap_id="GAP-SYNTH-01")
    assert res_gap["total_matrices"] >= 1

    # Query by dopant
    res_dop = engine.query_matrices(dopant="Mg")
    assert res_dop["total_matrices"] >= 1


# ---------------------------------------------------------------------------
# Test 14: FastAPI Backend Endpoints Live Verification
# ---------------------------------------------------------------------------
def test_backend_api_verification_matrices_endpoints():
    # 1. GET /api/copilot/verification-matrices
    resp = client.get("/api/copilot/verification-matrices")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_matrices" in data
    assert data["total_matrices"] >= 6
    assert len(data["matrices"]) >= 6

    # 2. GET /api/copilot/verification-matrices/{matrix_id}
    m_id = data["matrices"][0]["matrix_id"]
    resp_id = client.get(f"/api/copilot/verification-matrices/{m_id}")
    assert resp_id.status_code == 200
    assert resp_id.json()["matrix_id"] == m_id

    # 3. POST /api/copilot/verification-matrices/generate (by hypothesis_id)
    resp_gen = client.post(
        "/api/copilot/verification-matrices/generate",
        json={"hypothesis_id": "HYP-LMFP-SYNTH-01"},
    )
    assert resp_gen.status_code == 200
    assert resp_gen.json()["matrix_id"] == "MAT-LMFP-SYNTH-01"

    # 4. POST /api/copilot/verification-matrices/generate (by gap_id)
    resp_gap = client.post(
        "/api/copilot/verification-matrices/generate",
        json={"gap_id": "GAP-ELEC-01"},
    )
    assert resp_gap.status_code == 200
    assert "GAP-ELEC-01" in resp_gap.json()["matrix_id"]


# ---------------------------------------------------------------------------
# Test 15: Absolute Data Protection & Invariants Verification
# ---------------------------------------------------------------------------
def test_milestone_4_4_data_protection_and_invariants():
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


# ---------------------------------------------------------------------------
# Test 16: Regression Test - Undoped LiMn0.7Fe0.3PO4 Exact Q_M2 Transition-Metal Charge
# ---------------------------------------------------------------------------
def test_undoped_composition_exact_q_m2_regression():
    """
    Scientific Consistency Verification:
    For nominal undoped LiMn0.7Fe0.3PO4/C with Mn2+ and Fe2+:
    - Transition-metal cation charge Q_M2 must be exactly 2.0000 e.
    - Required Li for neutrality must be exactly 1.0000 (delta_Li = 0.0000).
    - Net unit cell charge Q_net must be 0.0000.
    - Dopants must not be artificially injected into undoped candidate compositions.
    """
    from chemistry.charge_balance import calculate_charge_balance
    from copilot.research_intelligence import get_hypothesis_generation_engine, get_verification_matrix_engine

    # 1. Deterministic chemistry engine baseline
    cb_undoped = calculate_charge_balance(mn_frac=0.70, fe_frac=0.30, dopants=[], user_li=1.0)
    assert cb_undoped.q_m2 == 2.0, f"Expected Q_M2 = 2.0000, got {cb_undoped.q_m2}"
    assert cb_undoped.required_li == 1.0, f"Expected required_li = 1.0000, got {cb_undoped.required_li}"
    assert cb_undoped.delta_li == 0.0, f"Expected delta_li = 0.0000, got {cb_undoped.delta_li}"
    assert cb_undoped.is_balanced is True, "Undoped composition should be naturally charge balanced"

    # 2. Hypothesis engine dynamic synthesis for GAP-ELEC-01
    hyp_engine = get_hypothesis_generation_engine()
    hyp = hyp_engine.generate_hypothesis_for_gap("GAP-ELEC-01")
    assert hyp.experimental_protocol.candidate_composition == "LiMn0.7Fe0.3PO4/C"
    assert hyp.chemical_validation["q_m2"] == 2.0, (
        f"Hypothesis chemical validation Q_M2 mismatch: expected 2.0, got {hyp.chemical_validation['q_m2']}"
    )
    assert hyp.chemical_validation["required_li"] == 1.0, (
        f"Expected required_li = 1.0, got {hyp.chemical_validation['required_li']}"
    )
    assert hyp.chemical_validation["delta_li_vacancies"] == 0.0, (
        f"Expected delta_li_vacancies = 0.0, got {hyp.chemical_validation['delta_li_vacancies']}"
    )
    assert hyp.chemical_validation["is_charge_balanced"] is True

    # 3. Verification matrix engine synthesis for GAP-ELEC-01
    mat_engine = get_verification_matrix_engine()
    mat = mat_engine.generate_matrix_for_gap("GAP-ELEC-01")
    assert mat.candidate_composition == "LiMn0.7Fe0.3PO4/C"
    assert mat.chemical_validation["q_m2"] == 2.0, (
        f"Matrix chemical validation Q_M2 mismatch: expected 2.0, got {mat.chemical_validation['q_m2']}"
    )
    assert mat.chemical_validation["required_li"] == 1.0
    assert mat.chemical_validation["delta_li_vacancies"] == 0.0
    assert mat.chemical_validation["is_charge_balanced"] is True
