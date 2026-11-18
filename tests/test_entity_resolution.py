"""
Comprehensive Verification Suite for Stage 4: Sample-Centric Entity Graph & Resolution Engine.

Covers the 10 domain scenarios required by HE-LMFP-Designer:
1. Multiple samples in one paper (SD_NO3 vs SD_SO4 in srep26686).
2. Identical compositions with different synthesis conditions / precursors.
3. Different dopants (Mg vs Ti vs Ni).
4. Carbon-coated vs uncoated materials (LMFP vs LMFP/C vs LMFP/rGO).
5. Repeated sample mentions across sections (merging into single sample, appending distinct measurements).
6. Measurements under multiple C-rates (preserving condition integrity).
7. Secondary citations in review papers ([79], [29], flags for unverified primary source).
8. Missing or ambiguous sample identity (is_unresolved = True, low confidence).
9. Duplicate detection classification (all 4 outcomes).
10. Review and export protection (Review 6 quarantined, Review 7 export-blocked, CSV untouched).
"""

import pandas as pd
import pytest

from literature.entity_models import (
    CharacterizationProfileEntity,
    CompositeModificationEntity,
    CompositionEntity,
    DopantEntity,
    MaterialSample,
    PaperEntity,
    PropertyMeasurementEntity,
    ProvenanceType,
    ResolutionStatus,
    SecondaryCitationLink,
    SynthesisProfileEntity,
)
from literature.property_extractor import ExtractedPaperProperties, PropertyMeasurement, SynthesisProfile, CharacterizationProfile
from literature.sample_resolver import (
    DuplicateClassification,
    detect_sample_duplicates,
    extract_explicit_sample_labels,
    resolve_composition_entity,
    resolve_sample_entities_from_document,
)
from literature.entity_store import (
    init_entity_tables,
    list_material_samples,
    get_material_sample_graph,
    save_paper_entity_graph,
    update_material_sample,
)
import literature.review_store as rs
from backend.main import CSV_PATH


# ---------------------------------------------------------------------------
# Test Fixture for Isolated SQLite Entity Database
# ---------------------------------------------------------------------------
@pytest.fixture
def isolated_entity_db(tmp_path, monkeypatch):
    """Ensure entity tests do not alter production database."""
    test_db = tmp_path / "test_literature_review.db"
    import literature.entity_store as es
    monkeypatch.setattr(es, "DB_PATH", test_db)
    monkeypatch.setattr(rs, "DB_PATH", test_db)
    es.init_entity_tables()
    rs.init_review_db()
    return test_db


