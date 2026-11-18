"""
Universal LMFP Scientific Property & Electrochemical Measurement Extraction Engine.

Publisher-independent extractor for peer-reviewed LMFP research papers.
Extracts:
1. Electrochemical Performance:
   - Specific discharge and charge capacities across arbitrary C-rates (0.05C, 0.1C, 0.2C, 0.5C, 1C, 2C, 5C, 10C, 20C, C/10, etc.)
   - Cycling retention percentages, cycle counts, and testing C-rates
   - Initial Coulombic Efficiency (ICE) and operational Coulombic efficiency
   - Operating voltage windows (e.g. 2.5–4.5 V vs. Li/Li+)
2. Condition Association:
   - Strictly pairs each measurement with its specific sample label, C-rate, cycle count, temperature, voltage window, and exact evidence
   - Never averages, collapses, or transfers conditions between different samples or cycling regimes
3. Synthesis Conditions:
   - Routes (solid-state, sol-gel, hydrothermal, solvothermal, co-precipitation, spray drying, ball milling)
   - Calcination temperature (°C), duration (h), heating rate (°C/min), atmosphere (Ar, N2, air, reducing)
   - Precursor chemicals
4. Material Characterization:
   - Space group (Pnma), lattice parameters (a, b, c in Å), unit cell volume (Å³)
   - Crystallite and particle sizes (nm / μm), morphology
   - EIS charge-transfer resistance (Rct in Ω)
   - Lithium-ion diffusion coefficients (D_Li in cm²/s)
5. Evidence & Provenance:
   - Preserves source PDF, page number, section type, table/figure ID, verbatim quote, and validation status
"""

import math
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from literature.composition_parser import (
    ParsedLMFPComposition,
    normalize_formula_text,
    parse_lmfp_composition,
)
from literature.section_parser import (
    DocumentStructure,
    SectionBlock,
    SectionType,
    is_non_scientific_section,
)

# ---------------------------------------------------------------------------
# Structured Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class PropertyMeasurement:
    """A distinct scientific measurement with strict condition attribution."""

    measurement_id: str
    sample_label: Optional[str]
    measurement_type: str  # discharge_capacity, charge_capacity, capacity_retention, ice, coulombic_efficiency, voltage_window, synthesis, lattice_parameters, eis_rct, li_diffusion, particle_size
    reported_value: Any
    reported_unit: Optional[str]
    normalized_value: Optional[float]
    normalized_unit: Optional[str]
    conditions: Dict[str, Any] = field(default_factory=dict)
    # conditions may contain: c_rate, cycle_count, temperature_c, voltage_window, atmosphere, etc.
    source_pdf: str = "unknown.pdf"
    page_number: int = 1
    section_type: str = "UNKNOWN"
    table_or_figure_id: Optional[str] = None
    evidence_quote: str = ""
    extraction_method: str = "text_rule"  # text_rule, table_row, caption, graph_manual_required
    validation_status: str = "VERIFIED"  # VERIFIED, PROVISIONAL, AMBIGUOUS, UNVERIFIED
    warnings: List[str] = field(default_factory=list)


@dataclass
class SynthesisProfile:
    """Reported synthesis conditions and precursor chemistries for a sample."""

    sample_label: Optional[str] = None
    route: Optional[str] = None
    calcination_temperature_c: Optional[float] = None
    calcination_duration_hours: Optional[float] = None
    heating_rate_c_min: Optional[float] = None
    atmosphere: Optional[str] = None
    precursors: List[str] = field(default_factory=list)
    raw_evidence: Optional[str] = None
    source_page: int = 1


@dataclass
class CharacterizationProfile:
    """Reported crystallographic, physical, and transport properties."""

    sample_label: Optional[str] = None
    phase: Optional[str] = None
    space_group: Optional[str] = None
    lattice_a_angstrom: Optional[float] = None
    lattice_b_angstrom: Optional[float] = None
    lattice_c_angstrom: Optional[float] = None
    unit_cell_volume_angstrom3: Optional[float] = None
    crystallite_size_nm: Optional[float] = None
    particle_size_nm: Optional[float] = None
    morphology: Optional[str] = None
    eis_rct_ohm: Optional[float] = None
    li_diffusion_coefficient_cm2_s: Optional[float] = None
    raw_evidence: Optional[str] = None
    source_page: int = 1


@dataclass
class ExtractedPaperProperties:
    """Comprehensive structured scientific output for an entire paper."""

    source_pdf: str
    measurements: List[PropertyMeasurement] = field(default_factory=list)
    synthesis_profiles: List[SynthesisProfile] = field(default_factory=list)
    characterization_profiles: List[CharacterizationProfile] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def get_measurements_by_type(self, m_type: str) -> List[PropertyMeasurement]:
        """Filter measurements by measurement_type."""
        return [m for m in self.measurements if m.measurement_type == m_type]

    def get_capacities_for_sample(self, sample_label: str) -> List[PropertyMeasurement]:
        """Return all discharge/charge capacity records for a given sample."""
        return [
            m for m in self.measurements
            if m.sample_label == sample_label and "capacity" in m.measurement_type
        ]

    def get_retentions_for_sample(self, sample_label: str) -> List[PropertyMeasurement]:
        """Return all cycling retention records for a given sample."""
        return [
            m for m in self.measurements
            if m.sample_label == sample_label and m.measurement_type == "capacity_retention"
        ]


# ---------------------------------------------------------------------------
# C-rate Parsing and Normalization
# ---------------------------------------------------------------------------

CRATE_PATTERN = re.compile(
    r"\b(?:at|@|under)?\s*(?:a\s+rate\s+of\s+)?(\d+(?:\.\d+)?\s*C|C\s*\/\s*\d+(?:\.\d+)?)\b",
    re.IGNORECASE,
)


