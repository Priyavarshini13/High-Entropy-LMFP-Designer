"""
Parser module for V2 literature composition representation.
Standardizes representation of host ratios, dopants, dopant counts, and dopant sets.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any, Union
from .loader import LiteratureSampleRecord

@dataclass
class ParsedComposition:
    mn_ratio: float
    fe_ratio: float
    dopants: Dict[str, Dict[str, Any]] = field(default_factory=dict) # elem -> {"fraction": float, "oxidation_state": Optional[int]}
    
    @property
    def dopant_count(self) -> int:
        return len(self.dopants)
        
    @property
    def dopant_set(self) -> Set[str]:
        return set(self.dopants.keys())

def parse_dopant_element_string(dopant_str: str, default_x: Optional[float] = None) -> Dict[str, Dict[str, Any]]:
    """
    Parse dopant string representations such as "Mg;Ti", "Mg, Zn", "Co", "None/Undoped".
    Returns dictionary mapping element symbol -> {"fraction": float, "oxidation_state": Optional[int]}.
    """
    if not dopant_str or dopant_str.strip().lower() in ["none/undoped", "none", "undoped", "nan", ""]:
        return {}
        
    result = {}
    # Split by semicolon or comma
    delims = [";", ",", "/"]
    raw_str = dopant_str
    for d in delims:
        raw_str = raw_str.replace(d, "|")
        
    tokens = [t.strip() for t in raw_str.split("|") if t.strip()]
    
    for tok in tokens:
        if tok.lower() in ["none/undoped", "none", "undoped"]:
            continue
        # Check if concentration is in token, e.g. "Mg:0.02" or "Mg0.02"
        elem = tok
        frac = default_x if default_x is not None else 0.0
        ox = None
        
        if ":" in tok:
            parts = tok.split(":")
            elem = parts[0].strip()
            try:
                frac = float(parts[1])
            except ValueError:
                pass
        
        if elem:
            result[elem] = {"fraction": frac, "oxidation_state": ox}
            
    return result

def parse_composition(
    source: Union[LiteratureSampleRecord, Dict[str, Any], ParsedComposition],
    mn_ratio: Optional[float] = None,
    fe_ratio: Optional[float] = None,
    dopants: Optional[Union[List[Dict[str, Any]], Dict[str, Any], str]] = None
) -> ParsedComposition:
    """
    Standardize a composition into a ParsedComposition object.
    Supports input as a LiteratureSampleRecord, a dictionary, or explicit (mn, fe, dopants) parameters.
    """
    if isinstance(source, ParsedComposition):
        return source
        
    if isinstance(source, LiteratureSampleRecord):
        mn = source.mn_ratio if source.mn_ratio is not None else 0.0
        fe = source.fe_ratio if source.fe_ratio is not None else 0.0
        
        d_dict = {}
        elem_str = source.dopant_element
        x_per_fu = source.dopant_x_per_fu
        
        if elem_str and elem_str.strip().lower() not in ["none/undoped", "none", "undoped"]:
            parsed_elems = parse_dopant_element_string(elem_str, default_x=x_per_fu)
            if len(parsed_elems) > 0:
                d_dict = parsed_elems
                
        return ParsedComposition(mn_ratio=mn, fe_ratio=fe, dopants=d_dict)
        
    # Support ChemicalFormula objects or any object with mn_fraction / fe_fraction
    if source is not None and hasattr(source, "mn_fraction") and hasattr(source, "fe_fraction"):
        mn = float(source.mn_fraction)
        fe = float(source.fe_fraction)
        d_dict = {}
        raw_dopants = getattr(source, "dopants", [])
        if isinstance(raw_dopants, list):
            for d in raw_dopants:
                if hasattr(d, "element"):
                    sym = d.element
                    frac = getattr(d, "fraction", 0.0)
                    ox = getattr(d, "oxidation_state", None)
                elif isinstance(d, dict):
                    sym = d.get("symbol") or d.get("element")
                    frac = d.get("fraction", 0.0)
                    ox = d.get("oxidation_state")
                else:
                    continue
                if sym and str(sym).strip().lower() not in ["none/undoped", "none", "undoped"]:
                    d_dict[str(sym).strip()] = {"fraction": float(frac), "oxidation_state": int(ox) if ox is not None else None}
        elif isinstance(raw_dopants, dict):
            for sym, info in raw_dopants.items():
                if sym and str(sym).strip().lower() not in ["none/undoped", "none", "undoped"]:
                    if isinstance(info, dict):
                        d_dict[str(sym).strip()] = {"fraction": float(info.get("fraction", 0.0)), "oxidation_state": info.get("oxidation_state")}
                    else:
                        d_dict[str(sym).strip()] = {"fraction": float(info), "oxidation_state": None}
        return ParsedComposition(mn_ratio=mn, fe_ratio=fe, dopants=d_dict)
        
    # If explicit parameters passed
    if mn_ratio is not None and fe_ratio is not None:
        mn = float(mn_ratio)
        fe = float(fe_ratio)
        d_dict = {}
        
        if isinstance(dopants, list):
            for item in dopants:
                sym = item.get("symbol") or item.get("element")
                if sym and sym.strip().lower() not in ["none/undoped", "none", "undoped"]:
                    frac = float(item.get("fraction", item.get("conc", 0.0)))
                    ox = item.get("oxidation_state")
                    d_dict[sym] = {"fraction": frac, "oxidation_state": int(ox) if ox is not None else None}
        elif isinstance(dopants, dict):
            for sym, info in dopants.items():
                if sym and sym.strip().lower() not in ["none/undoped", "none", "undoped"]:
                    if isinstance(info, dict):
                        frac = float(info.get("fraction", 0.0))
                        ox = info.get("oxidation_state")
                    else:
                        frac = float(info)
                        ox = None
                    d_dict[sym] = {"fraction": frac, "oxidation_state": int(ox) if ox is not None else None}
        elif isinstance(dopants, str):
            d_dict = parse_dopant_element_string(dopants)
            
        return ParsedComposition(mn_ratio=mn, fe_ratio=fe, dopants=d_dict)
        
    if isinstance(source, dict):
        mn = float(source.get("mn_frac", source.get("mn_ratio", source.get("Mn_Ratio", 0.0))))
        fe = float(source.get("fe_frac", source.get("fe_ratio", source.get("Fe_Ratio", 0.0))))
        d_raw = source.get("dopants") or source.get("Dopant_Element")
        
        return parse_composition(None, mn_ratio=mn, fe_ratio=fe, dopants=d_raw)
        
    raise ValueError("Invalid composition input to parse_composition")

