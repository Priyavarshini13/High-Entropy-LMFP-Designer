"""Automated verification suite for the PDF literature upload-to-review workflow.

Tests:
1. Valid PDF with structured doping table.
2. Valid PDF with narrative text LMFP records.
3. Invalid file type (.docx).
4. Empty PDF (0 bytes).
5. Corrupted / unreadable PDF bytes.
6. Scanned PDF (no selectable text).
7. PDF with no LMFP content (status: no_records_found).
8. Partial extraction with missing fields.
9. Review queue de-duplication on re-upload.
10. Master CSV preservation (1,215 rows x 41 columns unchanged).
"""

import io
import fitz
import pandas as pd
import pytest
from fastapi import HTTPException, UploadFile

from backend.main import extract_pdf
import literature.review_store as rs


def _build_pdf_bytes(pages_text: list[str]) -> bytes:
    """Create an in-memory PDF from a list of page strings."""
    doc = fitz.open()
    for text in pages_text:
        page = doc.new_page()
        page.insert_text((50, 50), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.fixture
def isolated_review_db(tmp_path, monkeypatch):
    """Isolate review database so tests never touch production literature_review.db."""
    test_db = tmp_path / "test_literature_review.db"
    monkeypatch.setattr(rs, "DB_PATH", test_db)
    rs.init_review_db()
    return test_db


def test_reject_invalid_file_extension(isolated_review_db):
    """Non-PDF files must be rejected with HTTP 400."""
    uf = UploadFile(filename="test_paper.docx", file=io.BytesIO(b"word-content"))
    with pytest.raises(HTTPException) as exc_info:
        extract_pdf(uf)
    assert exc_info.value.status_code == 400
    assert "Only PDF files are supported" in exc_info.value.detail


def test_reject_empty_pdf(isolated_review_db):
    """Empty 0-byte PDF uploads must be rejected with HTTP 400."""
    uf = UploadFile(filename="empty.pdf", file=io.BytesIO(b""))
    with pytest.raises(HTTPException) as exc_info:
        extract_pdf(uf)
    assert exc_info.value.status_code == 400
    assert "empty" in exc_info.value.detail.lower()


def test_reject_corrupted_pdf(isolated_review_db):
    """Corrupted PDF binary files must be rejected with HTTP 400."""
    uf = UploadFile(filename="corrupted.pdf", file=io.BytesIO(b"%PDF-corrupted-random-binary-bytes"))
    with pytest.raises(HTTPException) as exc_info:
        extract_pdf(uf)
    assert exc_info.value.status_code == 400
    assert "Failed to read PDF" in exc_info.value.detail


def test_reject_scanned_pdf_no_selectable_text(isolated_review_db):
    """PDFs with no selectable text must trigger clear OCR guidance."""
    doc = fitz.open()
    doc.new_page()
    pdf_bytes = doc.tobytes()
    doc.close()

    uf = UploadFile(filename="scanned.pdf", file=io.BytesIO(pdf_bytes))
    with pytest.raises(HTTPException) as exc_info:
        extract_pdf(uf)
    assert exc_info.value.status_code == 400
    assert "No selectable text was found" in exc_info.value.detail


def test_pdf_with_no_lmfp_records(isolated_review_db):
    """PDFs with text but no LMFP content must return no_records_found with guidance."""
    pdf_bytes = _build_pdf_bytes([
        "This paper discusses the optical properties of silicon solar cells.",
        "Measurements were performed at room temperature under AM1.5 illumination."
    ])

    uf = UploadFile(filename="silicon_solar.pdf", file=io.BytesIO(pdf_bytes))
    data = extract_pdf(uf)
    assert data["status"] == "no_records_found"
    assert data["records_extracted"] == 0
    assert data["saved_reviews_count"] == 0
    assert len(data["warnings"]) > 0
    assert "suggested_next_action" in data
    assert len(data["suggested_next_action"]) > 0


def test_valid_pdf_with_text_extraction(isolated_review_db):
    """Valid PDF with narrative LMFP text must extract records and stage to review queue."""
    paper_text = """
    In this research, LiMn0.75Fe0.25PO4/C composites were prepared by a sol-gel method.
    The discharge capacity reached 162.8 mAh/g at 0.1 C, and 143.5 mAh/g at 1 C.
    Capacity retention was 96.2% after 200 cycles at 1 C rate [31].
    """
    pdf_bytes = _build_pdf_bytes([paper_text])

    uf = UploadFile(filename="lmfp_solgel_paper.pdf", file=io.BytesIO(pdf_bytes))
    data = extract_pdf(uf)

    assert data["status"] == "success"
    assert data["filename"] == "lmfp_solgel_paper.pdf"
    assert data["total_pages"] == 1
    assert data["pages_with_text"] == 1
    assert data["records_extracted"] == 1
    assert data["saved_reviews_count"] == 1
    assert len(data["saved_review_ids"]) == 1

    review_summary = data["saved_reviews"][0]
    assert review_summary["composition"] == "LiMn0.75Fe0.25PO4/C"
    assert review_summary["status"] == "pending"
    assert review_summary["is_new"] is True

    # Check that isolated database actually holds this record
    stored = rs.get_review(review_summary["id"])
    assert stored is not None
    assert stored["composition"] == "LiMn0.75Fe0.25PO4/C"
    assert stored["extracted_data"]["discharge_capacity_0_1c"] == 162.8
    assert stored["extracted_data"]["capacity_retention_percent"] == 96.2
    assert stored["extracted_data"]["retention_cycles"] == 200
    assert stored["extracted_data"]["reference"] == "[31]"
    assert stored["status"] == "pending"


def test_valid_pdf_with_doping_table(isolated_review_db):
    """Valid PDF containing LMFP doping table must parse structured records and stage them."""
    table_page = (
        "Methods of element doping of LMFP\n"
        "2023\n"
        "LiMn0.5Fe0.5PO4\n"
        "Solvothermal method\n"
        "CTAB, TAA\n"
        "N/S\n"
        "166.8 (0.1 C), 118.9 (5 C)\n"
        "100.0% (100 cycles, 1 C), 92.0% (1000 cycles, 5 C)\n"
        "-\n"
        "2.5-4.5\n"
        "[79]\n"
    )
    pdf_bytes = _build_pdf_bytes([table_page])

    uf = UploadFile(filename="lmfp_review_table.pdf", file=io.BytesIO(pdf_bytes))
    data = extract_pdf(uf)

    assert data["records_extracted"] >= 1
    assert data["saved_reviews_count"] >= 1
    assert any("LiMn0.5Fe0.5PO4" in r["composition"] for r in data["saved_reviews"])


def test_partial_extraction_identifies_missing_fields(isolated_review_db):
    """Partial extractions must be flagged as partial_extraction with explanatory warnings."""
    paper_text = """
    LiMn0.8Fe0.2PO4 cathode material delivered 158.0 mAh/g at 0.1 C.
    """
    pdf_bytes = _build_pdf_bytes([paper_text])

    uf = UploadFile(filename="partial_lmfp.pdf", file=io.BytesIO(pdf_bytes))
    data = extract_pdf(uf)

    assert data["status"] == "partial_extraction"
    assert data["records_extracted"] == 1
    assert len(data["warnings"]) > 0
    assert "missing" in data["warnings"][0].lower()


def test_reupload_does_not_duplicate_reviews(isolated_review_db):
    """Re-uploading the same PDF must reuse existing review records instead of duplicating them."""
    paper_text = """
    LiMn0.7Fe0.3PO4/C composites were prepared by sol-gel method.
    Discharge capacity was 161.0 mAh/g at 0.1 C and 95.0% retention after 100 cycles at 1 C [18].
    """
    pdf_bytes = _build_pdf_bytes([paper_text])

    # First upload
    uf1 = UploadFile(filename="reupload_test.pdf", file=io.BytesIO(pdf_bytes))
    d1 = extract_pdf(uf1)
    first_id = d1["saved_review_ids"][0]
    assert d1["saved_reviews"][0]["is_new"] is True

    # Second upload with identical file name and content
    uf2 = UploadFile(filename="reupload_test.pdf", file=io.BytesIO(pdf_bytes))
    d2 = extract_pdf(uf2)
    assert d2["saved_review_ids"][0] == first_id
    assert d2["saved_reviews"][0]["is_new"] is False

    # Verify database total count is still 1
    all_reviews = rs.list_reviews()
    assert len(all_reviews) == 1


def test_master_csv_remains_strictly_untouched(isolated_review_db):
    """The master CSV dataset must remain at exactly 1,215 rows and 41 columns."""
    from backend.main import CSV_PATH

    df = pd.read_csv(CSV_PATH)
    assert df.shape == (1215, 41), f"Expected (1215, 41), got {df.shape}"


def test_upload_invokes_stage3_and_persists_structured_properties(isolated_review_db):
    """Verify PDF upload invokes Stage 3 property extractor and persists structured measurements."""
    p1 = (
        "Abstract\n"
        "LiMn0.8Fe0.2PO4/C demonstrated extraordinary stability with 94.5% capacity retention after 1,000 cycles at 1 C [12]."
    )
    p2 = (
        "2. Experimental Methods\n"
        "The LiMn0.8Fe0.2PO4 was synthesized via solid-state reaction and calcined at 700 °C for 8 h in an Ar/H2 atmosphere."
    )
    p3 = (
        "3. Results and Discussion\n"
        "XRD refinement confirmed olivine structure with space group Pnma. "
        "Galvanostatic testing between 2.5 and 4.5 V yielded discharge capacities of 164.0 mAh/g at 0.1 C and 142.5 mAh/g at 1 C."
    )
    pdf_bytes = _build_pdf_bytes([p1, p2, p3])

    uf = UploadFile(filename="stage3_integrated_test.pdf", file=io.BytesIO(pdf_bytes))
    res = extract_pdf(uf)

    # 1. Check API response includes Stage 3 outputs
    assert "structured_measurements" in res
    assert len(res["structured_measurements"]) >= 2
    assert "property_summary" in res
    assert res["property_summary"]["total_measurements"] >= 2

    # 2. Check synthesis profile was extracted
    assert len(res["synthesis_profiles"]) >= 1
    synth = res["synthesis_profiles"][0]
    assert synth["route"] == "Solid-state"
    assert synth["calcination_temperature_c"] == 700.0
    assert synth["atmosphere"] == "Ar/H2"

    # 3. Check characterization profile was extracted
    assert len(res["characterization_profiles"]) >= 1
    char = res["characterization_profiles"][0]
    assert char["space_group"] == "Pnma"

    # 4. Check review records staged in database
    staged_reviews = rs.list_reviews()
    assert len(staged_reviews) >= 1
    sample_rec = staged_reviews[0]
    assert "structured_measurements" in sample_rec["extracted_data"]
    assert sample_rec["extracted_data"]["structured_measurements"] is not None
    assert len(sample_rec["extracted_data"]["structured_measurements"]) >= 1
    assert sample_rec["status"] == "pending"