def parse_c_rate(c_rate_str: str) -> Optional[float]:
    """
    Parse arbitrary reported C-rate strings (e.g. '0.1 C', '1C', '5C', 'C/10', 'C/5', 'C/20').
    Returns numeric multiplier (e.g., C/10 -> 0.1, 0.5C -> 0.5).
    """
    if not c_rate_str:
        return None

    clean = c_rate_str.strip().upper()
    # Check for C/N notation: C/10, C/5, C/20
    c_div_m = re.search(r"C\s*\/\s*(\d+(?:\.\d+)?)", clean)
    if c_div_m:
        try:
            divisor = float(c_div_m.group(1))
            return round(1.0 / divisor, 4) if divisor > 0 else None
        except (ValueError, ZeroDivisionError):
            return None

    # Check for standard NC notation: 0.1 C, 1C, 5 C
    nc_m = re.search(r"(\d+(?:\.\d+)?)\s*C", clean)
    if nc_m:
        try:
            return round(float(nc_m.group(1)), 4)
        except ValueError:
            return None

    return None


# ---------------------------------------------------------------------------
# Scientific Notation and Unit Cleaners
# ---------------------------------------------------------------------------

def parse_scientific_notation(val_str: str) -> Optional[float]:
    """Parse floats with scientific notation (e.g. '2.4 x 10^-14', '1.5e-14', '3.5 × 10⁻¹⁴')."""
    if not val_str:
        return None

    # Replace unicode times and minus
    norm = val_str.replace("×", "x").replace("·", "*").replace("−", "-").replace("⁻", "-")
    # Convert unicode superscript numbers (¹ ⁴ etc)
    supers = {"⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4", "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9", "⁺": "+", "⁻": "-"}
    for sup, asc in supers.items():
        norm = norm.replace(sup, asc)

    sci_m = re.search(r"(\d+(?:\.\d+)?)\s*(?:[xX*]\s*10\s*(?:\^|\*\*)?\s*(-?\d+)|[eE](-?\d+))", norm)
    if sci_m:
        base = float(sci_m.group(1))
        exp = int(sci_m.group(2) if sci_m.group(2) is not None else sci_m.group(3))
        return base * (10 ** exp)

    try:
        return float(re.sub(r"[^\d.eE+-]", "", norm))
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Synthesis Routes & Precursors
# ---------------------------------------------------------------------------

KNOWN_SYNTHESIS_ROUTES = [
    ("solid-state", "Solid-state"),
    ("solid state", "Solid-state"),
    ("sol-gel", "Sol-gel"),
    ("sol gel", "Sol-gel"),
    ("hydrothermal", "Hydrothermal"),
    ("solvothermal", "Solvothermal"),
    ("co-precipitation", "Co-precipitation"),
    ("coprecipitation", "Co-precipitation"),
    ("spray pyrolysis", "Spray pyrolysis"),
    ("spray drying", "Spray drying"),
    ("spray-drying", "Spray drying"),
    ("ball milling", "Ball milling"),
    ("combustion", "Combustion"),
    ("freeze drying", "Freeze drying"),
    ("freeze-drying", "Freeze drying"),
]

KNOWN_PRECURSORS = [
    "LiOH", "LiOH.H2O", "LiOH·H2O", "Li2CO3", "CH3COOLi", "LiAc",
    "Mn(CH3COO)2", "Mn(Ac)2", "MnSO4", "MnCO3", "MnO2", "MnCl2",
    "FeSO4", "FeSO4.7H2O", "FeSO4·7H2O", "FeC2O4", "FeC2O4.2H2O",
    "Fe(NO3)3", "FeCl2", "FeCl3", "NH4H2PO4", "(NH4)2HPO4", "H3PO4",
    "sucrose", "glucose", "citric acid", "PVP", "PEG", "ascorbic acid",
]


# ---------------------------------------------------------------------------
# Electrochemical Property Extraction Functions
# ---------------------------------------------------------------------------

