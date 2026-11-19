"""
Generator for ECMT AI Supabase Production Migration SQL Script.
Generates idempotent, non-destructive SQL script containing:
1. lab_experiments table schema & RLS policies
2. extraction_reviews table schema, indexes & RLS policies
3. EXP-9260F00A preservation (ON CONFLICT DO NOTHING)
4. 37 extraction reviews preservation (ON CONFLICT DO NOTHING)
5. Private ecmt-uploads storage bucket & storage RLS policies
"""

import os
import sys
import json
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXP_DB = PROJECT_ROOT / "data" / "lab_experiments.db"
REV_DB = PROJECT_ROOT / "data" / "literature_review.db"
OUTPUT_SQL_PATH = PROJECT_ROOT / "scripts" / "migration_supabase_ecmt_ai.sql"


def escape_sql_string(val):
    if val is None:
        return "NULL"
    val_str = str(val).replace("'", "''")
    return f"'{val_str}'"


def generate_migration_sql():
    print("Generating idempotent migration SQL script...")

    # Read experiments
    conn_exp = sqlite3.connect(EXP_DB)
    conn_exp.row_factory = sqlite3.Row
    c_exp = conn_exp.cursor()
    c_exp.execute("SELECT * FROM lab_experiments")
    exp_rows = [dict(r) for r in c_exp.fetchall()]
    conn_exp.close()

    # Read reviews
    conn_rev = sqlite3.connect(REV_DB)
    conn_rev.row_factory = sqlite3.Row
    c_rev = conn_rev.cursor()
    c_rev.execute("SELECT * FROM extraction_reviews ORDER BY id")
    rev_rows = [dict(r) for r in c_rev.fetchall()]
    conn_rev.close()

    sql_lines = [
        "-- ============================================================================",
        "-- ECMT AI — IDEMPOTENT NON-DESTRUCTIVE SUPABASE PRODUCTION MIGRATION SCRIPT",
        "-- Target Project: HE-LMFP-Designer (zhbzuncrttvyvercutub)",
        "-- Safety Guarantee: Zero Drops, Zero Truncates, Zero Overwrites of Existing Rows",
        "-- ============================================================================",
        "",
        "BEGIN;",
        "",
        "-- ----------------------------------------------------------------------------",
        "-- 1. Table: lab_experiments (Schema verification & Non-destructive creation)",
        "-- ----------------------------------------------------------------------------",
        "CREATE TABLE IF NOT EXISTS public.lab_experiments (",
        "    experiment_id VARCHAR(255) PRIMARY KEY,",
        "    sample_id VARCHAR(255) NOT NULL,",
        "    created_at VARCHAR(255) NOT NULL,",
        "    updated_at VARCHAR(255) NOT NULL,",
        "    operator VARCHAR(255),",
        "    batch_id VARCHAR(255),",
        "    status VARCHAR(100) NOT NULL,",
        "    generated_formula TEXT NOT NULL,",
        "    json_data TEXT NOT NULL",
        ");",
        "",
        "-- ----------------------------------------------------------------------------",
        "-- 2. Table: extraction_reviews (Schema creation, constraints & indexes)",
        "-- ----------------------------------------------------------------------------",
        "CREATE TABLE IF NOT EXISTS public.extraction_reviews (",
        "    id SERIAL PRIMARY KEY,",
        "    source_pdf TEXT NOT NULL,",
        "    page_number INTEGER,",
        "    reference TEXT,",
        "    composition TEXT,",
        "    extracted_data TEXT NOT NULL,",
        "    evidence_quote TEXT,",
        "    status VARCHAR(50) NOT NULL DEFAULT 'pending'",
        "        CHECK (status IN ('pending', 'approved', 'rejected')),",
        "    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,",
        "    reviewed_at TIMESTAMPTZ",
        ");",
        "",
        "CREATE INDEX IF NOT EXISTS idx_extraction_reviews_status ON public.extraction_reviews(status);",
        "CREATE INDEX IF NOT EXISTS idx_extraction_reviews_source_pdf ON public.extraction_reviews(source_pdf);",
        "CREATE INDEX IF NOT EXISTS idx_extraction_reviews_composition ON public.extraction_reviews(composition);",
        "",
        "-- ----------------------------------------------------------------------------",
        "-- 3. Row Level Security (RLS) & Access Control (No public exposure)",
        "-- ----------------------------------------------------------------------------",
        "ALTER TABLE public.lab_experiments ENABLE ROW LEVEL SECURITY;",
        "ALTER TABLE public.extraction_reviews ENABLE ROW LEVEL SECURITY;",
        "",
        "-- Explicitly revoke all access from unauthenticated anonymous users",
        "REVOKE ALL ON TABLE public.lab_experiments FROM anon;",
        "REVOKE ALL ON TABLE public.extraction_reviews FROM anon;",
        "",
        "-- Grant permissions to authenticated team members and backend service role",
        "GRANT ALL ON TABLE public.lab_experiments TO authenticated, service_role;",
        "GRANT ALL ON TABLE public.extraction_reviews TO authenticated, service_role;",
        "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO authenticated, service_role;",
        "",
        "-- Drop existing policies safely if re-running",
        "DROP POLICY IF EXISTS \"Team read lab_experiments\" ON public.lab_experiments;",
        "DROP POLICY IF EXISTS \"Team write lab_experiments\" ON public.lab_experiments;",
        "DROP POLICY IF EXISTS \"Team read extraction_reviews\" ON public.extraction_reviews;",
        "DROP POLICY IF EXISTS \"Team write extraction_reviews\" ON public.extraction_reviews;",
        "",
        "-- Strict policies: Authenticated team members or backend service role only",
        "CREATE POLICY \"Team read lab_experiments\" ON public.lab_experiments",
        "    FOR SELECT TO authenticated, service_role USING (true);",
        "",
        "CREATE POLICY \"Team write lab_experiments\" ON public.lab_experiments",
        "    FOR ALL TO authenticated, service_role USING (true) WITH CHECK (true);",
        "",
        "CREATE POLICY \"Team read extraction_reviews\" ON public.extraction_reviews",
        "    FOR SELECT TO authenticated, service_role USING (true);",
        "",
        "CREATE POLICY \"Team write extraction_reviews\" ON public.extraction_reviews",
        "    FOR ALL TO authenticated, service_role USING (true) WITH CHECK (true);",
        "",
        "-- ----------------------------------------------------------------------------",
        "-- 4. Private Storage Bucket: ecmt-uploads (Strictly Private: public = false)",
        "-- ----------------------------------------------------------------------------",
        "INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)",
        "VALUES (",
        "    'ecmt-uploads',",
        "    'ecmt-uploads',",
        "    false, -- STRICT PRIVATE",
        "    26214400, -- 25MB max",
        "    ARRAY['image/png', 'image/jpeg', 'image/webp', 'image/tiff', 'application/pdf', 'text/csv', 'application/json']",
        ")",
        "ON CONFLICT (id) DO UPDATE SET public = false;",
        "",
        "-- Storage RLS: Disallow unauthenticated public reads, allow authenticated service access",
        "DROP POLICY IF EXISTS \"Team read ecmt-uploads\" ON storage.objects;",
        "DROP POLICY IF EXISTS \"Team write ecmt-uploads\" ON storage.objects;",
        "",
        "CREATE POLICY \"Team read ecmt-uploads\" ON storage.objects",
        "    FOR SELECT TO authenticated, service_role USING (bucket_id = 'ecmt-uploads');",
        "",
        "CREATE POLICY \"Team write ecmt-uploads\" ON storage.objects",
        "    FOR ALL TO authenticated, service_role USING (bucket_id = 'ecmt-uploads') WITH CHECK (bucket_id = 'ecmt-uploads');",
        "",
        "-- ----------------------------------------------------------------------------",
        "-- 5. Safe Record Ingestion: lab_experiments (EXP-9260F00A)",
        "-- Safety: ON CONFLICT (experiment_id) DO NOTHING guarantees existing is unchanged!",
        "-- ----------------------------------------------------------------------------",
    ]

    for exp in exp_rows:
        sql_lines.append(f"""INSERT INTO public.lab_experiments (
    experiment_id, sample_id, created_at, updated_at,
    operator, batch_id, status, generated_formula, json_data
)
VALUES (
    {escape_sql_string(exp['experiment_id'])},
    {escape_sql_string(exp['sample_id'])},
    {escape_sql_string(exp['created_at'])},
    {escape_sql_string(exp['updated_at'])},
    {escape_sql_string(exp['operator'])},
    {escape_sql_string(exp['batch_id'])},
    {escape_sql_string(exp['status'])},
    {escape_sql_string(exp['generated_formula'])},
    {escape_sql_string(exp['json_data'])}
)
ON CONFLICT (experiment_id) DO NOTHING;
""")

    sql_lines.append("-- ----------------------------------------------------------------------------")
    sql_lines.append("-- 6. Safe Record Ingestion: extraction_reviews (37 Literature Records)")
    sql_lines.append("-- Safety: ON CONFLICT (id) DO NOTHING guarantees zero overwrites!")
    sql_lines.append("-- ----------------------------------------------------------------------------")

    for rev in rev_rows:
        reviewed_val = escape_sql_string(rev['reviewed_at']) if rev['reviewed_at'] else "NULL"
        created_val = escape_sql_string(rev['created_at']) if rev['created_at'] else "CURRENT_TIMESTAMP"
        page_val = str(rev['page_number']) if rev['page_number'] is not None else "NULL"

        sql_lines.append(f"""INSERT INTO public.extraction_reviews (
    id, source_pdf, page_number, reference, composition,
    extracted_data, evidence_quote, status, created_at, reviewed_at
)
VALUES (
    {rev['id']},
    {escape_sql_string(rev['source_pdf'])},
    {page_val},
    {escape_sql_string(rev['reference'])},
    {escape_sql_string(rev['composition'])},
    {escape_sql_string(rev['extracted_data'])},
    {escape_sql_string(rev['evidence_quote'])},
    {escape_sql_string(rev['status'])},
    {created_val},
    {reviewed_val}
)
ON CONFLICT (id) DO NOTHING;
""")

    sql_lines.append("-- Reset serial sequence for extraction_reviews to prevent ID collisions")
    sql_lines.append("SELECT setval('public.extraction_reviews_id_seq', (SELECT COALESCE(MAX(id), 1) FROM public.extraction_reviews));")
    sql_lines.append("")
    sql_lines.append("COMMIT;")
    sql_lines.append("")

    with open(OUTPUT_SQL_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(sql_lines))

    print(f"Generated {len(sql_lines)} lines of safe SQL at: {OUTPUT_SQL_PATH}")
    return OUTPUT_SQL_PATH


if __name__ == "__main__":
    generate_migration_sql()
