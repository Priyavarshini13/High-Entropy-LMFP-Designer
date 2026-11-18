"""
Comprehensive Unit Tests for Universal LMFP Property Extraction Engine (Stage 3).

Covers:
- Specific discharge and charge capacities across arbitrary C-rates (fractional, integer, C/N)
- Strict condition association (C-rate, cycle count, voltage window, temperature, evidence)
- Multiple cycling retention regimes without merging or data collapse
- Operating voltage windows and Coulombic efficiency (ICE and operational CE)
- Synthesis conditions (route, calcination temperature, duration, atmosphere, precursors)
- Crystallographic characterization (space group, lattice a, b, c, volume)
- Physical & transport kinetics (crystallite/particle size, EIS Rct, D_Li diffusion)
- Scientific notation and Unicode units (mAh·g⁻¹, cm²·s⁻¹, ×10⁻¹⁴)
- Document structure integration with section filtering
- Negative controls:
  1. References section strictly excluded from generating measurements.
  2. False positive numeric rejection (non-electrochemical counts).
  3. Missing properties preserved as None.
"""

import pytest
from literature.property_extractor import (
    CharacterizationProfile,
    ExtractedPaperProperties,
    PropertyMeasurement,
    SynthesisProfile,
    extract_characterization_profile,
    extract_electrochemical_measurements,
    extract_properties_from_document,
    extract_synthesis_profile,
    parse_c_rate,
    parse_scientific_notation,
)
from literature.section_parser import DocumentStructure, SectionBlock, SectionType


def test_parse_arbitrary_c_rates():
    """Verify parsing arbitrary numeric C-rates and C/N notations."""
    cases = [
        ("0.05 C", 0.05),
        ("0.1C", 0.1),
        ("0.2 C", 0.2),
        ("0.5 C", 0.5),
        ("1C", 1.0),
        ("2 C", 2.0),
        ("5C", 5.0),
        ("10 C", 10.0),
        ("20C", 20.0),
        ("C/10", 0.1),
        ("C/5", 0.2),
        ("C/20", 0.05),
        ("C/2", 0.5),
        ("C/1", 1.0),
    ]
    for rate_str, expected in cases:
        val = parse_c_rate(rate_str)
        assert val == pytest.approx(expected, abs=1e-4), f"Failed for {rate_str}"


def test_multiple_capacities_in_one_paragraph_with_strict_conditions():
    """Verify extracting multiple capacity values at distinct C-rates from one paragraph."""
    text = (
        "The LiMn0.8Fe0.2PO4/C electrode delivered specific discharge capacities of "
        "166.8 mAh/g at 0.1 C, 154.2 mAh g-1 at 1 C, 138.5 mAh/g at 2 C, and "
        "118.9 mAh/g at 5 C in the voltage window of 2.5-4.5 V vs. Li/Li+."
    )
    meas = extract_electrochemical_measurements(
        text=text,
        page_number=4,
        section_type="RESULTS_DISCUSSION",
        source_pdf="lmfp_paper.pdf",
        sample_label="LiMn0.8Fe0.2PO4/C",
    )

    caps = [m for m in meas if m.measurement_type == "discharge_capacity"]
    assert len(caps) == 4

    # Verify each capacity has its exact corresponding C-rate and voltage window
    cap_map = {m.conditions["c_rate"]: m.normalized_value for m in caps}
    assert cap_map[0.1] == 166.8
    assert cap_map[1.0] == 154.2
    assert cap_map[2.0] == 138.5
    assert cap_map[5.0] == 118.9

    for c in caps:
        assert c.sample_label == "LiMn0.8Fe0.2PO4/C"
        assert c.conditions["voltage_window"] == "2.5-4.5 V"
        assert c.reported_unit == "mAh/g"
        assert "166.8" in c.evidence_quote or "154.2" in c.evidence_quote or "138.5" in c.evidence_quote or "118.9" in c.evidence_quote


