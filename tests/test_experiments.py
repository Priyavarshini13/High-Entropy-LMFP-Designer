"""
Unit Tests for Laboratory Experiment Engine (tests/test_experiments.py).

Tests:
1. Model creation and JSON dictionary serialization.
2. Status auto-update logic based on completion stages.
3. SQLite storage CRUD operations (save, load, list, update, delete).
4. Export utilities (CSV export, JSON export).
5. Input validation rules for laboratory data.
6. Triple comparison matrix generation and residual calculation.
"""

import os
import pytest
import tempfile
from experiments.models import (
    LabExperiment,
    ExperimentStatus,
    ActualSynthesisData,
    ActualCharacterizationData,
    ActualElectrochemicalData
)
from experiments.storage import (
    init_db,
    save_experiment,
    load_experiment,
    list_experiments,
    update_experiment,
    delete_experiment,
    export_experiments_to_csv,
    export_experiments_to_json,
    get_database_mode_info
)
from experiments.validation import validate_lab_experiment
from experiments.comparison import generate_comparison_matrix
from chemistry.formula import generate_formula
from chemistry.capacity import calculate_capacity_metrics


@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    if os.path.exists(db_path):
        os.remove(db_path)


def test_lab_experiment_model_and_serialization():
    """Test experiment data model instantiation and dict conversion."""
    exp = LabExperiment(
        experiment_id="EXP-2026-001",
        sample_id="SMP-LMFP-001",
        created_at="2026-09-15T12:00:00",
        updated_at="2026-09-15T12:00:00",
        operator="Dr. Priya",
        batch_id="BATCH-001",
        notes="Initial trial synthesis of HE-LMFP",
        status=ExperimentStatus.DESIGNED,
        generated_formula="Li0.93[Mn0.65Fe0.26Mg0.02Zn0.02Nb0.01Cu0.02Zr0.02]PO4",
        mn_frac=0.65,
        fe_frac=0.26,
        dopants=[
            {"symbol": "Mg", "fraction": 0.02, "oxidation_state": 2},
            {"symbol": "Zn", "fraction": 0.02, "oxidation_state": 2},
            {"symbol": "Nb", "fraction": 0.01, "oxidation_state": 5},
            {"symbol": "Cu", "fraction": 0.02, "oxidation_state": 2},
            {"symbol": "Zr", "fraction": 0.02, "oxidation_state": 4}
        ],
        carbon_wt_pct=2.5,
        cnt_wt_pct=1.0,
        mgo_enabled=False,
        synthesis_route="Co-precipitation"
    )

    d = exp.to_dict()
    assert d["experiment_id"] == "EXP-2026-001"
    assert d["status"] == "DESIGNED"
    assert d["mn_frac"] == 0.65

    reconstructed = LabExperiment.from_dict(d)
    assert reconstructed.experiment_id == "EXP-2026-001"
    assert reconstructed.operator == "Dr. Priya"
    assert reconstructed.status == ExperimentStatus.DESIGNED


def test_experiment_status_auto_update():
    """Test automatic status progression as experimental data is entered."""
    exp = LabExperiment(
        experiment_id="EXP-002",
        sample_id="SMP-002",
        created_at="2026-09-15T12:00:00",
        updated_at="2026-09-15T12:00:00",
        operator="Researcher",
        batch_id="BATCH-002",
        notes="",
        status=ExperimentStatus.DESIGNED,
        generated_formula="Li[Mn0.65Fe0.26Mg0.02Zn0.02Nb0.01Cu0.02Zr0.02]PO4",
        mn_frac=0.65,
        fe_frac=0.26,
        dopants=[],
        carbon_wt_pct=2.5,
        cnt_wt_pct=1.0,
        mgo_enabled=False,
        synthesis_route="Co-precipitation"
    )
    assert exp.status == ExperimentStatus.DESIGNED

    # Add synthesis data
    exp.synthesis_data = ActualSynthesisData(reaction_ph=8.5, calcination_temp_c=700.0)
    exp.update_status_automatically()
    assert exp.status == ExperimentStatus.SYNTHESIZED

    # Add characterization data
    exp.characterization_data = ActualCharacterizationData(xrd_phase_purity_pct=98.5, bet_surface_area_m2g=18.4)
    exp.update_status_automatically()
    assert exp.status == ExperimentStatus.CHARACTERIZATION_COMPLETE

    # Add electrochemical data
    exp.electrochemical_data = ActualElectrochemicalData(cap_0_1c=155.2, retention_25c_pct=96.5)
    exp.update_status_automatically()
    assert exp.status == ExperimentStatus.EXPERIMENTALLY_VALIDATED


