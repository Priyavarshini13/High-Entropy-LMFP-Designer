"""Unit tests for EvidenceOrganizer, DynamicScientificSynthesizer, and Condition Parity in Stage 5 Phase 3."""

import pytest
from copilot.models import (
    EvidencePassage,
    RetrievalMatch,
    StructuredSampleProfile,
    MeasurementRecord,
    ConditionParityResult,
)
from copilot.evidence_organizer import EvidenceOrganizer
from copilot.grounding import DynamicScientificSynthesizer, audit_citations_and_claims


@pytest.fixture
def organizer():
    return EvidenceOrganizer()


@pytest.fixture
def synthesizer():
    return DynamicScientificSynthesizer()


def _make_match(
    passage_id: str,
    paper_id: str,
    text: str,
    sample_id: str = "SD_NO3",
    sample_label: str = "SD_NO3",
    composition: str = "LiMn0.8Fe0.2PO4",
    title: str = "Test Title",
    doi: str = "10.1038/srep26686",
    page_number: int = 1,
    provenance_type: str = "PRIMARY_RESEARCH",
    structured_data: dict = None,
) -> RetrievalMatch:
    p = EvidencePassage(
        passage_id=passage_id,
        paper_id=paper_id,
        title=title,
        doi=doi,
        page_number=page_number,
        sample_id=sample_id,
        sample_label=sample_label,
        composition=composition,
        text=text,
        provenance_type=provenance_type,
        structured_data=structured_data or {},
    )
    return RetrievalMatch(passage=p, combined_score=0.9, sample_id=sample_id)


def test_organizer_measurement_extraction_and_condition_binding(organizer):
    """Verify that measurements are extracted with their condition bindings (C-rate, voltage, cycle count)."""
    matches = [
        _make_match(
            passage_id="P_nov_sec_res_p1_0",
            paper_id="paper_novel_synth",
            sample_id="Sample_Novel_001",
            sample_label="Sample_Novel_001",
            text="The Sample_Novel_001 sample delivered a discharge capacity of 158.4 mAh/g at 0.05C in the voltage window 2.5-4.5V. At 1C rate, the capacity was 142.1 mAh/g. After 500 cycles at 1C, the capacity retention reached 89.4%. EIS measurement showed a charge transfer resistance Rct of 48.2 Ohm.",
            page_number=4,
        ),
        _make_match(
            passage_id="P_nov_sec_exp_p1_0",
            paper_id="paper_novel_synth",
            sample_id="Sample_Novel_001",
            sample_label="Sample_Novel_001",
            text="Sample_Novel_001 was prepared by spray drying using iron nitrate Fe(NO3)3 precursor followed by calcination at 650 C for 6 h under Ar/H2 (95:5 vol%). XRD revealed pure orthorhombic olivine phase with Pnma space group.",
            page_number=2,
            structured_data={
                "synthesis_route": "spray drying",
                "calcination_temperature_c": 650.0,
                "calcination_time_h": 6.0,
                "atmosphere": "Ar/H2",
            },
        ),
    ]

    profiles = organizer.organize_matches(matches)
    assert len(profiles) == 1
    p = profiles[0]
    assert p.sample_id == "Sample_Novel_001"
    assert p.composition == "LiMn0.8Fe0.2PO4"
    assert p.synthesis_method == "spray drying"
    assert p.calcination_temp_c == 650.0
    assert p.calcination_time_h == 6.0
    assert p.atmosphere == "Ar/H2"
    assert p.space_group == "Pnma"
    assert "Fe(NO3)3" in p.precursor_salts

    # Verify extracted measurements
    meas_types = [m.measurement_type for m in p.measurements]
    assert "discharge_capacity" in meas_types
    assert "capacity_retention" in meas_types
    assert "charge_transfer_resistance" in meas_types

    # Find the 0.05C measurement
    c005 = [m for m in p.measurements if m.c_rate == 0.05]
    assert len(c005) > 0
    assert c005[0].value == 158.4
    assert c005[0].voltage_window == "2.5-4.5V"

    # Find retention measurement
    ret = [m for m in p.measurements if m.measurement_type == "capacity_retention"]
    assert len(ret) > 0
    assert ret[0].value == 89.4
    assert ret[0].cycle_count == 500


