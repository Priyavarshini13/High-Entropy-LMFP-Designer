"""
Data models for Laboratory Experiments in HE-LMFP Materials Design.

Defines structures for actual synthesis parameters, characterization measurements,
electrochemical performance data, experiment statuses, and complete lab experiment records.
"""

from enum import Enum
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime


class ExperimentStatus(str, Enum):
    DESIGNED = "DESIGNED"
    SYNTHESIS_PLANNED = "SYNTHESIS_PLANNED"
    SYNTHESIZED = "SYNTHESIZED"
    CHARACTERIZATION_COMPLETE = "CHARACTERIZATION_COMPLETE"
    ELECTROCHEMICAL_TESTED = "ELECTROCHEMICAL_TESTED"
    EXPERIMENTALLY_VALIDATED = "EXPERIMENTALLY_VALIDATED"


@dataclass
class ActualSynthesisData:
    metal_precursors: Optional[str] = None
    precursor_mass_g: Optional[float] = None
    precipitating_agent: Optional[str] = None
    reaction_ph: Optional[float] = None
    reaction_temp_c: Optional[float] = None
    reaction_time_h: Optional[float] = None
    calcination_temp_c: Optional[float] = None
    calcination_duration_h: Optional[float] = None
    calcination_atmosphere: Optional[str] = None
    yield_pct: Optional[float] = None
    observations: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> Optional["ActualSynthesisData"]:
        if not data:
            return None
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ActualCharacterizationData:
    xrd_phase_purity_pct: Optional[float] = None
    lattice_param_a: Optional[float] = None
    lattice_param_b: Optional[float] = None
    lattice_param_c: Optional[float] = None
    unit_cell_volume: Optional[float] = None
    impurity_phases: Optional[str] = None
    antisite_defects_pct: Optional[float] = None
    sem_morphology: Optional[str] = None
    particle_size_nm: Optional[float] = None
    bet_surface_area_m2g: Optional[float] = None
    electrical_conductivity_scm: Optional[float] = None
    tap_density_gcm3: Optional[float] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> Optional["ActualCharacterizationData"]:
        if not data:
            return None
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ActualElectrochemicalData:
    cap_0_02c: Optional[float] = None
    cap_0_1c: Optional[float] = None
    cap_1c: Optional[float] = None
    cap_2c: Optional[float] = None
    cap_4c: Optional[float] = None
    voltage_min: Optional[float] = None
    voltage_max: Optional[float] = None
    initial_discharge_cap: Optional[float] = None
    initial_coulombic_efficiency: Optional[float] = None
    cycle_life_cycles: Optional[int] = None
    capacity_retention_pct: Optional[float] = None
    retention_25c_pct: Optional[float] = None
    retention_55c_pct: Optional[float] = None
    retention_minus20c_pct: Optional[float] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> Optional["ActualElectrochemicalData"]:
        if not data:
            return None
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class LabExperiment:
    experiment_id: str
    sample_id: str
    created_at: str
    updated_at: str
    operator: str
    batch_id: str
    notes: str
    status: ExperimentStatus
    # Computational Design Parameters
    generated_formula: str
    mn_frac: float
    fe_frac: float
    dopants: List[Dict[str, Any]]
    carbon_wt_pct: float
    cnt_wt_pct: float
    mgo_enabled: bool
    synthesis_route: str
    # Measured Experimental Data
    synthesis_data: Optional[ActualSynthesisData] = None
    characterization_data: Optional[ActualCharacterizationData] = None
    electrochemical_data: Optional[ActualElectrochemicalData] = None

    def update_status_automatically(self):
        """Update experiment status based on recorded data completeness."""
        if self.electrochemical_data and any(
            v is not None for k, v in self.electrochemical_data.to_dict().items() if k != "notes"
        ):
            self.status = ExperimentStatus.EXPERIMENTALLY_VALIDATED
        elif self.characterization_data and any(
            v is not None for k, v in self.characterization_data.to_dict().items() if k != "notes"
        ):
            self.status = ExperimentStatus.CHARACTERIZATION_COMPLETE
        elif self.synthesis_data and any(
            v is not None for k, v in self.synthesis_data.to_dict().items() if k != "observations"
        ):
            self.status = ExperimentStatus.SYNTHESIZED
        else:
            self.status = ExperimentStatus.DESIGNED

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "experiment_id": self.experiment_id,
            "sample_id": self.sample_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "operator": self.operator,
            "batch_id": self.batch_id,
            "notes": self.notes,
            "status": self.status.value if isinstance(self.status, ExperimentStatus) else str(self.status),
            "generated_formula": self.generated_formula,
            "mn_frac": self.mn_frac,
            "fe_frac": self.fe_frac,
            "dopants": self.dopants,
            "carbon_wt_pct": self.carbon_wt_pct,
            "cnt_wt_pct": self.cnt_wt_pct,
            "mgo_enabled": self.mgo_enabled,
            "synthesis_route": self.synthesis_route,
            "synthesis_data": self.synthesis_data.to_dict() if self.synthesis_data else None,
            "characterization_data": self.characterization_data.to_dict() if self.characterization_data else None,
            "electrochemical_data": self.electrochemical_data.to_dict() if self.electrochemical_data else None,
        }
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LabExperiment":
        raw_status = data.get("status", "DESIGNED")
        try:
            status_enum = ExperimentStatus(raw_status)
        except ValueError:
            status_enum = ExperimentStatus.DESIGNED

        return cls(
            experiment_id=data["experiment_id"],
            sample_id=data.get("sample_id", f"SMP-{data['experiment_id']}"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            operator=data.get("operator", "Unspecified"),
            batch_id=data.get("batch_id", "BATCH-001"),
            notes=data.get("notes", ""),
            status=status_enum,
            generated_formula=data.get("generated_formula", "Li[Mn0.65Fe0.26Mg0.02Zn0.02Nb0.01Cu0.02Zr0.02]PO4"),
            mn_frac=data.get("mn_frac", 0.65),
            fe_frac=data.get("fe_frac", 0.26),
            dopants=data.get("dopants", []),
            carbon_wt_pct=data.get("carbon_wt_pct", 2.5),
            cnt_wt_pct=data.get("cnt_wt_pct", 1.0),
            mgo_enabled=data.get("mgo_enabled", False),
            synthesis_route=data.get("synthesis_route", "Co-precipitation"),
            synthesis_data=ActualSynthesisData.from_dict(data.get("synthesis_data")),
            characterization_data=ActualCharacterizationData.from_dict(data.get("characterization_data")),
            electrochemical_data=ActualElectrochemicalData.from_dict(data.get("electrochemical_data")),
        )