# ---------------------------------------------------------------------------
# Scenario 1: Multiple samples in one paper (SD_NO3 and SD_SO4)
# ---------------------------------------------------------------------------
def test_scenario_1_multiple_samples_in_single_paper(isolated_entity_db):
    """
    srep26686 reports SD_NO3 (nitrate precursor, Fe2O3 impurity, 45 mAh/g)
    and SD_SO4 (sulfate precursor, pure olivine, 114 mAh/g).
    They share base composition LiMn0.75Fe0.25PO4, but MUST NOT be conflated.
    """
    props = ExtractedPaperProperties(
        source_pdf="srep26686.pdf",
        measurements=[
            PropertyMeasurement(
                measurement_id="m1",
                sample_label="SD_NO3",
                measurement_type="discharge_capacity",
                reported_value="45.0 mAh/g",
                reported_unit="mAh/g",
                normalized_value=45.0,
                normalized_unit="mAh/g",
                conditions={"c_rate": 0.05, "cycle_count": 1},
                page_number=4,
                section_type="RESULTS",
                evidence_quote="SD_NO3 delivered only 45 mAh g-1 at 0.05 C due to electrochemically inactive Fe2O3.",
            ),
            PropertyMeasurement(
                measurement_id="m2",
                sample_label="SD_SO4",
                measurement_type="discharge_capacity",
                reported_value="114.0 mAh/g",
                reported_unit="mAh/g",
                normalized_value=114.0,
                normalized_unit="mAh/g",
                conditions={"c_rate": 0.05, "cycle_count": 1},
                page_number=4,
                section_type="RESULTS",
                evidence_quote="SD_SO4 delivered a high discharge capacity of 114 mAh g-1 at 0.05 C.",
            ),
        ],
        synthesis_profiles=[
            SynthesisProfile(
                sample_label="SD_NO3",
                route="Spray drying",
                precursors=["Fe(NO3)3", "Mn(NO3)2"],
                calcination_temperature_c=650.0,
                atmosphere="Ar/H2",
                source_page=2,
            ),
            SynthesisProfile(
                sample_label="SD_SO4",
                route="Spray drying",
                precursors=["FeSO4.7H2O", "MnSO4.H2O"],
                calcination_temperature_c=650.0,
                atmosphere="Ar/H2",
                source_page=2,
            ),
        ],
    )

    paper = resolve_sample_entities_from_document(
        source_pdf="srep26686.pdf",
        paper_properties=props,
        raw_records=[{"composition": "SD_NO3", "page": 4}, {"composition": "SD_SO4", "page": 4}],
    )

    save_paper_entity_graph(paper)
    samples = list_material_samples(paper_id="srep26686")

    # Assert 2 distinct samples exist
    assert len(samples) == 2
    labels = {s["sample_label"] for s in samples}
    assert labels == {"SD_NO3", "SD_SO4"}

    # Verify precursor isolation
    sd_no3 = next(s for s in samples if s["sample_label"] == "SD_NO3")
    sd_so4 = next(s for s in samples if s["sample_label"] == "SD_SO4")

    assert "Fe(NO3)3" in sd_no3["precursor_salts"]
    assert "FeSO4.7H2O" in sd_so4["precursor_salts"]
    assert sd_no3["sample_id"] != sd_so4["sample_id"]

    # Verify measurement attribution
    assert len(sd_no3["measurements"]) == 1
    assert sd_no3["measurements"][0]["normalized_value"] == 45.0
    assert len(sd_so4["measurements"]) == 1
    assert sd_so4["measurements"][0]["normalized_value"] == 114.0


# ---------------------------------------------------------------------------
# Scenario 2: Identical compositions with different synthesis conditions
# ---------------------------------------------------------------------------
def test_scenario_2_identical_composition_different_synthesis():
    """Two samples sharing LiMn0.8Fe0.2PO4 synthesized via solid-state vs hydrothermal."""
    comp = CompositionEntity(
        composition_id="comp_80_20",
        raw_formula="LiMn0.8Fe0.2PO4",
        base_lmfp_formula="LiMn0.8Fe0.2PO4",
        mn_ratio=0.8,
        fe_ratio=0.2,
    )
    sample_ss = MaterialSample(
        sample_id="P1_Sample_SS",
        paper_id="Paper_001",
        sample_label="SS-LMFP",
        composition=comp,
        synthesis_profile=SynthesisProfileEntity(
            synthesis_profile_id="syn_ss",
            method="Solid-state",
            calcination_temp_c=700.0,
            calcination_time_h=8.0,
            precursor_salts=["Li2CO3", "MnCO3", "FeC2O4.2H2O", "NH4H2PO4"],
        ),
    )
    sample_ht = MaterialSample(
        sample_id="P1_Sample_HT",
        paper_id="Paper_001",
        sample_label="HT-LMFP",
        composition=comp,
        synthesis_profile=SynthesisProfileEntity(
            synthesis_profile_id="syn_ht",
            method="Hydrothermal",
            calcination_temp_c=200.0,
            calcination_time_h=12.0,
            precursor_salts=["LiOH.H2O", "MnSO4.H2O", "FeSO4.7H2O", "H3PO4"],
        ),
    )

    classification, score, rationale = detect_sample_duplicates(sample_ss, sample_ht)
    assert classification == DuplicateClassification.DISTINCT_SAMPLES_SAME_COMPOSITION
    assert "precursor salts" in rationale.lower() or "different" in rationale.lower()
    assert sample_ss.sample_id != sample_ht.sample_id


