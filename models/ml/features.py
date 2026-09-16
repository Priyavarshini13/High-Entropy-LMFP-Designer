"""
Feature engineering module for High-Entropy LMFP Literature ML Pipeline.

Derives multi-dopant composition features, entropy calculations from V1 chemistry engine,
theoretical capacity metrics, synthesis parameters, and dopant molar ratios.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple

from chemistry.entropy import calculate_configurational_entropy
from chemistry.capacity import calculate_capacity_metrics
from literature.parser import parse_composition

TOP_DOPANT_ELEMENTS = [
    'Co', 'Ti', 'Mg', 'Ni', 'V', 'Al', 'Na', 'Ca', 'Zn', 'Zr', 'F', 'Nb', 'Cr', 'Cu'
]

def get_feature_names() -> List[str]:
    """Return ordered list of engineered feature names for tabular models."""
    base_feats = [
        'Mn_Ratio',
        'Fe_Ratio',
        'Dopant_Count',
        'Sum_Dopant_Ratio',
        'S_config_over_R',
        'Theoretical_Capacity',
        'Carbon_wt_percent',
        'Calcination_Temp_1_C',
        'Calcination_Time_1_h',
    ]
    dopant_feats = [f"dopant_{el}" for el in TOP_DOPANT_ELEMENTS]
    return base_feats + dopant_feats

def extract_features_from_dict(
    mn_ratio: float,
    fe_ratio: float,
    dopants: List[Dict[str, Any]], # list of {"symbol": str, "fraction": float}
    carbon_wt: float = 0.0,
    calc_temp: float = 700.0,
    calc_time: float = 8.0,
    molar_mass: float = 157.7
) -> pd.DataFrame:
    """
    Extract feature vector for a single active composition design.
    """
    feat = {f: 0.0 for f in get_feature_names()}
    
    feat['Mn_Ratio'] = float(mn_ratio)
    feat['Fe_Ratio'] = float(fe_ratio)
    
    # Process dopants
    dop_count = 0
    sum_dop_ratio = 0.0
    for d in dopants:
        sym = d.get('symbol', '').strip()
        frac = float(d.get('fraction', 0.0))
        if frac > 0:
            dop_count += 1
            sum_dop_ratio += frac
            key = f"dopant_{sym}"
            if key in feat:
                feat[key] = frac
                
    feat['Dopant_Count'] = float(dop_count)
    feat['Sum_Dopant_Ratio'] = float(sum_dop_ratio)
    
    # Calculate S_config via V1 chemistry engine
    ent_res = calculate_configurational_entropy(mn_ratio, fe_ratio, dopants)
    feat['S_config_over_R'] = float(ent_res.s_config_over_r)
    
    # Calculate theoretical capacity via V1 chemistry engine
    cap_res = calculate_capacity_metrics(1.0, molar_mass)
    feat['Theoretical_Capacity'] = float(cap_res.formula_calculated_capacity_metric)
    
    feat['Carbon_wt_percent'] = float(carbon_wt or 0.0)
    feat['Calcination_Temp_1_C'] = float(calc_temp or 700.0)
    feat['Calcination_Time_1_h'] = float(calc_time or 8.0)
    
    return pd.DataFrame([feat])[get_feature_names()]

def safe_num(val, default=0.0) -> float:
    n = pd.to_numeric(val, errors='coerce')
    if pd.isna(n):
        return float(default)
    return float(n)

def extract_features_from_dataframe(df: pd.DataFrame) -> Tuple[pd.DataFrame, np.ndarray]:
    """
    Extract feature matrix X and Paper_ID groups array from raw literature dataframe.
    """
    feat_rows = []
    groups = []
    
    for idx, row in df.iterrows():
        paper_id = str(row.get('Paper_ID', f'PAPER_{idx}'))
        if paper_id == 'nan':
            paper_id = f'PAPER_{idx}'
        groups.append(paper_id)
        
        formula = row.get('Full_Doped_Composition')
        if not isinstance(formula, str) or not formula.strip():
            formula = row.get('Composition_Formula')
            
        mn = safe_num(row.get('Mn_Ratio'), 0.0)
        fe = safe_num(row.get('Fe_Ratio'), 0.0)
        d_cnt = safe_num(row.get('Dopant_Count'), 0.0)
        carbon_wt = safe_num(row.get('Carbon_wt_percent'), 0.0)
        calc_temp = safe_num(row.get('Calcination_Temp_1_C'), 700.0)
        calc_time = safe_num(row.get('Calcination_Time_1_h'), 8.0)
        
        top_dopant_ratios = {f"dopant_{el}": 0.0 for el in TOP_DOPANT_ELEMENTS}
        d_elem = str(row.get('Dopant_Element', ''))
        d_ratio = safe_num(row.get('Dopant_Molar_Ratio'), 0.0)
        
        dop_list = []
        if d_elem and d_elem not in ('None/Undoped', 'nan', 'Unspecified'):
            parts = [x.strip() for x in d_elem.split(';')]
            sub_frac = d_ratio / max(1, len(parts))
            for p in parts:
                dop_list.append({"symbol": p, "fraction": sub_frac})
                if f"dopant_{p}" in top_dopant_ratios:
                    top_dopant_ratios[f"dopant_{p}"] = sub_frac
                    
        s_config = 0.0
        q_theo = 170.0
        try:
            if isinstance(formula, str) and formula.strip():
                comp_dict = parse_composition(formula)
                m2_dict = comp_dict.get('M2', {})
                mn = m2_dict.get('Mn', mn)
                fe = m2_dict.get('Fe', fe)
                
                parsed_dopants = [{"symbol": k, "fraction": v} for k, v in m2_dict.items() if k not in ("Mn", "Fe")]
                if parsed_dopants:
                    dop_list = parsed_dopants
                    d_cnt = len(parsed_dopants)
                    
                ent_res = calculate_configurational_entropy(mn, fe, dop_list)
                s_config = ent_res.s_config_over_r
                
                mol_mass = comp_dict.get('molar_mass', 157.7)
                cap_res = calculate_capacity_metrics(1.0, mol_mass)
                q_theo = cap_res.formula_calculated_capacity_metric
        except Exception:
            pass
            
        sum_dop_ratio = sum(d['fraction'] for d in dop_list)
        
        row_feat = {
            'Mn_Ratio': mn,
            'Fe_Ratio': fe,
            'Dopant_Count': d_cnt,
            'Sum_Dopant_Ratio': sum_dop_ratio,
            'S_config_over_R': s_config,
            'Theoretical_Capacity': q_theo,
            'Carbon_wt_percent': carbon_wt,
            'Calcination_Temp_1_C': calc_temp,
            'Calcination_Time_1_h': calc_time,
            **top_dopant_ratios
        }
        feat_rows.append(row_feat)
        
    X_df = pd.DataFrame(feat_rows)[get_feature_names()]
    return X_df, np.array(groups)
