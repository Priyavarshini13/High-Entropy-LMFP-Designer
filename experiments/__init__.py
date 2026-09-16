"""
Laboratory Experiment Engine for HE-LMFP Materials.

Provides data models, SQLite storage persistence, input validation,
and computational vs literature vs actual experiment comparison engines.
"""

from .models import (
    ExperimentStatus,
    ActualSynthesisData,
    ActualCharacterizationData,
    ActualElectrochemicalData,
    LabExperiment
)
from .storage import (
    init_db,
    save_experiment,
    load_experiment,
    list_experiments,
    update_experiment,
    delete_experiment,
    export_experiments_to_csv,
    export_experiments_to_json
)
from .validation import validate_lab_experiment
from .comparison import generate_comparison_matrix, ComparisonRow, ComparisonMatrix

__all__ = [
    "ExperimentStatus",
    "ActualSynthesisData",
    "ActualCharacterizationData",
    "ActualElectrochemicalData",
    "LabExperiment",
    "init_db",
    "save_experiment",
    "load_experiment",
    "list_experiments",
    "update_experiment",
    "delete_experiment",
    "export_experiments_to_csv",
    "export_experiments_to_json",
    "validate_lab_experiment",
    "generate_comparison_matrix",
    "ComparisonRow",
    "ComparisonMatrix"
]
