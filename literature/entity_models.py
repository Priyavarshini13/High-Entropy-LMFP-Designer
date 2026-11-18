"""
Sample-Centric Entity Graph Models for LMFP Literature Intelligence (Stage 4).

Connects:
Research Paper → Material Sample → Composition → Synthesis Conditions → Characterization → Electrochemical Measurements.

Ensures:
1. A paper can contain multiple distinct samples.
2. Two samples can have identical compositions but different synthesis routes, coatings, or performance.
3. Every measurement is strictly linked to its sample and experimental conditions.
4. Review paper secondary citations ([79], [29]) are distinguished from primary sources.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ResolutionStatus(str, Enum):
    """Confidence status for sample identity resolution."""
    CONFIRMED_EXPLICIT = "CONFIRMED_EXPLICIT"      # Author explicitly labelled sample (e.g. SD_NO3, S1, Ni-D5)
    CONFIRMED_FORMULA = "CONFIRMED_FORMULA"        # Isolated by unique composition within paper
    CONFIRMED_MODIFICATION = "CONFIRMED_MODIFICATION"  # Isolated by coating or precursor (e.g. LMFP vs LMFP/rGO)
    SECONDARY_CITATION = "SECONDARY_CITATION"      # Extracted from a review paper citing a secondary study (e.g. [79])
    AMBIGUOUS = "AMBIGUOUS"                        # Multiple possible sample matches
    UNRESOLVED = "UNRESOLVED"                      # Identity could not be confidently established


class ProvenanceType(str, Enum):
    """Origin classification for scientific evidence."""
    PRIMARY_EXPERIMENTAL = "PRIMARY_EXPERIMENTAL"  # Newly measured experimental sample in primary paper
    SECONDARY_REVIEW = "SECONDARY_REVIEW"          # Cited from an earlier paper in a review or introduction
    BACKGROUND_MENTION = "BACKGROUND_MENTION"      # Historical literature mention without new experimental data


@dataclass
class DopantEntity:
    """Individual dopant element with site and precursor attribution."""
    dopant_id: str
    element: str                        # e.g. "Mg", "Ti", "Ni", "Nb"
    molar_ratio: Optional[float] = None # e.g. 0.05
    substitution_site: str = "M2"       # M1 (Li), M2 (Mn/Fe), Anion (F, Cl, S)
    precursor_agent: Optional[str] = None  # e.g. "NiSO4.6H2O", "Ti(OBu)4", "CTAB, TAA"


@dataclass
class CompositeModificationEntity:
    """Surface coating, conductive carbon, or 2D matrix modification."""
    modification_id: str
    modification_type: str              # "carbon_coating", "rgo", "cnt", "graphene", "conductive_polymer"
    carbon_source: Optional[str] = None # "glucose", "sucrose", "pitch", "graphene_oxide"
    carbon_wt_percent: Optional[float] = None
    morphology: Optional[str] = None    # e.g. "3D microsphere wrapping", "conformal nanoscale shell"


@dataclass
class CompositionEntity:
    """Chemical composition of a material sample."""
    composition_id: str
    raw_formula: str                    # Original text: e.g. "LiMn0.75Fe0.25PO4/rGO"
    base_lmfp_formula: str              # Host stoichiometry: e.g. "LiMn0.75Fe0.25PO4"
    mn_ratio: float = 0.5
    fe_ratio: float = 0.5
    li_stoichiometry: float = 1.0
    dopants: List[DopantEntity] = field(default_factory=list)
    composite_modifications: List[CompositeModificationEntity] = field(default_factory=list)
    is_stoichiometric: bool = True
    configurational_entropy_over_r: Optional[float] = None


@dataclass
class SynthesisProfileEntity:
    """Reported thermal and chemical preparation conditions."""
    synthesis_profile_id: str
    method: str                         # "Solid-state", "Solvothermal", "Hydrothermal", "Spray drying", "Sol-gel", "Co-precipitation"
    calcination_temp_c: Optional[float] = None
    calcination_time_h: Optional[float] = None
    heating_rate_c_min: Optional[float] = None
    atmosphere: Optional[str] = None    # "Ar/H2 (95/5 vol%)", "N2", "Ar", "Air"
    precursor_salts: List[str] = field(default_factory=list) # e.g. ["FeSO4.7H2O", "MnSO4.H2O", "H3PO4", "LiOH.H2O"]
    solvent: Optional[str] = None       # e.g. "ethylene glycol", "deionized water", "DMF"
    raw_evidence: Optional[str] = None
    source_page: int = 1


@dataclass
class CharacterizationProfileEntity:
    """Crystallographic, phase purity, and transport characterization."""
    characterization_profile_id: str
    crystal_structure: str = "orthorhombic olivine"
    space_group: str = "Pnma"
    xrd_phase_purity: Optional[str] = None       # "phase-pure", "trace Fe2O3 impurity"
    impurity_phases: List[str] = field(default_factory=list) # e.g. ["Fe2O3"]
    lattice_a_angstrom: Optional[float] = None
    lattice_b_angstrom: Optional[float] = None
    lattice_c_angstrom: Optional[float] = None
    unit_cell_volume_angstrom3: Optional[float] = None
    crystallite_size_nm: Optional[float] = None
    particle_size_nm: Optional[float] = None
    morphology: Optional[str] = None             # "spherical microspheres", "nanoparticles", "nanorods"
    eis_rct_ohm: Optional[float] = None
    li_diffusion_coefficient_cm2_s: Optional[float] = None
    raw_evidence: Optional[str] = None
    source_page: int = 1


@dataclass
class EvidenceRecordEntity:
    """Exact verbatim excerpt and provenance linking an entity to its source document."""
    evidence_id: str
    paper_id: str
    page_number: int
    section_type: str                   # "METHODS", "RESULTS", "TABLE", "FIGURE_CAPTION", "ABSTRACT"
    text_snippet: str
    table_or_figure_ref: Optional[str] = None # e.g. "Figure 7(a)", "Table 1"


@dataclass
class PropertyMeasurementEntity:
    """A distinct electrochemical measurement tied to a specific sample and testing condition."""
    measurement_id: str
    sample_id: Optional[str]            # Foreign key to MaterialSample (None if unresolved)
    paper_id: str
    measurement_type: str               # "discharge_capacity", "charge_capacity", "capacity_retention", "ice", "coulombic_efficiency"
    reported_value: Any
    reported_unit: Optional[str]
    normalized_value: Optional[float]   # Clean numeric value: e.g. 114.0 mAh/g, 93.0 %
    normalized_unit: Optional[str]
    c_rate: Optional[float] = None      # 0.05, 0.1, 1.0, 5.0, 10.0
    cycle_count: Optional[int] = None   # 1, 100, 500, 1000
    temperature_c: Optional[float] = 25.0
    voltage_window_lower_v: Optional[float] = None
    voltage_window_upper_v: Optional[float] = None
    source_page: int = 1
    section_type: str = "RESULTS"
    table_or_figure_ref: Optional[str] = None
    evidence_quote: str = ""
    extraction_method: str = "stage3_property_extractor"
    validation_status: str = "VERIFIED" # "VERIFIED", "PROVISIONAL", "FLAGGED_CONDITION_MISMATCH"
    warnings: List[str] = field(default_factory=list)


@dataclass
class SecondaryCitationLink:
    """Provenance tracking for review papers citing primary experimental studies."""
    citation_id: str
    review_paper_id: str                # e.g. "Lithium manganese iron phosphate materials..."
    citation_key: str                   # e.g. "[79]", "[29]"
    primary_paper_id: Optional[str] = None # Resolved primary paper ID or None
    primary_doi: Optional[str] = None      # Primary DOI if verified; never fabricate
    primary_title: Optional[str] = None
    primary_year: Optional[int] = None
    is_verified: bool = False
    notes: Optional[str] = None


@dataclass
class MaterialSample:
    """
    Central scientific entity representing a distinct experimental or literature material.
    Uniquely distinguishes samples even when they share identical host compositions.
    """
    sample_id: str                      # Unique ID: e.g. "srep26686_SD_SO4", "P1_S1", "review_p18_ref79_sample"
    paper_id: str                       # Owning Paper ID
    sample_label: str                   # Author's label: e.g. "SD_SO4", "SD_NO3", "S1", "Sample A", "Ni-D5"
    composition: CompositionEntity
    synthesis_profile: Optional[SynthesisProfileEntity] = None
    characterization_profile: Optional[CharacterizationProfileEntity] = None
    provenance_type: ProvenanceType = ProvenanceType.PRIMARY_EXPERIMENTAL
    resolution_status: ResolutionStatus = ResolutionStatus.CONFIRMED_EXPLICIT
    resolution_confidence: float = 1.0  # 0.0 to 1.0
    resolution_notes: str = ""
    secondary_citation: Optional[SecondaryCitationLink] = None
    is_unresolved: bool = False
    measurements: List[PropertyMeasurementEntity] = field(default_factory=list)
    evidence_records: List[EvidenceRecordEntity] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class PaperEntity:
    """Research paper container holding bibliographic metadata and material samples."""
    paper_id: str                       # e.g. "srep26686", "P1", "review_progress_challenges_2023"
    title: str
    doi: Optional[str] = None
    authors: Optional[str] = None
    year: Optional[int] = None
    journal: Optional[str] = None
    is_review_paper: bool = False
    source_pdf: Optional[str] = None
    samples: List[MaterialSample] = field(default_factory=list)
    secondary_citations: List[SecondaryCitationLink] = field(default_factory=list)
    raw_sections_count: int = 0
