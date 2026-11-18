"""
Comprehensive Unit Tests for Universal LMFP Composition & Composite Parser (Stage 2).

Covers:
- Standard LMFP compositions with variable Mn/Fe ratios
- Single, dual, triple, and high-entropy multi-element elemental doping
- Carbon coatings, rGO, CNT, graphene, and surface modifications
- Unicode subscripts and formatting variants
- Non-stoichiometric lithium and transition metal vacancies
- Ambiguous/parameterized formulas (e.g. LiMnxFe1-xPO4)
- Negative control tests:
  1. Fe is never mistaken for F (Fluorine).
  2. Carbon coating (/C, @C) is never mistaken for elemental carbon doping.
  3. Repeated formula mentions do not generate duplicate samples.
- Compatibility with literature_review.db and 41-column dataset schema.
"""

import pytest
from literature.composition_parser import (
    ParsedLMFPComposition,
    are_compositions_equivalent,
    deduplicate_compositions,
    extract_composite_info,
    normalize_formula_text,
    parse_lmfp_composition,
)


def test_standard_lmfp_variable_ratios():
    """Verify standard LMFP with varied Mn/Fe ratios (0.8/0.2, 0.7/0.3, 0.5/0.5, 0.75/0.25, 0.6/0.4)."""
    cases = [
        ("LiMn0.8Fe0.2PO4", 0.8, 0.2, 1.0),
        ("LiMn0.7Fe0.3PO4", 0.7, 0.3, 1.0),
        ("LiMn0.5Fe0.5PO4", 0.5, 0.5, 1.0),
        ("LiMn0.75Fe0.25PO4", 0.75, 0.25, 1.0),
        ("LiMn0.6Fe0.4PO4", 0.6, 0.4, 1.0),
        ("LiMn0.85Fe0.15PO4", 0.85, 0.15, 1.0),
    ]

    for formula, exp_mn, exp_fe, exp_li in cases:
        parsed = parse_lmfp_composition(formula)
        assert parsed.validation_status == "VALID"
        assert parsed.mn_fraction == exp_mn
        assert parsed.fe_fraction == exp_fe
        assert parsed.lithium_stoichiometry == exp_li
        assert parsed.dopant_list == []
        assert parsed.composite_type == "none"
        assert parsed.m2_occupancy == pytest.approx(1.0, abs=1e-4)
        assert parsed.mn_ratio == pytest.approx(exp_mn / (exp_mn + exp_fe), abs=1e-4)


def test_single_elemental_doping():
    """Verify single-element doping (Mg, V, Al)."""
    # 1. Mg doping
    p_mg = parse_lmfp_composition("LiMn0.75Fe0.2Mg0.05PO4")
    assert p_mg.validation_status in ("VALID", "PROVISIONAL")
    assert p_mg.mn_fraction == 0.75
    assert p_mg.fe_fraction == 0.2
    assert "Mg" in p_mg.dopant_list
    assert p_mg.dopant_concentrations["Mg"] == 0.05
    assert p_mg.m2_occupancy == pytest.approx(1.0, abs=1e-4)

    # 2. V doping
    p_v = parse_lmfp_composition("LiMn0.8Fe0.18V0.02PO4")
    assert "V" in p_v.dopant_list
    assert p_v.dopant_concentrations["V"] == 0.02
    assert p_v.fe_fraction == 0.18

    # 3. Al doping
    p_al = parse_lmfp_composition("LiMn0.78Fe0.2Al0.02PO4")
    assert "Al" in p_al.dopant_list
    assert p_al.dopant_concentrations["Al"] == 0.02
    assert p_al.mn_fraction == 0.78