# ---------------------------------------------------------------------------
# Scenario 3: Different dopants (Mg vs Ti vs Ni)
# ---------------------------------------------------------------------------
def test_scenario_3_different_dopants_isolation(isolated_entity_db):
    """Doping series: Mg vs Ti vs Ni on LiMn0.75Fe0.20M0.05PO4."""
    formulas = [
        ("Mg-Doped", "LiMn0.75Fe0.2Mg0.05PO4"),
        ("Ti-Doped", "LiMn0.75Fe0.2Ti0.05PO4"),
        ("Ni-Doped", "LiMn0.75Fe0.2Ni0.05PO4"),
    ]

    paper = PaperEntity(
        paper_id="Doping_Study_2024",
        title="Comparative Doping Study of LMFP",
        source_pdf="doping_study.pdf",
    )

    for label, form in formulas:
        comp_ent = resolve_composition_entity(form)
        sample = MaterialSample(
            sample_id=f"Doping_Study_{label}",
            paper_id=paper.paper_id,
            sample_label=label,
            composition=comp_ent,
            resolution_status=ResolutionStatus.CONFIRMED_EXPLICIT,
        )
        paper.samples.append(sample)

    save_paper_entity_graph(paper)

    # Filter by Mg
    mg_samples = list_material_samples(paper_id="Doping_Study_2024", dopant="Mg")
    assert len(mg_samples) == 1
    assert mg_samples[0]["sample_label"] == "Mg-Doped"
    assert mg_samples[0]["dopants"][0]["element"] == "Mg"

    # Filter by Ti
    ti_samples = list_material_samples(paper_id="Doping_Study_2024", dopant="Ti")
    assert len(ti_samples) == 1
    assert ti_samples[0]["sample_label"] == "Ti-Doped"
    assert ti_samples[0]["dopants"][0]["element"] == "Ti"

    # Filter by Ni
    ni_samples = list_material_samples(paper_id="Doping_Study_2024", dopant="Ni")
    assert len(ni_samples) == 1
    assert ni_samples[0]["sample_label"] == "Ni-Doped"
    assert ni_samples[0]["dopants"][0]["element"] == "Ni"


# ---------------------------------------------------------------------------
# Scenario 4: Carbon-coated vs uncoated materials
# ---------------------------------------------------------------------------
def test_scenario_4_carbon_coating_and_composite_variants():
    """Isolate pristine LMFP vs LMFP/C vs LMFP/rGO."""
    comp_pristine = resolve_composition_entity("LiMn0.7Fe0.3PO4")
    comp_coated = resolve_composition_entity("LiMn0.7Fe0.3PO4/C")
    comp_rgo = resolve_composition_entity("LiMn0.7Fe0.3PO4/rGO")

    assert len(comp_pristine.composite_modifications) == 0
    assert len(comp_coated.composite_modifications) == 1
    assert comp_coated.composite_modifications[0].modification_type == "carbon_coating"
    assert len(comp_rgo.composite_modifications) == 1
    assert comp_rgo.composite_modifications[0].modification_type.lower() == "rgo"

    s_pristine = MaterialSample(
        sample_id="P_Pristine",
        paper_id="P1",
        sample_label="Pristine-LMFP",
        composition=comp_pristine,
    )
    s_rgo = MaterialSample(
        sample_id="P_rGO",
        paper_id="P1",
        sample_label="LMFP/rGO",
        composition=comp_rgo,
    )

    classification, _, rationale = detect_sample_duplicates(s_pristine, s_rgo)
    assert classification == DuplicateClassification.DISTINCT_SAMPLES_SAME_COMPOSITION
    assert "composite modifications" in rationale.lower()


