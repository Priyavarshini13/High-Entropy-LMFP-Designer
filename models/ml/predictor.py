"""
Inference engine for Literature-Based ML Stage in HE-LMFP Designer.

Loads trained model artifacts, computes predictions and tree standard deviation uncertainty,
and applies data coverage / HE-LMFP domain warnings.
"""

import os
import json
import joblib
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from models.ml.features import extract_features_from_dict

ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")

_MODELS_CACHE = None
_METADATA_CACHE = None

def load_trained_models(artifacts_dir: str = ARTIFACTS_DIR) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Load serialized model artifacts and metadata JSON into memory.
    """
    global _MODELS_CACHE, _METADATA_CACHE
    
    meta_path = os.path.join(artifacts_dir, "ml_metadata.json")
    if not os.path.exists(meta_path):
        # Auto-train if artifacts are missing
        from models.ml.trainer import train_all_models
        csv_file = os.path.abspath(os.path.join(artifacts_dir, "..", "..", "..", "data", "literature_reference.csv"))
        train_all_models(csv_file)
        
    with open(meta_path, "r") as f:
        metadata = json.load(f)
        
    models = {}
    for t_key, t_meta in metadata.get("targets", {}).items():
        if t_meta.get("status") == "trained":
            model_path = os.path.join(artifacts_dir, f"model_{t_key}.joblib")
            if os.path.exists(model_path):
                models[t_key] = joblib.load(model_path)
                
    _MODELS_CACHE = models
    _METADATA_CACHE = metadata
    return models, metadata

def predict_composition_performance(
    mn_ratio: float,
    fe_ratio: float,
    dopants: List[Dict[str, Any]],
    carbon_wt: float = 0.0,
    calc_temp: float = 700.0,
    calc_time: float = 8.0,
    molar_mass: float = 157.7,
    artifacts_dir: str = ARTIFACTS_DIR
) -> Dict[str, Any]:
    """
    Generate literature ML predictions and uncertainty for a designed HE-LMFP composition.
    """
    models, metadata = load_trained_models(artifacts_dir)
    
    X_df = extract_features_from_dict(
        mn_ratio=mn_ratio,
        fe_ratio=fe_ratio,
        dopants=dopants,
        carbon_wt=carbon_wt,
        calc_temp=calc_temp,
        calc_time=calc_time,
        molar_mass=molar_mass
    )
    
    dopant_count = len([d for d in dopants if d.get('fraction', 0) > 0])
    
    predictions = {}
    
    for t_key, t_meta in metadata.get("targets", {}).items():
        label = t_meta.get("label", t_key)
        unit = t_meta.get("unit", "")
        status = t_meta.get("status", "insufficient_data")
        
        if status == "trained" and t_key in models:
            rf = models[t_key]
            val_pred = float(rf.predict(X_df)[0])
            
            # Tree-level predictions for standard deviation uncertainty calculation
            tree_preds = np.array([tree.predict(X_df.values)[0] for tree in rf.estimators_])
            std_uncertainty = float(np.std(tree_preds))
            
            predictions[t_key] = {
                "target_key": t_key,
                "label": label,
                "unit": unit,
                "status": "trained",
                "predicted_value": round(val_pred, 2),
                "std_uncertainty": round(std_uncertainty, 2),
                "sample_count": t_meta.get("sample_count", 0),
                "paper_count": t_meta.get("paper_count", 0),
                "metrics": t_meta.get("metrics", {}),
                "disclaimer": "Literature-trained ML prediction — not experimentally validated by ECMT."
            }
        else:
            predictions[t_key] = {
                "target_key": t_key,
                "label": label,
                "unit": unit,
                "status": "insufficient_data",
                "message": t_meta.get("message", "Insufficient literature data for reliable ML model."),
                "sample_count": t_meta.get("sample_count", 0),
                "paper_count": t_meta.get("paper_count", 0)
            }
            
    # Formulate coverage warnings
    coverage_warnings = []
    if dopant_count >= 3:
        coverage_warnings.append(
            "Notice: Dataset contains 6 high-entropy (3+ dopants) literature records out of 1,215 total. "
            "ML predictions represent an initial literature-based baseline for multi-doping."
        )
    if carbon_wt == 0.0:
        coverage_warnings.append(
            "Notice: Carbon wt% is set to 0.0%. Literature records typically use 1–5 wt% carbon coating."
        )
        
    return {
        "predictions": predictions,
        "dopant_count": dopant_count,
        "coverage_warnings": coverage_warnings,
        "metadata": {
            "model_type": metadata.get("model_type"),
            "validation_strategy": metadata.get("validation_strategy"),
            "total_literature_records": metadata.get("total_records"),
            "total_papers": metadata.get("total_papers")
        }
    }