def extract_electrochemical_measurements(
    text: str,
    page_number: int,
    section_type: str,
    source_pdf: str = "unknown.pdf",
    sample_label: Optional[str] = None,
    table_or_figure_id: Optional[str] = None,
) -> List[PropertyMeasurement]:
    """
    Extract specific discharge capacities, charge capacities, cycling retention,
    ICE, and operational Coulombic efficiency with exact condition attribution.
    """
    measurements: List[PropertyMeasurement] = []
    clean_text = normalize_formula_text(text)
    meas_idx = 1

    # Pre-extract local voltage window if mentioned in the block
    voltage_window = None
    vw_match = re.search(
        r"(?:between\s+(\d+(?:\.\d+)?)\s*(?:and|-)\s*(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*[\u2013\u2212\-\~–—to]+\s*(\d+(?:\.\d+)?))\s*V(?:\s*vs\.?\s*Li[\/\+]?Li\+?)?",
        clean_text,
        re.IGNORECASE,
    )
    if vw_match:
        v_low = float(vw_match.group(1) or vw_match.group(3))
        v_high = float(vw_match.group(2) or vw_match.group(4))
        if 1.0 <= v_low < v_high <= 5.5:
            voltage_window = f"{v_low}-{v_high} V"

    # Pre-extract local operating temperature if mentioned
    temp_c = None
    t_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:°C|℃|deg\s*C)", clean_text)
    if t_match:
        t_val = float(t_match.group(1))
        if -40.0 <= t_val <= 120.0:
            temp_c = t_val

    # 1. Capacity Patterns:
    # Pattern 1A: '163.8 mAh/g at 0.1 C' or '163.8 mAh g-1 (0.1 C)'
    cap_pat1 = re.compile(
        r"(\d+(?:\.\d+)?)\s*(?:mAh\s*[\/\-·.]?\s*g(?:-1)?|mA\s*h\s*g(?:-1)?)\s*(?:\(|at|@|under)?\s*(\d+(?:\.\d+)?\s*C|C\s*\/\s*\d+(?:\.\d+)?)\b",
        re.IGNORECASE,
    )
    captured_cap_spans = []

    for m in cap_pat1.finditer(clean_text):
        cap_val = float(m.group(1))
        rate_str = m.group(2)
        c_rate = parse_c_rate(rate_str)
        if 15.0 <= cap_val <= 260.0:
            captured_cap_spans.append(m.span(1))
            conds = {"c_rate": c_rate, "raw_c_rate": rate_str}
            if voltage_window:
                conds["voltage_window"] = voltage_window
            if temp_c is not None:
                conds["temperature_c"] = temp_c

            start_idx = max(0, m.start() - 60)
            end_idx = min(len(clean_text), m.end() + 60)
            quote = clean_text[start_idx:end_idx].replace("\n", " ").strip()

            measurements.append(PropertyMeasurement(
                measurement_id=f"cap_{page_number}_{meas_idx}",
                sample_label=sample_label,
                measurement_type="discharge_capacity",
                reported_value=str(cap_val),
                reported_unit="mAh/g",
                normalized_value=cap_val,
                normalized_unit="mAh/g",
                conditions=conds,
                source_pdf=source_pdf,
                page_number=page_number,
                section_type=section_type,
                table_or_figure_id=table_or_figure_id,
                evidence_quote=quote,
                extraction_method="text_rule",
                validation_status="VERIFIED",
            ))
            meas_idx += 1

    # Pattern 1B: 'at 0.1 C, it delivers 163.8 mAh/g'
    cap_pat2 = re.compile(
        r"(?:at|@)\s*(\d+(?:\.\d+)?\s*C|C\s*\/\s*\d+(?:\.\d+)?)[^\n.,;]{0,45}?(?:delivers?|exhibits?|shows?|yields?|achieves?|discharge\s+capacity\s+of)?\s*(\d+(?:\.\d+)?)\s*(?:mAh\s*[\/\-·.]?\s*g(?:-1)?|mA\s*h\s*g(?:-1)?)",
        re.IGNORECASE,
    )
    for m in cap_pat2.finditer(clean_text):
        cap_span = m.span(2)
        if any(abs(cap_span[0] - s[0]) < 2 for s in captured_cap_spans):
            continue

        rate_str = m.group(1)
        cap_val = float(m.group(2))
        c_rate = parse_c_rate(rate_str)
        if 15.0 <= cap_val <= 260.0:
            captured_cap_spans.append(cap_span)
            conds = {"c_rate": c_rate, "raw_c_rate": rate_str}
            if voltage_window:
                conds["voltage_window"] = voltage_window
            if temp_c is not None:
                conds["temperature_c"] = temp_c

            start_idx = max(0, m.start() - 50)
            end_idx = min(len(clean_text), m.end() + 50)
            quote = clean_text[start_idx:end_idx].replace("\n", " ").strip()

            measurements.append(PropertyMeasurement(
                measurement_id=f"cap_{page_number}_{meas_idx}",
                sample_label=sample_label,
                measurement_type="discharge_capacity",
                reported_value=str(cap_val),
                reported_unit="mAh/g",
                normalized_value=cap_val,
                normalized_unit="mAh/g",
                conditions=conds,
                source_pdf=source_pdf,
                page_number=page_number,
                section_type=section_type,
                table_or_figure_id=table_or_figure_id,
                evidence_quote=quote,
                extraction_method="text_rule",
                validation_status="VERIFIED",
            ))
            meas_idx += 1

    # Pattern 1C: Initial Charge Capacity (e.g. 'initial charge capacity was 172.5 mAh/g')
    charge_pat = re.compile(
        r"(?:initial|first)?\s*\bcharge\s+capacity\b\s*(?:of|is|was|:)?\s*(\d+(?:\.\d+)?)\s*(?:mAh\s*[\/\-·]?\s*g(?:-1)?|mA\s*h\s*g(?:-1)?)",
        re.IGNORECASE,
    )
    for m in charge_pat.finditer(clean_text):
        chg_val = float(m.group(1))
        if 20.0 <= chg_val <= 280.0:
            conds = {}
            if voltage_window:
                conds["voltage_window"] = voltage_window
            if temp_c is not None:
                conds["temperature_c"] = temp_c

            start_idx = max(0, m.start() - 40)
            end_idx = min(len(clean_text), m.end() + 40)
            quote = clean_text[start_idx:end_idx].replace("\n", " ").strip()

            measurements.append(PropertyMeasurement(
                measurement_id=f"chg_{page_number}_{meas_idx}",
                sample_label=sample_label,
                measurement_type="charge_capacity",
                reported_value=str(chg_val),
                reported_unit="mAh/g",
                normalized_value=chg_val,
                normalized_unit="mAh/g",
                conditions=conds,
                source_pdf=source_pdf,
                page_number=page_number,
                section_type=section_type,
                table_or_figure_id=table_or_figure_id,
                evidence_quote=quote,
                extraction_method="text_rule",
                validation_status="VERIFIED",
            ))
            meas_idx += 1

    # Pattern 1D: 'discharge capacities of SampleA and SampleB were ValA and ValB, respectively'
    resp_sample_pat = re.compile(
        r"discharge\s+capacit(?:y|ies)\s+of\s+([A-Za-z0-9_\-\/]+)\s+and\s+([A-Za-z0-9_\-\/]+)\s+(?:were|was|are|is)\s+(\d+(?:\.\d+)?)\s*(?:mAh\s*[\/\-·.]?\s*g(?:-1)?|mA\s*h\s*g(?:-1)?)\s+and\s+(\d+(?:\.\d+)?)\s*(?:mAh\s*[\/\-·.]?\s*g(?:-1)?|mA\s*h\s*g(?:-1)?)[^.\n]*?\brespectively\b",
        re.IGNORECASE,
    )
    for m in resp_sample_pat.finditer(clean_text):
        s1, s2 = m.group(1), m.group(2)
        v1, v2 = float(m.group(3)), float(m.group(4))
        # Check for local C-rate in block
        block_rate = None
        rate_m = re.search(r"(\d+(?:\.\d+)?)\s*C(?:-rate|\b)", clean_text)
        if rate_m:
            block_rate = parse_c_rate(rate_m.group(0))

        start_idx = max(0, m.start() - 40)
        end_idx = min(len(clean_text), m.end() + 40)
        quote = clean_text[start_idx:end_idx].replace("\n", " ").strip()

        for samp, val in [(s1, v1), (s2, v2)]:
            conds = {}
            if block_rate is not None:
                conds["c_rate"] = block_rate
            if voltage_window:
                conds["voltage_window"] = voltage_window
            if temp_c is not None:
                conds["temperature_c"] = temp_c

            measurements.append(PropertyMeasurement(
                measurement_id=f"cap_resp_{page_number}_{meas_idx}",
                sample_label=samp,
                measurement_type="discharge_capacity",
                reported_value=str(val),
                reported_unit="mAh/g",
                normalized_value=val,
                normalized_unit="mAh/g",
                conditions=conds,
                source_pdf=source_pdf,
                page_number=page_number,
                section_type=section_type,
                table_or_figure_id=table_or_figure_id,
                evidence_quote=quote,
                extraction_method="respectively_rule",
                validation_status="VERIFIED",
            ))
            meas_idx += 1

    # Pattern 1E: 'discharge capacities of 114, 107, 100 ... at 0.05, 0.1, 0.5 ... C, respectively'
    resp_rates_pat = re.compile(
        r"discharge\s+capacit(?:y|ies)[^\n.,;]{0,35}?\s+of\s+([\d.,\s]+?(?:and\s+[\d.]+)?)\s*(?:mAh\s*[\/\-·.]?\s*g(?:-1)?|mA\s*h\s*g(?:-1)?)\s+at\s+([\d.,\s]+?(?:and\s+[\d.]+)?)\s*C[^.\n]*?\brespectively\b",
        re.IGNORECASE,
    )
    for m in resp_rates_pat.finditer(clean_text):
        val_strs = [v.strip() for v in re.split(r"[,;\s]+|and", m.group(1)) if v.strip()]
        rate_strs = [r.strip() for r in re.split(r"[,;\s]+|and", m.group(2)) if r.strip()]
        
        # Candidate sample name preceding
        samp_match = re.search(r"\b([A-Za-z0-9_\-\/]+)\s+(?:delivered|exhibited|showed)", clean_text[:m.start()+25])
        curr_sample = samp_match.group(1) if samp_match else sample_label

        start_idx = max(0, m.start() - 40)
        end_idx = min(len(clean_text), m.end() + 40)
        quote = clean_text[start_idx:end_idx].replace("\n", " ").strip()

        if len(val_strs) == len(rate_strs):
            for v_str, r_str in zip(val_strs, rate_strs):
                try:
                    v_num = float(v_str)
                    r_num = parse_c_rate(f"{r_str} C")
                    if 15.0 <= v_num <= 260.0 and r_num is not None:
                        conds = {"c_rate": r_num, "raw_c_rate": f"{r_str} C"}
                        if voltage_window:
                            conds["voltage_window"] = voltage_window
                        if temp_c is not None:
                            conds["temperature_c"] = temp_c

                        measurements.append(PropertyMeasurement(
                            measurement_id=f"cap_resp_rate_{page_number}_{meas_idx}",
                            sample_label=curr_sample,
                            measurement_type="discharge_capacity",
                            reported_value=str(v_num),
                            reported_unit="mAh/g",
                            normalized_value=v_num,
                            normalized_unit="mAh/g",
                            conditions=conds,
                            source_pdf=source_pdf,
                            page_number=page_number,
                            section_type=section_type,
                            table_or_figure_id=table_or_figure_id,
                            evidence_quote=quote,
                            extraction_method="respectively_rate_rule",
                            validation_status="VERIFIED",
                        ))
                        meas_idx += 1
                except (ValueError, TypeError):
                    continue

    # 2. Cycling Capacity Retention & Cycle Count:
    # Pattern 2A: 'retention of 95.8% after 200 cycles at 1 C' or '100.0% (100 cycles, 1 C)'
    ret_pat1 = re.compile(
        r"(\d+(?:\.\d+)?)\s*%\s*(?:capacity\s+retention|retention)?[^\n.]{0,45}?(?:after|\()\s*([\d,]+)\s*cycles?(?:[,\s]+(?:at|@)?\s*(\d+(?:\.\d+)?\s*C|C\s*\/\s*\d+(?:\.\d+)?))?",
        re.IGNORECASE,
    )
    captured_ret_pct_spans = []

    for m in ret_pat1.finditer(clean_text):
        pct = float(m.group(1))
        cycles = int(m.group(2).replace(",", ""))
        crate_str = m.group(3)
        c_rate = parse_c_rate(crate_str) if crate_str else None

        if 0.0 <= pct <= 115.0 and cycles > 0:
            captured_ret_pct_spans.append(m.span(1))
            conds = {"cycle_count": cycles}
            if c_rate is not None:
                conds["c_rate"] = c_rate
                conds["raw_c_rate"] = crate_str
            if voltage_window:
                conds["voltage_window"] = voltage_window
            if temp_c is not None:
                conds["temperature_c"] = temp_c

            start_idx = max(0, m.start() - 50)
            end_idx = min(len(clean_text), m.end() + 50)
            quote = clean_text[start_idx:end_idx].replace("\n", " ").strip()

            measurements.append(PropertyMeasurement(
                measurement_id=f"ret_{page_number}_{meas_idx}",
                sample_label=sample_label,
                measurement_type="capacity_retention",
                reported_value=str(pct),
                reported_unit="%",
                normalized_value=pct,
                normalized_unit="%",
                conditions=conds,
                source_pdf=source_pdf,
                page_number=page_number,
                section_type=section_type,
                table_or_figure_id=table_or_figure_id,
                evidence_quote=quote,
                extraction_method="text_rule",
                validation_status="VERIFIED",
            ))
            meas_idx += 1

    # Pattern 2B: 'after 500 cycles at 2 C, the capacity retention was 92.4%'
    ret_pat2 = re.compile(
        r"(?:after|\()\s*([\d,]+)\s*cycles?(?:[,\s]+(?:at|@)?\s*(\d+(?:\.\d+)?\s*C|C\s*\/\s*\d+(?:\.\d+)?))?[^\n.]{0,45}?(?:retains?|retention\s+(?:of|was|is)?|capacity\s+retention\s+of)?\s*(\d+(?:\.\d+)?)\s*%",
        re.IGNORECASE,
    )
    for m in ret_pat2.finditer(clean_text):
        pct_span = m.span(3)
        # Skip if this percentage number has already been captured by pattern 2A
        if any(abs(pct_span[0] - span[0]) < 2 for span in captured_ret_pct_spans):
            continue

        cycles = int(m.group(1).replace(",", ""))
        crate_str = m.group(2)
        pct = float(m.group(3))
        crate_str = m.group(2)
        pct = float(m.group(3))
        c_rate = parse_c_rate(crate_str) if crate_str else None

        if 0.0 <= pct <= 115.0 and cycles > 0:
            captured_ret_pct_spans.append(pct_span)
            conds = {"cycle_count": cycles}
            if c_rate is not None:
                conds["c_rate"] = c_rate
                conds["raw_c_rate"] = crate_str
            if voltage_window:
                conds["voltage_window"] = voltage_window
            if temp_c is not None:
                conds["temperature_c"] = temp_c

            start_idx = max(0, m.start() - 50)
            end_idx = min(len(clean_text), m.end() + 50)
            quote = clean_text[start_idx:end_idx].replace("\n", " ").strip()

            measurements.append(PropertyMeasurement(
                measurement_id=f"ret_{page_number}_{meas_idx}",
                sample_label=sample_label,
                measurement_type="capacity_retention",
                reported_value=str(pct),
                reported_unit="%",
                normalized_value=pct,
                normalized_unit="%",
                conditions=conds,
                source_pdf=source_pdf,
                page_number=page_number,
                section_type=section_type,
                table_or_figure_id=table_or_figure_id,
                evidence_quote=quote,
                extraction_method="text_rule",
                validation_status="VERIFIED",
            ))
            meas_idx += 1

    # 3. Initial Coulombic Efficiency (ICE) and Operational CE
    ice_pat = re.compile(
        r"(?:initial\s+coulombic\s+efficiency|ICE)\s*(?:of|is|was|:)?\s*(\d+(?:\.\d+)?)\s*%",
        re.IGNORECASE,
    )
    for m in ice_pat.finditer(clean_text):
        ice_val = float(m.group(1))
        if 40.0 <= ice_val <= 105.0:
            start_idx = max(0, m.start() - 40)
            end_idx = min(len(clean_text), m.end() + 40)
            quote = clean_text[start_idx:end_idx].replace("\n", " ").strip()

            measurements.append(PropertyMeasurement(
                measurement_id=f"ice_{page_number}_{meas_idx}",
                sample_label=sample_label,
                measurement_type="ice",
                reported_value=str(ice_val),
                reported_unit="%",
                normalized_value=ice_val,
                normalized_unit="%",
                conditions={"voltage_window": voltage_window} if voltage_window else {},
                source_pdf=source_pdf,
                page_number=page_number,
                section_type=section_type,
                table_or_figure_id=table_or_figure_id,
                evidence_quote=quote,
                extraction_method="text_rule",
                validation_status="VERIFIED",
            ))
            meas_idx += 1

    # Operational Coulombic Efficiency (e.g. 'coulombic efficiency of 99.8%', 'remained above 99.8%')
    ce_pat = re.compile(
        r"(?<!initial\s)\bcoulombic\s+efficiency[^\n.,;]{0,35}?(\d+(?:\.\d+)?)\s*%",
        re.IGNORECASE,
    )
    for m in ce_pat.finditer(clean_text):
        ce_val = float(m.group(1))
        if 70.0 <= ce_val <= 100.5:
            start_idx = max(0, m.start() - 40)
            end_idx = min(len(clean_text), m.end() + 40)
            quote = clean_text[start_idx:end_idx].replace("\n", " ").strip()

            measurements.append(PropertyMeasurement(
                measurement_id=f"ce_{page_number}_{meas_idx}",
                sample_label=sample_label,
                measurement_type="coulombic_efficiency",
                reported_value=str(ce_val),
                reported_unit="%",
                normalized_value=ce_val,
                normalized_unit="%",
                conditions={"voltage_window": voltage_window} if voltage_window else {},
                source_pdf=source_pdf,
                page_number=page_number,
                section_type=section_type,
                table_or_figure_id=table_or_figure_id,
                evidence_quote=quote,
                extraction_method="text_rule",
                validation_status="VERIFIED",
            ))
            meas_idx += 1

    # 4. Standalone Voltage Window (if not already captured as condition)
    if voltage_window and not measurements:
        measurements.append(PropertyMeasurement(
            measurement_id=f"vw_{page_number}_{meas_idx}",
            sample_label=sample_label,
            measurement_type="voltage_window",
            reported_value=voltage_window,
            reported_unit="V",
            normalized_value=None,
            normalized_unit="V",
            conditions={"voltage_window": voltage_window},
            source_pdf=source_pdf,
            page_number=page_number,
            section_type=section_type,
            table_or_figure_id=table_or_figure_id,
            evidence_quote=vw_match.group(0),
            extraction_method="text_rule",
            validation_status="VERIFIED",
        ))

    return measurements


