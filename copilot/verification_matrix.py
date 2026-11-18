"""
Cross-Study Hypothesis Synthesis & Experimental Verification Matrix Engine.

Connects Literature Intelligence, Research Gaps (Milestone 4.2),
Scientific Hypotheses (Milestone 4.3), Materials Designer, Property Prediction (ML),
and Experiment Management into an integrated, evidence-backed workflow.

Enforces:
1. Complete link from hypothesis -> gap -> supporting papers -> samples -> measurements.
2. Structured experimental verification matrix with candidate composition, control samples,
   independent/dependent/controlled variables, synthesis plan, characterization battery,
   and electrochemical testing protocols.
3. Strict preservation of uncertainty and epistemic separation:
   - "EXPERIMENT_STATUS": "PROPOSED_UNPERFORMED" (never claimed as executed).
   - "ML_VALIDATION_STATUS": "IN_SILICO_PREDICTION_NOT_EXPERIMENTAL_PROOF".
   - "SUPERVISOR_POLICY": Explicitly marked separately from scientific laws.
4. Chemical charge neutrality ($Q_{net} = 0$) and physical plausibility via deterministic chemistry engine.
"""

import json
import logging
import math
import os
import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd

from chemistry.capacity import REFERENCE_THEORETICAL_CAPACITY, calculate_capacity_metrics
from chemistry.charge_balance import calculate_charge_balance, TOLERANCE
from chemistry.dopants import (
    ALLOWED_DOPANTS,
    DOPANT_DATABASE,
    EXCLUDED_DOPANTS,
    get_dopant_info,
    get_valid_oxidation_states,
)
from copilot.hypothesis_engine import (
    EpistemicType,
    HypothesisCategory,
    HypothesisStatus,
    ScientificHypothesis,
    get_hypothesis_generation_engine,
)

logger = logging.getLogger("copilot.verification_matrix")


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class VariableType(str, Enum):
    INDEPENDENT = "INDEPENDENT"
    DEPENDENT = "DEPENDENT"
    CONTROLLED = "CONTROLLED"


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class VariableSpecification:
    """Specification of an experimental variable in the verification matrix."""
    variable_name: str
    variable_type: VariableType
    target_value: str
    tolerance: str
    rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "variable_name": self.variable_name,
            "variable_type": self.variable_type.value,
            "target_value": self.target_value,
            "tolerance": self.tolerance,
            "rationale": self.rationale,
        }