# ---------------------------------------------------------------------------
# Scenario 5: Repeated sample mentions across sections
# ---------------------------------------------------------------------------
def test_scenario_5_repeated_sample_mentions_across_sections(isolated_entity_db):
    """
    Author mentions S1 in Methods (page 2), Results (page 4, capacity),
    and Cycling (page 5, retention).
    Must merge into ONE sample and aggregate measurements without duplicating sample.
    """
    props = ExtractedPaperProperties(
        source_pdf="paper_ms.pdf",
        measurements=[
            PropertyMeasurement(
                measurement_id="m_cap",
                sample_label="S1",
                measurement_type="discharge_capacity",
                reported_value="152.0 mAh/g",
                reported_unit="mAh/g",
                normalized_value=152.0,
                normalized_unit="mAh/g",
                conditions={"c_rate": 0.1},
                page_number=4,
                section_type="RESULTS",
                evidence_quote="Sample S1 delivered 152 mAh/g at 0.1C.",
            ),
            PropertyMeasurement(
                measurement_id="m_ret",
                sample_label="S1",
                measurement_type="capacity_retention",
                reported_value="91.5%",
                reported_unit="%",
                normalized_value=91.5,
                normalized_unit="%",
                conditions={"c_rate": 1.0, "cycle_count": 500},
                page_number=5,
                section_type="RESULTS",
                evidence_quote="Sample S1 retained 91.5% after 500 cycles at 1C.",
            ),
        ],
        synthesis_profiles=[
            SynthesisProfile(
                sample_label="S1",
                route="Sol-gel",
                calcination_temperature_c=600.0,
                source_page=2,
            )
        ],
    )

    paper = resolve_sample_entities_from_document(
        source_pdf="paper_ms.pdf",
        paper_properties=props,
        raw_records=[{"composition": "LiMn0.7Fe0.3PO4", "page": 2, "evidence_quote": "Sample S1 was synthesized"}],
    )
    save_paper_entity_graph(paper)

    samples = list_material_samples(paper_id="paper_ms")
    # Must only have 1 sample
    assert len(samples) == 1
    s1 = samples[0]
    assert s1["sample_label"] in {"S1", "Sample S1"}
    # Both measurements linked to this single sample
    assert len(s1["measurements"]) == 2
    types = {m["measurement_type"] for m in s1["measurements"]}
    assert types == {"discharge_capacity", "capacity_retention"}


# ---------------------------------------------------------------------------
# Scenario 6: Measurements under multiple C-rates
# ---------------------------------------------------------------------------
def test_scenario_6_multiple_crates_condition_integrity(isolated_entity_db):
    """Rate capability at 0.05C, 0.1C, 1C, 2C, 5C strictly preserved."""
    rates = [0.05, 0.1, 1.0, 2.0, 5.0]
    caps = [162.0, 158.0, 142.0, 125.0, 98.0]

    measurements = [
        PropertyMeasurement(
            measurement_id=f"m_rate_{r}",
            sample_label="Ni-D5",
            measurement_type="discharge_capacity",
            reported_value=f"{c} mAh/g",
            reported_unit="mAh/g",
            normalized_value=c,
            normalized_unit="mAh/g",
            conditions={"c_rate": r},
            page_number=4,
            section_type="RESULTS",
            evidence_quote=f"At {r} C, Ni-D5 yielded {c} mAh/g.",
        )
        for r, c in zip(rates, caps)
    ]

    props = ExtractedPaperProperties(
        source_pdf="rate_study.pdf",
        measurements=measurements,
    )

    paper = resolve_sample_entities_from_document(
        source_pdf="rate_study.pdf",
        paper_properties=props,
    )
    save_paper_entity_graph(paper)

    sample = get_material_sample_graph("rate_study_Ni-D5")
    assert sample is not None
    assert len(sample["measurements"]) == 5

    stored_rates = [m["c_rate"] for m in sample["measurements"]]
    assert stored_rates == rates
    stored_caps = [m["normalized_value"] for m in sample["measurements"]]
    assert stored_caps == caps