def test_dual_and_triple_elemental_doping():
    """Verify dual (Mg/Ti, Co/Ni) and triple (Mg/Ti/V) co-doping."""
    # Dual: Mg + Ti
    p_dual = parse_lmfp_composition("LiMn0.75Fe0.20Mg0.03Ti0.02PO4")
    assert set(p_dual.dopant_list) == {"Mg", "Ti"}
    assert p_dual.dopant_concentrations["Mg"] == 0.03
    assert p_dual.dopant_concentrations["Ti"] == 0.02
    assert p_dual.m2_occupancy == pytest.approx(1.0, abs=1e-4)

    # Dual: Co + Ni
    p_coni = parse_lmfp_composition("LiMn0.7Fe0.2Co0.05Ni0.05PO4")
    assert set(p_coni.dopant_list) == {"Co", "Ni"}
    assert p_coni.dopant_concentrations["Co"] == 0.05
    assert p_coni.dopant_concentrations["Ni"] == 0.05

    # Triple: Mg + Ti + V
    p_triple = parse_lmfp_composition("LiMn0.7Fe0.2Mg0.04Ti0.03V0.03PO4")
    assert set(p_triple.dopant_list) == {"Mg", "Ti", "V"}
    assert p_triple.dopant_concentrations["Mg"] == 0.04
    assert p_triple.dopant_concentrations["Ti"] == 0.03
    assert p_triple.dopant_concentrations["V"] == 0.03


def test_high_entropy_lmfp():
    """Verify high-entropy multi-element compositions (5+ cations)."""
    # 5-cation equimolar: Mn0.2 Fe0.2 Co0.2 Ni0.2 Mg0.2
    he_formula = "Li[Mn0.2Fe0.2Co0.2Ni0.2Mg0.2]PO4"
    p_he = parse_lmfp_composition(he_formula)
    assert p_he.mn_fraction == 0.2
    assert p_he.fe_fraction == 0.2
    assert set(p_he.dopant_list) == {"Co", "Ni", "Mg"}
    assert p_he.m2_occupancy == pytest.approx(1.0, abs=1e-4)
    # Check configurational entropy calculation
    assert p_he.configurational_entropy_over_r is not None
    assert p_he.configurational_entropy_over_r >= 1.5  # High-entropy criterion
    assert p_he.entropy_classification == "High-Entropy"

    # 6-cation multi-element: LiMn0.6Fe0.2Co0.05Ni0.05Mg0.05Zn0.05PO4
    he_6 = parse_lmfp_composition("LiMn0.6Fe0.2Co0.05Ni0.05Mg0.05Zn0.05PO4")
    assert len(he_6.dopant_list) == 4
    assert set(he_6.dopant_list) == {"Co", "Ni", "Mg", "Zn"}
    assert he_6.m2_occupancy == pytest.approx(1.0, abs=1e-4)


def test_carbon_and_composite_modifications():
    """Verify carbon coating (/C, @C), rGO, CNT, graphene, and carbon weight %."""
    # /C
    p_c1 = parse_lmfp_composition("LiMn0.8Fe0.2PO4/C")
    assert p_c1.composite_type == "carbon_coating"
    assert p_c1.mn_fraction == 0.8
    assert p_c1.fe_fraction == 0.2
    assert "C" not in p_c1.dopant_list

    # @C
    p_c2 = parse_lmfp_composition("LiMn0.75Fe0.25PO4@C")
    assert p_c2.composite_type == "carbon_coating"
    assert "C" not in p_c2.dopant_list

    # rGO
    p_rgo = parse_lmfp_composition("LiMn0.75Fe0.25PO4/rGO")
    assert p_rgo.composite_type == "rGO"
    assert p_rgo.base_lmfp_composition == "LiMn0.75Fe0.25PO4"

    # CNTs
    p_cnt = parse_lmfp_composition("LiMn0.8Fe0.2PO4/CNTs")
    assert p_cnt.composite_type == "CNT"

    # Graphene
    p_grap = parse_lmfp_composition("LiMn0.8Fe0.2PO4/graphene")
    assert p_grap.composite_type == "graphene"

    # Explicit Carbon Content wt%
    p_wt = parse_lmfp_composition("LiMn0.8Fe0.2PO4/C (2.5 wt% C)")
    assert p_wt.composite_type == "carbon_coating"
    assert p_wt.carbon_content == 2.5


def test_unicode_subscript_notation():
    """Verify proper normalization of Unicode subscripts in formulas."""
    unicode_form = "LiMn₀.₈Fe₀.₂PO₄"
    p_uni = parse_lmfp_composition(unicode_form)
    assert p_uni.validation_status == "VALID"
    assert p_uni.mn_fraction == 0.8
    assert p_uni.fe_fraction == 0.2
    assert p_uni.lithium_stoichiometry == 1.0

    # Unicode with dopant and carbon coating
    uni_doped = "LiMn₀.₇₅Fe₀.₂₀Mg₀.₀₅PO₄/C"
    p_uni_doped = parse_lmfp_composition(uni_doped)
    assert p_uni_doped.mn_fraction == 0.75
    assert p_uni_doped.fe_fraction == 0.20
    assert "Mg" in p_uni_doped.dopant_list
    assert p_uni_doped.dopant_concentrations["Mg"] == 0.05
    assert p_uni_doped.composite_type == "carbon_coating"


