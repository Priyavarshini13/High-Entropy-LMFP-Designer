"""
Regression tests for Product Readiness Remediation — Phase 1.
Covers:
- Priority 1: Prevent fabricated experimental measurements in /api/experiments/compare.
- Priority 2: Property Prediction cross-validation evaluation contract and metrics.
- Priority 3: Dynamic Copilot literature index refresh & Review #6 quarantine integrity.
- Priority 4: Manual experiment creation with custom dopants, undoped composition, and stoichiometry validation.
"""

import os
import sqlite3
import pytest
from fastapi.testclient import TestClient

from backend.main import app, CSV_PATH
from copilot.index import ScientificPassageIndex, reload_passage_index, get_passage_index
from copilot.engine import reload_copilot_index, get_research_copilot
from literature.review_store import DB_PATH as REVIEW_DB_PATH

client = TestClient(app)
LAB_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "lab_experiments.db")


def cleanup_lab_db():
    if os.path.exists(LAB_DB_PATH):
        with sqlite3.connect(LAB_DB_PATH) as conn:
            conn.execute("DELETE FROM lab_experiments")
            conn.commit()


# ---------------------------------------------------------------------------
# Priority 1: Prevent fabricated experimental measurements
# ---------------------------------------------------------------------------
def test_priority1_compare_unperformed_experiment_returns_null_measurements():
    """Verify that an unperformed planned experiment returns null measurements and residuals without fabrication."""
    cleanup_lab_db()
    try:
        # Create a planned experiment with no measurements
        payload = {
            "sample_id": "REMED-P1-PLANNED-01",
            "operator": "Dr. Verification",
            "batch_id": "BATCH-P1",
            "synthesis_route": "sol-gel",
            "mn_frac": 0.70,
            "fe_frac": 0.30,
            "dopants": [],
            "carbon_wt_pct": 2.0,
            "status": "SYNTHESIS_PLANNED",
            "synthesis_data": {
                "calcination_temp_c": 650,
                "calcination_duration_h": 6.0,
                "observations": "Unperformed synthesis proposal",
            },
            "electrochemical_data": None,
        }
        res_create = client.post("/api/experiments", json=payload)
        assert res_create.status_code == 200, res_create.text
        exp_id = res_create.json()["experiment_id"]

        # Call compare endpoint
        res_comp = client.post(f"/api/experiments/compare?experiment_id={exp_id}")
        assert res_comp.status_code == 200, res_comp.text
        data = res_comp.json()

        # Scientific integrity assertions
        actual = data["actual_experiment"]
        residuals = data["residuals"]

        assert actual["is_performed"] is False, "Unperformed experiment must have is_performed=False"
        assert actual["status"] == "SYNTHESIS_PLANNED"
        assert actual["measured_discharge_cap"] is None, "Measured capacity must be None/null, never fabricated 152.4"
        assert actual["measured_retention"] is None, "Measured retention must be None/null, never fabricated 93.8"
        assert residuals["capacity_vs_lit_delta"] is None, "Residual capacity delta must be None/null when unperformed"
        assert residuals["retention_vs_lit_delta"] is None, "Residual retention delta must be None/null when unperformed"

        # Verify in silico ML predictions are present in target_design
        assert "target_design" in data
        assert data["target_design"]["theoretical_capacity"] > 160.0

    finally:
        cleanup_lab_db()


