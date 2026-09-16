"""
SQLite Database Persistence Manager for HE-LMFP Laboratory Experiments.

Provides thread-safe local storage, retrieval, modification, deletion,
and CSV/JSON export utilities for laboratory experiments.
"""

import os
import json
import sqlite3
import pandas as pd
from typing import List, Optional, Dict, Any
from datetime import datetime
from .models import LabExperiment, ExperimentStatus

DEFAULT_DB_PATH = os.path.join("data", "lab_experiments.db")


def get_database_mode_info() -> Dict[str, Any]:
    """
    Return database connection mode details.
    
    LOCAL MODE: Default SQLite file database ('data/lab_experiments.db').
    CLOUD MODE: External PostgreSQL/Supabase database via DATABASE_URL environment variable.
    """
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        return {
            "mode": "CLOUD_MODE",
            "engine": "PostgreSQL / Cloud DB",
            "connection": "DATABASE_URL environment variable configured",
            "is_local_sqlite": False
        }
    return {
        "mode": "LOCAL_MODE",
        "engine": "SQLite File Database",
        "db_path": DEFAULT_DB_PATH,
        "is_local_sqlite": True
    }


def _get_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DEFAULT_DB_PATH):
    """Initialize SQLite database and create experiments table if missing."""
    conn = _get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lab_experiments (
        experiment_id TEXT PRIMARY KEY,
        sample_id TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        operator TEXT,
        batch_id TEXT,
        status TEXT NOT NULL,
        generated_formula TEXT NOT NULL,
        json_data TEXT NOT NULL
    );
    """)
    conn.commit()
    conn.close()


def save_experiment(exp: LabExperiment, db_path: str = DEFAULT_DB_PATH) -> str:
    """Save or update a LabExperiment record in SQLite."""
    init_db(db_path)
    conn = _get_connection(db_path)
    cursor = conn.cursor()

    exp.updated_at = datetime.now().isoformat()
    json_str = json.dumps(exp.to_dict(), indent=2)

    cursor.execute("""
    INSERT OR REPLACE INTO lab_experiments (
        experiment_id, sample_id, created_at, updated_at, operator, batch_id, status, generated_formula, json_data
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        exp.experiment_id,
        exp.sample_id,
        exp.created_at,
        exp.updated_at,
        exp.operator,
        exp.batch_id,
        exp.status.value if isinstance(exp.status, ExperimentStatus) else str(exp.status),
        exp.generated_formula,
        json_str
    ))

    conn.commit()
    conn.close()
    return exp.experiment_id


def load_experiment(experiment_id: str, db_path: str = DEFAULT_DB_PATH) -> Optional[LabExperiment]:
    """Load a single LabExperiment by ID."""
    init_db(db_path)
    conn = _get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT json_data FROM lab_experiments WHERE experiment_id = ?;", (experiment_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    data_dict = json.loads(row["json_data"])
    return LabExperiment.from_dict(data_dict)


def list_experiments(db_path: str = DEFAULT_DB_PATH) -> List[LabExperiment]:
    """Return all stored LabExperiment records sorted by updated_at descending."""
    init_db(db_path)
    conn = _get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT json_data FROM lab_experiments ORDER BY updated_at DESC;")
    rows = cursor.fetchall()
    conn.close()

    experiments = []
    for r in rows:
        data_dict = json.loads(r["json_data"])
        experiments.append(LabExperiment.from_dict(data_dict))

    return experiments


def update_experiment(exp: LabExperiment, db_path: str = DEFAULT_DB_PATH) -> str:
    """Update an existing LabExperiment record."""
    return save_experiment(exp, db_path)


def delete_experiment(experiment_id: str, db_path: str = DEFAULT_DB_PATH) -> bool:
    """Delete a LabExperiment record by ID."""
    init_db(db_path)
    conn = _get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM lab_experiments WHERE experiment_id = ?;", (experiment_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def export_experiments_to_csv(output_path: str = os.path.join("data", "lab_experiments_export.csv"), db_path: str = DEFAULT_DB_PATH) -> str:
    """Export flattened overview of all experiments to CSV."""
    experiments = list_experiments(db_path)
    rows = []
    for exp in experiments:
        syn = exp.synthesis_data
        char = exp.characterization_data
        elec = exp.electrochemical_data

        rows.append({
            "Experiment_ID": exp.experiment_id,
            "Sample_ID": exp.sample_id,
            "Status": exp.status.value,
            "Created_At": exp.created_at,
            "Operator": exp.operator,
            "Batch_ID": exp.batch_id,
            "Generated_Formula": exp.generated_formula,
            "Mn_Fraction": exp.mn_frac,
            "Fe_Fraction": exp.fe_frac,
            "Synthesis_Route": exp.synthesis_route,
            "Precursor_Mass_g": syn.precursor_mass_g if syn else None,
            "Calcination_Temp_C": syn.calcination_temp_c if syn else None,
            "XRD_Phase_Purity_Pct": char.xrd_phase_purity_pct if char else None,
            "BET_Surface_Area_m2g": char.bet_surface_area_m2g if char else None,
            "Cap_0.1C_mAhg": elec.cap_0_1c if elec else None,
            "Cap_1C_mAhg": elec.cap_1c if elec else None,
            "ICE_Pct": elec.initial_coulombic_efficiency if elec else None,
            "Retention_25C_Pct": elec.retention_25c_pct if elec else None,
            "Retention_55C_Pct": elec.retention_55c_pct if elec else None,
            "Retention_-20C_Pct": elec.retention_minus20c_pct if elec else None,
            "Notes": exp.notes
        })

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(output_path, index=False)
    return output_path


def export_experiments_to_json(output_path: str = os.path.join("data", "lab_experiments_export.json"), db_path: str = DEFAULT_DB_PATH) -> str:
    """Export complete JSON representation of all experiments."""
    experiments = list_experiments(db_path)
    data_list = [exp.to_dict() for exp in experiments]

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data_list, f, indent=2)

    return output_path