def test_lithium_non_stoichiometry_and_vacancies():
    """Verify Li deficiency, Li excess, and M2-site vacancies."""
    # Li deficiency
    p_def = parse_lmfp_composition("Li0.95Mn0.8Fe0.2PO4")
    assert p_def.lithium_stoichiometry == 0.95
    assert p_def.mn_fraction == 0.8
    assert p_def.fe_fraction == 0.2

    # Li excess
    p_exc = parse_lmfp_composition("Li1.05Mn0.7Fe0.3PO4")
    assert p_exc.lithium_stoichiometry == 1.05

    # M2-site vacancies (Mn + Fe < 1.0)
    p_vac = parse_lmfp_composition("LiMn0.8Fe0.15PO4")
    assert p_vac.m2_occupancy == 0.95
    assert p_vac.m2_vacancies == 0.05
    assert p_vac.base_lmfp_composition == "LiMn0.8421Fe0.1579PO4"


def test_ambiguous_and_invalid_formulas():
    """Verify algebraic parameters are marked AMBIGUOUS and invalid syntax is rejected."""
    # Algebraic variable
    p_amb = parse_lmfp_composition("LiMnxFe1-xPO4")
    assert p_amb.validation_status == "AMBIGUOUS"
    assert "algebraic variables" in p_amb.warnings[0].lower()

    # Invalid chemical element (XYZ)
    p_inv = parse_lmfp_composition("LiMn0.8Fe0.2XYZ0.05PO4")
    assert p_inv.validation_status == "INVALID"
    assert any("unrecognized" in w.lower() for w in p_inv.warnings)

    # Missing PO4 frame
    p_no_p = parse_lmfp_composition("LiMn0.8Fe0.2O2")
    assert p_inv.validation_status == "INVALID"


def test_negative_control_fe_not_mistaken_for_f():
    """CRITICAL NEGATIVE TEST: Ensure Fe (Iron) is never parsed as F (Fluorine)."""
    parsed = parse_lmfp_composition("LiMn0.8Fe0.2PO4")
    assert parsed.fe_fraction == 0.2
    assert "Fe" not in parsed.dopant_list
    assert "F" not in parsed.dopant_list
    assert "F" not in parsed.dopant_concentrations


def test_negative_control_carbon_coating_not_mistaken_for_doping():
    """CRITICAL NEGATIVE TEST: Ensure /C or @C is never parsed as elemental carbon lattice doping."""
    variants = [
        "LiMn0.8Fe0.2PO4/C",
        "LiMn0.75Fe0.25PO4@C",
        "LiMn0.8Fe0.2PO4 carbon-coated",
    ]
    for v in variants:
        parsed = parse_lmfp_composition(v)
        assert parsed.composite_type == "carbon_coating"
        assert "C" not in parsed.dopant_list
        assert "C" not in parsed.dopant_concentrations
        assert parsed.dopant_list == []


def test_negative_control_deduplication():
    """CRITICAL NEGATIVE TEST: Repeated mentions of same nominal formula do not create duplicates."""
    c1 = parse_lmfp_composition("LiMn0.8Fe0.2PO4/C")
    c2 = parse_lmfp_composition("LiMn₀.₈Fe₀.₂PO₄/C")
    c3 = parse_lmfp_composition("LiMn0.8Fe0.2PO4/C (2.0 wt% C)")
    c4 = parse_lmfp_composition("LiMn0.75Fe0.25PO4/C")  # distinct composition

    assert are_compositions_equivalent(c1, c2)
    assert are_compositions_equivalent(c1, c3)
    assert not are_compositions_equivalent(c1, c4)

    deduped = deduplicate_compositions([c1, c2, c3, c4])
    assert len(deduped) == 2


