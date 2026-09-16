"""
Unit tests for Literature-Based ML Module in HE-LMFP Designer.

Tests dataset loading, feature engineering, missing value handling, GroupKFold paper leakage prevention,
model training, prediction inference, invalid composition handling, missing target behavior, and artifact loading.
"""

import os
import json
import pytest
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

from models.ml.features import get_feature_names, extract_features_from_dict, extract_features_from_dataframe
from models.ml.trainer import train_all_models, ARTIFACTS_DIR
from models.ml.predictor import load_trained_models, predict_composition_performance
from chemistry.charge_balance import calculate_charge_balance
from chemistry.formula import generate_formula

DATASET_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "literature_reference.csv"))


def test_dataset_loading():
    """1. Test literature dataset exists and loads correctly."""
    assert os.path.exists(DATASET_PATH), "Literature CSV dataset missing."
    df = pd.read_csv(DATASET_PATH)
    assert len(df) >= 1200, f"Expected at least 1200 records, got {len(df)}"
    assert "Paper_ID" in df.columns
    assert "Discharge_Capacity_0_1C_mAh_g" in df.columns


def test_feature_generation():
    """2. Test feature engineering for single dict and dataframe inputs."""
    feat_names = get_feature_names()
    assert len(feat_names) >= 15
    assert "Mn_Ratio" in feat_names
    assert "S_config_over_R" in feat_names
    assert "Theoretical_Capacity" in feat_names
    
    dopants = [
        {"symbol": "Mg", "fraction": 0.02, "oxidation_state": 2},
        {"symbol": "Zn", "fraction": 0.02, "oxidation_state": 2}
    ]
    df_feat = extract_features_from_dict(
        mn_ratio=0.70,
        fe_ratio=0.26,
        dopants=dopants,
        carbon_wt=3.0,
        calc_temp=700.0,
        calc_time=8.0
    )
    assert list(df_feat.columns) == feat_names
    assert float(df_feat["Mn_Ratio"].iloc[0]) == 0.70
    assert float(df_feat["Dopant_Count"].iloc[0]) == 2.0
    assert float(df_feat["dopant_Mg"].iloc[0]) == 0.02
    assert float(df_feat["S_config_over_R"].iloc[0]) > 0.0


def test_missing_value_handling():
    """3. Test robust handling of missing or NaN values in feature extraction."""
    raw_df = pd.DataFrame([{
        "Paper_ID": "P1",
        "Composition_Formula": "LiMn0.8Fe0.2PO4",
        "Mn_Ratio": np.nan,
        "Fe_Ratio": None,
        "Dopant_Count": np.nan,
        "Carbon_wt_percent": "invalid_str",
        "Calcination_Temp_1_C": np.nan
    }])
    X_df, groups = extract_features_from_dataframe(raw_df)
    assert len(X_df) == 1
    assert not X_df.isna().any().any(), "Feature matrix contains NaN values"
    assert groups[0] == "P1"


def test_paper_level_leakage_prevention():
    """4. Test that GroupKFold strictly prevents paper-level leakage between train and test splits."""
    df = pd.read_csv(DATASET_PATH)
    X_all, groups = extract_features_from_dataframe(df)
    
    gkf = GroupKFold(n_splits=5)
    for fold, (train_idx, val_idx) in enumerate(gkf.split(X_all, np.zeros(len(X_all)), groups)):
        train_papers = set(groups[train_idx])
        val_papers = set(groups[val_idx])
        intersection = train_papers.intersection(val_papers)
        assert len(intersection) == 0, f"Fold {fold} has paper leakage: {intersection}"


def test_model_training():
    """5. Test full training execution and metadata file creation."""
    meta = train_all_models(DATASET_PATH)
    assert "targets" in meta
    assert meta["targets"]["0_1C_capacity"]["status"] == "trained"
    assert meta["targets"]["capacity_retention"]["status"] == "trained"
    assert os.path.exists(os.path.join(ARTIFACTS_DIR, "ml_metadata.json"))


