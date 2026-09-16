"""
Material Modifications Module for HE-LMFP.

Handles Carbon coating, Carbon Nanotube (CNT) additions, and
future mGO (modified Graphene Oxide) status.
"""

from dataclasses import dataclass
from typing import Dict, Any, List

@dataclass
class MaterialModifications:
    modification_mode: str      # "None", "Carbon Coating Only", "CNT Only", "Carbon Coating + CNT"
    carbon_coating_enabled: bool
    carbon_coating_wt_pct: float
    cnt_enabled: bool
    cnt_wt_pct: float
    mgo_enabled: bool            # Default False (Future Feature)
    mgo_status_label: str       # "Future option / Not part of current optimization"
    total_conductive_additive_wt_pct: float
    warnings: List[str]

def get_material_modifications(
    mode: str = "Carbon Coating Only",
    carbon_wt_pct: float = 2.5,
    cnt_wt_pct: float = 1.0,
    enable_mgo: bool = False
) -> MaterialModifications:
    """
    Construct material modification specifications.
    
    Modes supported:
    - "No conductive modification"
    - "Carbon Coating Only"
    - "CNT Only"
    - "Carbon Coating + CNT"
    """
    warnings = []
    
    carbon_enabled = mode in ["Carbon Coating Only", "Carbon Coating + CNT"]
    cnt_enabled = mode in ["CNT Only", "Carbon Coating + CNT"]
    
    actual_carbon_wt = carbon_wt_pct if carbon_enabled else 0.0
    actual_cnt_wt = cnt_wt_pct if cnt_enabled else 0.0
    
    if carbon_enabled and (actual_carbon_wt < 2.0 or actual_carbon_wt > 3.0):
        warnings.append(f"Carbon coating ({actual_carbon_wt:.2f} wt%) is outside supervisor recommended range [2.0, 3.0] wt%.")
        
    if cnt_enabled and (actual_cnt_wt < 0.5 or actual_cnt_wt > 1.5):
        warnings.append(f"CNT addition ({actual_cnt_wt:.2f} wt%) is outside supervisor recommended range [0.5, 1.5] wt%.")
        
    mgo_label = "Future Option (Not part of current optimization)"
    if enable_mgo:
        warnings.append("mGO modification is enabled but flagged as a future/provisional option per supervisor guidelines.")
        
    total_additive_wt = actual_carbon_wt + actual_cnt_wt

    return MaterialModifications(
        modification_mode=mode,
        carbon_coating_enabled=carbon_enabled,
        carbon_coating_wt_pct=actual_carbon_wt,
        cnt_enabled=cnt_enabled,
        cnt_wt_pct=actual_cnt_wt,
        mgo_enabled=enable_mgo,
        mgo_status_label=mgo_label,
        total_conductive_additive_wt_pct=round(total_additive_wt, 3),
        warnings=warnings
    )
