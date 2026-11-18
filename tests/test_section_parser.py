"""Unit test suite for the publisher-independent document structure and section zoning engine.

Tests:
1. Heading classification across multiple publishers and naming styles.
2. Semantic categorization (experimental vs background vs excluded).
3. Table and figure caption isolation and ID extraction.
4. Running header and footer detection and suppression.
5. Multi-page document segmentation with section state persistence.
6. Negative control: reference section exclusion (no false records from citations).
7. Background mention preservation: prior literature in introductions tracked as context.
8. Graceful handling of documents with missing headings.
9. Corrigendum and erratum detection.
10. Section-aware integration with PDF literature extractor.
"""

import pytest
from literature.section_parser import (
    SectionType,
    SectionBlock,
    DocumentStructure,
    is_experimental_section,
    is_background_section,
    is_non_scientific_section,
    classify_heading,
    classify_table_or_figure,
    is_running_header_or_footer,
    segment_page_text,
    segment_document_pages,
)
from literature.pdf_extractor import extract_lmfp_records_from_pages


def test_heading_classification_across_publishers():
    """Verify heading recognition for major styles: Elsevier, ACS, Wiley, Springer, and Roman."""
    cases = [
        # Abstract
        ("Abstract", SectionType.ABSTRACT),
        ("Graphical Abstract", SectionType.ABSTRACT),
        ("ABSTRACT:", SectionType.ABSTRACT),
        # Introduction
        ("1. Introduction", SectionType.INTRODUCTION),
        ("I. INTRODUCTION", SectionType.INTRODUCTION),
        ("Introduction", SectionType.INTRODUCTION),
        ("Background and Literature Review", SectionType.INTRODUCTION),
        # Experimental
        ("2. Experimental Section", SectionType.EXPERIMENTAL),
        ("2. Materials and methods", SectionType.EXPERIMENTAL),
        ("II. EXPERIMENTAL PROCEDURES", SectionType.EXPERIMENTAL),
        ("Experimental Details", SectionType.EXPERIMENTAL),
        ("Methodology", SectionType.EXPERIMENTAL),
        ("Synthesis and Characterization", SectionType.EXPERIMENTAL),
        # Results and Discussion
        ("3. Results and discussion", SectionType.RESULTS_DISCUSSION),
        ("3. Results & Discussion", SectionType.RESULTS_DISCUSSION),
        ("III. RESULTS AND DISCUSSION", SectionType.RESULTS_DISCUSSION),
        ("Results and Analysis", SectionType.RESULTS_DISCUSSION),
        ("Electrochemical Performance", SectionType.RESULTS_DISCUSSION),
        # Conclusion
        ("4. Conclusions", SectionType.CONCLUSION),
        ("Conclusions and Outlook", SectionType.CONCLUSION),
        ("Summary and Concluding Remarks", SectionType.CONCLUSION),
        # References
        ("References", SectionType.REFERENCES),
        ("Bibliography", SectionType.REFERENCES),
        ("Literature Cited", SectionType.REFERENCES),
        ("5. References", SectionType.REFERENCES),
        # Acknowledgements
        ("Acknowledgements", SectionType.ACKNOWLEDGEMENTS),
        ("Acknowledgments", SectionType.ACKNOWLEDGEMENTS),
        ("Funding Information", SectionType.ACKNOWLEDGEMENTS),
        ("Author Contributions", SectionType.ACKNOWLEDGEMENTS),
        # Corrigendum
        ("Corrigendum to: High-rate LMFP", SectionType.CORRIGENDUM),
        ("Erratum", SectionType.CORRIGENDUM),
        ("Correction to: Synthesis of Olivine", SectionType.CORRIGENDUM),
    ]

    for heading_text, expected_type in cases:
        sec_type, label = classify_heading(heading_text)
        assert sec_type == expected_type, f"Failed for '{heading_text}': got {sec_type}, expected {expected_type}"
        assert label is not None


