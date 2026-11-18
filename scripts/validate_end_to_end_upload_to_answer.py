"""
Stage 5 Phase 3 Final Validation: Step 5
End-to-End Upload-to-Answer Pipeline Verification

Executes the complete end-to-end scientific research assistant workflow:
1. Upload & PDF Extraction (PyMuPDF / Stage 1-3 extraction)
2. Evidence Review & Structured Sample Entity Resolution (Stage 4)
3. Dynamic Indexing into Scientific Passage Index
4. Multi-Intent Routing & Subquery Retrieval
5. Dynamic Grounded Evidence Synthesis
6. Verified Citation Generation & Provenance Attribution
"""

import sys
import io
import json
import sqlite3
from pathlib import Path

# Ensure UTF-8 output encoding on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import fitz
from fastapi import UploadFile
from backend.main import extract_pdf
from copilot.engine import LMFPResearchCopilot
from copilot.index import get_passage_index
import literature.review_store as rs


def run_end_to_end_validation():
    print("=" * 80)
    print("STAGE 5 PHASE 3: END-TO-END UPLOAD-TO-ANSWER WORKFLOW VALIDATION")
    print("=" * 80)

    # 1. Synthesize a realistic peer-reviewed LMFP research paper PDF in-memory
    paper_title = "Novel Co-Precipitated LiMn0.72Fe0.24Mg0.04PO4/C Cathodes"
    paper_filename = "novel_lmfp_e2e_paper.pdf"
    paper_text = """
    Title: Novel Co-Precipitated LiMn0.72Fe0.24Mg0.04PO4/C Cathodes
    Abstract: In this work, high-performance LiMn0.72Fe0.24Mg0.04PO4/C was synthesized via co-precipitation.
    Galvanostatic testing showed discharge capacity of 158.4 mAh/g at 0.1 C and 94.6% capacity retention after 500 cycles.
    XRD confirmed orthorhombic olivine structure with space group Pnma.
    """

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), paper_text)
    pdf_bytes = doc.tobytes()
    doc.close()

    print(f"\n1. Ingesting & Extracting PDF: '{paper_filename}' ({len(pdf_bytes)} bytes)...")
    uf = UploadFile(filename=paper_filename, file=io.BytesIO(pdf_bytes))
    extraction_data = extract_pdf(uf)

    print(f"   Extraction Status: {extraction_data['status']}")
    print(f"   Candidate Pages: {extraction_data['candidate_pages_count']}")
    print(f"   Records Extracted: {extraction_data['records_extracted']}")
    print(f"   Saved Reviews Count: {extraction_data['saved_reviews_count']}")
    saved_ids = extraction_data.get("saved_review_ids", [])
    print(f"   Saved Review IDs: {saved_ids}")

    assert extraction_data["status"] in ("success", "partial_extraction")
    assert extraction_data["records_extracted"] >= 1
    review_id = saved_ids[0]

    # Verify review record in DB
    stored = rs.get_review(review_id)
    print(f"   Stored Composition: {stored.get('composition')}")
    print(f"   Stored Capacity (0.1C): {stored.get('extracted_data', {}).get('discharge_capacity_0_1c')} mAh/g")
    print(f"   Stored Retention: {stored.get('extracted_data', {}).get('capacity_retention_percent')}% ({stored.get('extracted_data', {}).get('retention_cycles')} cycles)")

    # 2. Re-index scientific literature passages to include this newly uploaded paper
    print("\n2. Updating Scientific Passage Index...")
    idx = get_passage_index()
    idx.build_index()
    print(f"   Total Indexed Passages: {len(idx.passages)}")

    # 3. Query the Copilot regarding this newly uploaded paper
    print("\n3. Testing Scientific Query Generation on Newly Uploaded Paper...")
    copilot = LMFPResearchCopilot()

    query1 = f"What is the 0.1C discharge capacity reported in {paper_filename}?"
    print(f"   Query 1: '{query1}'")
    res1 = copilot.chat(query1, force_deterministic=True)

    print(f"   Inference Source: {res1.inference_source}")
    print(f"   Direct Answer: {res1.direct_answer}")
    print(f"   Explanation: {res1.explanation[:200]}...")
    print(f"   Citations Count: {len(res1.citations)}")
    for cit in res1.citations[:2]:
        print(f"     - Paper: {cit.get('paper_id')}, Sample: {cit.get('sample_label')}, Quote: {cit.get('evidence_quote')[:80]}...")

    q1_text = f"{res1.direct_answer} {res1.explanation}".lower()
    q1_passed = (
        ("158.4" in q1_text or "158" in q1_text)
        and any("novel" in (c.get("paper_id") or "").lower() for c in res1.citations)
    )
    print(f"   Query 1 Verification: {'PASS' if q1_passed else 'FAIL'}")

    query2 = f"What synthesis route was confirmed for the material in {paper_filename}?"
    print(f"\n   Query 2: '{query2}'")
    res2 = copilot.chat(query2, force_deterministic=True)

    print(f"   Inference Source: {res2.inference_source}")
    print(f"   Direct Answer: {res2.direct_answer}")
    print(f"   Explanation: {res2.explanation[:200]}...")

    q2_text = f"{res2.direct_answer} {res2.explanation}".lower()
    q2_passed = (
        ("co-precipitation" in q2_text or "coprecipitation" in q2_text)
        and ("pnma" in q2_text or "olivine" in q2_text)
        and any("novel" in (c.get("paper_id") or "").lower() for c in res2.citations)
    )
    print(f"   Query 2 Verification: {'PASS' if q2_passed else 'FAIL'}")

    # 4. Clean up the test review record from review store
    print(f"\n4. Cleaning up temporary test review records for {paper_filename}...")
    try:
        conn = sqlite3.connect(rs.DB_PATH)
        cur = conn.cursor()
        tables = [t[0] for t in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        for t in tables:
            for col in ["source_pdf", "paper_id"]:
                try:
                    cur.execute(f"DELETE FROM {t} WHERE {col} LIKE '%novel%'")
                except Exception:
                    pass
        conn.commit()
        conn.close()
        print("   Temporary review and entity records cleaned up successfully.")
    except Exception as exc:
        print(f"   Cleanup warning: {exc}")

    # Re-index to restore clean state
    idx.build_index()

    e2e_passed = q1_passed and q2_passed
    print("\n" + "=" * 80)
    print(f"END-TO-END UPLOAD-TO-ANSWER WORKFLOW: {'PASSED (100%)' if e2e_passed else 'FAILED'}")
    print("=" * 80)

    # Save summary
    out_path = PROJECT_ROOT / "scripts" / "upload_to_answer_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "paper_filename": paper_filename,
            "extraction_status": extraction_data["status"],
            "records_extracted": extraction_data["records_extracted"],
            "query1": {
                "question": query1,
                "direct_answer": res1.direct_answer,
                "passed": q1_passed,
            },
            "query2": {
                "question": query2,
                "direct_answer": res2.direct_answer,
                "passed": q2_passed,
            },
            "overall_passed": e2e_passed,
        }, f, indent=2)


if __name__ == "__main__":
    run_end_to_end_validation()
