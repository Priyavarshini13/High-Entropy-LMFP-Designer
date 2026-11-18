"""
Model Training & GroupKFold Cross-Validation Pipeline for Literature ML Stage.

Strictly enforces Paper-Level GroupKFold splitting to prevent data leakage across papers.
Saves serialized model artifacts and metadata JSON for inference.
"""

import os
import json
import joblib
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GroupKFold
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from models.ml.features import get_feature_names, extract_features_from_dataframe

ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")

TARGET_CONFIGS = {
    "0_1C_capacity": {
        "column": "Discharge_Capacity_0_1C_mAh_g",
        "label": "0.1C Discharge Capacity",
        "unit": "mAh/g",
        "min_val": 10.0,
        "max_val": 220.0,
        "min_samples": 80
    },
    "1C_capacity": {
        "column": "Discharge_Capacity_1C_mAh_g",
        "label": "1C Discharge Capacity",
        "unit": "mAh/g",
        "min_val": 10.0,
        "max_val": 220.0,
        "min_samples": 80
    },
    "5C_capacity": {
        "column": "Discharge_Capacity_5C_mAh_g",
        "label": "5C Discharge Capacity",
        "unit": "mAh/g",
        "min_val": 5.0,
        "max_val": 220.0,
        "min_samples": 80
    },
    "capacity_retention": {
        "column": "Capacity_Retention_percent",
        "label": "Capacity Retention",
        "unit": "%",
        "min_val": 10.0,
        "max_val": 110.0,
        "min_samples": 80
    },
    "0_05C_capacity": {
        "column": "Discharge_Capacity_0_05C_mAh_g",
        "label": "0.05C Discharge Capacity",
        "unit": "mAh/g",
        "min_val": 10.0,
        "max_val": 220.0,
        "min_samples": 80
    },
    "initial_ice": {
        "column": "Initial_Coulombic_Efficiency_percent",
        "label": "Initial Coulombic Efficiency",
        "unit": "%",
        "min_val": 50.0,
        "max_val": 100.0,
        "min_samples": 80
    }
}

def train_and_evaluate_target(
    X_all: pd.DataFrame,
    groups_all: np.ndarray,
    df_raw: pd.DataFrame,
    target_key: str,
    cfg: Dict[str, Any]
) -> Tuple[Any, Dict[str, Any]]:
    """
    Quality filter data, perform GroupKFold CV grouped by Paper_ID, and fit full RandomForest model.
    """
    col_name = cfg["column"]
    min_v, max_v = cfg["min_val"], cfg["max_val"]
    
    y_raw = pd.to_numeric(df_raw[col_name], errors="coerce")
    valid_mask = (y_raw >= min_v) & (y_raw <= max_v)
    
    X_sub = X_all[valid_mask].copy()
    y_sub = y_raw[valid_mask].copy()
    groups_sub = groups_all[valid_mask]
    
    n_samples = len(y_sub)
    n_papers = len(np.unique(groups_sub))
    
    if n_samples < cfg["min_samples"] or n_papers < 10:
        meta = {
            "target_key": target_key,
            "label": cfg["label"],
            "unit": cfg["unit"],
            "status": "insufficient_data",
            "message": "Insufficient literature data for reliable ML model.",
            "sample_count": n_samples,
            "paper_count": n_papers
        }
        return None, meta
        
    n_splits = min(5, n_papers)
    gkf = GroupKFold(n_splits=n_splits)
    
    maes, rmses, r2s = [], [], []
    
    for train_idx, val_idx in gkf.split(X_sub, y_sub, groups_sub):
        X_tr, X_val = X_sub.iloc[train_idx], X_sub.iloc[val_idx]
        y_tr, y_val = y_sub.iloc[train_idx], y_sub.iloc[val_idx]
        
        rf = RandomForestRegressor(n_estimators=100, max_depth=8, random_state=42)
        rf.fit(X_tr, y_tr)
        preds = rf.predict(X_val)
        
        maes.append(mean_absolute_error(y_val, preds))
        rmses.append(np.sqrt(mean_squared_error(y_val, preds)))
        r2s.append(r2_score(y_val, preds))
        
    # Fit final production model on full quality-filtered subset
    final_rf = RandomForestRegressor(n_estimators=100, max_depth=8, random_state=42)
    final_rf.fit(X_sub, y_sub)
    
    meta = {
        "target_key": target_key,
        "label": cfg["label"],
        "unit": cfg["unit"],
        "status": "trained",
        "sample_count": n_samples,
        "paper_count": n_papers,
        "cv_strategy": f"GroupKFold ({n_splits}-fold by Paper_ID)",
        "metrics": {
            "mae": round(float(np.mean(maes)), 2),
            "mae_std": round(float(np.std(maes)), 2),
            "rmse": round(float(np.mean(rmses)), 2),
            "rmse_std": round(float(np.std(rmses)), 2),
            "r2": round(float(np.mean(r2s)), 3),
            "r2_std": round(float(np.std(r2s)), 3)
        }
    }
    return final_rf, meta

def train_all_models(csv_path: str) -> Dict[str, Any]:
    """
    Execute full dataset loading, feature matrix extraction, model training, and artifact serialization.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Literature dataset not found at {csv_path}")
        
    df_raw = pd.read_csv(csv_path)
    X_all, groups_all = extract_features_from_dataframe(df_raw)
    
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    
    metadata = {
        "dataset_path": csv_path,
        "total_records": len(df_raw),
        "total_papers": int(pd.Series(groups_all).nunique()),
        "feature_names": get_feature_names(),
        "model_type": "RandomForestRegressor(n_estimators=100, max_depth=8)",
        "validation_strategy": "GroupKFold by Paper_ID",
        "targets": {}
    }
    
    for key, cfg in TARGET_CONFIGS.items():
        model, meta = train_and_evaluate_target(X_all, groups_all, df_raw, key, cfg)
        metadata["targets"][key] = meta
        
        if model is not None:
            model_path = os.path.join(ARTIFACTS_DIR, f"model_{key}.joblib")
            joblib.dump(model, model_path)
            
    meta_path = os.path.join(ARTIFACTS_DIR, "ml_metadata.json")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
        
    return metadata

if __name__ == "__main__":
    csv_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "literature_reference.csv"))
    res = train_all_models(csv_file)
    print("Training finished successfully. Summary:")
    print(json.dumps(res, indent=2))