def test_semantic_role_categorization():
    """Verify semantic classification partitions sections into scientific vs non-scientific."""
    # Experimental evidence zones
    for st in [SectionType.EXPERIMENTAL, SectionType.RESULTS_DISCUSSION, SectionType.TABLE, SectionType.FIGURE_CAPTION]:
        assert is_experimental_section(st) is True
        assert is_background_section(st) is False
        assert is_non_scientific_section(st) is False

    # Background context zones
    for st in [SectionType.ABSTRACT, SectionType.INTRODUCTION, SectionType.CONCLUSION]:
        assert is_experimental_section(st) is False
        assert is_background_section(st) is True
        assert is_non_scientific_section(st) is False

    # Non-scientific / Excluded zones
    for st in [SectionType.REFERENCES, SectionType.ACKNOWLEDGEMENTS, SectionType.CORRIGENDUM, SectionType.UNKNOWN]:
        assert is_experimental_section(st) is False
        assert is_background_section(st) is False
        assert is_non_scientific_section(st) is True


def test_table_and_figure_caption_detection():
    """Verify table titles and figure captions are isolated with their IDs."""
    table_cases = [
        ("Table 1. Electrochemical performance summary of LMFP.", "Table 1"),
        ("Table 2: Comparison of rate capability for doped LMFP.", "Table 2"),
        ("TABLE I - Lattice parameters of samples.", "Table I"),
    ]
    for text, expected_id in table_cases:
        st, lbl, tid = classify_table_or_figure(text)
        assert st == SectionType.TABLE
        assert tid == expected_id

    fig_cases = [
        ("Fig. 1. XRD patterns of LiMn0.7Fe0.3PO4.", "Fig. 1"),
        ("Figure 2: Discharge curves at various C-rates.", "Figure 2"),
        ("Scheme 1 - Schematic illustration of solvothermal synthesis.", "Scheme 1"),
    ]
    for text, expected_id in fig_cases:
        st, lbl, fid = classify_table_or_figure(text)
        assert st == SectionType.FIGURE_CAPTION
        assert fid == expected_id


def test_running_header_footer_detection():
    """Verify journal running headers and pagination are detected and suppressed."""
    headers = [
        "Journal of Power Sources 450 (2023) 140000",
        "Electrochimica Acta 400 (2022) 139000",
        "Page 2 of 10",
        "1 / 8",
        "https://doi.org/10.1016/j.jpowsour.2023.140000",
        "2023 Elsevier B.V. All rights reserved.",
    ]
    for h in headers:
        assert is_running_header_or_footer(h, 2, 10) is True

    # Real scientific sentences must NOT be flagged as headers
    valid_sentences = [
        "LiMn0.7Fe0.3PO4 was synthesized via solvothermal route.",
        "The discharge capacity at 0.1C was 161.4 mAh/g.",
    ]
    for s in valid_sentences:
        assert is_running_header_or_footer(s, 2, 10) is False


def test_multi_page_document_segmentation():
    """Verify section flow across multiple pages with section state persistence."""
    pages = [
        {
            "page": 1,
            "text": (
                "Journal of Power Sources 500 (2023) 230100\n\n"
                "Abstract\n"
                "LiMn0.7Fe0.3PO4/C nanocomposites were prepared by a solvothermal method.\n\n"
                "1. Introduction\n"
                "Olivine LMFP cathodes have attracted significant attention due to 4.1 V plateau."
            ),
        },
        {
            "page": 2,
            "text": (
                "2. Experimental\n"
                "LiMn0.7Fe0.3PO4 was synthesized using solvothermal route at 180 C for 12 h.\n\n"
                "3. Results and discussion\n"
                "Fig. 1. XRD patterns of pristine and doped LMFP.\n"
                "The initial discharge capacity at 0.1C reached 161.4 mAh/g.\n"
                "Table 1. Rate capability of synthesized materials."
            ),
        },
        {
            "page": 3,
            "text": (
                "4. Conclusions\n"
                "In summary, solvothermal synthesis achieved high electrochemical performance.\n\n"
                "Acknowledgements\n"
                "This research was funded by grant ABC-123.\n\n"
                "References\n"
                "[1] A. Padhi et al., J. Electrochem. Soc. 144 (1997) 1188."
            ),
        },
    ]

    doc_struct = segment_document_pages(pages, "multi_page_test.pdf")

    assert "ABSTRACT" in doc_struct.detected_sections
    assert "INTRODUCTION" in doc_struct.detected_sections
    assert "EXPERIMENTAL" in doc_struct.detected_sections
    assert "RESULTS_DISCUSSION" in doc_struct.detected_sections
    assert "CONCLUSION" in doc_struct.detected_sections
    assert "REFERENCES" in doc_struct.detected_sections
    assert "TABLE" in doc_struct.detected_sections
    assert "FIGURE_CAPTION" in doc_struct.detected_sections

    exp_blocks = doc_struct.get_experimental_blocks()
    assert len(exp_blocks) >= 3  # Experimental text, Fig 1, Table 1

    excluded_blocks = doc_struct.get_excluded_blocks()
    assert any(b.section_type == SectionType.REFERENCES for b in excluded_blocks)
    assert any(b.section_type == SectionType.ACKNOWLEDGEMENTS for b in excluded_blocks)


