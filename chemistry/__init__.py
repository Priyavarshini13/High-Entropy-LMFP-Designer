"""
Chemistry Package for High-Entropy Doped LMFP Materials Designer.
"""

from .dopants import (
    DOPANT_DATABASE,
    HOST_ELEMENTS,
    ALLOWED_DOPANTS,
    EXCLUDED_DOPANTS,
    MIN_DOPANTS,
    MAX_DOPANTS,
    MIN_DOPANT_CONC,
    MAX_DOPANT_CONC,
    get_dopant_info,
    get_host_element_info,
    get_allowed_dopants,
    get_excluded_dopants,
    get_valid_oxidation_states,
    validate_dopant_selection
)

__all__ = [
    "DOPANT_DATABASE",
    "HOST_ELEMENTS",
    "ALLOWED_DOPANTS",
    "EXCLUDED_DOPANTS",
    "MIN_DOPANTS",
    "MAX_DOPANTS",
    "MIN_DOPANT_CONC",
    "MAX_DOPANT_CONC",
    "get_dopant_info",
    "get_host_element_info",
    "get_allowed_dopants",
    "get_excluded_dopants",
    "get_valid_oxidation_states",
    "validate_dopant_selection"
]