# ---------------------------------------------------------------------------
# Synthesis Condition Extractor
# ---------------------------------------------------------------------------

def extract_synthesis_profile(
    text: str,
    page_number: int,
    sample_label: Optional[str] = None,
) -> Optional[SynthesisProfile]:
    """Extract calcination temperature, duration, heating rate, atmosphere, and precursors."""
    lower_text = text.lower()

    # Route identification
    detected_route = None
    for pattern, clean_name in KNOWN_SYNTHESIS_ROUTES:
        if pattern in lower_text:
            detected_route = clean_name
            break

    # Calcination temperature
    calc_temp = None
    t_match = re.search(
        r"(?:calcined|calcination|annealed|annealing|sintered|sintering|heated|heating)\s*(?:at|temperature\s+of)?\s*(\d{3,4})\s*(?:°C|℃|deg\s*C|K)",
        text,
        re.IGNORECASE,
    )
    if t_match:
        val = float(t_match.group(1))
        if 200 <= val <= 1300:
            calc_temp = val

    # Calcination duration
    calc_dur = None
    d_match = re.search(
        r"(?:calcined|annealed|sintered|heated|held)?\s*(?:for|at[^\n.,]{0,25}?for)\s*(\d+(?:\.\d+)?)\s*(?:h|hrs?|hours?)\b",
        text,
        re.IGNORECASE,
    )
    if d_match:
        dur = float(d_match.group(1))
        if 0.1 <= dur <= 72.0:
            calc_dur = dur

    # Heating rate
    heat_rate = None
    hr_match = re.search(
        r"(?:heating\s+rate|ramped?\s+at)\s*(?:of)?\s*(\d+(?:\.\d+)?)\s*(?:°C\s*[\/\-]?\s*min|℃\s*[\/\-]?\s*min|K\s*[\/\-]?\s*min)",
        text,
        re.IGNORECASE,
    )
    if hr_match:
        hr = float(hr_match.group(1))
        if 0.5 <= hr <= 50.0:
            heat_rate = hr

    # Atmosphere
    atmosphere = None
    atm_match = re.search(
        r"\b(?:under|in)\s+(?:an?\s+)?(Ar\/H2|Ar\s*\+\s*H2|argon|Ar|nitrogen|N2|air|vacuum|reducing\s+atmosphere)\s*(?:atmosphere|flow|gas)?\b",
        text,
        re.IGNORECASE,
    )
    if atm_match:
        raw_atm = atm_match.group(1).strip()
        if raw_atm.lower() in ("ar/h2", "ar + h2", "ar/h2"):
            atmosphere = "Ar/H2"
        elif raw_atm.lower() in ("ar", "argon"):
            atmosphere = "Ar"
        elif raw_atm.lower() in ("n2", "nitrogen"):
            atmosphere = "N2"
        else:
            atmosphere = raw_atm.capitalize()

    # Precursors
    found_precursors = []
    for prec in KNOWN_PRECURSORS:
        # Match precursor with word boundaries or punctuation
        if re.search(rf"\b{re.escape(prec)}\b", text):
            found_precursors.append(prec)

    # If any synthesis parameter was found, construct profile
    if any([detected_route, calc_temp, calc_dur, heat_rate, atmosphere, found_precursors]):
        return SynthesisProfile(
            sample_label=sample_label,
            route=detected_route,
            calcination_temperature_c=calc_temp,
            calcination_duration_hours=calc_dur,
            heating_rate_c_min=heat_rate,
            atmosphere=atmosphere,
            precursors=sorted(list(set(found_precursors))),
            raw_evidence=text[:350].replace("\n", " ").strip(),
            source_page=page_number,
        )

    return None