def test_negative_control_reference_section_exclusion():
    """Verify that references mentioning LMFP formulas are never extracted as experimental records."""
    paper_with_refs = [
        {
            "page": 1,
            "text": (
                "2. Experimental\n"
                "LiMn0.7Fe0.3PO4/C composites were prepared by a sol-gel method.\n"
                "The discharge capacity at 0.1C was 161.4 mAh/g with 96.5% retention after 100 cycles at 1C [14].\n\n"
                "References\n"
                "[14] H. Chen, J. Power Sources 350 (2017) 120.\n"
                "[25] X. Wang, LiMn0.8Fe0.2PO4 cathode delivering 155 mAh/g, Electrochim. Acta 200 (2016) 45.\n"
                "[26] Y. Zhao, LiMn0.5Fe0.5PO4 nanorods with 165 mAh/g capacity, Nat. Commun. 8 (2017) 999."
            ),
        }
    ]

    extraction_res = extract_lmfp_records_from_pages(paper_with_refs, "paper_with_refs.pdf")

    # Primary synthesized sample from Experimental section must be extracted
    extracted_comps = [r["composition"] for r in extraction_res["records"]]
    assert "LiMn0.7Fe0.3PO4/C" in extracted_comps

    # Literature citations in References section (LiMn0.8Fe0.2PO4, LiMn0.5Fe0.5PO4) must NOT be extracted
    assert "LiMn0.8Fe0.2PO4" not in extracted_comps
    assert "LiMn0.5Fe0.5PO4" not in extracted_comps


def test_background_mention_preservation():
    """Verify that prior literature in Introduction is preserved as background evidence, not experimental samples."""
    paper_with_intro = [
        {
            "page": 1,
            "text": (
                "1. Introduction\n"
                "Previously, LiMn0.8Fe0.2PO4 was reported by Wang [15] to reach 150 mAh/g at 0.1C.\n\n"
                "2. Experimental\n"
                "In this work, LiMn0.7Fe0.3PO4/C composites were prepared by a sol-gel method.\n"
                "The discharge capacity at 0.1C was 161.4 mAh/g with 96.5% retention after 100 cycles at 1C [14]."
            ),
        }
    ]

    extraction_res = extract_lmfp_records_from_pages(paper_with_intro, "paper_with_intro.pdf")

    # Experimental sample created only for the paper's actual synthesis
    assert len(extraction_res["records"]) == 1
    assert extraction_res["records"][0]["composition"] == "LiMn0.7Fe0.3PO4/C"
    assert extraction_res["records"][0]["is_experimental"] is True

    # Introduction mention preserved under background_mentions
    bg_comps = [m["composition"] for m in extraction_res.get("background_mentions", [])]
    assert any("LiMn0.8Fe0.2PO4" in c for c in bg_comps)


def test_missing_headings_graceful_handling():
    """Verify documents with missing headings do not crash and extract available data."""
    text_without_headings = [
        {
            "page": 1,
            "text": (
                "LiMn0.75Fe0.25PO4/C cathode material was prepared by sol-gel method.\n"
                "The initial discharge capacity was 162.5 mAh/g at 0.1C and 142.0 mAh/g at 1C.\n"
                "Capacity retention was 95.2% after 200 cycles at 1C [42]."
            ),
        }
    ]

    extraction_res = extract_lmfp_records_from_pages(text_without_headings, "no_headings.pdf")
    assert extraction_res["status"] == "success"
    assert len(extraction_res["records"]) == 1
    assert extraction_res["records"][0]["composition"] == "LiMn0.75Fe0.25PO4/C"


def test_corrigendum_detection():
    """Verify papers that are corrigenda/errata are classified accordingly."""
    corrigendum_text = (
        "Corrigendum to: High-rate LiMn0.7Fe0.3PO4/C cathode materials\n\n"
        "The authors regret that an incorrect discharge capacity was printed."
    )
    blocks, sec, lbl = segment_page_text(corrigendum_text, 1)
    assert any(b.section_type == SectionType.CORRIGENDUM for b in blocks)