def test_prediction_output_structure():
    """6. Test prediction response structure and uncertainty calculations."""
    dopants = [
        {"symbol": "Mg", "fraction": 0.02, "oxidation_state": 2},
        {"symbol": "Zn", "fraction": 0.02, "oxidation_state": 2}
    ]
    res = predict_composition_performance(
        mn_ratio=0.70,
        fe_ratio=0.26,
        dopants=dopants,
        carbon_wt=2.5
    )
    assert "predictions" in res
    assert "coverage_warnings" in res
    preds = res["predictions"]
    
    # Check 0.1C capacity trained prediction
    p01 = preds["0_1C_capacity"]
    assert p01["status"] == "trained"
    assert 50.0 <= p01["predicted_value"] <= 200.0
    assert p01["std_uncertainty"] >= 0.0
    assert "Literature-trained ML prediction" in p01["disclaimer"]


def test_invalid_composition_rejection():
    """7. Test UI/API level rejection flow when M2 occupancy is invalid."""
    mn_frac, fe_frac = 0.80, 0.30  # Sum = 1.1000 (Invalid M2 occupancy)
    dopants = []
    cb_res = calculate_charge_balance(mn_frac, fe_frac, dopants)
    assert cb_res.m2_occupancy_valid is False
    assert abs(cb_res.m2_occupancy - 1.1000) < 1e-4


def test_valid_composition_prediction():
    """8. Test inference for a valid high-entropy multi-doped composition."""
    mn_frac, fe_frac = 0.65, 0.26
    dopants = [
        {"symbol": "Mg", "fraction": 0.02, "oxidation_state": 2},
        {"symbol": "Zn", "fraction": 0.02, "oxidation_state": 2},
        {"symbol": "Nb", "fraction": 0.01, "oxidation_state": 5},
        {"symbol": "Cu", "fraction": 0.02, "oxidation_state": 2},
        {"symbol": "Zr", "fraction": 0.02, "oxidation_state": 4}
    ]
    cb_res = calculate_charge_balance(mn_frac, fe_frac, dopants)
    assert cb_res.m2_occupancy_valid is True
    formula = generate_formula(cb_res.adjusted_li, mn_frac, fe_frac, dopants)
    
    res = predict_composition_performance(
        mn_ratio=mn_frac,
        fe_ratio=fe_frac,
        dopants=dopants,
        carbon_wt=3.0,
        molar_mass=formula.molar_mass
    )
    assert res["dopant_count"] == 5
    assert len(res["coverage_warnings"]) >= 1  # 3+ dopants HE warning triggered
    assert "6 high-entropy" in res["coverage_warnings"][0]


def test_missing_target_behavior():
    """9. Test that targets with insufficient observations explicitly display missing status."""
    dopants = [{"symbol": "Co", "fraction": 0.05, "oxidation_state": 2}]
    res = predict_composition_performance(mn_ratio=0.7, fe_ratio=0.25, dopants=dopants)
    preds = res["predictions"]
    
    # Initial ICE has only 18 records -> should be skipped
    p_ice = preds["initial_ice"]
    assert p_ice["status"] == "insufficient_data"
    assert "Insufficient literature data for reliable ML model." in p_ice["message"]
    
    # 0.05C Capacity has 50 records -> should be skipped
    p_005c = preds["0_05C_capacity"]
    assert p_005c["status"] == "insufficient_data"
    assert "Insufficient literature data for reliable ML model." in p_005c["message"]


def test_model_artifact_loading():
    """10. Test loading trained model artifacts from disk."""
    models, metadata = load_trained_models(ARTIFACTS_DIR)
    assert isinstance(models, dict)
    assert len(models) >= 4  # 0.1C, 1C, 5C, Retention
    assert "0_1C_capacity" in models
    assert "capacity_retention" in models
    assert metadata["total_records"] == 1215
