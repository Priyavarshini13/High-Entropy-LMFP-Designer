"""
ECMT AI — Existing Supabase Project Non-Destructive Inspection Script.

Performs READ-ONLY inspection of the existing 'HE-LMFP-Designer' Supabase project:
1. Lists all PostgreSQL tables, row counts, and column definitions.
2. Compares existing remote records with local SQLite (1 experiment, 37 reviews).
3. Inspects Supabase Storage buckets, privacy settings, and stored objects.
4. Generates a non-destructive delta report without modifying any data.
"""

import os
import sys
import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

LOCAL_EXP_DB = PROJECT_ROOT / "data" / "lab_experiments.db"
LOCAL_REV_DB = PROJECT_ROOT / "data" / "literature_review.db"


def inspect_supabase():
    print("=" * 75)
    print("ECMT AI — NON-DESTRUCTIVE SUPABASE PROJECT INSPECTION")
    print("Project Target: HE-LMFP-Designer (Resumed Existing Project)")
    print("=" * 75)

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("\n[INFO] DATABASE_URL is not set.")
        print("To inspect your resumed Supabase project, run:")
        print("  $env:DATABASE_URL='postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres?sslmode=require'")
        print("  $env:SUPABASE_URL='https://[ref].supabase.co'")
        print("  $env:SUPABASE_KEY='[anon-or-service-key]'")
        print("  python scripts/inspect_existing_supabase.py\n")
        return False

    if "sslmode" not in db_url:
        db_url += ("&" if "?" in db_url else "?") + "sslmode=require"

    print("\n[1/4] Connecting to existing Supabase PostgreSQL...")
    import psycopg2
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        print("      Connected successfully to Supabase PostgreSQL!")
    except Exception as exc:
        print(f"[ERROR] Failed to connect: {exc}")
        return False

    # 1. Query all tables in public schema
    print("\n[2/4] Querying existing tables, columns, and row counts...")
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name;
    """)
    tables = [r[0] for r in cur.fetchall()]
    print(f"      Found {len(tables)} table(s) in public schema: {tables}")

    db_summary = {}
    for tbl in tables:
        # Get row count
        cur.execute(f'SELECT COUNT(*) FROM "{tbl}"')
        count = cur.fetchone()[0]

        # Get column details
        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position;
        """, (tbl,))
        cols = cur.fetchall()
        db_summary[tbl] = {
            "row_count": count,
            "columns": [{"name": c[0], "type": c[1], "nullable": c[2]} for c in cols]
        }
        print(f"      • Table '{tbl}': {count} row(s)")
        col_names = [c[0] for c in cols]
        print(f"        Columns ({len(cols)}): {', '.join(col_names[:6])}{'...' if len(col_names) > 6 else ''}")

    # 2. Check lab_experiments specifically
    print("\n[3/4] Comparing existing Supabase records with local SQLite...")
    local_exp_count = 0
    local_exp_ids = set()
    if LOCAL_EXP_DB.exists():
        l_conn = sqlite3.connect(LOCAL_EXP_DB)
        l_cur = l_conn.cursor()
        l_cur.execute("SELECT experiment_id FROM lab_experiments")
        local_exp_ids = {r[0] for r in l_cur.fetchall()}
        local_exp_count = len(local_exp_ids)
        l_conn.close()

    remote_exp_ids = set()
    if "lab_experiments" in tables:
        cur.execute('SELECT experiment_id FROM "lab_experiments"')
        remote_exp_ids = {r[0] for r in cur.fetchall()}
        print(f"      Supabase 'lab_experiments': {len(remote_exp_ids)} record(s)")
        print(f"      Local SQLite 'lab_experiments': {local_exp_count} record(s)")
        common_exp = local_exp_ids.intersection(remote_exp_ids)
        missing_in_remote_exp = local_exp_ids - remote_exp_ids
        print(f"      • Matching existing records: {len(common_exp)} {list(common_exp)}")
        print(f"      • Local records not yet in Supabase: {len(missing_in_remote_exp)} {list(missing_in_remote_exp)}")
    else:
        print("      • Notice: Table 'lab_experiments' does NOT exist yet on Supabase.")

    # Check extraction_reviews specifically
    local_rev_count = 0
    if LOCAL_REV_DB.exists():
        r_conn = sqlite3.connect(LOCAL_REV_DB)
        r_cur = r_conn.cursor()
        r_cur.execute("SELECT count(*) FROM extraction_reviews")
        local_rev_count = r_cur.fetchone()[0]
        r_conn.close()

    if "extraction_reviews" in tables:
        cur.execute('SELECT COUNT(*) FROM "extraction_reviews"')
        remote_rev_count = cur.fetchone()[0]
        print(f"      Supabase 'extraction_reviews': {remote_rev_count} record(s)")
        print(f"      Local SQLite 'extraction_reviews': {local_rev_count} record(s)")
    else:
        print("      • Notice: Table 'extraction_reviews' does NOT exist yet on Supabase.")

    conn.close()

    # 3. Check Supabase Storage Buckets
    print("\n[4/4] Inspecting Supabase Storage Buckets...")
    supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
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
                    b_public = b.get("public")
                    print(f"      • Bucket '{b_id}': public={b_public}")

                    # List objects inside bucket
                    list_res = requests.post(
                        f"{supabase_url}/storage/v1/object/list/{b_id}",
                        headers={**headers, "Content-Type": "application/json"},
                        json={"prefix": "", "limit": 20},
                        timeout=5
                    )
                    if list_res.status_code == 200:
                        objs = list_res.json()
                        print(f"        Objects inside '{b_id}': {len(objs)} items")
                        for o in objs[:5]:
                            print(f"          - {o.get('name')} ({o.get('metadata', {}).get('size', 0)} bytes)")
            else:
                print(f"      Could not list storage buckets (HTTP {res.status_code}): {res.text}")
        except Exception as exc:
            print(f"      Storage inspection error: {exc}")
    else:
        print("      (SUPABASE_URL and SUPABASE_KEY not provided; skipping storage bucket API probe)")

    print("\n" + "=" * 75)
    print("INSPECTION COMPLETE (READ-ONLY): Zero data was modified.")
    print("=" * 75)
    return True


if __name__ == "__main__":
    inspect_supabase()
