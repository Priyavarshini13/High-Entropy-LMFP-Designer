"""
Universal LMFP Chemical Composition & Composite Parser.

Engineered specifically for peer-reviewed LMFP research papers across publishers.
Supports:
- Variable Mn/Fe stoichiometries (e.g. 0.8/0.2, 0.75/0.25, 0.7/0.3, 0.5/0.5, etc.)
- Lithium non-stoichiometry (deficiency 1-x / excess 1+x)
- Transition metal M2-site vacancies
- Single, dual, triple, and high-entropy multi-element elemental doping
- Carbon coatings, rGO, CNT, and conductive composite surface modifications
- Unicode subscripts and formatting variants
- Exact provenance and chemical validation without inventing missing properties
"""

import math
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from chemistry.charge_balance import calculate_charge_balance
from chemistry.dopants import DOPANT_DATABASE, HOST_ELEMENTS, get_valid_oxidation_states
from chemistry.entropy import calculate_configurational_entropy

# ---------------------------------------------------------------------------
# Unicode Character Translation Tables
# ---------------------------------------------------------------------------

UNICODE_SUBSCRIPT_MAP = {
    "₀": "0",
    "₁": "1",
    "₂": "2",
    "₃": "3",
    "₄": "4",
    "₅": "5",
    "₆": "6",
    "₇": "7",
    "₈": "8",
    "₉": "9",
    "․": ".",
    "·": ".",
    "₊": "+",
    "₋": "-",
}

UNICODE_SUPERSCRIPT_MAP = {
    "⁰": "0",
    "¹": "1",
    "²": "2",
    "³": "3",
    "⁴": "4",
    "⁵": "5",
    "⁶": "6",
    "⁷": "7",
    "⁸": "8",
    "⁹": "9",
    "⁺": "+",
    "⁻": "-",
}

# Recognized valid chemical element symbols in battery research
VALID_ELEMENT_SYMBOLS: Set[str] = {
    # Host and common battery elements
    "Li", "Mn", "Fe", "P", "O", "C", "F", "Si", "S", "N",
    # Transition metals and common dopants
    "Mg", "Zn", "Ti", "Nb", "V", "Co", "Ni", "Zr", "Al", "Cr",
    "Cu", "Mo", "W", "Ta", "Sc", "Y", "Sn", "Ga", "In", "Na",
    "K", "Ca", "Ba", "Sr", "B", "Ce", "La", "Nd", "Sm", "Eu",
    "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu", "Bi", "Sb",
    "Ag", "Hf", "Ru", "Rh", "Pd", "Pt", "Au", "Pb", "Te", "Se",
}

# ---------------------------------------------------------------------------
# Composite & Surface Modification Patterns
# ---------------------------------------------------------------------------

COMPOSITE_PATTERNS = [
    # Reduced graphene oxide
    (
        "rGO",
        re.compile(
            r"(?:[/@\-+]\s*(?:rGO|reduced\s+graphene\s+oxide|RGO)|(?:rGO|reduced\s+graphene\s+oxide)\s*(?:composite|nanosheets?))\b",
            re.IGNORECASE,
        ),
    ),
    # Carbon nanotubes
    (
        "CNT",
        re.compile(
            r"(?:[/@\-+]\s*(?:MWCNTs?|SWCNTs?|CNTs?|carbon\s+nanotubes?)|(?:MWCNTs?|SWCNTs?|CNTs?|carbon\s+nanotubes?)\s*(?:composite|network)?)\b",
            re.IGNORECASE,
        ),
    ),
    # Graphene
    (
        "graphene",
        re.compile(
            r"(?:[/@\-+]\s*graphene|graphene\s*(?:nanosheets?|composite))\b",
            re.IGNORECASE,
        ),
    ),
    # Carbon coating / Carbon composite (crucial: must not match single 'C' in formulas without / @ + - prefix or explicit 'carbon')
    (
        "carbon_coating",
        re.compile(
            r"(?:[/@\-+]\s*C\b|[/@\-+]\s*carbon\b|\bcarbon[- ]coated\b|\bC[- ]coated\b|\bcore[- ]shell\b.*?\bcarbon\b|\bcoated\s+with\s+carbon\b|\bcarbon\s+composite\b)",
            re.IGNORECASE,
        ),
    ),
    # Metal oxide / phosphate surface coatings
    (
        "oxide_coating",
        re.compile(
            r"(?:[/@\-+]\s*(?:Al2O3|TiO2|ZrO2|SiO2|Li3PO4|CeO2|ZnO))\b",
            re.IGNORECASE,
        ),
    ),
]

