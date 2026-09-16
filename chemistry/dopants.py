"""
Dopants module for HE-LMFP Designer.
Provides dopant database lookup, validation of dopant selections,
and oxidation state queries.
"""

import json
import os
from typing import Dict, List, Any, Tuple, Optional

def _load_dopant_data() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    # Locate data/dopants.json relative to this file or working directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(base_dir, "data", "dopants.json")
    if not os.path.exists(json_path):
        # Fallback search path
        json_path = os.path.join(os.getcwd(), "data", "dopants.json")
    
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("dopants", {}), data.get("host_elements", {})

DOPANT_DATABASE, HOST_ELEMENTS = _load_dopant_data()

ALLOWED_DOPANTS = [sym for sym, info in DOPANT_DATABASE.items() if info.get("allowed", False)]
EXCLUDED_DOPANTS = [sym for sym, info in DOPANT_DATABASE.items() if not info.get("allowed", False)]

MIN_DOPANTS = 3
MAX_DOPANTS = 5
MIN_DOPANT_CONC = 0.005
MAX_DOPANT_CONC = 0.05

def get_dopant_info(symbol: str) -> Optional[Dict[str, Any]]:
    """Return dictionary info for a dopant symbol."""
    return DOPANT_DATABASE.get(symbol)

def get_host_element_info(symbol: str) -> Optional[Dict[str, Any]]:
    """Return dictionary info for a host element symbol."""
    return HOST_ELEMENTS.get(symbol)

def get_allowed_dopants() -> List[str]:
    """Return list of allowed dopant symbols."""
    return list(ALLOWED_DOPANTS)

def get_excluded_dopants() -> List[str]:
    """Return list of excluded dopant symbols."""
    return list(EXCLUDED_DOPANTS)

def get_valid_oxidation_states(symbol: str) -> List[int]:
    """Return list of valid oxidation states for an element (dopant or host)."""
    if symbol in DOPANT_DATABASE:
        return DOPANT_DATABASE[symbol]["allowed_oxidation_states"]
    elif symbol in HOST_ELEMENTS:
        return [HOST_ELEMENTS[symbol]["default_oxidation_state"]]
    return []

def validate_dopant_selection(dopants: List[str]) -> Tuple[bool, List[str]]:
    """
    Validate selected list of dopants.
    Returns (is_valid, list_of_error_or_warning_messages).
    """
    errors = []
    
    # Check count
    count = len(dopants)
    if count < MIN_DOPANTS or count > MAX_DOPANTS:
        errors.append(f"Invalid dopant count: {count}. Exactly 3, 4, or 5 dopant elements must be selected.")
        
    # Check individual dopants
    for d in dopants:
        if d in EXCLUDED_DOPANTS:
            reason = DOPANT_DATABASE[d].get("exclusion_reason", "Excluded element")
            errors.append(f"Dopant '{d}' is strictly excluded from active design set ({reason}).")
        elif d not in ALLOWED_DOPANTS:
            errors.append(f"Dopant '{d}' is not in the recognized allowed dopant set.")
            
    # Check duplicates
    if len(set(dopants)) != len(dopants):
        errors.append("Duplicate dopant elements selected.")
        
    return (len(errors) == 0, errors)