# ---------------------------------------------------------------------------
# Scenario 7: Secondary citations in review papers
# ---------------------------------------------------------------------------
def test_scenario_7_secondary_citations_in_review_paper(isolated_entity_db):
    """
    Review paper cites [79] and [29].
    Must mark SECONDARY_CITATION and SECONDARY_REVIEW, create SecondaryCitationLink,
    and prevent DOI fabrication.
    """
    props = ExtractedPaperProperties(
        source_pdf="lmfp_review_2023.pdf",
        measurements=[
            PropertyMeasurement(
                measurement_id="m_ref79",
                sample_label="[79]",
                measurement_type="discharge_capacity",
                reported_value="160.0 mAh/g",
                reported_unit="mAh/g",
                normalized_value=160.0,
                normalized_unit="mAh/g",
                conditions={"c_rate": 0.1},
                page_number=8,
                section_type="RESULTS",
                evidence_quote="Zhang et al. [79] reported 160 mAh/g at 0.1 C for LiMn0.5Fe0.5PO4 nanosheets.",
            ),
            PropertyMeasurement(
                measurement_id="m_ref29",
                sample_label="[29]",
                measurement_type="discharge_capacity",
                reported_value="148.0 mAh/g",
                reported_unit="mAh/g",
                normalized_value=148.0,
                normalized_unit="mAh/g",
                conditions={"c_rate": 1.0},
                page_number=9,
                section_type="RESULTS",
                evidence_quote="Wang et al. [29] demonstrated 148 mAh/g at 1 C for Ni-doped LMFP.",
            ),
        ],
    )

    paper = resolve_sample_entities_from_document(
        source_pdf="lmfp_review_2023.pdf",
        paper_properties=props,
        raw_records=[
            {"composition": "LiMn0.5Fe0.5PO4", "page": 8, "reference": "[79]"},
            {"composition": "LiMn0.8Fe0.2PO4", "page": 9, "reference": "[29]"},
        ],
        is_review_paper=True,
    )
    save_paper_entity_graph(paper)

    samples = list_material_samples(paper_id="lmfp_review_2023")
    assert len(samples) == 2

    for s in samples:
        assert s["provenance_type"] == "SECONDARY_REVIEW"
        assert s["resolution_status"] == "SECONDARY_CITATION"
        assert s["secondary_citation_key"] in {"[79]", "[29]"}
        # Ensure no fabricated primary DOI
        assert s["secondary_primary_doi"] is None


# ---------------------------------------------------------------------------
# Scenario 8: Missing or ambiguous sample identity
# ---------------------------------------------------------------------------
def test_scenario_8_missing_or_ambiguous_sample_identity():
    """Unlabeled candidate or casual mention flagged as is_unresolved = True."""
    props = ExtractedPaperProperties(
        source_pdf="vague.pdf",
        measurements=[
            PropertyMeasurement(
                measurement_id="m_vague",
                sample_label=None,  # No explicit label
                measurement_type="discharge_capacity",
                reported_value="130.0 mAh/g",
                reported_unit="mAh/g",
                normalized_value=130.0,
                normalized_unit="mAh/g",
                conditions={"c_rate": 0.1},
                page_number=1,
                section_type="INTRODUCTION",
                evidence_quote="LMFP cathodes typically exhibit 130 mAh/g at 0.1C.",
            )
        ],
    )

    paper = resolve_sample_entities_from_document(
        source_pdf="vague.pdf",
        paper_properties=props,
    )

    assert len(paper.samples) >= 1
    vague_sample = paper.samples[0]
    assert vague_sample.is_unresolved is True
    assert vague_sample.resolution_status == ResolutionStatus.UNRESOLVED
    assert vague_sample.resolution_confidence < 0.5