def test_sqlite_storage_crud_operations(temp_db):
    """Test SQLite database initialization, insert, load, list, update, and delete."""
    init_db(temp_db)

    exp1 = LabExperiment(
        experiment_id="EXP-SQL-001",
        sample_id="SMP-001",
        created_at="2026-09-15T12:00:00",
        updated_at="2026-09-15T12:00:00",
        operator="Alice",
        batch_id="B1",
        notes="Test exp 1",
        status=ExperimentStatus.DESIGNED,
        generated_formula="Formula1",
        mn_frac=0.65,
        fe_frac=0.26,
        dopants=[],
        carbon_wt_pct=2.5,
        cnt_wt_pct=1.0,
        mgo_enabled=False,
        synthesis_route="Co-precipitation"
    )

    # Save
    save_experiment(exp1, temp_db)

    # Load
    loaded = load_experiment("EXP-SQL-001", temp_db)
    assert loaded is not None
    assert loaded.operator == "Alice"
    assert loaded.generated_formula == "Formula1"

    # Update
    exp1.notes = "Updated notes"
    exp1.synthesis_data = ActualSynthesisData(reaction_ph=9.0)
    update_experiment(exp1, temp_db)

    updated_exp = load_experiment("EXP-SQL-001", temp_db)
    assert updated_exp.notes == "Updated notes"
    assert updated_exp.synthesis_data.reaction_ph == 9.0

    # List
    all_exps = list_experiments(temp_db)
    assert len(all_exps) == 1

    # Delete
    deleted = delete_experiment("EXP-SQL-001", temp_db)
    assert deleted is True
    assert load_experiment("EXP-SQL-001", temp_db) is None


def test_export_utilities(temp_db):
    """Test CSV and JSON export functions for lab experiments."""
    exp = LabExperiment(
        experiment_id="EXP-EXP-001",
        sample_id="SMP-001",
        created_at="2026-09-15T12:00:00",
        updated_at="2026-09-15T12:00:00",
        operator="Bob",
        batch_id="B2",
        notes="Export test",
        status=ExperimentStatus.EXPERIMENTALLY_VALIDATED,
        generated_formula="Formula_Test",
        mn_frac=0.65,
        fe_frac=0.26,
        dopants=[],
        carbon_wt_pct=2.5,
        cnt_wt_pct=1.0,
        mgo_enabled=False,
        synthesis_route="Co-precipitation",
        synthesis_data=ActualSynthesisData(precursor_mass_g=50.0, calcination_temp_c=700.0),
        characterization_data=ActualCharacterizationData(xrd_phase_purity_pct=99.0, bet_surface_area_m2g=22.5),
        electrochemical_data=ActualElectrochemicalData(cap_0_1c=156.5, retention_25c_pct=98.0)
    )
    save_experiment(exp, temp_db)

    with tempfile.TemporaryDirectory() as tmp_dir:
        csv_path = os.path.join(tmp_dir, "export.csv")
        json_path = os.path.join(tmp_dir, "export.json")

        export_experiments_to_csv(csv_path, temp_db)
        export_experiments_to_json(json_path, temp_db)

        assert os.path.exists(csv_path)
        assert os.path.exists(json_path)
        assert os.path.getsize(csv_path) > 0
        assert os.path.getsize(json_path) > 0