def test_multiple_retention_measurements_preserved_separately():
    """Verify preserving multiple retention measurements across different cycle counts and rates."""
    text = (
        "Long-term cycling tests demonstrated exceptional stability: "
        "retention of 98.4% after 100 cycles at 0.5 C, "
        "89.1% after 500 cycles at 2 C, and "
        "82.5% after 1000 cycles at 5 C."
    )
    meas = extract_electrochemical_measurements(
        text=text,
        page_number=5,
        section_type="RESULTS_DISCUSSION",
        sample_label="LiMn0.75Fe0.25PO4/rGO",
    )

    rets = [m for m in meas if m.measurement_type == "capacity_retention"]
    assert len(rets) == 3

    # Check distinct condition attribution
    cond_map = {(m.conditions["cycle_count"], m.conditions["c_rate"]): m.normalized_value for m in rets}
    assert cond_map[(100, 0.5)] == 98.4
    assert cond_map[(500, 2.0)] == 89.1
    assert cond_map[(1000, 5.0)] == 82.5

    # Ensure no values are collapsed into a single number
    for r in rets:
        assert r.sample_label == "LiMn0.75Fe0.25PO4/rGO"
        assert r.reported_unit == "%"


def test_ice_and_operational_coulombic_efficiency():
    """Verify extraction of initial Coulombic efficiency (ICE) and operational CE."""
    text = (
        "In the initial cycle between 2.2 and 4.4 V, the material showed an "
        "initial charge capacity of 175.2 mAh/g and discharge capacity of 158.4 mAh/g at 0.1 C, "
        "corresponding to an initial Coulombic efficiency of 90.4%. "
        "During subsequent cycling, the Coulombic efficiency remained above 99.8%."
    )
    meas = extract_electrochemical_measurements(
        text=text,
        page_number=3,
        section_type="RESULTS_DISCUSSION",
        sample_label="LiMn0.8Fe0.2PO4",
    )

    ice_list = [m for m in meas if m.measurement_type == "ice"]
    ce_list = [m for m in meas if m.measurement_type == "coulombic_efficiency"]
    chg_list = [m for m in meas if m.measurement_type == "charge_capacity"]

    assert len(ice_list) == 1
    assert ice_list[0].normalized_value == 90.4
    assert ice_list[0].conditions["voltage_window"] == "2.2-4.4 V"

    assert len(ce_list) == 1
    assert ce_list[0].normalized_value == 99.8

    assert len(chg_list) == 1
    assert chg_list[0].normalized_value == 175.2


def test_synthesis_conditions_extraction():
    """Verify extraction of route, calcination temperature, duration, atmosphere, and precursors."""
    text = (
        "The LiMn0.8Fe0.2PO4 cathode was prepared via a sol-gel method. "
        "Stoichiometric amounts of LiOH.H2O, Mn(CH3COO)2, FeSO4.7H2O, and NH4H2PO4 "
        "were dissolved with citric acid. The dried gel precursor was calcined at 650 °C for 8 h "
        "under an Ar/H2 atmosphere with a heating rate of 5 °C/min."
    )
    profile = extract_synthesis_profile(text=text, page_number=2, sample_label="LiMn0.8Fe0.2PO4")
    assert profile is not None
    assert profile.route == "Sol-gel"
    assert profile.calcination_temperature_c == 650.0
    assert profile.calcination_duration_hours == 8.0
    assert profile.heating_rate_c_min == 5.0
    assert "ar/h2" in profile.atmosphere.lower()
    assert "LiOH.H2O" in profile.precursors
    assert "NH4H2PO4" in profile.precursors
    assert "citric acid" in profile.precursors


def test_characterization_profile_crystallography_and_eis():
    """Verify space group, lattice parameters, crystallite size, Rct, and D_Li."""
    text = (
        "Rietveld refinement confirmed a single-phase olivine structure with space group Pnma. "
        "The lattice parameters were determined to be a = 10.428 Å, b = 6.082 Å, c = 4.745 Å, "
        "with a unit-cell volume of 300.9 Å3. The average crystallite size was 38.5 nm. "
        "EIS measurements revealed a charge-transfer resistance of 42.6 Ω. "
        "The lithium-ion diffusion coefficient was calculated as 2.4 x 10^-14 cm2/s."
    )
    char = extract_characterization_profile(text=text, page_number=4, sample_label="LiMn0.8Fe0.2PO4/C")
    assert char is not None
    assert char.space_group == "Pnma"
    assert char.lattice_a_angstrom == 10.428
    assert char.lattice_b_angstrom == 6.082
    assert char.lattice_c_angstrom == 4.745
    assert char.unit_cell_volume_angstrom3 == 300.9
    assert char.crystallite_size_nm == 38.5
    assert char.eis_rct_ohm == 42.6
    assert char.li_diffusion_coefficient_cm2_s == pytest.approx(2.4e-14, abs=1e-16)