def test_priority1_compare_performed_experiment_returns_real_measurements():
    """Verify that a completed experiment with actual measurements returns real numbers and non-null residuals."""
    cleanup_lab_db()
    try:
        payload = {
            "sample_id": "REMED-P1-TESTED-02",
            "operator": "Dr. BatteryTester",
            "batch_id": "BATCH-P1-REAL",
            "synthesis_route": "sol-gel",
            "mn_frac": 0.70,
            "fe_frac": 0.30,
            "dopants": [],
            "carbon_wt_pct": 2.0,
            "status": "ELECTROCHEMICAL_TESTED",
            "electrochemical_data": {
                "initial_discharge_cap": 158.2,
                "capacity_retention_pct": 94.5,
                "cycle_life_cycles": 200,
            },
            "characterization_data": {
                "impurity_phases": "Phase pure olivine Pnma",
            },
        }
        res_create = client.post("/api/experiments", json=payload)
        assert res_create.status_code == 200, res_create.text
        exp_id = res_create.json()["experiment_id"]

        res_comp = client.post(f"/api/experiments/compare?experiment_id={exp_id}")
        assert res_comp.status_code == 200, res_comp.text
        data = res_comp.json()

        actual = data["actual_experiment"]
        residuals = data["residuals"]

        assert actual["is_performed"] is True
        assert actual["measured_discharge_cap"] == 158.2
        assert actual["measured_retention"] == 94.5
        assert residuals["capacity_vs_lit_delta"] is not None
        assert residuals["retention_vs_lit_delta"] is not None
    finally:
        cleanup_lab_db()


# ---------------------------------------------------------------------------
# Priority 2: Property Prediction Evaluation Contract
# ---------------------------------------------------------------------------
def test_priority2_prediction_evaluation_contract(monkeypatch):
    """Verify that /api/predictions/evaluation returns the expected schema with targets dictionary."""
    mock_targets = {
        "0_1C_capacity": {
            "label": "0.1C Discharge Capacity",
            "unit": "mAh/g",
            "status": "evaluated",
            "sample_count": 182,
            "paper_count": 54,
            "model_metrics": {"mae": 5.12, "rmse": 6.84, "r2": 0.412},
            "baseline_metrics": {"mae": 5.89, "rmse": 7.45, "r2": 0.298},
            "comparison": {"mae_delta": -0.77, "model_beats_baseline_mae": True},
        },
        "1C_capacity": {
            "label": "1C Discharge Capacity",
            "unit": "mAh/g",
            "status": "evaluated",
            "sample_count": 160,
            "paper_count": 48,
            "model_metrics": {"mae": 6.30, "rmse": 8.10, "r2": 0.380},
            "baseline_metrics": {"mae": 6.80, "rmse": 8.70, "r2": 0.290},
            "comparison": {"mae_delta": -0.50, "model_beats_baseline_mae": True},
        },
        "5C_capacity": {
            "label": "5C Discharge Capacity",
            "unit": "mAh/g",
            "status": "evaluated",
            "sample_count": 130,
            "paper_count": 40,
            "model_metrics": {"mae": 7.20, "rmse": 9.40, "r2": 0.320},
            "baseline_metrics": {"mae": 8.10, "rmse": 10.20, "r2": 0.180},
            "comparison": {"mae_delta": -0.90, "model_beats_baseline_mae": True},
        },
        "capacity_retention": {
            "label": "Capacity Retention",
            "unit": "%",
            "status": "evaluated",
            "sample_count": 192,
            "paper_count": 58,
            "model_metrics": {"mae": 3.80, "rmse": 5.10, "r2": 0.450},
            "baseline_metrics": {"mae": 4.50, "rmse": 5.90, "r2": 0.310},
            "comparison": {"mae_delta": -0.70, "model_beats_baseline_mae": True},
        },
    }
    monkeypatch.setattr("backend.main.evaluate_models_against_baseline", lambda *args, **kwargs: mock_targets)

    res = client.get("/api/predictions/evaluation")
    assert res.status_code == 200, res.text
    data = res.json()

    assert data.get("status") == "success"
    assert data.get("cv_strategy") == "GroupKFold (5-fold by publication)"
    assert data.get("models_evaluated") == 4
    assert "models" in data
    assert "targets" in data
    assert isinstance(data["targets"], dict)
    assert len(data["targets"]) == 4

    targets = data["targets"]
    for key in ["0_1C_capacity", "1C_capacity", "5C_capacity", "capacity_retention"]:
        assert key in targets, f"Target '{key}' missing from evaluation response"
        item = targets[key]
        assert "label" in item
        assert "sample_count" in item
        assert "paper_count" in item
        assert "status" in item
        if item["status"] == "evaluated":
            assert "model_metrics" in item
            assert "baseline_metrics" in item
            assert "mae" in item["model_metrics"]
            assert "r2" in item["model_metrics"]
            assert "mae" in item["baseline_metrics"]


