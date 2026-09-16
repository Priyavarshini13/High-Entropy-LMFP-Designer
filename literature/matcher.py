"""
Matcher module for V2 literature reference engine.
Provides deterministic exact matching, near matching, status classification,
and explicit difference reporting.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
from .loader import LiteratureSampleRecord
from .parser import parse_composition, ParsedComposition

class MatchStatus(str, Enum):
    SUPERVISOR_REFERENCE = "SUPERVISOR_REFERENCE"
    LITERATURE_MATCH = "LITERATURE_MATCH"
    NEAR_LITERATURE_MATCH = "NEAR_LITERATURE_MATCH"
    NO_MATCH_IN_DATABASE = "NO_MATCH_IN_DATABASE"
    GENERATED_BY_OUR_SYSTEM = "GENERATED_BY_OUR_SYSTEM"
    EXPERIMENTALLY_VALIDATED = "EXPERIMENTALLY_VALIDATED"

# Supervisor baseline reference composition definition
SUPERVISOR_BASELINE = ParsedComposition(
    mn_ratio=0.65,
    fe_ratio=0.26,
    dopants={
        "Mg": {"fraction": 0.02, "oxidation_state": 2},
        "Zn": {"fraction": 0.02, "oxidation_state": 2},
        "Nb": {"fraction": 0.01, "oxidation_state": 5},
        "Cu": {"fraction": 0.02, "oxidation_state": 2},
        "Zr": {"fraction": 0.02, "oxidation_state": 4},
    }
)

@dataclass
class MatchDifference:
    sample_id: str
    paper_id: str
    mn_difference: float
    fe_difference: float
    dopant_set_status: str  # "EXACT_SET", "PARTIAL_OVERLAP", "NO_OVERLAP"
    dopant_differences: Dict[str, float]  # elem -> abs_diff
    is_within_near_tolerance: bool
    summary_text: str

@dataclass
class MatchResult:
    status: MatchStatus
    target_composition: ParsedComposition
    exact_matches: List[LiteratureSampleRecord] = field(default_factory=list)
    near_matches: List[LiteratureSampleRecord] = field(default_factory=list)
    differences: List[MatchDifference] = field(default_factory=list)
    explanation: str = ""

def _is_supervisor_reference(comp: ParsedComposition, float_tol: float = 1e-4) -> bool:
    if abs(comp.mn_ratio - SUPERVISOR_BASELINE.mn_ratio) > float_tol:
        return False
    if abs(comp.fe_ratio - SUPERVISOR_BASELINE.fe_ratio) > float_tol:
        return False
    if comp.dopant_set != SUPERVISOR_BASELINE.dopant_set:
        return False
    for elem, info in SUPERVISOR_BASELINE.dopants.items():
        if elem not in comp.dopants:
            return False
        if abs(comp.dopants[elem]["fraction"] - info["fraction"]) > float_tol:
            return False
    return True

def exact_match(
    target: ParsedComposition,
    db_records: List[LiteratureSampleRecord],
    float_tol: float = 1e-4
) -> List[LiteratureSampleRecord]:
    """
    Find all records in literature database that exactly match the target composition.
    An exact match requires:
    - Mn ratio matches within float_tol
    - Fe ratio matches within float_tol
    - Dopant set matches exactly
    - Per-dopant concentration matches within float_tol
    """
    matches = []
    for rec in db_records:
        parsed_rec = parse_composition(rec)
        
        # Mn check
        if abs(target.mn_ratio - parsed_rec.mn_ratio) > float_tol:
            continue
        # Fe check
        if abs(target.fe_ratio - parsed_rec.fe_ratio) > float_tol:
            continue
        # Dopant set check
        if target.dopant_set != parsed_rec.dopant_set:
            continue
        # Per-dopant concentration check
        conc_mismatch = False
        for elem in target.dopant_set:
            t_x = target.dopants[elem]["fraction"]
            l_x = parsed_rec.dopants[elem]["fraction"]
            if abs(t_x - l_x) > float_tol:
                conc_mismatch = True
                break
        if conc_mismatch:
            continue
            
        matches.append(rec)
        
    return matches

def calculate_difference(
    target: ParsedComposition,
    rec: LiteratureSampleRecord,
    near_mn_fe_tol: float = 0.005,
    near_conc_tol: float = 0.002
) -> MatchDifference:
    """
    Calculate explicit, unhidden differences between target and a literature sample record.
    """
    parsed_rec = parse_composition(rec)
    
    mn_diff = abs(target.mn_ratio - parsed_rec.mn_ratio)
    fe_diff = abs(target.fe_ratio - parsed_rec.fe_ratio)
    
    # Dopant set overlap
    t_set = target.dopant_set
    l_set = parsed_rec.dopant_set
    
    if t_set == l_set:
        set_status = "EXACT_SET"
    elif len(t_set.intersection(l_set)) > 0:
        set_status = "PARTIAL_OVERLAP"
    else:
        set_status = "NO_OVERLAP"
        
    all_elems = t_set.union(l_set)
    dop_diffs = {}
    conc_within_tol = True
    
    for elem in all_elems:
        t_conc = target.dopants[elem]["fraction"] if elem in t_set else 0.0
        l_conc = parsed_rec.dopants[elem]["fraction"] if elem in l_set else 0.0
        diff = abs(t_conc - l_conc)
        dop_diffs[elem] = round(diff, 6)
        if diff > near_conc_tol:
            conc_within_tol = False
            
    mn_fe_within_tol = (mn_diff <= near_mn_fe_tol) and (fe_diff <= near_mn_fe_tol)
    is_near = mn_fe_within_tol and conc_within_tol and (set_status in ["EXACT_SET", "PARTIAL_OVERLAP"])
    
    summary_parts = []
    if mn_diff > 0:
        summary_parts.append(f"Mn diff: {mn_diff:.4f}")
    if fe_diff > 0:
        summary_parts.append(f"Fe diff: {fe_diff:.4f}")
    for elem, diff in dop_diffs.items():
        if diff > 0:
            summary_parts.append(f"{elem} diff: {diff:.4f}")
            
    summary_str = ", ".join(summary_parts) if summary_parts else "Identical stoichiometry"
    
    return MatchDifference(
        sample_id=rec.sample_id,
        paper_id=rec.paper_id,
        mn_difference=round(mn_diff, 6),
        fe_difference=round(fe_diff, 6),
        dopant_set_status=set_status,
        dopant_differences=dop_diffs,
        is_within_near_tolerance=is_near,
        summary_text=summary_str
    )

def match_composition(
    target_input: Any,
    db_records: List[LiteratureSampleRecord],
    float_tol: float = 1e-4,
    near_mn_fe_tol: float = 0.005,
    near_conc_tol: float = 0.002
) -> MatchResult:
    """
    Perform full deterministic literature matching for a target composition.
    Evaluates exact match, near match, and returns appropriate MatchStatus.
    """
    target = parse_composition(target_input)
    
    # 1. Exact Match Check
    exact_recs = exact_match(target, db_records, float_tol=float_tol)
    if exact_recs:
        diffs = [calculate_difference(target, r, near_mn_fe_tol, near_conc_tol) for r in exact_recs]
        return MatchResult(
            status=MatchStatus.LITERATURE_MATCH,
            target_composition=target,
            exact_matches=exact_recs,
            near_matches=[],
            differences=diffs,
            explanation=f"Exact chemical literature match found: {len(exact_recs)} record(s) matched in database."
        )
        
    # 2. Near Match Check
    near_recs = []
    near_diffs = []
    
    for rec in db_records:
        diff = calculate_difference(target, rec, near_mn_fe_tol, near_conc_tol)
        if diff.is_within_near_tolerance:
            near_recs.append(rec)
            near_diffs.append(diff)
            
    if near_recs:
        return MatchResult(
            status=MatchStatus.NEAR_LITERATURE_MATCH,
            target_composition=target,
            exact_matches=[],
            near_matches=near_recs,
            differences=near_diffs,
            explanation=f"Near literature match found: {len(near_recs)} record(s) within Mn/Fe tolerance ±{near_mn_fe_tol} and dopant tolerance ±{near_conc_tol}."
        )
        
    # 3. Check if target matches Supervisor Reference Baseline
    if _is_supervisor_reference(target, float_tol=float_tol):
        return MatchResult(
            status=MatchStatus.SUPERVISOR_REFERENCE,
            target_composition=target,
            exact_matches=[],
            near_matches=[],
            differences=[],
            explanation="Matches project reference baseline supervisor composition."
        )
        
    # 4. No Match In Current Literature Database
    return MatchResult(
        status=MatchStatus.NO_MATCH_IN_DATABASE,
        target_composition=target,
        exact_matches=[],
        near_matches=[],
        differences=[],
        explanation="No sufficiently matching record was found in the current literature database."
    )
