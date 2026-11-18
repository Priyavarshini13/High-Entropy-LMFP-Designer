import sqlite3
import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with sqlite3.connect("data/literature_review.db") as conn:
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT id, source_pdf, page_number, composition, evidence_quote, status, extracted_data
        FROM extraction_reviews
        WHERE id >= 100000
        ORDER BY id ASC
    """).fetchall()

    print(f"Total newly staged reviews: {len(rows)}")
    by_pdf = {}
    for r in rows:
        pdf = r["source_pdf"]
        by_pdf.setdefault(pdf, []).append(r)

    for pdf, items in by_pdf.items():
        print(f"\n=======================================================")
        print(f"Paper: {pdf} ({len(items)} staged reviews)")
        print(f"=======================================================")
        for r in items[:4]:
            ext = json.loads(r["extracted_data"]) if r["extracted_data"] else {}
            quote = (r["evidence_quote"] or "")[:120].replace("\n", " ")
            print(f"  ID {r['id']} | Page {r['page_number']} | Status: {r['status']}")
            print(f"    Composition: {r['composition']}")
            print(f"    Quote: \"{quote}\"")
            print(f"    Extracted: {ext}")