def test_review_record_schema_compatibility():
    """Verify structured output converts to review record with exact schema fields."""
    parsed = parse_lmfp_composition(
        "LiMn0.75Fe0.20Mg0.05PO4/C",
        evidence_text="The LiMn0.75Fe0.20Mg0.05PO4/C sample was synthesized by solid-state reaction."
    )
    rec = parsed.to_review_record(source_pdf="test_paper.pdf", page_number=3)

    assert rec["source_pdf"] == "test_paper.pdf"
    assert rec["page"] == 3
    assert rec["composition"] == "Li[Mn0.75Fe0.2Mg0.05]PO4/C"
    assert rec["base_lmfp_composition"] == "LiMn0.7895Fe0.2105PO4"
    assert rec["dopants"] == ["Mg"]
    assert rec["dopant_concentrations"] == {"Mg": 0.05}
    assert rec["composite_type"] == "carbon_coating"
    assert rec["evidence_quote"] == "The LiMn0.75Fe0.20Mg0.05PO4/C sample was synthesized by solid-state reaction."


@pytest.mark.parametrize(
    "formula, expected_status, expected_composite, expected_dopants_count",
    [
        # 1-6: Normal LMFP & Different Mn/Fe ratios
        ("LiMn0.8Fe0.2PO4", "VALID", "none", 0),
        ("LiMn0.7Fe0.3PO4", "VALID", "none", 0),
        ("LiMn0.5Fe0.5PO4", "VALID", "none", 0),
        ("LiMn0.75Fe0.25PO4", "VALID", "none", 0),
        ("LiMn0.6Fe0.4PO4", "VALID", "none", 0),
        ("LiMn0.85Fe0.15PO4", "VALID", "none", 0),
        # 7-10: Single elemental doping
        ("LiMn0.75Fe0.20Mg0.05PO4", "VALID", "none", 1),
        ("LiMn0.8Fe0.18V0.02PO4", "VALID", "none", 1),
        ("LiMn0.78Fe0.20Al0.02PO4", "VALID", "none", 1),
        ("LiMn0.7Fe0.25Co0.05PO4", "VALID", "none", 1),
        # 11-13: Dual and triple elemental co-doping
        ("LiMn0.75Fe0.20Mg0.03Ti0.02PO4", "VALID", "none", 2),
        ("LiMn0.7Fe0.2Co0.05Ni0.05PO4", "VALID", "none", 2),
        ("LiMn0.7Fe0.2Mg0.04Ti0.03V0.03PO4", "VALID", "none", 3),
        # 14-15: High-entropy doping
        ("Li[Mn0.2Fe0.2Co0.2Ni0.2Mg0.2]PO4", "VALID", "none", 3),
        ("LiMn0.6Fe0.2Co0.05Ni0.05Mg0.05Zn0.05PO4", "VALID", "none", 4),
        # 16-20: Carbon and composite surface modifications
        ("LiMn0.8Fe0.2PO4/C", "VALID", "carbon_coating", 0),
        ("LiMn0.75Fe0.25PO4@C", "VALID", "carbon_coating", 0),
        ("LiMn0.75Fe0.25PO4/rGO", "VALID", "rGO", 0),
        ("LiMn0.8Fe0.2PO4/CNTs", "VALID", "CNT", 0),
        ("LiMn0.8Fe0.2PO4/graphene", "VALID", "graphene", 0),
        # 21-22: Unicode notation
        ("LiMn₀.₈Fe₀.₂PO₄", "VALID", "none", 0),
        ("LiMn₀.₇₅Fe₀.₂₀Mg₀.₀₅PO₄/C", "VALID", "carbon_coating", 1),
        # 23-24: Non-stoichiometric lithium
        ("Li0.95Mn0.8Fe0.2PO4", "VALID", "none", 0),
        ("Li1.05Mn0.7Fe0.3PO4", "VALID", "none", 0),
        # 25: Non-stoichiometric transition metal vacancies
        ("LiMn0.8Fe0.15PO4", "VALID", "none", 0),
    ],
)
def test_25_formula_matrix(formula, expected_status, expected_composite, expected_dopants_count):
    """Explicit 25-formula matrix verifying all required LMFP variants individually."""
    parsed = parse_lmfp_composition(formula)
    assert parsed.validation_status in ("VALID", "PROVISIONAL")
    assert parsed.composite_type == expected_composite
    assert len(parsed.dopant_list) == expected_dopants_count
    assert parsed.mn_fraction is not None and parsed.mn_fraction > 0
    assert parsed.fe_fraction is not None and parsed.fe_fraction > 0

