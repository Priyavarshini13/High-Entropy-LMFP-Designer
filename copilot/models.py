"""Data models and schemas for the LMFP Research Copilot."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ScientificIntent(str, Enum):
    """The 18 structured scientific research intents for the LMFP Copilot."""

    SAMPLE_PROPERTY_LOOKUP = "SAMPLE_PROPERTY_LOOKUP"
    SAMPLE_COMPARISON = "SAMPLE_COMPARISON"
    COMPOSITION_COMPARISON = "COMPOSITION_COMPARISON"
    DOPANT_ANALYSIS = "DOPANT_ANALYSIS"
    COMPOSITE_MODIFICATION_ANALYSIS = "COMPOSITE_MODIFICATION_ANALYSIS"
    SYNTHESIS_COMPARISON = "SYNTHESIS_COMPARISON"
    PRECURSOR_COMPARISON = "PRECURSOR_COMPARISON"
    ELECTROCHEMICAL_PERFORMANCE_ANALYSIS = "ELECTROCHEMICAL_PERFORMANCE_ANALYSIS"
    RATE_CAPABILITY_ANALYSIS = "RATE_CAPABILITY_ANALYSIS"
    CYCLING_STABILITY_ANALYSIS = "CYCLING_STABILITY_ANALYSIS"
    CHARACTERIZATION_ANALYSIS = "CHARACTERIZATION_ANALYSIS"
    CROSS_PAPER_COMPARISON = "CROSS_PAPER_COMPARISON"
    MECHANISM_EXPLANATION = "MECHANISM_EXPLANATION"
    RESEARCH_GAP_ANALYSIS = "RESEARCH_GAP_ANALYSIS"
    LITERATURE_SEARCH = "LITERATURE_SEARCH"
    EXPERIMENTAL_CONDITION_FILTER = "EXPERIMENTAL_CONDITION_FILTER"
    FOLLOW_UP_QUESTION = "FOLLOW_UP_QUESTION"
    OUT_OF_SCOPE_OR_INSUFFICIENT_EVIDENCE = "OUT_OF_SCOPE_OR_INSUFFICIENT_EVIDENCE"


def is_synthetic_test_record(paper_id: Optional[str], sample_id: Optional[str] = None, text: Optional[str] = None) -> bool:
    """Filter out synthetic test fixtures and pipeline test records from peer-reviewed scientific evidence."""
    combined = f"{paper_id or ''} {sample_id or ''} {text or ''}".lower()
    test_markers = (
        "test_syn",
        "test_chk",
        "stage3_integrated",
        "reupload_test",
        "mock_",
        "dummy_",
        "test_pipeline",
        "paper_with_refs",
        "paper_with_intro",
        "no_headings",
        "partial_lmfp",
    )
    return any(marker in combined for marker in test_markers)


@dataclass
class ExtractedEntities:
    """Structured entities and conditions extracted from a scientific research question."""

    sample_ids: List[str] = field(default_factory=list)
    sample_labels: List[str] = field(default_factory=list)
    paper_ids: List[str] = field(default_factory=list)
    dopants: List[str] = field(default_factory=list)
    formulas: List[str] = field(default_factory=list)
    modifications: List[str] = field(default_factory=list)  # rGO, CNT, carbon coating
    precursors: List[str] = field(default_factory=list)    # sulfate, nitrate, acetate
    synthesis_methods: List[str] = field(default_factory=list)  # spray drying, sol-gel, solid-state
    c_rates: List[float] = field(default_factory=list)
    cycle_counts: List[int] = field(default_factory=list)
    temperature_c: Optional[float] = None
    voltage_window: Optional[Tuple[float, float]] = None
    mass_loading_mg_cm2: Optional[float] = None
    measurement_types: List[str] = field(default_factory=list)
    comparison_dimensions: List[str] = field(default_factory=list)
    raw_query: str = ""


@dataclass
class ScientificIntentPayload:
    """Structured classification payload for an incoming research question."""

    intent: ScientificIntent
    confidence: float
    extracted_entities: ExtractedEntities
    target_measurements: List[str] = field(default_factory=list)
    comparison_dimensions: List[str] = field(default_factory=list)
    is_ambiguous: bool = False
    ambiguity_reason: Optional[str] = None
    requires_clarification: bool = False
    clarification_question: Optional[str] = None
    candidate_referents: List[str] = field(default_factory=list)


@dataclass
class ConversationContextState:
    """Stateful conversational memory tracking active referents and conditions across turns."""

    active_samples: List[str] = field(default_factory=list)
    active_sample_labels: List[str] = field(default_factory=list)
    active_papers: List[str] = field(default_factory=list)
    active_dopants: List[str] = field(default_factory=list)
    active_compositions: List[str] = field(default_factory=list)
    active_conditions: Dict[str, Any] = field(default_factory=dict)
    active_measurement_types: List[str] = field(default_factory=list)
    last_comparison_pair: Optional[Tuple[str, str]] = None
    last_intent: Optional[ScientificIntent] = None
    turn_count: int = 1
    requires_clarification: bool = False
    clarification_prompt: Optional[str] = None


@dataclass
class ScientificSubQuery:
    """An atomic, condition-isolated sub-query derived from a composite question."""

    sub_query_id: str
    query_text: str
    intent: ScientificIntent
    target_entities: List[str] = field(default_factory=list)
    target_conditions: Dict[str, Any] = field(default_factory=dict)
    target_measurements: List[str] = field(default_factory=list)
    provenance_requirement: Optional[str] = None
    retrieval_strategy: str = "hybrid_default"  # entity_graph, measurements, synthesis, bm25_expanded


@dataclass
class RetrievalPlan:
    """Execution plan directing retrieval strategy and sub-query routing."""

    original_query: str
    primary_intent: ScientificIntent
    is_composite: bool
    sub_queries: List[ScientificSubQuery] = field(default_factory=list)
    requires_comparability_check: bool = False
    requires_policy_separation: bool = False
    is_out_of_scope: bool = False
    abstention_reason: Optional[str] = None


@dataclass
class EvidenceSufficiencyReport:
    """Pre-generation report validating evidence completeness, parity, and boundaries."""

    is_sufficient: bool = True
    is_comparable: bool = True
    condition_parity: bool = True
    missing_counterparts: List[str] = field(default_factory=list)
    condition_divergences: List[str] = field(default_factory=list)
    provenance_warnings: List[str] = field(default_factory=list)
    policy_distinctions: List[str] = field(default_factory=list)
    limitation_notes: Optional[str] = None
    is_recommendation_hypothesis: bool = False


@dataclass
class EvidencePassage:
    """A discrete scientific text passage with rich metadata and structured properties."""

    passage_id: str
    paper_id: str
    title: Optional[str] = None
    doi: Optional[str] = None
    page_number: int = 1
    section_type: str = "RESULTS_DISCUSSION"
    sample_id: Optional[str] = None
    sample_label: Optional[str] = None
    composition: Optional[str] = None
    text: str = ""
    source_type: str = "master_dataset"  # master_dataset, literature_review, entity_graph, uploaded_paper
    provenance_type: Optional[str] = None  # PRIMARY_PAPER, SECONDARY_REVIEW, DATASET_ROW, UNRESOLVED
    is_unresolved: bool = False
    secondary_citation_key: Optional[str] = None
    synthesis_profile_id: Optional[str] = None
    characterization_profile_id: Optional[str] = None
    entity_graph: Optional[Dict[str, Any]] = None
    structured_data: Dict[str, Any] = field(default_factory=dict)
    tokens: List[str] = field(default_factory=list)
    term_frequencies: Dict[str, int] = field(default_factory=dict)


@dataclass
class RetrievalMatch:
    """A ranked evidence match combining entity graph, semantic, keyword, and structured scores."""

    passage: EvidencePassage
    semantic_score: float = 0.0
    bm25_score: float = 0.0
    structured_score: float = 0.0
    entity_score: float = 0.0
    lsa_score: float = 0.0
    combined_score: float = 0.0
    sample_id: Optional[str] = None
    provenance_type: Optional[str] = None
    match_reasons: List[str] = field(default_factory=list)


@dataclass
class CopilotCitation:
    """A strictly verified literature citation tied to paper, page, and evidence."""

    paper_id: str
    page_number: int
    doi: Optional[str] = None
    sample_label: Optional[str] = None
    composition: Optional[str] = None
    evidence_quote: str = ""
    is_verified: bool = True
    conditions: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MeasurementRecord:
    """A condition-bound experimental measurement extracted from literature evidence."""

    measurement_type: str  # discharge_capacity, capacity_retention, initial_coulombic_efficiency, rct, li_diffusion
    value: Any
    unit: str
    c_rate: Optional[float] = None
    cycle_count: Optional[int] = None
    voltage_window: Optional[str] = None
    temperature_c: Optional[float] = None
    source_page: Optional[int] = None
    figure_or_table: Optional[str] = None
    evidence_quote: Optional[str] = None


@dataclass
class StructuredSampleProfile:
    """Aggregated scientific profile of an experimental LMFP sample with full provenance."""

    sample_id: str
    sample_label: str
    paper_id: str
    composition: str
    doi: Optional[str] = None
    title: Optional[str] = None
    dopants: List[str] = field(default_factory=list)
    modifications: List[str] = field(default_factory=list)
    precursor_salts: List[str] = field(default_factory=list)
    synthesis_method: Optional[str] = None
    calcination_temp_c: Optional[float] = None
    calcination_time_h: Optional[float] = None
    atmosphere: Optional[str] = None
    crystal_structure: Optional[str] = None
    space_group: Optional[str] = None
    xrd_phase_purity: Optional[str] = None
    impurity_phases: Optional[str] = None
    provenance_type: str = "PRIMARY_PAPER"  # PRIMARY_PAPER, SECONDARY_REVIEW, DATASET_ROW, UNRESOLVED
    measurements: List[MeasurementRecord] = field(default_factory=list)
    passages: List[EvidencePassage] = field(default_factory=list)


@dataclass
class ConditionParityResult:
    """Evaluation of condition alignment between compared material samples."""

    is_aligned: bool = True
    c_rate_aligned: bool = True
    voltage_window_aligned: bool = True
    temperature_aligned: bool = True
    cycle_count_aligned: bool = True
    divergence_notes: List[str] = field(default_factory=list)
    comparability_verdict: str = "MATCHED_CONDITIONS"  # MATCHED_CONDITIONS, CONDITION_DIVERGENT, INSUFFICIENT_DATA


@dataclass
class CopilotResponseData:
    """Comprehensive structured response adhering to scientific publication standards."""

    response: str
    direct_answer: str
    explanation: str
    comparison_table: Optional[List[Dict[str, Any]]] = None
    sourced_facts: List[Dict[str, str]] = field(default_factory=list)
    engine_facts: List[Dict[str, str]] = field(default_factory=list)
    citations: List[Dict[str, Any]] = field(default_factory=list)
    conflicts_and_limitations: Optional[str] = None
    inference_source: str = "deterministic_synthesis_fallback"  # qwen3:4b_grounded or deterministic_synthesis_fallback
    predictions_note: Optional[str] = None
    disclaimer: str = "AI-assisted scientific research · Strictly evidence-grounded · Verify against original publications"
    context_state: Optional[Dict[str, Any]] = None
    intent_payload: Optional[Dict[str, Any]] = None
    retrieval_plan: Optional[Dict[str, Any]] = None
    sufficiency_report: Optional[Dict[str, Any]] = None
    sample_profiles: Optional[List[Dict[str, Any]]] = None