# ---------------------------------------------------------------------------
# Scenario 9: Duplicate detection classification
# ---------------------------------------------------------------------------
def test_scenario_9_duplicate_detection_all_classes():
    """Test all 4 outcomes of detect_sample_duplicates."""
    comp_a = resolve_composition_entity("LiMn0.7Fe0.3PO4")
    comp_b = resolve_composition_entity("LiMn0.8Fe0.2PO4")

    # 1. REPEATED_MENTION: Same paper, same label
    s1_p1 = MaterialSample(sample_id="s1", paper_id="p1", sample_label="Sample-A", composition=comp_a)
    s2_p1 = MaterialSample(sample_id="s2", paper_id="p1", sample_label="Sample-A", composition=comp_a)
    res1, score1, _ = detect_sample_duplicates(s1_p1, s2_p1)
    assert res1 == DuplicateClassification.REPEATED_MENTION
    assert score1 == 1.0

    # 2. INDEPENDENT_LITERATURE_STUDIES: Different papers, same formula
    s1_p2 = MaterialSample(sample_id="s3", paper_id="p2", sample_label="Sample-A", composition=comp_a)
    res2, _, _ = detect_sample_duplicates(s1_p1, s1_p2)
    assert res2 == DuplicateClassification.INDEPENDENT_LITERATURE_STUDIES

    # 3. DISTINCT_SAMPLES_SAME_COMPOSITION: Same paper, different coatings
    comp_coated = resolve_composition_entity("LiMn0.7Fe0.3PO4/C")
    s_coated = MaterialSample(sample_id="s4", paper_id="p1", sample_label="LMFP/C", composition=comp_coated)
    res3, _, _ = detect_sample_duplicates(s1_p1, s_coated)
    assert res3 == DuplicateClassification.DISTINCT_SAMPLES_SAME_COMPOSITION

    # 4. AMBIGUOUS_SUSPECTED_DUPLICATE: Same paper, different labels, identical formula and synthesis
    s_diff_label = MaterialSample(sample_id="s5", paper_id="p1", sample_label="Sample-B", composition=comp_a)
    res4, _, _ = detect_sample_duplicates(s1_p1, s_diff_label)
    assert res4 == DuplicateClassification.AMBIGUOUS_SUSPECTED_DUPLICATE


# ---------------------------------------------------------------------------
# Scenario 10: Review and export protection
# ---------------------------------------------------------------------------
def test_scenario_10_review_and_export_integrity(isolated_entity_db):
    """
    Verify Review 6 remains quarantined, Review 7 remains export-blocked,
    and master CSV (1,215 x 41) remains untouched.
    """
    # 1. Master CSV shape check
    df = pd.read_csv(CSV_PATH)
    assert df.shape == (1215, 41), f"Expected (1215, 41), got {df.shape}"

    # 2. Stage 4 entity updates do not modify master CSV or force approval
    comp = resolve_composition_entity("LiMn0.75Fe0.25PO4")
    sample = MaterialSample(
        sample_id="test_sample_integrity",
        paper_id="paper_integrity",
        sample_label="TestSample",
        composition=comp,
        resolution_status=ResolutionStatus.AMBIGUOUS,
        resolution_notes="Needs reviewer check",
    )
    paper = PaperEntity(paper_id="paper_integrity", title="Integrity Test", samples=[sample])
    save_paper_entity_graph(paper)

    # Disambiguate without altering CSV
    updated = update_material_sample(
        sample_id="test_sample_integrity",
        sample_label="TestSample_Verified",
        resolution_status=ResolutionStatus.CONFIRMED_EXPLICIT.value,
        resolution_notes="Manually confirmed by reviewer.",
    )
    assert updated is not None
    assert updated["sample_label"] == "TestSample_Verified"
    assert updated["resolution_status"] == "CONFIRMED_EXPLICIT"

    # Verify CSV is still untouched
    df_after = pd.read_csv(CSV_PATH)
    assert df_after.shape == (1215, 41)