def test_organizer_multi_sample_separation(organizer):
    """Verify that multiple samples from the same paper remain strictly separated."""
    matches = [
        _make_match(
            passage_id="P1_sample1",
            paper_id="srep26686",
            sample_id="SD_NO3",
            sample_label="SD_NO3",
            text="SD_NO3 synthesized from nitrate delivered 158.4 mAh/g at 0.05C and showed pure olivine phase.",
        ),
        _make_match(
            passage_id="P1_sample2",
            paper_id="srep26686",
            sample_id="SD_SO4",
            sample_label="SD_SO4",
            text="In contrast, SD_SO4 derived from sulfate exhibited residual Fe2O3 impurity and delivered only 131.2 mAh/g at 0.05C.",
        ),
    ]

    profiles = organizer.organize_matches(matches)
    assert len(profiles) == 2
    sample_ids = {p.sample_id for p in profiles}
    assert sample_ids == {"SD_NO3", "SD_SO4"}

    p_no3 = next(p for p in profiles if p.sample_id == "SD_NO3")
    p_so4 = next(p for p in profiles if p.sample_id == "SD_SO4")

    assert p_no3.xrd_phase_purity == "phase-pure"
    assert p_so4.impurity_phases == "Fe2O3"


def test_condition_parity_evaluation(organizer):
    """Verify that condition parity checks detect matching vs mismatched experimental conditions."""
    p1 = StructuredSampleProfile(
        sample_id="Sample_A",
        sample_label="Sample_A",
        paper_id="P001",
        composition="LiMn0.7Fe0.3PO4/C",
        provenance_type="PRIMARY_PAPER",
        measurements=[
            MeasurementRecord(
                measurement_type="discharge_capacity",
                value=160.0,
                unit="mAh/g",
                c_rate=0.1,
                voltage_window="2.5-4.5V",
                temperature_c=25.0,
            ),
            MeasurementRecord(
                measurement_type="capacity_retention",
                value=92.0,
                unit="%",
                c_rate=1.0,
                cycle_count=500,
                voltage_window="2.5-4.5V",
                temperature_c=25.0,
            ),
        ],
    )

    p2_matched = StructuredSampleProfile(
        sample_id="Sample_B",
        sample_label="Sample_B",
        paper_id="P002",
        composition="LiMn0.7Fe0.3PO4/C-rGO",
        provenance_type="PRIMARY_PAPER",
        measurements=[
            MeasurementRecord(
                measurement_type="discharge_capacity",
                value=165.0,
                unit="mAh/g",
                c_rate=0.1,
                voltage_window="2.5-4.5V",
                temperature_c=25.0,
            ),
            MeasurementRecord(
                measurement_type="capacity_retention",
                value=96.0,
                unit="%",
                c_rate=1.0,
                cycle_count=500,
                voltage_window="2.5-4.5V",
                temperature_c=25.0,
            ),
        ],
    )

    p2_mismatched = StructuredSampleProfile(
        sample_id="Sample_C",
        sample_label="Sample_C",
        paper_id="P003",
        composition="LiMn0.8Fe0.2PO4",
        provenance_type="SECONDARY_REVIEW",
        measurements=[
            MeasurementRecord(
                measurement_type="discharge_capacity",
                value=145.0,
                unit="mAh/g",
                c_rate=1.0,  # Mismatched C-rate (1C vs 0.1C)
                voltage_window="2.0-4.2V",  # Mismatched window
                temperature_c=55.0,  # Mismatched temperature
            ),
            MeasurementRecord(
                measurement_type="capacity_retention",
                value=85.0,
                unit="%",
                c_rate=2.0,
                cycle_count=1000,  # Mismatched cycle count
                voltage_window="2.0-4.2V",
                temperature_c=55.0,
            ),
        ],
    )

    # Test matched parity
    parity_matched = organizer.evaluate_condition_parity([p1, p2_matched])
    assert parity_matched.c_rate_aligned is True
    assert parity_matched.voltage_window_aligned is True
    assert parity_matched.cycle_count_aligned is True
    assert parity_matched.comparability_verdict == "MATCHED_CONDITIONS"
    assert len(parity_matched.divergence_notes) == 0

    # Test mismatched parity
    parity_mismatched = organizer.evaluate_condition_parity([p1, p2_mismatched])
    assert parity_mismatched.c_rate_aligned is False
    assert parity_mismatched.voltage_window_aligned is False
    assert parity_mismatched.cycle_count_aligned is False
    assert parity_mismatched.comparability_verdict == "CONDITION_DIVERGENT"
    assert len(parity_mismatched.divergence_notes) >= 3


