"""
Stage 5 Phase 4 - Milestone 4.5: Integrated Research Intelligence & Discovery Workspace E2E Test Suite.
Verifies the complete 7-step user discovery workflow across Trends, Gaps, Hypotheses, Matrices, and Lab DB.
"""
import os
import sqlite3
import pytest
from fastapi.testclient import TestClient
from backend.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_discovery_workspace_e2e_full_workflow(client):
    """
    Complete end-to-end user workflow:
    1. Select an LMFP research topic (e.g. 'spray-drying' or 'high-mn').
    2. Inspect relevant literature trends from /api/copilot/trends.
    3. Identify an evidence-backed research gap from /api/copilot/gaps.
    4. Generate a scientific hypothesis from /api/copilot/hypotheses/generate.
    5. Validate the proposed composition & charge balance.
    6. Review the experimental verification matrix from /api/copilot/verification-matrices/generate.
    7. Transfer the proposed experiment to Experiment Management without falsely marking it as performed.
    """
    # -------------------------------------------------------------------------
    # STEP 1: Select LMFP Research Topic & Query Trends
    # -------------------------------------------------------------------------
    topic = "spray-drying"
    trends_res = client.get(f"/api/copilot/trends?topic={topic}")
    assert trends_res.status_code == 200, f"Trends request failed: {trends_res.status_code}"
    trends_data = trends_res.json()
    assert "dataset_overview" in trends_data
    assert trends_data["dataset_overview"]["total_literature_records"] == 1215
    assert "trend_dimensions" in trends_data
    assert "synthesis_routes" in trends_data["trend_dimensions"]

    # -------------------------------------------------------------------------
    # STEP 2: Inspect Research Gaps & Distinguish Epistemic Status
    # -------------------------------------------------------------------------
    gaps_res = client.get("/api/copilot/gaps")
    assert gaps_res.status_code == 200, f"Gaps request failed: {gaps_res.status_code}"
    gaps_data = gaps_res.json()
    assert gaps_data["gaps_count"] >= 7
    gaps_list = gaps_data["gaps"]

    # Locate GAP-SYNTH-01 (Precursor Counter-Anion spray-drying discrepancy)
    target_gap = next((g for g in gaps_list if g["gap_id"] == "GAP-SYNTH-01"), None)
    assert target_gap is not None, "GAP-SYNTH-01 not found in registered gaps"
    assert target_gap["category"] == "SYNTHESIS_AND_PROCESSING"
    assert "srep26686" in target_gap["supporting_paper_ids"]
    assert target_gap["verification_status"] == "VERIFIED_LITERATURE_GAP"
    assert len(target_gap["missing_measurements"]) >= 1
    assert len(target_gap["confounding_variables"]) >= 1

    # -------------------------------------------------------------------------
    # STEP 3: Inspect Scientific Conflicts Explorer
    # -------------------------------------------------------------------------
    conflicts_res = client.get("/api/copilot/conflicts")
    assert conflicts_res.status_code == 200, f"Conflicts request failed: {conflicts_res.status_code}"
    conflicts_data = conflicts_res.json()
    assert "conflicts" in conflicts_data
    conflicts = conflicts_data["conflicts"]
    assert len(conflicts) >= 3
    synth_conflict = next((c for c in conflicts if "spray" in c.get("title", "").lower() or "precursor" in c.get("title", "").lower() or "precursor" in c.get("topic", "").lower()), None)
    assert synth_conflict is not None
    assert synth_conflict["finding_a"] != ""
    assert synth_conflict["finding_b"] != ""
    assert synth_conflict["suggested_resolution"] != ""

    # -------------------------------------------------------------------------
    # STEP 4: Generate Scientific Hypothesis from Gap
    # -------------------------------------------------------------------------
    hyp_payload = {"gap_id": target_gap["gap_id"], "topic": target_gap["title"]}
    hyp_res = client.post("/api/copilot/hypotheses/generate", json=hyp_payload)
    assert hyp_res.status_code == 200, f"Hypothesis generation failed: {hyp_res.status_code}"
    hyp = hyp_res.json()
    assert hyp["hypothesis_id"] == "HYP-LMFP-SYNTH-01"
    assert hyp["research_gap_id"] == "GAP-SYNTH-01"
    assert len(hyp["epistemic_breakdown"]) >= 3
    assert len(hyp["falsification_criteria"]) >= 1
    assert len(hyp["alternative_explanations"]) >= 1

    # -------------------------------------------------------------------------
    # STEP 5: Validate Proposed Composition & Chemistry
    # -------------------------------------------------------------------------
    chem_val = hyp["chemical_validation"]
    assert chem_val["is_charge_balanced"] is True
    assert chem_val["is_chemically_plausible"] is True
    assert chem_val["q_m2"] == 2.0  # Undoped LiMn0.75Fe0.25PO4 strictly has Q_M2 = 2.0000
    assert chem_val["required_li"] == 1.0
    assert chem_val["delta_li_vacancies"] == 0.0

    # -------------------------------------------------------------------------
    # STEP 6: Review Experimental Verification Matrix
    # -------------------------------------------------------------------------
    mat_payload = {"hypothesis_id": hyp["hypothesis_id"], "gap_id": hyp["research_gap_id"]}
    mat_res = client.post("/api/copilot/verification-matrices/generate", json=mat_payload)
    assert mat_res.status_code == 200, f"Matrix generation failed: {mat_res.status_code}"
    matrix = mat_res.json()
    assert matrix["matrix_id"] == "MAT-LMFP-SYNTH-01"
    assert matrix["hypothesis_id"] == hyp["hypothesis_id"]
    assert matrix["research_gap_id"] == hyp["research_gap_id"]

    # Verify status disclaimers (uncertainty preservation)
    disclaimers = matrix["status_disclaimers"]
    assert disclaimers["EXPERIMENT_STATUS"] == "PROPOSED_UNPERFORMED"
    assert disclaimers["ML_VALIDATION_STATUS"] == "IN_SILICO_PREDICTION_NOT_EXPERIMENTAL_PROOF"

    # Verify control samples
    assert len(matrix["control_samples"]) >= 3
    roles = [cs["role"] for cs in matrix["control_samples"]]
    assert any("REPLICATION" in r for r in roles)
    assert any("NEGATIVE" in r for r in roles)
    assert any("TARGET" in r for r in roles)

    # Verify variable specifications
    var_types = [vs["variable_type"] for vs in matrix["variable_specifications"]]
    assert "INDEPENDENT" in var_types
    assert "DEPENDENT" in var_types
    assert "CONTROLLED" in var_types

    # Verify synthesis protocol & characterization
    assert len(matrix["synthesis_plan"]) >= 4
    assert len(matrix["characterization_plan"]) >= 2
    assert len(matrix["electrochemical_plan"]) >= 1

    # -------------------------------------------------------------------------
    # STEP 7: Transfer Proposed Experiment to Experiment Management
    # -------------------------------------------------------------------------
    # Create experiment with explicit SYNTHESIS_PLANNED status
    exp_payload = {
        "sample_id": f"VERIFY-{matrix['matrix_id']}",
        "batch_id": "DISCOVERY-TEST-01",
        "operator": "Discovery Studio Researcher",
        "generated_formula": matrix["candidate_composition"],
        "mn_ratio": 0.75,
        "fe_ratio": 0.25,
        "dopants": matrix["intended_dopants"],
        "carbon_wt_percent": 2.0,
        "synthesis_route": matrix["synthesis_plan"][0]["operation"],
        "status": "SYNTHESIS_PLANNED",
        "notes": f"Transferred from Verification Matrix {matrix['matrix_id']}. Status: PROPOSED_UNPERFORMED.",
        "synthesis_data": {
            "observations": "Proposed protocol from verification matrix",
            "calcination_temp_c": 650,
            "calcination_duration_h": 6.0,
        },
        "characterization_data": {
            "impurity_phases": "Pending physical synthesis and XRD verification",
        },
        "electrochemical_data": {
            "initial_discharge_cap": None,
            "capacity_retention_pct": None,
            "cycle_life_cycles": None,
            "notes": "UNPERFORMED EXPERIMENT: Awaiting coin-cell assembly and electrochemical testing per protocol.",
        },
    }

    exp_id = None
    try:
        create_res = client.post("/api/experiments", json=exp_payload)
        assert create_res.status_code == 200, f"Experiment transfer failed: {create_res.status_code}"
        create_data = create_res.json()
        exp_id = create_data["experiment_id"]
        assert exp_id.startswith("EXP-")

        # Fetch and verify experiment in DB
        fetch_res = client.get(f"/api/experiments/{exp_id}")
        assert fetch_res.status_code == 200
        exp_record = fetch_res.json()
        assert exp_record["experiment_id"] == exp_id
        assert exp_record["status"] == "SYNTHESIS_PLANNED"  # Strictly unperformed
        assert exp_record["electrochemical_data"]["initial_discharge_cap"] is None  # Never fabricated
        assert "PROPOSED_UNPERFORMED" in exp_record["notes"]
    finally:
        # -------------------------------------------------------------------------
        # CLEANUP: Delete the test experiment so data/lab_experiments.db remains at 0 records
        # -------------------------------------------------------------------------
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "lab_experiments.db")
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        if exp_id:
            cur.execute("DELETE FROM lab_experiments WHERE experiment_id = ?", (exp_id,))
        cur.execute("DELETE FROM lab_experiments WHERE sample_id LIKE 'VERIFY-%'")
        conn.commit()
        cur.execute("SELECT COUNT(*) FROM lab_experiments")
        count_after = cur.fetchone()[0]
        conn.close()
        assert count_after == 0, f"Cleanup failed: lab_experiments count is {count_after}"

def test_discovery_workspace_api_query_filters(client):
    """Verify topic, category, and dopant query filters on discovery endpoints."""
    # Trends with specific dopant
    dopant_trends = client.get("/api/copilot/trends?dopant=Mg")
    assert dopant_trends.status_code == 200
    assert dopant_trends.json()["dopant"] == "Mg"

    # Gaps with category filter
    gaps_cat = client.get("/api/copilot/gaps?category=COMPOSITION_AND_DOPANT_COVERAGE")
    assert gaps_cat.status_code == 200
    for g in gaps_cat.json()["gaps"]:
        assert "COMPOSITION" in g["category"]

    # Hypotheses with category filter
    hyp_cat = client.get("/api/copilot/hypotheses?category=SYNTHESIS_AND_PROCESSING")
    assert hyp_cat.status_code == 200
    for h in hyp_cat.json()["hypotheses"]:
        assert "SYNTHESIS" in h["category"]

    # Matrices with gap filter
    mat_gap = client.get("/api/copilot/verification-matrices?gap_id=GAP-SYNTH-01")
    assert mat_gap.status_code == 200
    for m in mat_gap.json()["matrices"]:
        assert "GAP-SYNTH-01" in m["research_gap_id"]