# ---------------------------------------------------------------------------
# Priority 3: Dynamic Copilot literature index refresh & Review #6 quarantine
# ---------------------------------------------------------------------------
def test_priority3_review6_quarantine_in_index():
    """Verify that Review #6 is strictly quarantined and absent from the retrieval passage index."""
    idx = get_passage_index()

    # Verify no passage is rev_6
    assert "rev_6" not in idx.passage_map, "Review #6 must NOT be indexed in passage_map"

    # Verify no passage mentions the quarantined title
    for p in idx.passages:
        if p.source_type == "literature_review":
            assert "design, progress, and challenges" not in (p.title or "").lower(), (
                f"Quarantined review paper found in index: {p.title}"
            )


def test_priority3_provenance_and_verification_status():
    """Verify that approved reviews are marked APPROVED_REVIEW_QUEUE and pending are STAGED_REVIEW_QUEUE."""
    idx = get_passage_index()

    review_passages = [p for p in idx.passages if p.source_type == "literature_review"]
    assert len(review_passages) > 0, "Expected literature review passages in index"

    for p in review_passages:
        prov = p.provenance_type
        assert prov in ("APPROVED_REVIEW_QUEUE", "STAGED_REVIEW_QUEUE"), (
            f"Unexpected provenance_type: {prov}"
        )
        if prov == "APPROVED_REVIEW_QUEUE":
            assert p.structured_data.get("is_verified") is True
            assert p.is_unresolved is False
        elif prov == "STAGED_REVIEW_QUEUE":
            assert p.structured_data.get("is_verified") is False
            assert p.is_unresolved is True