CARBON_CONTENT_PATTERNS = [
    re.compile(
        r"(?:carbon|C|rGO|CNT)\s*(?:content|loading|fraction|weight)?\s*(?:of|is|:)?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:wt\.?%|%)",
        re.IGNORECASE,
    ),
    re.compile(
        r"([0-9]+(?:\.[0-9]+)?)\s*(?:wt\.?%|%)\s*(?:of\s+)?(?:carbon|C|rGO|CNT|carbon\s+coating)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\(\s*([0-9]+(?:\.[0-9]+)?)\s*(?:wt\.?%|%)\s*(?:C|carbon)?\s*\)",
        re.IGNORECASE,
    ),
]


# ---------------------------------------------------------------------------
# Structured Output Dataclass
# ---------------------------------------------------------------------------

@dataclass
class ParsedLMFPComposition:
    """Structured representation of an extracted LMFP chemical composition."""

    original_formula: str
    normalized_formula: str
    base_lmfp_composition: str
    mn_fraction: Optional[float] = None
    fe_fraction: Optional[float] = None
    lithium_stoichiometry: Optional[float] = 1.0
    dopant_list: List[str] = field(default_factory=list)
    dopant_concentrations: Dict[str, float] = field(default_factory=dict)
    substitution_sites: Dict[str, str] = field(default_factory=dict)
    dopant_oxidation_states: Dict[str, int] = field(default_factory=dict)
    composite_type: Optional[str] = "none"
    carbon_content: Optional[float] = None
    carbon_source: Optional[str] = None
    surface_coating: Optional[str] = None
    m2_occupancy: Optional[float] = None
    m2_vacancies: Optional[float] = None
    configurational_entropy_over_r: Optional[float] = None
    entropy_classification: Optional[str] = None
    charge_neutral: Optional[bool] = None
    validation_status: str = "VALID"  # VALID, PROVISIONAL, AMBIGUOUS, INVALID
    warnings: List[str] = field(default_factory=list)
    exact_source_evidence: Optional[str] = None

    def to_review_record(
        self,
        source_pdf: str = "unknown.pdf",
        page_number: Optional[int] = None,
        reference: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Convert into a standard dictionary compatible with literature_review.db."""
        return {
            "source_pdf": source_pdf,
            "page": page_number,
            "reference": reference,
            "composition": self.normalized_formula,
            "base_lmfp_composition": self.base_lmfp_composition,
            "mn_ratio": self.mn_ratio,
            "fe_ratio": self.fe_ratio,
            "li_stoichiometry": self.lithium_stoichiometry,
            "dopants": self.dopant_list,
            "dopant_concentrations": self.dopant_concentrations,
            "composite_type": self.composite_type,
            "carbon_content_wt_pct": self.carbon_content,
            "validation_status": self.validation_status,
            "warnings": self.warnings,
            "evidence_quote": self.exact_source_evidence or self.original_formula,
        }

    @property
    def mn_ratio(self) -> Optional[float]:
        """Calculated Mn / (Mn + Fe) ratio."""
        if self.mn_fraction is not None and self.fe_fraction is not None:
            total = self.mn_fraction + self.fe_fraction
            return round(self.mn_fraction / total, 4) if total > 0 else None
        return None

    @property
    def fe_ratio(self) -> Optional[float]:
        """Calculated Fe / (Mn + Fe) ratio."""
        if self.mn_fraction is not None and self.fe_fraction is not None:
            total = self.mn_fraction + self.fe_fraction
            return round(self.fe_fraction / total, 4) if total > 0 else None
        return None


# ---------------------------------------------------------------------------
# Unicode and String Normalization
# ---------------------------------------------------------------------------

def normalize_formula_text(text: str) -> str:
    """Normalize Unicode subscripts, dashes, and extra whitespace to standard ASCII."""
    if not text:
        return ""

    result = []
    for char in text:
        if char in UNICODE_SUBSCRIPT_MAP:
            result.append(UNICODE_SUBSCRIPT_MAP[char])
        elif char in UNICODE_SUPERSCRIPT_MAP:
            result.append(UNICODE_SUPERSCRIPT_MAP[char])
        elif char in {"–", "—", "−"}:
            result.append("-")
        else:
            result.append(char)

    clean = "".join(result)
    # Normalize unicode forms
    clean = unicodedata.normalize("NFKC", clean)
    # Remove interior whitespace in chemical formula tokens
    clean = clean.strip()
    return clean


# ---------------------------------------------------------------------------
# Composite & Surface Modification Parser
# ---------------------------------------------------------------------------

def extract_composite_info(raw_text: str) -> Tuple[str, str, Optional[float], Optional[str]]:
    """
    Separate surface/composite modification from core inorganic chemical formula.

    Returns:
        (core_formula, composite_type, carbon_content, surface_coating)
    """
    clean_text = normalize_formula_text(raw_text)
    detected_composite = "none"
    detected_coating = None
    carbon_wt_pct = None

    # Check for explicit carbon content in surrounding text
    for pat in CARBON_CONTENT_PATTERNS:
        m = pat.search(clean_text)
        if m:
            try:
                carbon_wt_pct = float(m.group(1))
                break
            except ValueError:
                pass

    core_formula = clean_text

    # Search for known composite patterns
    for comp_name, pat in COMPOSITE_PATTERNS:
        match = pat.search(core_formula)
        if match:
            detected_composite = comp_name
            # If it's a specific oxide coating, capture the exact oxide formula
            if comp_name == "oxide_coating":
                detected_coating = match.group(0).lstrip("/@-+ ")

            # Strip the composite tag from the core formula string
            core_formula = pat.sub("", core_formula).strip()
            # Also clean trailing slashes, dashes, or @ symbols left behind
            core_formula = re.sub(r"[/@\-+]\s*$", "", core_formula).strip()
            break

    # Also clean trailing parenthetical annotations like "(2.5 wt% C)" from core formula
    core_formula = re.sub(r"\s*\(\s*[\d\.]+\s*(?:wt\.?%|%)\s*(?:C|carbon)?\s*\)", "", core_formula).strip()

    return core_formula, detected_composite, carbon_wt_pct, detected_coating


# ---------------------------------------------------------------------------
# Core Chemical Formula Parser
# ---------------------------------------------------------------------------

def _parse_stoichiometric_number(subscript: str) -> Optional[float]:
    """Parse numeric subscript string safely."""
    if not subscript or subscript.strip() == "":
        return 1.0

    subscript = subscript.strip()
    try:
        val = float(subscript)
        return val
    except ValueError:
        return None


def parse_lmfp_composition(
    formula_text: str,
    evidence_text: Optional[str] = None,
) -> ParsedLMFPComposition:
    """
    Universal LMFP chemical composition parser.

    Accurately handles:
    - Pure LMFP (e.g. LiMn0.8Fe0.2PO4)
    - Non-stoichiometric Li (e.g. Li0.95Mn0.8Fe0.2PO4, Li1.05...)
    - Single, dual, triple, high-entropy doping (Mg, Ti, V, Al, Co, Ni, Zn, etc.)
    - M2 vacancies (Mn + Fe < 1.0 without other dopants)
    - Composites (/C, @C, /rGO, /CNTs)
    - Ambiguous variable notations (LiMnxFe1-xPO4)
    - Chemical validation, charge neutrality check, and entropy evaluation.
    """
    original = formula_text.strip()
    warnings: List[str] = []

    # 1. Normalize text and extract composite info
    core_formula, composite_type, carbon_pct, oxide_coating = extract_composite_info(original)

    # Check if formula contains algebraic variables (x, y, delta)
    # Must match lowercase variables like x, y, z or delta without matching elements like Zn, Zr, or Y
    has_variables = bool(
        re.search(
            r"(?:1\s*-\s*[xXyYzZδΔ]|(?:[A-Z][a-z]?|\))\s*([xyzδΔ])(?![a-z])|[_\s][xyzδΔ][\s_\-\]]|\bdelta\b|4\s*-\s*[xδΔ])",
            core_formula,
        )
    )

    # 2. Check for LMFP baseline presence: must contain Li (or olivine phosphate frame) and Mn/Fe and PO4
    # Note: High-entropy variants might substitute almost all Fe or Mn, but must have Mn or Fe and PO4
    has_mn_or_fe = ("Mn" in core_formula or "Fe" in core_formula)
    has_po4 = bool(re.search(r"PO_?4|\(PO4\)|P[0-9\.]*O4", core_formula, re.IGNORECASE))
    has_li = ("Li" in core_formula)

    if not (has_mn_or_fe and has_po4):
        return ParsedLMFPComposition(
            original_formula=original,
            normalized_formula=original,
            base_lmfp_composition="UNKNOWN",
            validation_status="INVALID",
            composite_type=composite_type,
            carbon_content=carbon_pct,
            warnings=["Formula does not contain LMFP olivine structure (Mn/Fe and PO4 group)."],
            exact_source_evidence=evidence_text or original,
        )

    # If formula contains algebraic parameters (e.g. LiMnxFe1-xPO4)
    if has_variables:
        # Determine variable Mn/Fe if possible
        return ParsedLMFPComposition(
            original_formula=original,
            normalized_formula=core_formula + (f"/{composite_type}" if composite_type not in ("none", "carbon_coating") else ("/C" if composite_type == "carbon_coating" else "")),
            base_lmfp_composition="LiMnxFe1-xPO4",
            validation_status="AMBIGUOUS",
            composite_type=composite_type,
            carbon_content=carbon_pct,
            warnings=["Formula contains algebraic variables (e.g. x, 1-x, delta); requires specific sample values."],
            exact_source_evidence=evidence_text or original,
        )

    # 3. Tokenize chemical elements and their numeric subscripts
    # Regex splits element symbols: Capital letter followed by optional lowercase letter,
    # followed by optional decimal number.
    # Grouping brackets: [ ... ] or ( ... ) for M2 site
    element_pattern = re.compile(r"([A-Z][a-z]?)([\d\.]*(?:[eE][+-]?\d+)?)")

    # Clean brackets for elemental scanning, but track bracketed M2 contents if present
    bracket_m = re.search(r"(?:\[|\()([^\]\)]+)(?:\]|\))", core_formula)
    bracket_content = bracket_m.group(1) if bracket_m else None

    # Find all elements and their raw numbers
    tokens: List[Tuple[str, str]] = element_pattern.findall(core_formula)

    if not tokens:
        return ParsedLMFPComposition(
            original_formula=original,
            normalized_formula=original,
            base_lmfp_composition="UNKNOWN",
            validation_status="INVALID",
            warnings=["Could not parse element tokens from formula."],
            exact_source_evidence=evidence_text or original,
        )

    # Verify all element symbols are real chemical elements
    parsed_elements: Dict[str, float] = {}
    for elem, num_str in tokens:
        if elem not in VALID_ELEMENT_SYMBOLS:
            warnings.append(f"Unrecognized chemical element symbol: '{elem}'.")
            return ParsedLMFPComposition(
                original_formula=original,
                normalized_formula=original,
                base_lmfp_composition="UNKNOWN",
                validation_status="INVALID",
                warnings=warnings,
                exact_source_evidence=evidence_text or original,
            )

        val = _parse_stoichiometric_number(num_str)
        if val is None:
            warnings.append(f"Invalid stoichiometric number for {elem}: '{num_str}'.")
            return ParsedLMFPComposition(
                original_formula=original,
                normalized_formula=original,
                base_lmfp_composition="UNKNOWN",
                validation_status="INVALID",
                warnings=warnings,
                exact_source_evidence=evidence_text or original,
            )
        # If element occurs multiple times, sum fractions
        parsed_elements[elem] = parsed_elements.get(elem, 0.0) + val

    # 4. Extract Li, Mn, Fe, P, O, and dopants
    li_stoich = parsed_elements.get("Li", 1.0 if has_li else 0.0)
    mn_frac = parsed_elements.get("Mn", 0.0)
    fe_frac = parsed_elements.get("Fe", 0.0)
    p_frac = parsed_elements.get("P", 1.0)
    o_frac = parsed_elements.get("O", 4.0)

    # Elemental dopants: any cation that is NOT Li, Mn, Fe, P, O
    # CRITICAL NEGATIVE CONTROL: 'C' from composite coating has already been removed in step 1.
    # If a stray 'C' appears here, check whether it was an unstripped composite or explicit dopant.
    dopant_dict: Dict[str, float] = {}
    dopant_list: List[str] = []
    substitution_sites: Dict[str, str] = {}
    dopant_oxidation_states: Dict[str, int] = {}

    for elem, frac in parsed_elements.items():
        if elem in {"Li", "Mn", "Fe", "P", "O"}:
            continue
        if elem == "C":
            # Stray carbon: if user wrote LiMn0.8Fe0.2PO4 C or similar, treat as composite, NOT elemental doping!
            composite_type = "carbon_coating"
            warnings.append("Carbon detected alongside olivine formula; classified as surface composite, not lattice dopant.")
            continue

        dopant_dict[elem] = round(frac, 4)
        dopant_list.append(elem)

        # Check if site is explicitly indicated by bracketing
        if bracket_content and elem in bracket_content:
            substitution_sites[elem] = "M2 (bracketed)"
        else:
            # Do NOT infer site from formula alone per strict requirements!
            pass

        # Check for explicit oxidation states in original text (e.g. Ti4+, Mg2+, V5+)
        ox_match = re.search(rf"\b{elem}\s*([1-6])\+|\b{elem}\s*\(([IVXLCDM]+)\)", original)
        if ox_match:
            try:
                ox_str = ox_match.group(1)
                dopant_oxidation_states[elem] = int(ox_str)
            except (ValueError, TypeError):
                pass

    # 5. Calculate M2-site Occupancy & Vacancies
    dopant_sum = sum(dopant_dict.values())
    m2_occupancy = round(mn_frac + fe_frac + dopant_sum, 4)
    m2_vacancies = round(1.0 - m2_occupancy, 4) if m2_occupancy < 1.0 else 0.0

    # 6. Base LMFP Composition Formula
    if mn_frac + fe_frac > 0:
        tot_mf = mn_frac + fe_frac
        norm_mn = round(mn_frac / tot_mf, 4) if tot_mf > 0 else 0.0
        norm_fe = round(fe_frac / tot_mf, 4) if tot_mf > 0 else 0.0
        base_lmfp = f"LiMn{norm_mn:g}Fe{norm_fe:g}PO4"
    else:
        base_lmfp = "LiMnPO4"

    # 7. Construct Clean Normalized Chemical Formula
    # Format: Li_x [Mn_m Fe_f Dop1_d1...] PO4 / Composite
    parts = []
    if abs(li_stoich - 1.0) > 1e-4:
        parts.append(f"Li{li_stoich:g}")
    else:
        parts.append("Li")

    m2_parts = []
    if mn_frac > 0:
        m2_parts.append(f"Mn{mn_frac:g}")
    if fe_frac > 0:
        m2_parts.append(f"Fe{fe_frac:g}")
    for d_elem in sorted(dopant_list):
        m2_parts.append(f"{d_elem}{dopant_dict[d_elem]:g}")

    if dopant_list or abs(m2_occupancy - 1.0) > 1e-4:
        parts.append("[" + "".join(m2_parts) + "]")
    else:
        parts.append("".join(m2_parts))

    parts.append("PO4")

    norm_chem = "".join(parts)
    if composite_type == "carbon_coating":
        norm_formula = f"{norm_chem}/C"
    elif composite_type in {"rGO", "CNT", "graphene"}:
        norm_formula = f"{norm_chem}/{composite_type}"
    elif composite_type == "oxide_coating" and oxide_coating:
        norm_formula = f"{norm_chem}@{oxide_coating}"
    else:
        norm_formula = norm_chem

    # 8. Chemical Validation & Configurational Entropy
    validation_status = "VALID"

    # Entropy evaluation if doped
    s_config_r = None
    entropy_class = None
    if dopant_list:
        dopants_input = [{"symbol": k, "fraction": v} for k, v in dopant_dict.items()]
        entropy_res = calculate_configurational_entropy(
            mn_frac=mn_frac,
            fe_frac=fe_frac,
            dopants=dopants_input,
            phi_m2_vacancy=max(0.0, m2_vacancies),
        )
        s_config_r = round(entropy_res.s_config_over_r, 4)
        entropy_class = entropy_res.classification

    # Charge balance evaluation
    charge_neutral = None
    if dopant_list:
        # Check if we have oxidation states
        known_ox = True
        dopants_charge_input = []
        for d_elem, d_frac in dopant_dict.items():
            if d_elem in dopant_oxidation_states:
                ox = dopant_oxidation_states[d_elem]
            else:
                # Check if element has a unique allowed oxidation state in DOPANT_DATABASE
                valid_states = get_valid_oxidation_states(d_elem)
                if len(valid_states) == 1:
                    ox = valid_states[0]
                else:
                    known_ox = False
                    break
            dopants_charge_input.append({"symbol": d_elem, "fraction": d_frac, "oxidation_state": ox})

        if known_ox:
            cb_res = calculate_charge_balance(
                mn_frac=mn_frac,
                fe_frac=fe_frac,
                dopants=dopants_charge_input,
                user_li=li_stoich,
            )
            charge_neutral = cb_res.is_balanced
            if not cb_res.is_balanced:
                warnings.append(
                    f"Nominal composition has net charge disparity ({cb_res.net_charge_before:+.3f} e-); "
                    "requires charge compensation or defect accommodation."
                )
        else:
            validation_status = "PROVISIONAL"
            warnings.append(
                "Dopant oxidation state not uniquely specified in literature; charge balance unverified."
            )

    # Check for extreme or physically suspicious stoichiometry
    if mn_frac > 1.2 or fe_frac > 1.2 or li_stoich > 1.5 or li_stoich < 0.2:
        validation_status = "PROVISIONAL"
        warnings.append(f"Unusual stoichiometry detected (Li={li_stoich}, Mn={mn_frac}, Fe={fe_frac}).")

    if abs(m2_occupancy - 1.0) > 0.15:
        validation_status = "PROVISIONAL"
        warnings.append(f"M2-site occupancy sum ({m2_occupancy}) deviates > 15% from ideal 1.0.")

    return ParsedLMFPComposition(
        original_formula=original,
        normalized_formula=norm_formula,
        base_lmfp_composition=base_lmfp,
        mn_fraction=round(mn_frac, 4),
        fe_fraction=round(fe_frac, 4),
        lithium_stoichiometry=round(li_stoich, 4),
        dopant_list=dopant_list,
        dopant_concentrations=dopant_dict,
        substitution_sites=substitution_sites,
        dopant_oxidation_states=dopant_oxidation_states,
        composite_type=composite_type,
        carbon_content=carbon_pct,
        surface_coating=oxide_coating,
        m2_occupancy=m2_occupancy,
        m2_vacancies=m2_vacancies,
        configurational_entropy_over_r=s_config_r,
        entropy_classification=entropy_class,
        charge_neutral=charge_neutral,
        validation_status=validation_status,
        warnings=warnings,
        exact_source_evidence=evidence_text or original,
    )


# ---------------------------------------------------------------------------
# Deduplication and Equivalence
# ---------------------------------------------------------------------------

def are_compositions_equivalent(
    comp1: ParsedLMFPComposition,
    comp2: ParsedLMFPComposition,
    tol: float = 1e-3,
) -> bool:
    """Return True if two parsed LMFP compositions describe the same material."""
    if comp1.validation_status == "INVALID" or comp2.validation_status == "INVALID":
        return False

    # Check host fractions
    mn1, mn2 = comp1.mn_fraction or 0.0, comp2.mn_fraction or 0.0
    fe1, fe2 = comp1.fe_fraction or 0.0, comp2.fe_fraction or 0.0
    li1, li2 = comp1.lithium_stoichiometry or 1.0, comp2.lithium_stoichiometry or 1.0

    if abs(mn1 - mn2) > tol or abs(fe1 - fe2) > tol or abs(li1 - li2) > tol:
        return False

    # Check dopants
    if set(comp1.dopant_list) != set(comp2.dopant_list):
        return False

    for elem in comp1.dopant_list:
        c1 = comp1.dopant_concentrations.get(elem, 0.0)
        c2 = comp2.dopant_concentrations.get(elem, 0.0)
        if abs(c1 - c2) > tol:
            return False

    # Check composite
    if comp1.composite_type != comp2.composite_type:
        return False

    return True


def deduplicate_compositions(
    compositions: List[ParsedLMFPComposition],
) -> List[ParsedLMFPComposition]:
    """
    Deduplicate multiple mentions of the same nominal composition.

    Prevents repeated mentions in abstract, introduction, and body text
    from creating redundant sample entries.
    """
    unique: List[ParsedLMFPComposition] = []
    for comp in compositions:
        if not any(are_compositions_equivalent(comp, existing) for existing in unique):
            unique.append(comp)
    return unique