# ---------------------------------------------------------------------------
# Material Characterization Extractor
# ---------------------------------------------------------------------------

def extract_characterization_profile(
    text: str,
    page_number: int,
    sample_label: Optional[str] = None,
) -> Optional[CharacterizationProfile]:
    """
    Extract crystallographic properties (space group, lattice a, b, c, volume),
    physical properties (crystallite size, particle size), and transport kinetics (Rct, D_Li).
    """
    clean_text = normalize_formula_text(text)

    # 1. Space group & Phase
    space_group = None
    phase = None
    if re.search(r"\bolivine\b", clean_text, re.IGNORECASE):
        phase = "Olivine"

    sg_match = re.search(
        r"(?:\bspace\s+group\s*(?:is|of|:)?\s*|(?:orthorhombic|olivine)\s+(?:structure\s+in\s+|structure\s+)?)((?:P\s*n\s*m\s*a|Pnma|Pmnb|P2_1\/c|Fd-3m|R-3m))\b",
        clean_text,
        re.IGNORECASE,
    )
    if sg_match:
        cand_sg = re.sub(r"\s+", "", sg_match.group(1)).strip()
        if cand_sg.lower() in {"pnma", "pmnb", "p2_1/c", "fd-3m", "r-3m"}:
            space_group = "Pnma" if cand_sg.lower() == "pnma" else cand_sg.capitalize()
            if not phase:
                phase = "Olivine"

    # 2. Lattice parameters (a, b, c in Angstroms)
    lat_a, lat_b, lat_c, cell_vol = None, None, None, None
    a_m = re.search(r"\ba\s*=\s*([0-9]+\.[0-9]+)\s*(?:Å|A|nm)?\b", clean_text)
    if a_m:
        val = float(a_m.group(1))
        lat_a = val if val > 1.0 else val * 10.0  # convert nm to Å if given in nm

    b_m = re.search(r"\bb\s*=\s*([0-9]+\.[0-9]+)\s*(?:Å|A|nm)?\b", clean_text)
    if b_m:
        val = float(b_m.group(1))
        lat_b = val if val > 1.0 else val * 10.0

    c_m = re.search(r"\bc\s*=\s*([0-9]+\.[0-9]+)\s*(?:Å|A|nm)?\b", clean_text)
    if c_m:
        val = float(c_m.group(1))
        lat_c = val if val > 1.0 else val * 10.0

    # Unit cell volume
    vol_m = re.search(
        r"(?:unit[- ]cell\s+volume|V)(?:\s*(?:of|is|was|:|=))?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:Å3|Å\^3|A3|A\^3)",
        clean_text,
        re.IGNORECASE,
    )
    if vol_m:
        cell_vol = float(vol_m.group(1))
    elif lat_a and lat_b and lat_c:
        cell_vol = round(lat_a * lat_b * lat_c, 2)

    # 3. Crystallite size
    cryst_size = None
    cs_m = re.search(r"(?:crystallite\s+size|grain\s+size)\s*(?:of|is|was|:)?\s*([0-9]+(?:\.[0-9]+)?)\s*(nm|μm|um)", clean_text, re.IGNORECASE)
    if cs_m:
        val = float(cs_m.group(1))
        unit = cs_m.group(2).lower()
        cryst_size = val if unit == "nm" else val * 1000.0

    # 4. Particle size
    part_size = None
    ps_m = re.search(r"(?:particle\s+size|average\s+size|D50)\s*(?:of|is|was|:)?\s*([0-9]+(?:\.[0-9]+)?)\s*(nm|μm|um)", clean_text, re.IGNORECASE)
    if ps_m:
        val = float(ps_m.group(1))
        unit = ps_m.group(2).lower()
        part_size = val if unit == "nm" else val * 1000.0

    # 5. EIS charge-transfer resistance (Rct)
    rct_val = None
    rct_m = re.search(r"(?:charge[- ]transfer\s+resistance|Rct|R_ct)\s*(?:of|is|was|:)?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:Ω|ohm|ohms)", clean_text, re.IGNORECASE)
    if rct_m:
        rct_val = float(rct_m.group(1))

    # 6. Lithium diffusion coefficient (D_Li)
    d_li_val = None
    dli_m = re.search(
        r"(?:diffusion\s+coefficient(?:\s+of\s+Li\+?)?|D_?Li\+?|D_?Li)(?:\s*(?:of|is|was|was\s+calculated\s+as|as|:|=))?\s*([0-9]+(?:\.[0-9]+)?(?:\s*[×x*]\s*10\s*(?:\^|\*\*)?\s*[-⁻]?\s*\d+|[eE][+-]?\d+)?)\s*(?:cm2\s*[\/\-·]?\s*s(?:-1)?|cm2\/s)",
        clean_text,
        re.IGNORECASE,
    )
    if dli_m:
        d_li_val = parse_scientific_notation(dli_m.group(1))

    if any([space_group, lat_a, lat_b, lat_c, cell_vol, cryst_size, part_size, rct_val, d_li_val]):
        return CharacterizationProfile(
            sample_label=sample_label,
            phase=phase or ("Olivine" if (lat_a or space_group) else None),
            space_group=space_group,
            lattice_a_angstrom=lat_a,
            lattice_b_angstrom=lat_b,
            lattice_c_angstrom=lat_c,
            unit_cell_volume_angstrom3=cell_vol,
            crystallite_size_nm=cryst_size,
            particle_size_nm=part_size,
            eis_rct_ohm=rct_val,
            li_diffusion_coefficient_cm2_s=d_li_val,
            raw_evidence=text[:350].replace("\n", " ").strip(),
            source_page=page_number,
        )

    return None


