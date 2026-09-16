"""
Synthesis & Processing Module for HE-LMFP Materials.

Primary Synthesis Route: Co-precipitation.
Per supervisor directive, unsupported synthesis parameters (pH, temperature, 
calcination conditions, precursors) are NOT populated with fabricated default values.
They are kept as configurable placeholders clearly labeled as
'Not specified by supervisor (Requires experimental input)'.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List

NOT_SPECIFIED = "Not specified by supervisor (Requires experimental input)"

@dataclass
class SynthesisProcessing:
    primary_synthesis_method: str  # Fixed to "Co-precipitation"
    sol_gel_status: str             # "Excluded / Not active method"
    metal_precursors: str           # User input or NOT_SPECIFIED
    precipitating_agent: str        # User input or NOT_SPECIFIED
    chelating_agent: str            # User input or NOT_SPECIFIED
    reaction_ph: str                # User input or NOT_SPECIFIED
    reaction_temperature: str       # User input or NOT_SPECIFIED
    calcination_temperature: str    # User input or NOT_SPECIFIED
    calcination_duration: str       # User input or NOT_SPECIFIED
    calcination_atmosphere: str     # User input or NOT_SPECIFIED
    notes: List[str]

def get_coprecipitation_processing(
    metal_precursors: str = NOT_SPECIFIED,
    precipitating_agent: str = NOT_SPECIFIED,
    chelating_agent: str = NOT_SPECIFIED,
    reaction_ph: str = NOT_SPECIFIED,
    reaction_temperature: str = NOT_SPECIFIED,
    calcination_temperature: str = NOT_SPECIFIED,
    calcination_duration: str = NOT_SPECIFIED,
    calcination_atmosphere: str = NOT_SPECIFIED
) -> SynthesisProcessing:
    """
    Build synthesis processing configuration for Co-precipitation.
    """
    notes = [
        "Co-precipitation is established as the primary required synthesis route.",
        "Sol-gel is currently excluded from active primary optimization workflow.",
        "Specific chemical precursor, pH, and calcination parameters are configurable place-holders requiring experimental confirmation."
    ]

    return SynthesisProcessing(
        primary_synthesis_method="Co-precipitation",
        sol_gel_status="Excluded from V1 active workflow",
        metal_precursors=metal_precursors if metal_precursors else NOT_SPECIFIED,
        precipitating_agent=precipitating_agent if precipitating_agent else NOT_SPECIFIED,
        chelating_agent=chelating_agent if chelating_agent else NOT_SPECIFIED,
        reaction_ph=reaction_ph if reaction_ph else NOT_SPECIFIED,
        reaction_temperature=reaction_temperature if reaction_temperature else NOT_SPECIFIED,
        calcination_temperature=calcination_temperature if calcination_temperature else NOT_SPECIFIED,
        calcination_duration=calcination_duration if calcination_duration else NOT_SPECIFIED,
        calcination_atmosphere=calcination_atmosphere if calcination_atmosphere else NOT_SPECIFIED,
        notes=notes
    )