@dataclass
class MatrixControlSample:
    """Specification of a control or comparison sample in the matrix."""
    sample_id: str
    label: str
    formula: str
    role: str  # e.g. "NEGATIVE_CONTROL", "POSITIVE_CONTROL", "REPLICATION_BASELINE", "COUNTER_PRECURSOR_CONTROL"
    expected_behavior: str
    epistemic_status: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SynthesisProtocolStep:
    """Discrete step in the candidate material synthesis plan."""
    step_number: int
    operation: str
    parameters: Dict[str, Any]
    atmosphere: str
    equipment: str
    safety_notes: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CharacterizationRequirement:
    """Pre-cycling characterization requirement with technique and acceptance criteria."""
    technique: str
    instrument: str
    target_feature: str
    acceptance_criteria: str
    epistemic_importance: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ElectrochemicalTestProtocol:
    """Standardized electrochemical evaluation protocol."""
    protocol_name: str
    voltage_window: str
    c_rates: List[float]
    temperature: str
    cycle_count: int
    mass_loading_min_mg_cm2: float
    electrolyte_spec: str
    target_metrics: Dict[str, str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExperimentalVerificationMatrix:
    """
    End-to-end Cross-Study Experimental Verification Matrix.
    Links Research Gap -> Scientific Hypothesis -> Materials Designer -> ML Predictor -> Lab Plan.
    """
    matrix_id: str
    title: str
    hypothesis_id: str
    research_gap_id: str
    scientific_question: str
    candidate_composition: str
    intended_dopants: List[Dict[str, Any]]
    supporting_literature: Dict[str, Any]
    chemical_validation: Dict[str, Any]
    materials_designer_link: Dict[str, Any]
    property_prediction_link: Dict[str, Any]
    supervisor_policy_link: Dict[str, Any]
    control_samples: List[MatrixControlSample]
    variable_specifications: List[VariableSpecification]
    synthesis_plan: List[SynthesisProtocolStep]
    characterization_plan: List[CharacterizationRequirement]
    electrochemical_plan: List[ElectrochemicalTestProtocol]
    expected_outcomes: List[str]
    falsification_criteria: List[str]
    researcher_selection_required: List[str]
    status_disclaimers: Dict[str, str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "matrix_id": self.matrix_id,
            "title": self.title,
            "hypothesis_id": self.hypothesis_id,
            "research_gap_id": self.research_gap_id,
            "scientific_question": self.scientific_question,
            "candidate_composition": self.candidate_composition,
            "intended_dopants": self.intended_dopants,
            "supporting_literature": self.supporting_literature,
            "chemical_validation": self.chemical_validation,
            "materials_designer_link": self.materials_designer_link,
            "property_prediction_link": self.property_prediction_link,
            "supervisor_policy_link": self.supervisor_policy_link,
            "control_samples": [s.to_dict() for s in self.control_samples],
            "variable_specifications": [v.to_dict() for v in self.variable_specifications],
            "synthesis_plan": [s.to_dict() for s in self.synthesis_plan],
            "characterization_plan": [c.to_dict() for c in self.characterization_plan],
            "electrochemical_plan": [e.to_dict() for e in self.electrochemical_plan],
            "expected_outcomes": self.expected_outcomes,
            "falsification_criteria": self.falsification_criteria,
            "researcher_selection_required": self.researcher_selection_required,
            "status_disclaimers": self.status_disclaimers,
        }


# ---------------------------------------------------------------------------
# VerificationMatrixEngine
# ---------------------------------------------------------------------------

class VerificationMatrixEngine:
    """
    Engine for synthesizing structured Experimental Verification Matrices.
    Integrates Literature Intelligence, Hypotheses, Materials Designer,
    ML Surrogates, and Lab Experiment Planning.
    """

    def __init__(
        self,
        hypothesis_engine: Optional[Any] = None,
        csv_path: Optional[str] = None,
    ):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.csv_path = csv_path or os.path.join(base_dir, "data", "literature_reference.csv")
        self.hypothesis_engine = hypothesis_engine or get_hypothesis_generation_engine()
        self._df: Optional[pd.DataFrame] = None

    def _get_df(self) -> pd.DataFrame:
        if self._df is None:
            if os.path.exists(self.csv_path):
                self._df = pd.read_csv(self.csv_path, low_memory=False)
            else:
                self._df = pd.DataFrame()
        return self._df

    def _build_materials_designer_link(
        self,
        candidate_formula: str,
        mn_ratio: float,
        fe_ratio: float,
        dopants: List[Dict[str, Any]],
        user_li: float = 1.0,
    ) -> Dict[str, Any]:
        """Compute Materials Designer properties (molar mass, capacity metrics, entropy)."""
        # Estimate molar mass
        # Li: 6.94, Mn: 54.94, Fe: 55.85, P: 30.97, O4: 64.00 = ~157.7 g/mol for baseline
        m2_mass = mn_ratio * 54.94 + fe_ratio * 55.85
        for d in dopants:
            sym = d.get("symbol", "")
            frac = d.get("fraction", 0.0)
            d_info = get_dopant_info(sym)
            atomic_mass = d_info.get("atomic_mass", 50.0) if d_info else 50.0
            m2_mass += frac * atomic_mass
        molar_mass = round(user_li * 6.94 + m2_mass + 30.97 + 64.00, 2)

        cap_metrics = calculate_capacity_metrics(li_fraction=user_li, molar_mass=molar_mass)

        return {
            "molar_mass_g_mol": molar_mass,
            "reference_theoretical_capacity_mAh_g": REFERENCE_THEORETICAL_CAPACITY,
            "formula_theoretical_capacity_mAh_g": round(cap_metrics.formula_calculated_capacity_metric, 1),
            "practical_target_min_0_1C": cap_metrics.practical_target_min,
            "practical_target_max_0_1C": cap_metrics.practical_target_max,
            "voltage_window_standard": f"{cap_metrics.voltage_window_min} - {cap_metrics.voltage_window_max} V",
            "epistemic_type": EpistemicType.LITERATURE_FACT.value,
        }

    def _build_property_prediction_link(
        self,
        mn_ratio: float,
        fe_ratio: float,
        dopants: List[Dict[str, Any]],
        carbon_wt: float = 3.0,
    ) -> Dict[str, Any]:
        """Query ML surrogate models, returning predictions and tree variance uncertainties."""
        try:
            from models.ml.predictor import predict_composition_performance
            res = predict_composition_performance(
                mn_ratio=mn_ratio,
                fe_ratio=fe_ratio,
                dopants=dopants,
                carbon_wt=carbon_wt,
                calc_temp=650.0,
                calc_time=6.0,
            )
            predictions = res.get("predictions", {})
            return {
                "model_capacity_0_1c": predictions.get("0.1C_capacity", {}).get("mean"),
                "model_capacity_0_1c_std": predictions.get("0.1C_capacity", {}).get("tree_std"),
                "model_capacity_1c": predictions.get("1C_capacity", {}).get("mean"),
                "model_capacity_1c_std": predictions.get("1C_capacity", {}).get("tree_std"),
                "model_capacity_5c": predictions.get("5C_capacity", {}).get("mean"),
                "model_capacity_5c_std": predictions.get("5C_capacity", {}).get("tree_std"),
                "model_retention_100cyc": predictions.get("capacity_retention", {}).get("mean"),
                "model_retention_100cyc_std": predictions.get("capacity_retention", {}).get("tree_std"),
                "coverage_status": res.get("coverage_warning", {}).get("status", "VALID"),
                "epistemic_type": EpistemicType.ML_PREDICTION.value,
                "disclaimer": (
                    "ML predictions are surrogate computational inferences with tree standard deviation uncertainty. "
                    "They do NOT constitute experimental validation and are provided solely for pre-screening."
                ),
            }
        except Exception as e:
            logger.debug(f"Property prediction surrogate omitted: {e}")
            return {
                "status": "UNAVAILABLE",
                "epistemic_type": EpistemicType.ML_PREDICTION.value,
                "disclaimer": "Surrogate model not invoked or training boundaries exceeded.",
            }

    def generate_matrix_for_hypothesis(self, hypothesis_id: str) -> ExperimentalVerificationMatrix:
        """
        Generate complete Experimental Verification Matrix directly from a ScientificHypothesis.
        """
        hyp = self.hypothesis_engine.get_hypothesis_by_id(hypothesis_id)
        if not hyp:
            lookup_key = hypothesis_id[4:] if hypothesis_id.upper().startswith("HYP-") else hypothesis_id
            hyp = self.hypothesis_engine.generate_hypothesis_for_gap(lookup_key)
        return self.generate_matrix_from_hypothesis(hyp)

    def generate_matrix_for_gap(self, gap_id: str) -> ExperimentalVerificationMatrix:
        """Generate verification matrix directly from a Research Gap ID."""
        hyp = self.hypothesis_engine.generate_hypothesis_for_gap(gap_id)
        return self.generate_matrix_from_hypothesis(hyp)

    def generate_matrix_from_hypothesis(self, hyp: ScientificHypothesis) -> ExperimentalVerificationMatrix:
        """
        Construct structured Experimental Verification Matrix from a ScientificHypothesis object.
        """
        proto = hyp.experimental_protocol
        candidate_formula = proto.candidate_composition

        # Parse Mn, Fe, dopants
        mn_ratio = 0.75
        fe_ratio = 0.25
        if "0.80" in candidate_formula or "0.8" in candidate_formula:
            mn_ratio = 0.80
            fe_ratio = 0.20
        elif "0.70" in candidate_formula or "0.7" in candidate_formula:
            mn_ratio = 0.70
            fe_ratio = 0.30

        dopants_list = []
        for sym, frac in proto.intended_dopant_concentration.items():
            d_info = get_dopant_info(sym)
            ox = d_info.get("default_oxidation_state", 2) if d_info else 2
            dopants_list.append({"symbol": sym, "fraction": frac, "oxidation_state": ox})
            fe_ratio = max(0.10, round(fe_ratio - frac, 4))

        # 1. Chemical Validation Link
        chem_valid = self.hypothesis_engine._validate_chemistry(mn_ratio, fe_ratio, dopants_list)

        # 2. Materials Designer Link
        mat_designer = self._build_materials_designer_link(
            candidate_formula, mn_ratio, fe_ratio, dopants_list, user_li=chem_valid["required_li"]
        )

        # 3. Property Prediction Link (ML Surrogate)
        prop_pred = self._build_property_prediction_link(mn_ratio, fe_ratio, dopants_list)

        # 4. Supervisor Policy Link
        sup_policy = self.hypothesis_engine._check_supervisor_policy(mn_ratio, fe_ratio, dopants_list)

        # 5. Supporting Literature Link
        sup_lit = {
            "paper_ids": hyp.supporting_paper_ids,
            "dois": hyp.supporting_dois,
            "sample_ids": hyp.supporting_sample_ids,
            "empirical_measurements": hyp.supporting_measurements,
            "contradictory_evidence": hyp.contradictory_or_limiting_evidence,
            "epistemic_type": EpistemicType.LITERATURE_FACT.value,
        }

        # 6. Control Samples
        ctrl_samples = []
        for c in proto.control_and_comparison_samples:
            sid = c.get("sample_id", "").upper()
            if "SO4" in sid or "REPL" in sid or "BASELINE" in sid:
                role = "REPLICATION_BASELINE"
            elif "TEST" in sid or "TARGET" in sid or "CAND" in sid:
                role = "TARGET_CANDIDATE"
            elif "POS" in sid or "BENCH" in sid:
                role = "POSITIVE_CONTROL_BENCHMARK"
            elif "CTRL" in sid or "UNDOPED" in sid or "NEG" in sid:
                role = "NEGATIVE_CONTROL_UNDOPED"
            else:
                role = "REPLICATION_BASELINE"
            ctrl_samples.append(
                MatrixControlSample(
                    sample_id=c.get("sample_id", "CTRL-01"),
                    label=c.get("description", "Control Sample"),
                    formula=candidate_formula if "TEST" in c.get("sample_id", "") else f"LiMn{mn_ratio}Fe{fe_ratio}PO4",
                    role=role,
                    expected_behavior=c.get("description", "Benchmark comparison"),
                    epistemic_status=EpistemicType.EXPERIMENTAL_RECOMMENDATION.value,
                )
            )

        # 7. Variable Specifications
        var_specs = []
        for vc in proto.variables_to_hold_constant:
            var_specs.append(
                VariableSpecification(
                    variable_name=vc.split("(")[0].strip(),
                    variable_type=VariableType.CONTROLLED,
                    target_value=vc,
                    tolerance="±5%",
                    rationale="Eliminate confounding experimental non-parity between candidate and controls.",
                )
            )
        for vch in proto.variables_to_change:
            var_specs.append(
                VariableSpecification(
                    variable_name=vch,
                    variable_type=VariableType.INDEPENDENT,
                    target_value=f"Varied per experimental design ({vch})",
                    tolerance="Exact formulation per batch",
                    rationale="Primary test variable to evaluate scientific hypothesis.",
                )
            )
        var_specs.append(
            VariableSpecification(
                variable_name="Discharge Capacity & Capacity Retention",
                variable_type=VariableType.DEPENDENT,
                target_value="Specific capacity (mAh/g) across 0.1C to 10C and 55°C retention",
                tolerance="Measured across 3 coin cells",
                rationale="Quantify electrochemical rate capability and degradation kinetics.",
            )
        )

        # 8. Synthesis Plan
        syn_steps = [
            SynthesisProtocolStep(
                step_number=1,
                operation="Precursor Dissolution & Sol Formation",
                parameters={"precursors": proto.precursors, "solvent": "Deionized water (18.2 MOhm.cm)", "chelation_ratio": "1.2:1 citric acid to total metal ions"},
                atmosphere="Ambient air / fume hood",
                equipment="Magnetic stirrer with heating mantle (80°C)",
                safety_notes="Use acid-resistant PPE; handle transition-metal salts with secondary containment.",
            ),
            SynthesisProtocolStep(
                step_number=2,
                operation="Sol Gelation & Evaporative Drying",
                parameters={"drying_temp": "120°C", "duration": "12.0 h", "residual_moisture": "<0.5 wt%"},
                atmosphere="Vacuum oven (-0.08 MPa)",
                equipment="Precision vacuum drying chamber",
                safety_notes="Ensure trap condensers capture volatilized organic vapors.",
            ),
            SynthesisProtocolStep(
                step_number=3,
                operation="Pre-Calcination & Organic Decomposition",
                parameters={"temperature": "350°C", "heating_rate": "3°C/min", "dwell_time": "3.0 h"},
                atmosphere="High-purity Ar (>99.999%, 100 sccm)",
                equipment="Quartz tube furnace",
                safety_notes="Inspect gas effluent scrubber for complete NOx/SOx neutralization.",
            ),
            SynthesisProtocolStep(
                step_number=4,
                operation="High-Temperature Crystallization & Sintering",
                parameters=proto.synthesis_variables or {"calcination_temp": "650°C", "heating_rate": "5°C/min", "dwell_time": "6.0 h"},
                atmosphere="Reducing atmosphere (Ar/H2 95/5 vol%)",
                equipment="Horizontal high-temperature quartz tube furnace",
                safety_notes="Continuous H2 leak detector operational; ensure positive furnace pressure.",
            ),
        ]

        # 9. Characterization Plan
        char_plan = []
        for rc in proto.required_characterization:
            tech = rc.get("technique", "XRD")
            char_plan.append(
                CharacterizationRequirement(
                    technique=tech,
                    instrument="Synchrotron / Laboratory Powder Diffractometer or In-situ System",
                    target_feature=rc.get("target", "Structural verification"),
                    acceptance_criteria="Phase-pure olivine Pnma with secondary phases <0.5 wt%",
                    epistemic_importance="Mandatory gate before coin-cell assembly to confirm phase identity.",
                )
            )

        # 10. Electrochemical Plan
        etc = proto.electrochemical_testing_conditions
        v_win = etc.get("voltage_window", "2.5 - 4.5 V")
        temp = etc.get("temperature", "25°C")
        c_rates = etc.get("c_rates", [0.1, 0.5, 1.0, 2.0, 5.0, 10.0])
        if not isinstance(c_rates, list):
            c_rates = [0.1, 1.0, 5.0]

        elec_plan = [
            ElectrochemicalTestProtocol(
                protocol_name=f"Standard Rate & Durability Protocol ({v_win}, {temp})",
                voltage_window=v_win,
                c_rates=c_rates,
                temperature=temp,
                cycle_count=etc.get("cycle_durability", 500) if isinstance(etc.get("cycle_durability"), int) else 500,
                mass_loading_min_mg_cm2=2.0,
                electrolyte_spec="1.0 M LiPF6 in EC:DMC (1:1 vol%) + 2.0 wt% VC",
                target_metrics={"0.1C_target": ">= 150 mAh/g", "5C_target": ">= 115 mAh/g", "retention_target": ">= 88% at 500 cyc"},
            )
        ]

        # 11. Disclaimers
        disclaimers = {
            "EXPERIMENT_STATUS": "PROPOSED_UNPERFORMED",
            "EXPERIMENT_STATUS_EXPLANATION": "This verification matrix is an automated experimental proposal. No physical synthesis or cell cycling has yet been performed.",
            "ML_VALIDATION_STATUS": "IN_SILICO_PREDICTION_NOT_EXPERIMENTAL_PROOF",
            "ML_VALIDATION_EXPLANATION": "Surrogate machine learning model predictions provide initial computational screening; they do NOT substitute for physical experimental testing.",
            "SUPERVISOR_POLICY_SEPARATION": "Industrial policy flags indicate alignment with current pilot line targets and are strictly distinguished from universal scientific laws.",
        }

        matrix_id = f"MAT-{hyp.hypothesis_id.replace('HYP-', '')}"

        return ExperimentalVerificationMatrix(
            matrix_id=matrix_id,
            title=f"Experimental Verification Matrix: {hyp.scientific_question[:80]}",
            hypothesis_id=hyp.hypothesis_id,
            research_gap_id=hyp.research_gap_id,
            scientific_question=hyp.scientific_question,
            candidate_composition=candidate_formula,
            intended_dopants=dopants_list,
            supporting_literature=sup_lit,
            chemical_validation=chem_valid,
            materials_designer_link=mat_designer,
            property_prediction_link=prop_pred,
            supervisor_policy_link=sup_policy,
            control_samples=ctrl_samples,
            variable_specifications=var_specs,
            synthesis_plan=syn_steps,
            characterization_plan=char_plan,
            electrochemical_plan=elec_plan,
            expected_outcomes=[hyp.expected_outcome],
            falsification_criteria=hyp.falsification_criteria,
            researcher_selection_required=proto.researcher_selection_required,
            status_disclaimers=disclaimers,
        )

    def get_canonical_verification_matrices(self) -> List[ExperimentalVerificationMatrix]:
        """Generate the core suite of canonical experimental verification matrices."""
        all_hyps = self.hypothesis_engine.generate_all_canonical_hypotheses()
        return [self.generate_matrix_for_hypothesis(h.hypothesis_id) for h in all_hyps]

    def get_matrix_by_id(self, matrix_id: str) -> Optional[ExperimentalVerificationMatrix]:
        """Lookup verification matrix by ID."""
        m_clean = matrix_id.upper().strip()
        for mat in self.get_canonical_verification_matrices():
            if mat.matrix_id.upper() == m_clean:
                return mat
        # Check if matrix_id corresponds to a hypothesis ID or gap ID
        hyp = self.hypothesis_engine.get_hypothesis_by_id(matrix_id)
        if hyp:
            return self.generate_matrix_for_hypothesis(hyp.hypothesis_id)
        return None

    def query_matrices(
        self,
        hypothesis_id: Optional[str] = None,
        gap_id: Optional[str] = None,
        dopant: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Structured query over generated verification matrices."""
        all_matrices = self.get_canonical_verification_matrices()
        filtered = []

        for m in all_matrices:
            if hypothesis_id and hypothesis_id.upper().strip() not in m.hypothesis_id.upper():
                continue
            if gap_id and gap_id.upper().strip() not in m.research_gap_id.upper():
                continue
            if dopant:
                d_up = dopant.upper().strip()
                matches_dopant = any(d_up in d.get("symbol", "").upper() for d in m.intended_dopants)
                matches_dopant = matches_dopant or d_up in m.candidate_composition.upper()
                if not matches_dopant:
                    continue
            filtered.append(m)

        return {
            "query_filters": {"hypothesis_id": hypothesis_id, "gap_id": gap_id, "dopant": dopant},
            "total_matrices": len(filtered),
            "matrices": [m.to_dict() for m in filtered],
        }


# ---------------------------------------------------------------------------
# Global Singleton Accessor
# ---------------------------------------------------------------------------

_VERIFICATION_MATRIX_ENGINE_INSTANCE: Optional[VerificationMatrixEngine] = None


def get_verification_matrix_engine() -> VerificationMatrixEngine:
    """Return the global singleton VerificationMatrixEngine instance."""
    global _VERIFICATION_MATRIX_ENGINE_INSTANCE
    if _VERIFICATION_MATRIX_ENGINE_INSTANCE is None:
        _VERIFICATION_MATRIX_ENGINE_INSTANCE = VerificationMatrixEngine()
    return _VERIFICATION_MATRIX_ENGINE_INSTANCE