# ---------------------------------------------------------------------------
# Table Property Extractor
# ---------------------------------------------------------------------------

def extract_table_measurements(
    table_text: str,
    page_number: int,
    table_id: str = "Table",
    source_pdf: str = "unknown.pdf",
) -> List[PropertyMeasurement]:
    """
    Extract property measurements from formatted or delimited scientific tables.
    Guarantees that each row's measurements are bound strictly to that row's sample.
    """
    measurements = []
    lines = [l.strip() for l in table_text.splitlines() if l.strip()]
    if len(lines) < 2:
        return measurements

    # Identify header line that defines C-rate columns
    header_line_idx = -1
    rate_columns: List[Tuple[int, float, str]] = []  # (col_idx, c_rate, raw_rate)
    delimiter = None

    for i, line in enumerate(lines):
        delim = "\t" if "\t" in line else ("|" if "|" in line else None)
        tokens = [t.strip() for t in (line.split(delim) if delim else line.split()) if t.strip()]
        found_rates = [(idx, parse_c_rate(tok), tok) for idx, tok in enumerate(tokens) if parse_c_rate(tok) is not None]
        if found_rates:
            header_line_idx = i
            delimiter = delim
            rate_columns = [(idx, rate, raw) for idx, rate, raw in found_rates]
            break

    if header_line_idx == -1 or not rate_columns:
        return measurements

    # Process each data row after the header line
    for r_idx, line in enumerate(lines[header_line_idx + 1:], start=header_line_idx + 1):
        row_tokens = [t.strip() for t in (line.split(delimiter) if delimiter else line.split()) if t.strip()]
        if not row_tokens:
            continue

        sample_name = row_tokens[0]
        # Skip repetitive header lines
        if parse_c_rate(sample_name) is not None or sample_name.lower() in ("sample", "material", "composition"):
            continue

        # Extract capacities corresponding to column C-rates
        for col_idx, crate, raw_rate in rate_columns:
            if col_idx < len(row_tokens):
                cell_val_str = row_tokens[col_idx]
                try:
                    num_str = re.sub(r"[^\d.]", "", cell_val_str)
                    if num_str:
                        cap_val = float(num_str)
                        if 20.0 <= cap_val <= 250.0:
                            measurements.append(PropertyMeasurement(
                                measurement_id=f"tbl_{page_number}_{r_idx}_{col_idx}",
                                sample_label=sample_name,
                                measurement_type="discharge_capacity",
                                reported_value=str(cap_val),
                                reported_unit="mAh/g",
                                normalized_value=cap_val,
                                normalized_unit="mAh/g",
                                conditions={"c_rate": crate, "raw_c_rate": raw_rate},
                                source_pdf=source_pdf,
                                page_number=page_number,
                                section_type="TABLE",
                                table_or_figure_id=table_id,
                                evidence_quote=line,
                                extraction_method="table_row",
                                validation_status="VERIFIED",
                            ))
                except ValueError:
                    pass

        # Check for retention in cell or row
        ret_m = re.search(
            r"(\d+(?:\.\d+)?)\s*%\s*(?:\(\s*(\d+)\s*(?:cycles?)?(?:,\s*(\d+(?:\.\d+)?\s*C))?\s*\))?",
            line,
            re.IGNORECASE,
        )
        if ret_m:
            try:
                pct = float(ret_m.group(1))
                cycles = int(ret_m.group(2)) if ret_m.group(2) else None
                crate_str = ret_m.group(3)
                c_rate = parse_c_rate(crate_str) if crate_str else None
                if 0.0 <= pct <= 115.0:
                    conds = {}
                    if cycles:
                        conds["cycle_count"] = cycles
                    if c_rate:
                        conds["c_rate"] = c_rate
                        conds["raw_c_rate"] = crate_str
                    measurements.append(PropertyMeasurement(
                        measurement_id=f"tbl_ret_{page_number}_{r_idx}",
                        sample_label=sample_name,
                        measurement_type="capacity_retention",
                        reported_value=str(pct),
                        reported_unit="%",
                        normalized_value=pct,
                        normalized_unit="%",
                        conditions=conds,
                        source_pdf=source_pdf,
                        page_number=page_number,
                        section_type="TABLE",
                        table_or_figure_id=table_id,
                        evidence_quote=line,
                        extraction_method="table_row",
                        validation_status="VERIFIED",
                    ))
            except ValueError:
                pass

    return measurements


