"""
Scientific Correctness and Entity Retrieval Tests (Stage 5, Phase 1).

Tests the 10 mandated scientific scenarios:
1. Compare SD_NO3 and SD_SO4 (preserving separate sample identities).
2. Find LMFP samples with measurements at 5C.
3. Find LMFP samples with measurements at 10C.
4. Find samples with carbon coatings.
5. Compare rGO-modified and unmodified LMFP.
6. Find Ni-doped LMFP samples.
7. Find samples synthesized using sulfate precursors.
8. Find samples synthesized using nitrate precursors.
9. Compare measurements only under equivalent C-rate conditions.
10. Find samples with unresolved experimental identity.
"""

import pytest
from copilot.index import ScientificPassageIndex
from copilot.retriever import HybridRetriever, compute_sample_dedup_key


@pytest.fixture(scope="module")
def hybrid_retriever():
    """Shared index and retriever fixture."""
    index = ScientificPassageIndex()
    index.build_index()
    return HybridRetriever(index=index)


def test_scenario_1_compare_sd_no3_and_sd_so4_separation(hybrid_retriever):
    """Scenario 1: SD_NO3 and SD_SO4 must remain separate even with identical nominal formulas."""
    matches = hybrid_retriever.retrieve(
        "What are the discharge capacities of SD_NO3 and SD_SO4 in srep26686 at 0.05 C?",
        top_k=6,
    )
    assert len(matches) >= 2

    # Collect retrieved sample labels and IDs
    sample_labels = [m.passage.sample_label for m in matches if m.passage.sample_label]
    sample_ids = [m.passage.sample_id for m in matches if m.passage.sample_id]

    assert "SD_NO3" in sample_labels, f"SD_NO3 missing from top matches: {sample_labels}"
    assert "SD_SO4" in sample_labels, f"SD_SO4 missing from top matches: {sample_labels}"

    # Verify distinct sample IDs
    assert "srep26686_SD_NO3" in sample_ids
    assert "srep26686_SD_SO4" in sample_ids

    # Find the matches for SD_NO3 and SD_SO4
    m_no3 = next(m for m in matches if m.passage.sample_id == "srep26686_SD_NO3")
    m_so4 = next(m for m in matches if m.passage.sample_id == "srep26686_SD_SO4")

    # Verify deduplication keys are distinct
    key_no3 = compute_sample_dedup_key(m_no3.passage)
    key_so4 = compute_sample_dedup_key(m_so4.passage)
    assert key_no3 != key_so4

    # Verify precursor salts and measurements remain isolated
    no3_precursors = m_no3.passage.structured_data.get("precursor_salts", [])
    so4_precursors = m_so4.passage.structured_data.get("precursor_salts", [])
    assert any("no3" in str(p).lower() for p in no3_precursors)
    assert any("so4" in str(p).lower() for p in so4_precursors)

    assert m_no3.passage.structured_data.get("discharge_capacity_0_05c") == 45.0
    assert m_so4.passage.structured_data.get("discharge_capacity_0_05c") == 114.0


def test_scenario_2_samples_with_measurements_at_5c(hybrid_retriever):
    """Scenario 2: Find LMFP samples with measurements at 5C."""
    matches = hybrid_retriever.retrieve("Find LMFP samples with measurements at 5C", top_k=6)
    assert len(matches) > 0

    has_5c = any(
        m.passage.structured_data.get("discharge_capacity_5c") is not None
        or m.passage.structured_data.get("discharge_capacity_5_0c") is not None
        or m.passage.structured_data.get("retention_crate") == 5.0
        for m in matches
    )
    assert has_5c, "Expected at least one sample with verified 5C measurement"


def test_scenario_3_samples_with_measurements_at_10c(hybrid_retriever):
    """Scenario 3: Find LMFP samples with measurements at 10C."""
    matches = hybrid_retriever.retrieve("Find LMFP samples with measurements at 10C", top_k=6)
    assert len(matches) > 0

    has_10c = any(
        m.passage.structured_data.get("discharge_capacity_10c") is not None
        or m.passage.structured_data.get("discharge_capacity_10_0c") is not None
        or m.passage.structured_data.get("retention_crate") == 10.0
        or "10 c" in m.passage.text.lower()
        or "10c" in m.passage.text.lower()
        for m in matches
    )
    assert has_10c, "Expected at least one sample with verified 10C high-rate measurement"