def test_scientific_notation_variations():
    """Verify scientific notation parsing across unicode exponents and ASCII."""
    assert parse_scientific_notation("2.4 x 10^-14") == pytest.approx(2.4e-14)
    assert parse_scientific_notation("1.5e-14") == pytest.approx(1.5e-14)
    assert parse_scientific_notation("3.8 × 10⁻¹⁵") == pytest.approx(3.8e-15)
    assert parse_scientific_notation("42.5") == pytest.approx(42.5)


def test_negative_control_reference_section_exclusion():
    """CRITICAL NEGATIVE TEST: Citations in References section must NOT extract experimental measurements."""
    ref_block = SectionBlock(
        block_id="b_ref_1",
        section_type=SectionType.REFERENCES,
        section_label="References",
        page_number=8,
        text=(
            "[14] X. Zhang et al., LiMn0.8Fe0.2PO4 delivering 160 mAh/g at 0.1 C "
            "with 95% retention after 500 cycles. J. Power Sources 2021."
        ),
        is_experimental=False,
    )
    doc_struct = DocumentStructure(source_pdf="test_paper.pdf", total_pages=8, blocks=[ref_block])
    props = extract_properties_from_document(doc_struct, source_pdf="test_paper.pdf")

    assert len(props.measurements) == 0
    assert len(props.synthesis_profiles) == 0
    assert len(props.characterization_profiles) == 0


def test_negative_control_false_positive_rejection():
    """CRITICAL NEGATIVE TEST: Non-electrochemical numbers must not be extracted as measurements."""
    text = (
        "We assembled a battery of 50 test cells using 25 mL of ethanol and 100 mg of binder. "
        "The experiments were repeated 3 times in 2022."
    )
    meas = extract_electrochemical_measurements(
        text=text,
        page_number=2,
        section_type="EXPERIMENTAL",
    )
    # None of these are capacities, retentions, or ICE
    assert len(meas) == 0


def test_missing_values_preserved_as_none():
    """Verify unreported properties remain None and are not filled with fabricated defaults."""
    text = "The sample was prepared by solid-state reaction and calcined at 700 °C."
    profile = extract_synthesis_profile(text=text, page_number=2)
    assert profile is not None
    assert profile.route == "Solid-state"
    assert profile.calcination_temperature_c == 700.0
    assert profile.calcination_duration_hours is None  # Unreported duration
    assert profile.heating_rate_c_min is None         # Unreported heating rate
    assert profile.atmosphere is None                # Unreported atmosphere


def test_multiple_samples_in_one_table_strict_isolation():
    """CRITICAL TEST: Ensure measurements in a table row are bound strictly to that row's sample."""
    table_text = (
        "Table 2. Rate capability and cycling retention of LMFP cathode samples.\n"
        "Sample\t0.1 C\t1 C\t5 C\tRetention (cycles, C-rate)\n"
        "Pristine-LMFP\t142.5\t125.0\t95.2\t82.1% (200, 1 C)\n"
        "LMFP/C\t162.8\t150.4\t122.1\t93.4% (500, 1 C)\n"
        "Mg-LMFP/C\t168.2\t158.7\t135.0\t96.5% (500, 1 C)\n"
    )
    from literature.property_extractor import extract_table_measurements

    meas = extract_table_measurements(table_text=table_text, page_number=4, table_id="Table 2")
    assert len(meas) == 12  # 3 samples x 3 capacities + 3 retentions

    # Check Pristine sample
    pristine_caps = [m for m in meas if m.sample_label == "Pristine-LMFP" and m.measurement_type == "discharge_capacity"]
    assert len(pristine_caps) == 3
    p_cap_map = {m.conditions["c_rate"]: m.normalized_value for m in pristine_caps}
    assert p_cap_map[0.1] == 142.5
    assert p_cap_map[1.0] == 125.0
    assert p_cap_map[5.0] == 95.2

    # Check Mg-LMFP/C sample
    mg_caps = [m for m in meas if m.sample_label == "Mg-LMFP/C" and m.measurement_type == "discharge_capacity"]
    assert len(mg_caps) == 3
    mg_cap_map = {m.conditions["c_rate"]: m.normalized_value for m in mg_caps}
    assert mg_cap_map[0.1] == 168.2
    assert mg_cap_map[1.0] == 158.7
    assert mg_cap_map[5.0] == 135.0

    # Check Mg-LMFP/C retention
    mg_ret = [m for m in meas if m.sample_label == "Mg-LMFP/C" and m.measurement_type == "capacity_retention"]
    assert len(mg_ret) == 1
    assert mg_ret[0].normalized_value == 96.5
    assert mg_ret[0].conditions["cycle_count"] == 500
    assert mg_ret[0].conditions["c_rate"] == 1.0