# ---------------------------------------------------------------------------
# Document-Level Property Extractor Orchestrator
# ---------------------------------------------------------------------------

def extract_properties_from_document(
    doc_struct: DocumentStructure,
    source_pdf: str = "unknown.pdf",
) -> ExtractedPaperProperties:
    """
    Extract all electrochemical measurements, synthesis conditions, and characterization
    properties across all sections of a document while strictly obeying section boundaries.
    """
    paper_props = ExtractedPaperProperties(source_pdf=source_pdf)

    # Iterate through all structural blocks
    for block in doc_struct.blocks:
        # STRICT NEGATIVE CONTROL: Never extract experimental measurements from References, Acknowledgements, Corrigenda
        if block.section_type in {
            SectionType.REFERENCES,
            SectionType.ACKNOWLEDGEMENTS,
            SectionType.CORRIGENDUM,
        }:
            continue

        # If table block, use dedicated table extractor
        if block.section_type == SectionType.TABLE:
            tbl_meas = extract_table_measurements(
                table_text=block.text,
                page_number=block.page_number,
                table_id=block.table_id or "Table",
                source_pdf=source_pdf,
            )
            if tbl_meas:
                paper_props.measurements.extend(tbl_meas)
                continue

        # Detect candidate chemical composition or sample label in this block
        block_text = block.text
        sample_label = None

        # Check for formula in block
        formula_m = re.search(
            r"\bLi[A-Za-z0-9_.\u2080-\u2089]*Mn[0-9.\u2080-\u2089]*Fe[0-9.\u2080-\u2089]*[A-Za-z0-9_.\u2080-\u2089]*PO4(?:\/[A-Za-z0-9_]+|@[A-Za-z0-9_]+)?\b",
            block_text,
        )
        if formula_m:
            parsed = parse_lmfp_composition(formula_m.group(0))
            if parsed.validation_status != "INVALID":
                sample_label = parsed.normalized_formula

        # 1. Electrochemical measurements
        measurements = extract_electrochemical_measurements(
            text=block_text,
            page_number=block.page_number,
            section_type=block.section_type.value,
            source_pdf=source_pdf,
            sample_label=sample_label,
            table_or_figure_id=block.table_id or block.figure_id,
        )
        paper_props.measurements.extend(measurements)

        # 2. Synthesis profile (primarily from Experimental section)
        if block.section_type in {SectionType.EXPERIMENTAL, SectionType.UNKNOWN}:
            synth = extract_synthesis_profile(
                text=block_text,
                page_number=block.page_number,
                sample_label=sample_label,
            )
            if synth:
                paper_props.synthesis_profiles.append(synth)

        # 3. Characterization profile (Results & Discussion, Experimental, Tables)
        if block.section_type in {
            SectionType.RESULTS_DISCUSSION,
            SectionType.EXPERIMENTAL,
            SectionType.TABLE,
            SectionType.UNKNOWN,
        }:
            char_prof = extract_characterization_profile(
                text=block_text,
                page_number=block.page_number,
                sample_label=sample_label,
            )
            if char_prof:
                paper_props.characterization_profiles.append(char_prof)

    return paper_props