def test_priority3_dynamic_index_refresh():
    """Verify that reload_copilot_index() updates the active index in memory without restarting backend."""
    # Insert a temporary mock review
    temp_rev_id = 99999
    with sqlite3.connect(REVIEW_DB_PATH) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO extraction_reviews
            (id, source_pdf, page_number, reference, composition, evidence_quote, status, created_at, extracted_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), ?)
            """,
            (
                temp_rev_id,
                "temp_dynamic_test_paper_2026.pdf",
                3,
                "Dynamic Test Reference (2026)",
                "LiMn0.72Fe0.28PO4",
                "Dynamic index test quote showing fast kinetics.",
                "approved",
                '{"discharge_capacity_0_1c": 161.5, "synthesis_method": "sol-gel", "doping_element": "none"}',
            ),
        )
        conn.commit()

    try:
        # Reload index
        copilot = reload_copilot_index()
        assert f"rev_{temp_rev_id}" in copilot.retriever.index.passage_map

        passage = copilot.retriever.index.passage_map[f"rev_{temp_rev_id}"]
        assert passage.composition == "LiMn0.72Fe0.28PO4"
        assert passage.provenance_type == "APPROVED_REVIEW_QUEUE"
        assert passage.structured_data.get("is_verified") is True

        # Search via copilot retriever
        matches = copilot.retriever.retrieve("dynamic test quote fast kinetics", top_k=5)
        matched_ids = [m.passage.passage_id for m in matches]
        assert f"rev_{temp_rev_id}" in matched_ids

    finally:
        # Cleanup temporary review
        with sqlite3.connect(REVIEW_DB_PATH) as conn:
            conn.execute("DELETE FROM extraction_reviews WHERE id = ?", (temp_rev_id,))
            conn.commit()
        # Restore index
        reload_copilot_index()
        fresh = get_passage_index()
        assert f"rev_{temp_rev_id}" not in fresh.passage_map


# ---------------------------------------------------------------------------
# Priority 4: Manual experiment creation with custom dopants and stoichiometry
# ---------------------------------------------------------------------------
def test_priority4_create_undoped_experiment():
    """Verify that an undoped experiment is saved with empty dopants list, NOT injected with hardcoded dopants."""
    cleanup_lab_db()
    try:
        payload = {
            "sample_id": "EXP-UNDOPED-01",
            "operator": "Researcher A",
            "batch_id": "BATCH-UNDOPED",
            "synthesis_route": "sol-gel",
            "mn_frac": 0.70,
            "fe_frac": 0.30,
            "dopants": [],
            "carbon_wt_pct": 2.0,
            "status": "SYNTHESIS_PLANNED",
        }
        res = client.post("/api/experiments", json=payload)
        assert res.status_code == 200, res.text
        exp_id = res.json()["experiment_id"]

        # Fetch saved experiment
        res_get = client.get(f"/api/experiments/{exp_id}")
        assert res_get.status_code == 200, res_get.text
        saved = res_get.json()

        assert saved["dopants"] == [], f"Expected empty dopants, got {saved['dopants']}"
        assert saved["mn_frac"] == 0.70
        assert saved["fe_frac"] == 0.30
        assert "Mn0.7" in saved["generated_formula"] and "Fe0.3" in saved["generated_formula"]
    finally:
        cleanup_lab_db()


def test_priority4_create_custom_dopants_experiment():
    """Verify that a custom single-dopant or dual-dopant experiment is saved exactly as specified."""
    cleanup_lab_db()
    try:
        payload = {
            "sample_id": "EXP-MG-DOPED-01",
            "operator": "Researcher B",
            "batch_id": "BATCH-MG",
            "synthesis_route": "solid-state",
            "mn_frac": 0.70,
            "fe_frac": 0.28,
            "dopants": [
                {"symbol": "Mg", "fraction": 0.02, "oxidation_state": 2}
            ],
            "carbon_wt_pct": 2.5,
            "status": "SYNTHESIS_PLANNED",
        }
        res = client.post("/api/experiments", json=payload)
        assert res.status_code == 200, res.text
        exp_id = res.json()["experiment_id"]

        res_get = client.get(f"/api/experiments/{exp_id}")
        assert res_get.status_code == 200, res_get.text
        saved = res_get.json()

        assert len(saved["dopants"]) == 1
        assert saved["dopants"][0]["symbol"] == "Mg"
        assert saved["dopants"][0]["fraction"] == 0.02
    finally:
        cleanup_lab_db()


def test_priority4_reject_invalid_m2_stoichiometry():
    """Verify that an invalid M2 cation sum (not 1.0000 +- 0.005) is rejected with 400 error."""
    cleanup_lab_db()
    try:
        # 0.70 + 0.30 + 0.05 = 1.05 != 1.0000
        payload = {
            "sample_id": "EXP-INVALID-M2",
            "operator": "Researcher C",
            "batch_id": "BATCH-INVALID",
            "synthesis_route": "sol-gel",
            "mn_frac": 0.70,
            "fe_frac": 0.30,
            "dopants": [
                {"symbol": "Mg", "fraction": 0.05, "oxidation_state": 2}
            ],
            "carbon_wt_pct": 2.0,
            "status": "SYNTHESIS_PLANNED",
        }
        res = client.post("/api/experiments", json=payload)
        assert res.status_code == 400, f"Expected 400 status, got {res.status_code}"
        assert "M2 occupancy invalid" in res.json()["detail"]
    finally:
        cleanup_lab_db()


def test_lab_db_clean_invariants():
    """Final invariant test: verify data/lab_experiments.db contains strictly 0 records."""
    cleanup_lab_db()
    if os.path.exists(LAB_DB_PATH):
        with sqlite3.connect(LAB_DB_PATH) as conn:
            cnt = conn.execute("SELECT COUNT(*) FROM lab_experiments").fetchone()[0]
            assert cnt == 0, f"lab_experiments.db must be 0, found {cnt}"