def test_unicode_units_and_superscripts_in_capacities():
    """Verify capacities reported with unicode superscripts like mAh·g⁻¹ and mA h g-1."""
    text = (
        "The composite delivered 164.5 mAh·g⁻¹ at 0.1 C and 148.0 mA h g-1 at 1 C."
    )
    meas = extract_electrochemical_measurements(
        text=text,
        page_number=3,
        section_type="RESULTS_DISCUSSION",
        sample_label="LiMn0.8Fe0.2PO4/C",
    )
    caps = [m for m in meas if m.measurement_type == "discharge_capacity"]
    assert len(caps) == 2
    assert caps[0].normalized_value == 164.5
    assert caps[0].conditions["c_rate"] == 0.1
    assert caps[1].normalized_value == 148.0
    assert caps[1].conditions["c_rate"] == 1.0


def test_document_level_integration_with_section_zoning():
    """Verify document-level orchestrator extracts properties obeying structural section zones."""
    blocks = [
        SectionBlock(
            block_id="b1",
            section_type=SectionType.EXPERIMENTAL,
            section_label="2. Experimental",
            page_number=2,
            text=(
                "LiMn0.8Fe0.2PO4/C was synthesized via a sol-gel route with LiOH and FeSO4 precursors. "
                "The powder was calcined at 650 °C for 6 h under Ar."
            ),
            is_experimental=True,
        ),
        SectionBlock(
            block_id="b2",
            section_type=SectionType.RESULTS_DISCUSSION,
            section_label="3. Results and discussion",
            page_number=3,
            text=(
                "XRD analysis confirmed space group Pnma with a = 10.43 Å, b = 6.08 Å, c = 4.74 Å. "
                "Electrochemical testing between 2.5 and 4.5 V demonstrated a discharge capacity of "
                "165.2 mAh/g at 0.1 C and retention of 91.5% after 500 cycles at 1 C."
            ),
            is_experimental=True,
        ),
        SectionBlock(
            block_id="b3",
            section_type=SectionType.REFERENCES,
            section_label="References",
            page_number=6,
            text="[22] Y. Kim et al., LiMn0.7Fe0.3PO4 with 150 mAh/g at 0.1 C, Electrochim. Acta 2020.",
            is_experimental=False,
        ),
    ]
    doc = DocumentStructure(source_pdf="paper.pdf", total_pages=6, blocks=blocks)
    props = extract_properties_from_document(doc, source_pdf="paper.pdf")

    # 1. Synthesis profile captured from Experimental block
    assert len(props.synthesis_profiles) == 1
    synth = props.synthesis_profiles[0]
    assert synth.route == "Sol-gel"
    assert synth.calcination_temperature_c == 650.0
    assert synth.calcination_duration_hours == 6.0
    assert synth.atmosphere == "Ar"

    # 2. Characterization profile captured from Results block
    assert len(props.characterization_profiles) == 1
    char = props.characterization_profiles[0]
    assert char.space_group == "Pnma"
    assert char.lattice_a_angstrom == 10.43

    # 3. Measurements captured from Results block
    caps = props.get_measurements_by_type("discharge_capacity")
    rets = props.get_measurements_by_type("capacity_retention")
    assert len(caps) == 1
    assert caps[0].normalized_value == 165.2
    assert caps[0].conditions["c_rate"] == 0.1
    assert caps[0].conditions["voltage_window"] == "2.5-4.5 V"

    assert len(rets) == 1
    assert rets[0].normalized_value == 91.5
    assert rets[0].conditions["cycle_count"] == 500
    assert rets[0].conditions["c_rate"] == 1.0

    # 4. Strict exclusion of Reference block: no measurements from page 6
    assert not any(m.page_number == 6 for m in props.measurements)


