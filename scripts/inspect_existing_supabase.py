"""
ECMT AI — Existing Supabase Project Non-Destructive Inspection Script.

Performs deep READ-ONLY inspection of the existing 'HE-LMFP-Designer' Supabase project:
1. Lists all PostgreSQL schemas, tables, columns, indexes, and constraints.
2. Compares existing remote records with local SQLite (1 experiment, 37 reviews).
3. Verifies whether EXP-9260F00A and extraction reviews exist.
4. Inspects Supabase Storage buckets, privacy settings, and stored objects.
5. Generates a non-destructive compatibility and delta report.
6. Strictly hides/masks all passwords, keys, and tokens from all logs.
"""

import os
import re
import sys
import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

LOCAL_EXP_DB = PROJECT_ROOT / "data" / "lab_experiments.db"
LOCAL_REV_DB = PROJECT_ROOT / "data" / "literature_review.db"
OUTPUT_REPORT_PATH = PROJECT_ROOT / "data" / "supabase_inspection_report.json"


def mask_sensitive_url(text: str) -> str:
    """Mask any passwords, API keys, or JWT tokens in text or error messages."""
    if not text:
        return ""
    # Mask postgresql://user:password@host
    masked = re.sub(r"://([^:]+):([^@]+)@", r"://\1:****@", text)
    # Mask password=xyz
    masked = re.sub(r"(?i)password=[^\s&]+", "password=****", masked)
    # Mask apikey or bearer tokens
    masked = re.sub(r"(?i)(?:apikey|bearer)\s+[a-zA-Z0-9_\-\.]{15,}", "Bearer ****", masked)
    return masked


def load_env_safely():
    """Load credentials from environment, user environment, or .env files if present."""
    # Check .env or .env.local
    for env_path in [PROJECT_ROOT / ".env", PROJECT_ROOT / ".env.local"]:
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("'\"")
                    if k not in os.environ and v:
                        os.environ[k] = v

    # If still not found on Windows, check User-level persistent environment
    if sys.platform == "win32" and not os.environ.get("DATABASE_URL"):
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
                for k in ["DATABASE_URL", "SUPABASE_URL", "SUPABASE_KEY"]:
                    try:
                        val, _ = winreg.QueryValueEx(key, k)
                        if val and k not in os.environ:
                            os.environ[k] = val
                    except FileNotFoundError:
                        pass
        except Exception:
            pass