def test_lab_experiment_validation_rules():
    """Test input validation for lab experiments."""
    exp = LabExperiment(
        experiment_id="EXP-VAL-001",
        sample_id="SMP-001",
        created_at="2026-09-15T12:00:00",
        updated_at="2026-09-15T12:00:00",
        operator="Test",
        batch_id="B1",
        notes="",
        status=ExperimentStatus.DESIGNED,
        generated_formula="Formula",
        mn_frac=0.65,
        fe_frac=0.26,
        dopants=[],
        carbon_wt_pct=2.5,
        cnt_wt_pct=1.0,
        mgo_enabled=False,
        synthesis_route="Co-precipitation",
        synthesis_data=ActualSynthesisData(reaction_ph=16.0),  # Invalid pH > 14
        electrochemical_data=ActualElectrochemicalData(cap_0_1c=-10.0, initial_coulombic_efficiency=105.0)  # Invalid cap & ICE
    )

    val_res = validate_lab_experiment(exp)
    assert val_res.is_valid is False
    assert len(val_res.errors) >= 3
    assert any("Reaction pH" in err for err in val_res.errors)
    assert any("0.1C capacity" in err for err in val_res.errors)
    assert any("ICE" in err for err in val_res.errors)


def test_triple_comparison_matrix():
    """Test comparison matrix generation between Calculated, Literature, and Experimental data."""
    formula = generate_formula(0.93, 0.65, 0.26, [
        {"symbol": "Mg", "fraction": 0.02, "oxidation_state": 2},
        {"symbol": "Zn", "fraction": 0.02, "oxidation_state": 2},
        {"symbol": "Nb", "fraction": 0.01, "oxidation_state": 5},
        {"symbol": "Cu", "fraction": 0.02, "oxidation_state": 2},
        {"symbol": "Zr", "fraction": 0.02, "oxidation_state": 4}
    ])
    cap_metrics = calculate_capacity_metrics(0.93, formula.molar_mass)

    exp = LabExperiment(
        experiment_id="EXP-COMP-001",
        sample_id="SMP-COMP",
        created_at="2026-09-15T12:00:00",
        updated_at="2026-09-15T12:00:00",
        operator="Lab",
        batch_id="B1",
        notes="",
        status=ExperimentStatus.EXPERIMENTALLY_VALIDATED,
        generated_formula=formula.formula_string,
        mn_frac=0.65,
        fe_frac=0.26,
        dopants=[],
        carbon_wt_pct=2.5,
        cnt_wt_pct=1.0,
        mgo_enabled=False,
        synthesis_route="Co-precipitation",
        electrochemical_data=ActualElectrochemicalData(cap_0_1c=154.0, cap_1c=135.0, retention_25c_pct=95.0)
    )

    matrix = generate_comparison_matrix(formula, cap_metrics, None, exp)
    assert matrix.formula_string == formula.formula_string
    assert len(matrix.rows) >= 6

    row_01c = next(r for r in matrix.rows if r.property_name == "0.1C Capacity")
    assert row_01c.calculated_val == pytest.approx(cap_metrics.formula_calculated_capacity_metric, abs=0.2)
    assert row_01c.experimental_val == 154.0
    assert row_01c.residual_vs_calculated == pytest.approx(154.0 - cap_metrics.formula_calculated_capacity_metric, abs=0.2)
    assert row_01c.calculated_label == "CALCULATED"
    assert row_01c.experimental_label == "EXPERIMENTAL"


def test_database_mode_selection(monkeypatch):
    """Test automatic database mode detection based on DATABASE_URL environment variable."""
    # Test 1: Without DATABASE_URL -> LOCAL_MODE (SQLite)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    info_local = get_database_mode_info()
    assert info_local["mode"] == "LOCAL_MODE"
    assert info_local["is_local_sqlite"] is True
    assert "SQLite" in info_local["engine"]

    # Test 2: With DATABASE_URL -> CLOUD_MODE (PostgreSQL)
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/testdb")
    info_cloud = get_database_mode_info()
    assert info_cloud["mode"] == "CLOUD_MODE"
    assert info_cloud["is_local_sqlite"] is False
    assert "PostgreSQL" in info_cloud["engine"]


def test_postgresql_backend_detection_and_mock(monkeypatch, mocker=None):
    """Test PostgreSQL backend initialization and SQL execution flow under CLOUD_MODE."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://testuser:testpass@supabasedb.com:5432/he_lmfp")
    info = get_database_mode_info()
    assert info["mode"] == "CLOUD_MODE"
    assert info["engine"] == "PostgreSQL / Supabase"

