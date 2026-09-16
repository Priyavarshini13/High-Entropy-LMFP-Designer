"""
Design Package for HE-LMFP Materials.
Contains material modifications, synthesis processing, characterization plans,
and electrochemical design modules.
"""

from .modifications import MaterialModifications, get_material_modifications
from .processing import SynthesisProcessing, get_coprecipitation_processing
from .characterization import CharacterizationPlan, get_characterization_plan
from .electrochemistry import ElectrochemicalPlan, get_electrochemical_plan

__all__ = [
    "MaterialModifications",
    "get_material_modifications",
    "SynthesisProcessing",
    "get_coprecipitation_processing",
    "CharacterizationPlan",
    "get_characterization_plan",
    "ElectrochemicalPlan",
    "get_electrochemical_plan"
]