def test_dynamic_synthesizer_unseen_paper_generation(synthesizer):
    """Verify that dynamic synthesis generates scientifically grounded answers for unseen papers."""
    matches = [
        _make_match(
            passage_id="P_nov_0",
            paper_id="paper_novel_2026",
            title="Scandium Doping in LiMn0.7Fe0.3PO4",
            sample_id="LMFP-Sc002",
            sample_label="LMFP-Sc002",
            composition="LiMn0.68Sc0.02Fe0.3PO4/C",
            doi="10.1016/j.jpowsour.2026.123456",
            text="Sc3+ doping expands the 1D [010] diffusion channels and delivers 138.5 mAh/g at 5C with 94.2% retention after 800 cycles.",
        )
    ]

    profile = StructuredSampleProfile(
        sample_id="LMFP-Sc002",
        sample_label="LMFP-Sc002",
        paper_id="paper_novel_2026",
        composition="LiMn0.68Sc0.02Fe0.3PO4/C",
        dopants=["Sc"],
        synthesis_method="sol-gel",
        calcination_temp_c=700.0,
        space_group="Pnma",
        crystal_structure="orthorhombic olivine",
        measurements=[
            MeasurementRecord(
                measurement_type="discharge_capacity",
                value=138.5,
                unit="mAh/g",
                c_rate=5.0,
            ),
            MeasurementRecord(
                measurement_type="capacity_retention",
                value=94.2,
                unit="%",
                cycle_count=800,
            ),
        ],
        passages=[matches[0].passage],
    )

    result = synthesizer.synthesize(
        query="What is the 5C discharge capacity and cycle retention of Sc-doped LMFP in paper_novel_2026?",
        matches=matches,
        profiles=[profile],
    )

    ans = result["direct_answer"]
    expl = result["explanation"]

    assert "138.5" in ans or "138.5" in expl
    assert "94.2" in ans or "94.2" in expl
    assert "800" in ans or "800" in expl
    assert "Sc" in expl or "Sc" in ans
    assert "Pnma" in expl or "olivine" in expl


def test_numerical_claim_auditing(synthesizer):
    """Verify that ungrounded numerical claims generate verification warnings."""
    matches = [
        _make_match(
            passage_id="P1",
            paper_id="paper_1",
            sample_id="Sample1",
            sample_label="Sample1",
            text="The capacity at 0.1C was 155.0 mAh/g and retention was 90.0% after 200 cycles.",
        )
    ]

    profiles = [
        StructuredSampleProfile(
            sample_id="Sample1",
            sample_label="Sample1",
            paper_id="paper_1",
            composition="LiMn0.8Fe0.2PO4",
            measurements=[
                MeasurementRecord(measurement_type="discharge_capacity", value=155.0, unit="mAh/g", c_rate=0.1),
                MeasurementRecord(measurement_type="capacity_retention", value=90.0, unit="%", cycle_count=200),
            ],
            passages=[matches[0].passage],
        )
    ]

    # Grounded text
    grounded_text = "The sample achieved 155.0 mAh/g at 0.1C with 90.0% retention."
    audited_text_g, citations_g, ungrounded_g = audit_citations_and_claims(grounded_text, matches, profiles)
    assert len(ungrounded_g) == 0

    # Ungrounded text containing hallucinated numbers (e.g. 178.5 mAh/g, 99.8%)
    hallucinated_text = "The sample achieved 178.5 mAh/g at 0.1C with 99.8% capacity retention after 1500 cycles."
    audited_text_h, citations_h, ungrounded_h = audit_citations_and_claims(hallucinated_text, matches, profiles)
    assert len(ungrounded_h) > 0
    assert any("178.5" in u for u in ungrounded_h)
    assert any("99.8" in u for u in ungrounded_h)