def test_scientific_respectively_sample_pairing():
    """Verify 'respectively' construction pairs sample labels with exact values and local C-rate."""
    text = (
        "Figure 7(a) shows the galvanostatic discharge curves of the samples prepared using the different "
        "metal salts at 0.05 C-rate. The discharge capacities of SD_NO3 and SD_SO4 were 45 mA h g-1 and "
        "114 mA h g-1, respectively."
    )
    meas = extract_electrochemical_measurements(
        text=text,
        page_number=7,
        section_type="RESULTS_DISCUSSION",
        source_pdf="srep26686.pdf",
    )
    caps = [m for m in meas if m.measurement_type == "discharge_capacity"]
    assert len(caps) == 2

    # SD_NO3 -> 45.0 mAh/g
    no3_caps = [m for m in caps if m.sample_label == "SD_NO3"]
    assert len(no3_caps) == 1
    assert no3_caps[0].normalized_value == 45.0
    assert no3_caps[0].conditions.get("c_rate") == 0.05

    # SD_SO4 -> 114.0 mAh/g
    so4_caps = [m for m in caps if m.sample_label == "SD_SO4"]
    assert len(so4_caps) == 1
    assert so4_caps[0].normalized_value == 114.0
    assert so4_caps[0].conditions.get("c_rate") == 0.05


def test_scientific_respectively_rate_capability():
    """Verify 'respectively' series pairing values to matching C-rates."""
    text = (
        "SD_SO4 delivered high discharge capacities of 114, 107, 100, 92, 83, 76, 68, 59, and 37 mAh/g "
        "at 0.05, 0.1, 0.5, 1, 2, 5, 10, 20, and 40 C, respectively."
    )
    meas = extract_electrochemical_measurements(
        text=text,
        page_number=8,
        section_type="RESULTS_DISCUSSION",
        source_pdf="srep26686.pdf",
    )
    caps = [m for m in meas if m.measurement_type == "discharge_capacity"]
    assert len(caps) == 9

    rate_val_map = {m.conditions["c_rate"]: m.normalized_value for m in caps}
    assert rate_val_map[0.05] == 114.0
    assert rate_val_map[0.1] == 107.0
    assert rate_val_map[0.5] == 100.0
    assert rate_val_map[1.0] == 92.0
    assert rate_val_map[2.0] == 83.0
    assert rate_val_map[5.0] == 76.0
    assert rate_val_map[10.0] == 68.0
    assert rate_val_map[20.0] == 59.0
    assert rate_val_map[40.0] == 37.0
    for m in caps:
        assert m.sample_label == "SD_SO4"


def test_long_term_cycling_retention_with_commas():
    """Verify retention parsing handles formatted cycle counts like 1,000 cycles."""
    text = (
        "The composite demonstrated extraordinary cycling stability with 93% capacity retention "
        "after 1,000 cycles at 10 C and 76% retention after 1,000 cycles at 20 C."
    )
    meas = extract_electrochemical_measurements(
        text=text,
        page_number=1,
        section_type="ABSTRACT",
        source_pdf="srep26686.pdf",
    )
    rets = [m for m in meas if m.measurement_type == "capacity_retention"]
    assert len(rets) == 2

    ret_10c = [m for m in rets if m.conditions.get("c_rate") == 10.0]
    assert len(ret_10c) == 1
    assert ret_10c[0].normalized_value == 93.0
    assert ret_10c[0].conditions["cycle_count"] == 1000

    ret_20c = [m for m in rets if m.conditions.get("c_rate") == 20.0]
    assert len(ret_20c) == 1
    assert ret_20c[0].normalized_value == 76.0
    assert ret_20c[0].conditions["cycle_count"] == 1000


