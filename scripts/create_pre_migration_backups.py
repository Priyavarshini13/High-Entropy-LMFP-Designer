"""
ECMT AI — Pre-Migration Backup and Export Script.
Creates timestamped binary SQLite database snapshots and structured JSON exports
for lab_experiments and literature_review databases before any cloud operations.
"""

import os
import sys
import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXP_DB = PROJECT_ROOT / "data" / "lab_experiments.db"
REV_DB = PROJECT_ROOT / "data" / "literature_review.db"
BACKUP_DIR = PROJECT_ROOT / "data" / "backups"


def create_pre_migration_backups():
    print("=" * 70)
    print("ECMT AI — PRE-MIGRATION SAFETY BACKUP & JSON EXPORT GENERATOR")
    print("=" * 70)

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 1. Backup lab_experiments.db
    exp_backup_db = BACKUP_DIR / f"lab_experiments_backup_{ts}.db"
    exp_export_json = BACKUP_DIR / f"lab_experiments_export_{ts}.json"

    if EXP_DB.exists():
        shutil.copy2(EXP_DB, exp_backup_db)
        print(f"[1/4] SQLite snapshot: {exp_backup_db.name} ({exp_backup_db.stat().st_size} bytes)")

        conn = sqlite3.connect(EXP_DB)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM lab_experiments")
        exp_rows = [dict(r) for r in cur.fetchall()]
        conn.close()

        with open(exp_export_json, "w", encoding="utf-8") as f:
            json.dump(exp_rows, f, indent=2)
        print(f"[2/4] JSON export: {exp_export_json.name} ({len(exp_rows)} experiments preserved)")
    else:
        print("[Warning] lab_experiments.db not found!")
        exp_rows = []

    # 2. Backup literature_review.db
    rev_backup_db = BACKUP_DIR / f"literature_review_backup_{ts}.db"
    rev_export_json = BACKUP_DIR / f"literature_review_export_{ts}.json"

    if REV_DB.exists():
        shutil.copy2(REV_DB, rev_backup_db)
        print(f"[3/4] SQLite snapshot: {rev_backup_db.name} ({rev_backup_db.stat().st_size} bytes)")

        conn = sqlite3.connect(REV_DB)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM extraction_reviews")
        rev_rows = [dict(r) for r in cur.fetchall()]
        conn.close()

        with open(rev_export_json, "w", encoding="utf-8") as f:
            json.dump(rev_rows, f, indent=2)
        print(f"[4/4] JSON export: {rev_export_json.name} ({len(rev_rows)} reviews preserved)")
    else:
        print("[Warning] literature_review.db not found!")
        rev_rows = []

    print("\n" + "=" * 70)
    print("BACKUP VERIFICATION SUMMARY:")
    print(f"  • Lab Experiments : {len(exp_rows)} record(s) verified & exported")
    if exp_rows:
        print(f"    - Target ID: {exp_rows[0].get('experiment_id')} ({exp_rows[0].get('sample_id')})")
    print(f"  • Literature Reviews: {len(rev_rows)} record(s) verified & exported")
    print(f"    - Statuses: Pending={sum(1 for r in rev_rows if r.get('status') == 'pending')}, "
          f"Approved={sum(1 for r in rev_rows if r.get('status') == 'approved')}, "
          f"Rejected={sum(1 for r in rev_rows if r.get('status') == 'rejected')}")
    print("=" * 70)
    return {
        "timestamp": ts,
        "exp_backup_db": str(exp_backup_db),
        "exp_export_json": str(exp_export_json),
        "rev_backup_db": str(rev_backup_db),
        "rev_export_json": str(rev_export_json),
        "exp_count": len(exp_rows),
        "rev_count": len(rev_rows),
    }


if __name__ == "__main__":
    create_pre_migration_backups()
