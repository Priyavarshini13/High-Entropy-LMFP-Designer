"""
Evaluation module comparing trained ML models against simple baselines.

Implements GroupKFold publication-grouped cross-validation to rigorously compare:
1. Training-fold median baseline (predicting median of training fold targets)
2. Production RandomForest model

Measures MAE, RMSE, and R2 across folds without data leakage.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import json
import numpy as np
import pandas as pd
from typing import Dict, Any
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GroupKFold
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from models.ml.features import extract_features_from_dataframe, get_feature_names
from models.ml.trainer import TARGET_CONFIGS


def evaluate_models_against_baseline(
    csv_path: str,
    n_splits: int = 5,
    random_state: int = 42
) -> Dict[str, Any]:
    """
    Perform a strict publication-grouped cross-validation comparing
    RandomForest models against training-fold median baselines.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset not found at {csv_path}")

    df_raw = pd.read_csv(csv_path)
    X_all, _ = extract_features_from_dataframe(df_raw)

    # Construct publication grouping by DOI with normalized title fallback
    doi_groups = (
        df_raw["DOI"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"^https?://(?:dx\.)?doi\.org/", "", regex=True)
        .str.replace(r"^doi:\s*", "", regex=True)
    )

    title_groups = (
        df_raw["Paper_Title"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", " ", regex=True)
    )

    groups_all = doi_groups.where(
        doi_groups.ne(""),
        "title:" + title_groups
    )

    missing_identity = doi_groups.eq("") & title_groups.eq("")
    groups_all = groups_all.astype(str)
    groups_all.loc[missing_identity] = (
        "unknown:" + df_raw.loc[missing_identity, "Sample_ID"].astype(str)
    )
    groups_all = groups_all.to_numpy()

    results: Dict[str, Any] = {
        "dataset_path": csv_path,
        "total_records": len(df_raw),
        "total_publications": int(pd.Series(groups_all).nunique()),
        "targets": {}
    }

    for target_key, cfg in TARGET_CONFIGS.items():
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
            results["targets"][target_key] = {
                "target_key": target_key,
                "label": cfg["label"],
                "unit": cfg["unit"],
                "status": "insufficient_data",
                "sample_count": n_samples,
                "paper_count": n_papers,
                "message": "Insufficient literature data for reliable evaluation."
            }
            continue

        actual_splits = min(n_splits, n_papers)
        gkf = GroupKFold(n_splits=actual_splits)

        rf_maes, rf_rmses, rf_r2s = [], [], []
        base_maes, base_rmses, base_r2s = [], [], []

        for train_idx, val_idx in gkf.split(X_sub, y_sub, groups_sub):
            X_tr, X_val = X_sub.iloc[train_idx], X_sub.iloc[val_idx]
            y_tr, y_val = y_sub.iloc[train_idx], y_sub.iloc[val_idx]

            # 1. Baseline: Predict median of training fold targets
            median_pred = float(np.median(y_tr))
            base_preds = np.full_like(y_val, fill_value=median_pred)

            base_maes.append(mean_absolute_error(y_val, base_preds))
            base_rmses.append(np.sqrt(mean_squared_error(y_val, base_preds)))
            base_r2s.append(r2_score(y_val, base_preds))

            # 2. Model: RandomForestRegressor
            rf = RandomForestRegressor(n_estimators=100, max_depth=8, random_state=random_state)
            rf.fit(X_tr, y_tr)
            rf_preds = rf.predict(X_val)

            rf_maes.append(mean_absolute_error(y_val, rf_preds))
            rf_rmses.append(np.sqrt(mean_squared_error(y_val, rf_preds)))
            rf_r2s.append(r2_score(y_val, rf_preds))

        results["targets"][target_key] = {
            "target_key": target_key,
            "label": cfg["label"],
            "unit": cfg["unit"],
            "status": "evaluated",
            "sample_count": n_samples,
            "paper_count": n_papers,
            "cv_strategy": f"GroupKFold ({actual_splits}-fold by publication)",
            "model_metrics": {
                "mae": round(float(np.mean(rf_maes)), 2),
                "mae_std": round(float(np.std(rf_maes)), 2),
                "rmse": round(float(np.mean(rf_rmses)), 2),
                "rmse_std": round(float(np.std(rf_rmses)), 2),
                "r2": round(float(np.mean(rf_r2s)), 3),
                "r2_std": round(float(np.std(rf_r2s)), 3)
            },
            "baseline_metrics": {
                "mae": round(float(np.mean(base_maes)), 2),
                "mae_std": round(float(np.std(base_maes)), 2),
                "rmse": round(float(np.mean(base_rmses)), 2),
                "rmse_std": round(float(np.std(base_rmses)), 2),
                "r2": round(float(np.mean(base_r2s)), 3),
                "r2_std": round(float(np.std(base_r2s)), 3)
            },
            "comparison": {
                "mae_delta": round(float(np.mean(rf_maes) - np.mean(base_maes)), 2),
                "rmse_delta": round(float(np.mean(rf_rmses) - np.mean(base_rmses)), 2),
                "r2_delta": round(float(np.mean(rf_r2s) - np.mean(base_r2s)), 3),
                "model_beats_baseline_mae": bool(np.mean(rf_maes) < np.mean(base_maes))
            }
        }

    return results


if __name__ == "__main__":
    csv_file = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "data", "literature_reference.csv")
    )
    res = evaluate_models_against_baseline(csv_file)
    print(json.dumps(res, indent=2))