def test_scenario_4_samples_with_carbon_coatings(hybrid_retriever):
    """Scenario 4: Find samples with carbon coatings."""
    matches = hybrid_retriever.retrieve("Find samples with carbon coatings", top_k=6)
    assert len(matches) > 0

    has_carbon = any(
        "/c" in (m.passage.composition or "").lower()
        or "carbon" in m.passage.text.lower()
        or m.passage.structured_data.get("carbon_wt_percent") is not None
        or m.passage.structured_data.get("modifications")
        for m in matches
    )
    assert has_carbon, "Expected carbon coated cathode samples"


def test_scenario_5_compare_rgo_modified_and_unmodified_lmfp(hybrid_retriever):
    """Scenario 5: Compare rGO-modified and unmodified LMFP in srep26686."""
    matches = hybrid_retriever.retrieve("Compare rGO-modified and unmodified LMFP in srep26686", top_k=6)
    assert len(matches) >= 2

    # Must contain both the rGO composite and a non-rGO control
    has_rgo = any("rgo" in (m.passage.sample_label or "").lower() or "rgo" in (m.passage.sample_id or "").lower() for m in matches)
    has_control = any(m.passage.sample_label in {"SD_SO4", "SD_NO3", "LiMn0.75Fe0.25PO4"} for m in matches)

    assert has_rgo, "Expected rGO composite sample in retrieval"
    assert has_control, "Expected unmodified/control sample in retrieval"


def test_scenario_6_ni_doped_lmfp_samples(hybrid_retriever):
    """Scenario 6: Find Ni-doped LMFP samples."""
    matches = hybrid_retriever.retrieve("Find Ni-doped LMFP samples", top_k=6)
    assert len(matches) > 0

    top_m = matches[0]
    assert "ni" in str(top_m.passage.structured_data.get("dopant", "")).lower() or "ni" in (top_m.passage.composition or "").lower()
    assert top_m.passage.provenance_type in {"SECONDARY_REVIEW", "DATASET_ROW", "PRIMARY_PAPER"}


def test_scenario_7_sulfate_precursors(hybrid_retriever):
    """Scenario 7: Find samples synthesized using sulfate precursors."""
    matches = hybrid_retriever.retrieve("Find samples synthesized using sulfate precursors", top_k=6)
    assert len(matches) > 0

    has_sulfate = any(
        "sd_so4" in (m.passage.sample_id or "").lower()
        or any("so4" in str(p).lower() or "sulfate" in str(p).lower() for p in (m.passage.structured_data.get("precursor_salts") or []))
        or "sulfate" in m.passage.text.lower()
        for m in matches
    )
    assert has_sulfate, "Expected sulfate-derived LMFP sample"


def test_scenario_8_nitrate_precursors(hybrid_retriever):
    """Scenario 8: Find samples synthesized using nitrate precursors."""
    matches = hybrid_retriever.retrieve("Find samples synthesized using nitrate precursors", top_k=6)
    assert len(matches) > 0

    has_nitrate = any(
        "sd_no3" in (m.passage.sample_id or "").lower()
        or any("no3" in str(p).lower() or "nitrate" in str(p).lower() for p in (m.passage.structured_data.get("precursor_salts") or []))
        or "nitrate" in m.passage.text.lower()
        for m in matches
    )
    assert has_nitrate, "Expected nitrate-derived LMFP sample"


def test_scenario_9_compare_under_equivalent_c_rates(hybrid_retriever):
    """Scenario 9: Compare measurements only under equivalent 0.1C rate conditions."""
    matches = hybrid_retriever.retrieve("Compare discharge capacities under equivalent 0.1C conditions", top_k=6)
    assert len(matches) >= 2

    # At least two matches must have valid 0.1C capacity values
    cap_01_count = sum(
        1 for m in matches
        if m.passage.structured_data.get("discharge_capacity_0_1c") is not None
        or "0.1 c" in m.passage.text.lower()
        or "0.1c" in m.passage.text.lower()
    )
    assert cap_01_count >= 2, f"Expected at least 2 samples with 0.1C measurements, found {cap_01_count}"


def test_scenario_10_unresolved_experimental_identity(hybrid_retriever):
    """Scenario 10: Find samples with unresolved experimental identity."""
    matches = hybrid_retriever.retrieve("Find samples with unresolved experimental identity", top_k=6)
    assert len(matches) > 0

    unres_matches = [m for m in matches if m.passage.is_unresolved]
    assert len(unres_matches) > 0, "Expected at least one unresolved sample entity"
    top_unres = unres_matches[0]
    assert top_unres.passage.is_unresolved is True
    assert "UNRESOLVED" in top_unres.passage.text or "AMBIGUOUS" in top_unres.passage.text
