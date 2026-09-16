"""
Database Persistence Manager for HE-LMFP Laboratory Experiments.

Supports dual-backend persistence:
- LOCAL MODE (Default): SQLite local file database ('data/lab_experiments.db').
- CLOUD MODE: PostgreSQL / Supabase shared database via 'DATABASE_URL' environment variable.
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
            "engine": "PostgreSQL / Supabase",
            "connection": "DATABASE_URL environment variable active",
            "is_local_sqlite": False
        }
    return {
        "mode": "LOCAL_MODE",
        "engine": "SQLite File Database",
        "db_path": DEFAULT_DB_PATH,
        "is_local_sqlite": True
    }


def _get_pg_connection(db_url: str):
    import psycopg2
    try:
        # Ensure sslmode=require if not specified in URL
        if "sslmode" not in db_url:
            if "?" in db_url:
                db_url += "&sslmode=require"
            else:
                db_url += "?sslmode=require"
        return psycopg2.connect(db_url)
    except psycopg2.OperationalError as err:
        err_msg = str(err)
        if "could not translate host name" in err_msg or "Name or service not known" in err_msg:
            raise RuntimeError(
                "Supabase PostgreSQL Connection Error (DNS / IPv6 issue):\n"
                "Direct Supabase hostnames ('db.<ref>.supabase.co') are IPv6-only.\n"
                "To connect from an IPv4 network/laptop, use the Supabase Connection Pooler connection string:\n"
                "  Hostname: aws-0-[region].pooler.supabase.com (or pooler.supabase.com)\n"
                "  Port: 6543 (Session Mode)\n"
                "  Username format: postgres.[project_ref]\n"
                f"Original Driver Error: {err_msg}"
            ) from err
        elif "timed out" in err_msg.lower() or "10060" in err_msg:
            raise RuntimeError(
                "Supabase PostgreSQL Connection Timeout Error:\n"
                "TCP connection to the host timed out.\n"
                "For Supabase Connection Pooler ('pooler.supabase.com'), verify:\n"
                "  1. Port is set to 6543 (Session Mode) instead of 5432.\n"
                "  2. Username uses the format 'postgres.[project_ref]' (e.g. postgres.zhbzuncrttvyvercutub).\n"
                f"Original Driver Error: {err_msg}"
            ) from err
        raise


def _get_sqlite_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DEFAULT_DB_PATH):
    """Initialize database schema (SQLite or PostgreSQL) if missing."""
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        conn = _get_pg_connection(db_url)
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS lab_experiments (
            experiment_id VARCHAR(255) PRIMARY KEY,
            sample_id VARCHAR(255) NOT NULL,
            created_at VARCHAR(255) NOT NULL,
            updated_at VARCHAR(255) NOT NULL,
            operator VARCHAR(255),
            batch_id VARCHAR(255),
            status VARCHAR(100) NOT NULL,
            generated_formula TEXT NOT NULL,
            json_data TEXT NOT NULL
        );
        """)
        conn.commit()
        conn.close()
    else:
        conn = _get_sqlite_connection(db_path)
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
    """Save or update a LabExperiment record in current database backend."""
    init_db(db_path)
    exp.updated_at = datetime.now().isoformat()
    json_str = json.dumps(exp.to_dict(), indent=2)
    status_str = exp.status.value if isinstance(exp.status, ExperimentStatus) else str(exp.status)

    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        conn = _get_pg_connection(db_url)
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO lab_experiments (
            experiment_id, sample_id, created_at, updated_at, operator, batch_id, status, generated_formula, json_data
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (experiment_id) DO UPDATE SET
            sample_id = EXCLUDED.sample_id,
            updated_at = EXCLUDED.updated_at,
            operator = EXCLUDED.operator,
            batch_id = EXCLUDED.batch_id,
            status = EXCLUDED.status,
            generated_formula = EXCLUDED.generated_formula,
            json_data = EXCLUDED.json_data;
        """, (
            exp.experiment_id, exp.sample_id, exp.created_at, exp.updated_at,
            exp.operator, exp.batch_id, status_str, exp.generated_formula, json_str
        ))
        conn.commit()
        conn.close()
    else:
        conn = _get_sqlite_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO lab_experiments (
            experiment_id, sample_id, created_at, updated_at, operator, batch_id, status, generated_formula, json_data
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            exp.experiment_id, exp.sample_id, exp.created_at, exp.updated_at,
            exp.operator, exp.batch_id, status_str, exp.generated_formula, json_str
        ))
        conn.commit()
        conn.close()

    return exp.experiment_id


def load_experiment(experiment_id: str, db_path: str = DEFAULT_DB_PATH) -> Optional[LabExperiment]:
    """Load a single LabExperiment by ID."""
    init_db(db_path)
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        conn = _get_pg_connection(db_url)
        cursor = conn.cursor()
        cursor.execute("SELECT json_data FROM lab_experiments WHERE experiment_id = %s;", (experiment_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        json_data = row[0]
    else:
        conn = _get_sqlite_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT json_data FROM lab_experiments WHERE experiment_id = ?;", (experiment_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        json_data = row["json_data"]

    data_dict = json.loads(json_data)
    return LabExperiment.from_dict(data_dict)


def list_experiments(db_path: str = DEFAULT_DB_PATH) -> List[LabExperiment]:
    """Return all stored LabExperiment records sorted by updated_at descending."""
    init_db(db_path)
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        conn = _get_pg_connection(db_url)
        cursor = conn.cursor()
        cursor.execute("SELECT json_data FROM lab_experiments ORDER BY updated_at DESC;")
        rows = cursor.fetchall()
        conn.close()
        experiments = []
        for r in rows:
            data_dict = json.loads(r[0])
            experiments.append(LabExperiment.from_dict(data_dict))
        return experiments
    else:
        conn = _get_sqlite_connection(db_path)
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
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        conn = _get_pg_connection(db_url)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM lab_experiments WHERE experiment_id = %s;", (experiment_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted
    else:
        conn = _get_sqlite_connection(db_path)
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
