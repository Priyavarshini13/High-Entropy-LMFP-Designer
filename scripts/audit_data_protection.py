"""
Independent Data Protection and Repository Integrity Audit Script.
Verifies:
1. Master literature reference CSV remains exactly 1,215 rows × 41 columns.
2. Review database maintains 35 reviews, with Review 6 quarantined as 'pending'.
3. Review 7 remains approved but blocked by its 3 unresolved blockers, preventing export.
4. No unapproved/blocked reviews are exported into the master dataset.
5. Laboratory experiment database remains intact.
6. Machine learning artifacts and metadata remain intact.
"""

import json
import sqlite3
import sys
from pathlib import Path
import pandas as pd

# Ensure workspace root is in python path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))


def audit_data_protection():
    print("=" * 70)
    print("INDEPENDENT DATA PROTECTION AND REPOSITORY INTEGRITY AUDIT")
    print("=" * 70)

    # 1. Master Literature Reference CSV
    csv_path = WORKSPACE_ROOT / "data" / "literature_reference.csv"
    if not csv_path.exists():
        print(f"FAILED: Master CSV not found at {csv_path}")
        return False

    df = pd.read_csv(csv_path)
    print(f"1. Master Literature CSV: Shape is {df.shape}")
    if df.shape != (1215, 41):
        print(f"FAILED: Expected (1215, 41), got {df.shape}")
        return False
    print("   [OK] Row count: 1,215, Column count: 41 (exact match)")

    # 2. Literature Review DB
    db_path = WORKSPACE_ROOT / "data" / "literature_review.db"
    if not db_path.exists():
        print(f"FAILED: Review database not found at {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM extraction_reviews")
    rev_count = cur.fetchone()[0]
    print(f"2. Literature Review DB: Total reviews = {rev_count}")
    if rev_count < 35:
        print(f"FAILED: Expected at least 35 reviews, got {rev_count}")
        return False
    print(f"   [OK] Total review count = {rev_count} (>= 35 baseline preserved)")

    # Inspect Review 6
    cur.execute("SELECT id, status, source_pdf FROM extraction_reviews WHERE id = 6")
    r6 = cur.fetchone()
    if not r6 or r6[1] != "pending":
        print(f"FAILED: Review #6 status is {r6[1] if r6 else 'None'}, expected 'pending'")
        return False
    print(f"   [OK] Review #6 status = '{r6[1]}' (Quarantined, Source: {r6[2]})")

    # Inspect Review 7
    cur.execute("SELECT id, status, source_pdf FROM extraction_reviews WHERE id = 7")
    r7 = cur.fetchone()
    if not r7 or r7[1] != "approved":
        print(f"FAILED: Review #7 status is {r7[1] if r7 else 'None'}, expected 'approved'")
        return False
    print(f"   [OK] Review #7 status = '{r7[1]}' (Approved review with export blockers)")

    # Inspect export preview
    from literature.dataset_export import preview_approved_exports

    preview = preview_approved_exports()
    print("3. Dataset Export Preview Guardrails:")
    print(f"   Master records: {preview['master_records']}")
    print(f"   Approved reviews: {preview['approved_reviews']}")
    print(f"   Exportable records: {preview['exportable_records']}")
    print(f"   Blocked records: {preview['blocked_records']}")

    if preview["exportable_records"] != 0:
        print(f"FAILED: Expected 0 exportable records, got {preview['exportable_records']}")
        return False

    if preview["blocked_records"] != 1:
        print(f"FAILED: Expected 1 blocked record, got {preview['blocked_records']}")
        return False

    # Find Review 7 in export preview records
    r7_preview = next((r for r in preview["records"] if r.get("review_id") == 7), None)
    if not r7_preview:
        print("FAILED: Review #7 record missing in blocked records list")
        return False

    blockers = r7_preview.get("errors", [])
    print(f"   [OK] Review #7 is strictly blocked with {len(blockers)} unresolved blockers:")
    for b in blockers:
        print(f"        - {b}")

    if len(blockers) < 3:
        print(f"FAILED: Expected at least 3 blocker reasons, found {len(blockers)}")
        return False

    # Ensure Review 6 does not appear in export preview records
    r6_in_preview = any(r.get("review_id") == 6 for r in preview["records"])
    if r6_in_preview:
        print("FAILED: Review #6 (pending) appears in export preview")
        return False
    print("   [OK] Review #6 (pending) is excluded from export preview")

    # 4. Lab Experiments Database
    lab_db = WORKSPACE_ROOT / "data" / "lab_experiments.db"
    if not lab_db.exists():
        print("FAILED: Lab experiments DB missing")
        return False
    conn_lab = sqlite3.connect(lab_db)
    cur_lab = conn_lab.cursor()
    cur_lab.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cur_lab.fetchall()]
    print(f"4. Laboratory Experiment DB: Tables = {tables}")
    if "lab_experiments" not in tables:
        print("FAILED: 'lab_experiments' table not found in lab_experiments.db")
        return False
    cur_lab.execute("SELECT COUNT(*) FROM lab_experiments")
    exp_count = cur_lab.fetchone()[0]
    print(f"   [OK] Lab experiment table verified with {exp_count} recorded experiments")

    # 5. Machine Learning Artifacts
    ml_dir = WORKSPACE_ROOT / "models" / "ml" / "artifacts"
    if not ml_dir.exists():
        print("FAILED: ML artifacts directory missing")
        return False
    required_ml_files = [
        "ml_metadata.json",
        "model_0_1C_capacity.joblib",
        "model_1C_capacity.joblib",
        "model_5C_capacity.joblib",
        "model_capacity_retention.joblib",
    ]
    for mf in required_ml_files:
        p = ml_dir / mf
        if not p.exists() or p.stat().st_size == 0:
            print(f"FAILED: ML artifact missing or empty: {mf}")
            return False
    print("5. Machine Learning Artifacts: All 5 artifacts present and non-empty")
    print("   [OK] ml_metadata.json and all 4 trained joblib models verified")

    print("=" * 70)
    print("ALL DATA PROTECTION & REPOSITORY INTEGRITY CHECKS PASSED (100%)")
    print("=" * 70)
    return True


if __name__ == "__main__":
    success = audit_data_protection()
    sys.exit(0 if success else 1)
