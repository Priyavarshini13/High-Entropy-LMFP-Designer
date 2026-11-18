
import fitz
import pytest

from literature.pdf_extractor import extract_pdf_pages


def make_pdf_bytes(*page_texts):
    """Create a small in-memory PDF for testing."""
    document = fitz.open()

    for text in page_texts:
        page = document.new_page()
        page.insert_text((72, 72), text)

    pdf_bytes = document.tobytes()
    document.close()
    return pdf_bytes


def test_extracts_text_and_page_numbers():
    pdf_bytes = make_pdf_bytes(
        "LMFP cathode materials",
        "Discharge capacity: 150 mAh/g",
    )

    pages = extract_pdf_pages(pdf_bytes)

    assert len(pages) == 2
    assert pages[0]["page"] == 1
    assert "LMFP cathode materials" in pages[0]["text"]
    assert pages[1]["page"] == 2
    assert "150 mAh/g" in pages[1]["text"]


def test_rejects_empty_pdf_bytes():
    with pytest.raises(ValueError, match="uploaded PDF is empty"):
        extract_pdf_pages(b"")


def test_rejects_invalid_pdf():
    with pytest.raises(ValueError, match="Could not read this PDF"):
        extract_pdf_pages(b"this is not a PDF")


def test_rejects_pdf_without_selectable_text():
    pdf_bytes = make_pdf_bytes("")

    with pytest.raises(ValueError, match="No selectable text"):
        extract_pdf_pages(pdf_bytes)


def test_extracts_fe_first_formula_records():
    """Verify that formulas written with Fe first (e.g. LiFe0.6Mn0.4PO4) are properly parsed."""
    from literature.pdf_extractor import parse_text_lmfp_records
    from literature.composition_parser import parse_lmfp_composition

    text = (
        "Synthesis and characterization of a LiFe0.6Mn0.4PO4 olivine cathode. "
        "The prepared LiFe0.6Mn0.4PO4 delivered a discharge capacity of 130 mAh/g at C/10."
    )
    records = parse_text_lmfp_records(text, page_number=1)
    assert len(records) >= 1
    rec = records[0]
    assert rec["composition"] == "LiFe0.6Mn0.4PO4"

    # Check that composition parser correctly normalizes to IUPAC M2 site representation
    parsed = parse_lmfp_composition(rec["composition"])
    assert parsed.validation_status == "VALID"
    assert parsed.mn_fraction == 0.4
    assert parsed.fe_fraction == 0.6
    assert parsed.normalized_formula == "LiMn0.4Fe0.6PO4"