def inspect_supabase():
    print("=" * 75)
    print("ECMT AI — DEEP NON-DESTRUCTIVE SUPABASE PROJECT INSPECTION")
    print("Target Project: HE-LMFP-Designer (zhbzuncrttvyvercutub)")
    print("Security: Read-Only (0 Inserts, 0 Updates, 0 Deletes, 0 Alters, 0 Drops)")
    print("=" * 75)

    load_env_safely()

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("\n[INFO] DATABASE_URL is not set.")
        print("Please configure your credentials locally in your terminal:")
        print("  $env:DATABASE_URL='postgresql://postgres.zhbzuncrttvyvercutub:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?sslmode=require'")
        print("  $env:SUPABASE_URL='https://zhbzuncrttvyvercutub.supabase.co'")
        print("  $env:SUPABASE_KEY='[ANON-OR-SERVICE-KEY]'")
        print("  python scripts/inspect_existing_supabase.py\n")
        return False

    if "sslmode" not in db_url:
        db_url += ("&" if "?" in db_url else "?") + "sslmode=require"

    print("\n[1/5] Connecting to Supabase PostgreSQL (zhbzuncrttvyvercutub)...")
    import psycopg2
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        print("      Connected successfully to Supabase PostgreSQL (READ-ONLY)!")
    except Exception as exc:
        safe_msg = mask_sensitive_url(str(exc))
        print(f"[ERROR] Failed to connect: {safe_msg}")
        return False

    report: Dict[str, Any] = {
        "project_reference": "zhbzuncrttvyvercutub",
        "database_connected": True,
        "schemas": [],
        "tables": {},
        "indexes": [],
        "constraints": [],
        "storage_buckets": [],
        "reconciliation": {},
        "compatibility": {},
    }

    # 1. Query Schemas & Tables in public schema
    print("\n[2/5] Inspecting schemas, tables, and column types...")
    cur.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT IN ('pg_catalog', 'information_schema') ORDER BY schema_name;")
    report["schemas"] = [r[0] for r in cur.fetchall()]

    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name;
    """)
    tables = [r[0] for r in cur.fetchall()]
    print(f"      Found {len(tables)} table(s) in 'public' schema: {tables}")

    for tbl in tables:
        cur.execute(f'SELECT COUNT(*) FROM "{tbl}"')
        count = cur.fetchone()[0]

        cur.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position;
        """, (tbl,))
        cols = cur.fetchall()

        # Sample up to 2 existing rows (with sanitized text)
        sample_rows = []
        try:
            cur.execute(f'SELECT * FROM "{tbl}" LIMIT 2')
            raw_samples = cur.fetchall()
            col_names = [c[0] for c in cols]
            for r in raw_samples:
                row_dict = {}
                for k, v in zip(col_names, r):
                    row_dict[k] = str(v)[:80] if v is not None else None
                sample_rows.append(row_dict)
        except Exception:
            pass

        report["tables"][tbl] = {
            "row_count": count,
            "columns": [{"name": c[0], "type": c[1], "nullable": c[2], "default": c[3]} for c in cols],
            "sample_rows": sample_rows,
        }
        print(f"      • Table '{tbl}': {count} existing record(s), {len(cols)} columns")
        col_summary = [f"{c[0]} ({c[1]})" for c in cols[:6]]
        print(f"        Columns: {', '.join(col_summary)}{'...' if len(cols) > 6 else ''}")

    # 2. Inspect Indexes
    print("\n[3/5] Inspecting PostgreSQL Indexes and Constraints...")
    cur.execute("""
        SELECT tablename, indexname, indexdef 
        FROM pg_indexes 
        WHERE schemaname = 'public' 
        ORDER BY tablename, indexname;
    """)
    indexes = cur.fetchall()
    for idx in indexes:
        report["indexes"].append({"table": idx[0], "index": idx[1], "definition": idx[2]})
    print(f"      Found {len(indexes)} index(es) across tables.")
    for idx in indexes:
        print(f"      • [{idx[0]}] {idx[1]}")

    # Inspect Constraints
    cur.execute("""
        SELECT tc.table_name, tc.constraint_name, tc.constraint_type, kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
          AND tc.table_schema = kcu.table_schema
        WHERE tc.table_schema = 'public'
        ORDER BY tc.table_name, tc.constraint_name;
    """)
    constraints = cur.fetchall()
    for con in constraints:
        report["constraints"].append({
            "table": con[0], "constraint": con[1], "type": con[2], "column": con[3]
        })
    print(f"      Found {len(constraints)} constraint(s) (Primary Keys, Foreign Keys, Unique):")
    for con in constraints:
        print(f"      • [{con[0]}] {con[2]}: {con[1]} ({con[3]})")

    # 3. Specific Record Checks (EXP-9260F00A and 37 Reviews)
    print("\n[4/5] Reconciling Records vs Local SQLite Database...")
    local_exp_ids = set()
    local_exp_count = 0
    if LOCAL_EXP_DB.exists():
        l_conn = sqlite3.connect(LOCAL_EXP_DB)
        l_cur = l_conn.cursor()
        try:
            l_cur.execute("SELECT experiment_id FROM lab_experiments")
            local_exp_ids = {r[0] for r in l_cur.fetchall()}
            local_exp_count = len(local_exp_ids)
        except Exception:
            pass
        l_conn.close()

    remote_exp_ids = set()
    target_exp_found = False
    if "lab_experiments" in tables:
        cur.execute('SELECT experiment_id FROM "lab_experiments"')
        remote_exp_ids = {r[0] for r in cur.fetchall()}
        target_exp_found = "EXP-9260F00A" in remote_exp_ids

    common_exp = local_exp_ids.intersection(remote_exp_ids)
    missing_in_remote_exp = local_exp_ids - remote_exp_ids

    print("      • Experiment Record Audit:")
    print(f"        - Target 'EXP-9260F00A' (HE-LMFP-EXP-01): {'ALREADY PRESENT IN SUPABASE' if target_exp_found else 'NOT YET IN SUPABASE (in local SQLite)'}")
    print(f"        - Supabase Remote Count: {len(remote_exp_ids)}")
    print(f"        - Local SQLite Count   : {local_exp_count}")
    print(f"        - Common Experiment IDs: {list(common_exp)}")

    # Check reviews
    local_rev_count = 0
    if LOCAL_REV_DB.exists():
        r_conn = sqlite3.connect(LOCAL_REV_DB)
        r_cur = r_conn.cursor()
        try:
            r_cur.execute("SELECT count(*) FROM extraction_reviews")
            local_rev_count = r_cur.fetchone()[0]
        except Exception:
            pass
        r_conn.close()

    remote_rev_count = 0
    if "extraction_reviews" in tables:
        cur.execute('SELECT COUNT(*) FROM "extraction_reviews"')
        remote_rev_count = cur.fetchone()[0]

    all_reviews_present = (remote_rev_count >= local_rev_count) if local_rev_count > 0 else False
    print("      • Extraction Review Audit:")
    print(f"        - Supabase Remote Count: {remote_rev_count}")
    print(f"        - Local SQLite Count   : {local_rev_count}")
    print(f"        - All 37 Reviews Present: {'YES' if all_reviews_present else 'NOT YET (in local SQLite)'}")

    report["reconciliation"] = {
        "target_exp_EXP_9260F00A_present": target_exp_found,
        "remote_experiments_count": len(remote_exp_ids),
        "local_experiments_count": local_exp_count,
        "remote_reviews_count": remote_rev_count,
        "local_reviews_count": local_rev_count,
        "all_reviews_present": all_reviews_present,
    }

    conn.close()

    # 4. Storage Buckets Inspection
    print("\n[5/5] Inspecting Supabase Storage Buckets and Objects...")
    supabase_url = os.environ.get("SUPABASE_URL", "https://zhbzuncrttvyvercutub.supabase.co").rstrip("/")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY", "")

    if supabase_url and supabase_key:
        import requests
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
        }
        try:
            res = requests.get(f"{supabase_url}/storage/v1/bucket", headers=headers, timeout=5)
            if res.status_code == 200:
                buckets = res.json()
                print(f"      Found {len(buckets)} storage bucket(s):")
                for b in buckets:
                    b_id = b.get("id")
                    b_pub = b.get("public")
                    b_size = b.get("file_size_limit")
                    print(f"      • Bucket '{b_id}': public={b_pub} (Private: {not b_pub}), size_limit={b_size}")

                    list_res = requests.post(
                        f"{supabase_url}/storage/v1/object/list/{b_id}",
                        headers={**headers, "Content-Type": "application/json"},
                        json={"prefix": "", "limit": 50},
                        timeout=5
                    )
                    objs = list_res.json() if list_res.status_code == 200 else []
                    report["storage_buckets"].append({
                        "id": b_id, "public": b_pub, "is_private": not b_pub,
                        "file_size_limit": b_size, "object_count": len(objs),
                        "objects": [{"name": o.get("name"), "size": o.get("metadata", {}).get("size")} for o in objs]
                    })
                    print(f"        Objects inside '{b_id}': {len(objs)} file(s)")
                    for o in objs[:5]:
                        print(f"          - {o.get('name')} ({o.get('metadata', {}).get('size', 0)} bytes)")
            else:
                print(f"      Could not query storage buckets (HTTP {res.status_code})")
        except Exception as exc:
            safe_err = mask_sensitive_url(str(exc))
            print(f"      Storage inspection error: {safe_err}")
    else:
        print("      (SUPABASE_KEY not provided; storage API probe skipped)")

    # Save complete JSON report
    OUTPUT_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\nDetailed JSON report saved to: {OUTPUT_REPORT_PATH}")

    print("\n" + "=" * 75)
    print("READ-ONLY INSPECTION FINISHED: ZERO DATA WAS MODIFIED OR OVERWRITTEN.")
    print("=" * 75)
    return True


if __name__ == "__main__":
    inspect_supabase()
