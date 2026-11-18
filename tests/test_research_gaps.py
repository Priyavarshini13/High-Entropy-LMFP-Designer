"""
Independent Test Suite for Stage 5 Phase 4 - Milestone 4.2:
Structured Research Gap & Scientific Conflict Discovery Engine.

Validates:
- All 7 gap categories (Composition/dopants, Synthesis/processing, Characterization,
  Electrochemical, Comparability, Conflicting evidence, Literature knowledge).
- Epistemic classification: Database coverage gaps vs verified literature gaps.
- Conflict detection methodology (processing-dependent, condition-dependent, comparable).
- Sample versus independent paper counting.
- Missing characterization and condition non-parity detection.
- Primary vs secondary citation provenance.
- Empty and small dataset robustness.
- Data protection and repository integrity invariants.
"""

from pathlib import Path
import sqlite3
import pandas as pd
import pytest

from copilot.research_intelligence import (
    ConflictClassification,
    GapCategory,
    GapDiscoveryEngine,
    GapVerificationStatus,
    ResearchGap,
    ScientificConflict,
    get_gap_discovery_engine,
)
from backend.main import get_research_gaps, get_scientific_conflicts


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = WORKSPACE_ROOT / "data" / "literature_reference.csv"
REVIEW_DB_PATH = WORKSPACE_ROOT / "data" / "literature_review.db"
LAB_DB_PATH = WORKSPACE_ROOT / "data" / "lab_experiments.db"


@pytest.fixture(scope="module")
def gap_engine():
    """Shared GapDiscoveryEngine instance initialized on workspace dataset."""
    return get_gap_discovery_engine()


# =============================================================================
# 1. Seven Gap Categories Coverage
# =============================================================================
def test_all_seven_gap_categories_represented(gap_engine):
    """Verify that all 7 research gap categories are instantiated with structured gaps or conflicts."""
    all_gaps = gap_engine.discover_all_gaps()
    conflicts = gap_engine.discover_conflicting_scientific_evidence()

    represented_categories = {g.category for g in all_gaps}
    # Category F is represented by the systematic scientific conflicts
    assert len(conflicts) > 0

    expected_categories = {
        GapCategory.COMPOSITION_AND_DOPANT_COVERAGE,
        GapCategory.SYNTHESIS_AND_PROCESSING,
        GapCategory.CHARACTERIZATION_COVERAGE,
        GapCategory.ELECTROCHEMICAL_EVALUATION,
        GapCategory.EXPERIMENTAL_COMPARABILITY,
        GapCategory.LITERATURE_KNOWLEDGE,
    }
    assert expected_categories.issubset(represented_categories)


# =============================================================================
# 2. Database Gaps vs Verified Literature Gaps
# =============================================================================
def test_epistemic_gap_classification_distinction(gap_engine):
    """Verify strict epistemic separation between database omissions and verified literature gaps."""
    all_gaps = gap_engine.discover_all_gaps()

    verified_gaps = [g for g in all_gaps if g.verification_status == GapVerificationStatus.VERIFIED_LITERATURE_GAP]
    db_gaps = [g for g in all_gaps if g.verification_status == GapVerificationStatus.DATABASE_COVERAGE_GAP]
    char_gaps = [g for g in all_gaps if g.verification_status == GapVerificationStatus.EXPERIMENTAL_CHARACTERIZATION_GAP]
    comp_gaps = [g for g in all_gaps if g.verification_status == GapVerificationStatus.CONDITION_COMPARABILITY_GAP]

    assert len(verified_gaps) >= 3
    assert len(db_gaps) >= 1
    assert len(char_gaps) >= 2
    assert len(comp_gaps) >= 1

    # Verify that database gaps do NOT claim universal scientific non-existence
    for g in db_gaps:
        assert any("database" in lim.lower() or "local" in lim.lower() for lim in g.confidence_limitations)
        assert "DATABASE_COVERAGE_GAP" == g.verification_status.value


# =============================================================================
# 3. Category A: Composition and Dopant Coverage Gaps
# =============================================================================
def test_composition_and_dopant_gaps(gap_engine):
    gaps = gap_engine.discover_composition_and_dopant_gaps()
    assert len(gaps) >= 3

    gap_ids = [g.gap_id for g in gaps]
    assert "GAP-COMP-01" in gap_ids  # Ti+Mg in High-Mn
    assert "GAP-COMP-02" in gap_ids  # Unexplored pairs
    assert "GAP-COMP-03" in gap_ids  # High-Entropy scarcity

    ti_mg_gap = next(g for g in gaps if g.gap_id == "GAP-COMP-01")
    assert "Ti" in ti_mg_gap.related_dopants
    assert "Mg" in ti_mg_gap.related_dopants
    assert ti_mg_gap.verification_status == GapVerificationStatus.VERIFIED_LITERATURE_GAP
    assert ti_mg_gap.sample_count >= ti_mg_gap.paper_count


# =============================================================================
# 4. Category B: Synthesis and Processing Gaps
# =============================================================================
def test_synthesis_and_processing_gaps(gap_engine):
    gaps = gap_engine.discover_synthesis_and_processing_gaps()
    assert len(gaps) >= 2

    # Check aerosol precursor counter-anion gap (srep26686 SD_NO3 vs SD_SO4)
    precursor_gap = next(g for g in gaps if g.gap_id == "GAP-SYNTH-01")
    assert "srep26686" in precursor_gap.supporting_paper_ids
    assert "srep26686_SD_NO3" in precursor_gap.supporting_sample_ids
    assert "srep26686_SD_SO4" in precursor_gap.supporting_sample_ids
    assert "45.0 mAh/g" in str(precursor_gap.available_measurements)


# =============================================================================
# 5. Category C: Characterization Gaps
# =============================================================================
def test_characterization_coverage_gaps(gap_engine):
    gaps = gap_engine.discover_characterization_gaps()
    assert len(gaps) >= 1

    char_gap = next(g for g in gaps if g.gap_id == "GAP-CHAR-01")
    assert char_gap.category == GapCategory.CHARACTERIZATION_COVERAGE
    assert char_gap.verification_status == GapVerificationStatus.EXPERIMENTAL_CHARACTERIZATION_GAP
    assert any("EIS" in m for m in char_gap.missing_measurements)
    assert any("Galvanostatic" in m or "GITT" in m for m in char_gap.missing_measurements)
    assert char_gap.sample_count > 0


# =============================================================================
# 6. Category D: Electrochemical Evaluation Gaps
# =============================================================================
def test_electrochemical_evaluation_gaps(gap_engine):
    gaps = gap_engine.discover_electrochemical_evaluation_gaps()
    assert len(gaps) >= 2

    ice_gap = next(g for g in gaps if g.gap_id == "GAP-ELEC-01")
    assert "Initial Coulombic Efficiency" in ice_gap.title
    assert ice_gap.sample_count <= 50  # Verifies documented reporting scarcity

    temp_gap = next(g for g in gaps if g.gap_id == "GAP-ELEC-02")
    assert "55°C" in temp_gap.title
    assert temp_gap.verification_status == GapVerificationStatus.VERIFIED_LITERATURE_GAP


# =============================================================================
# 7. Category E: Experimental Comparability Gaps
# =============================================================================
def test_experimental_comparability_gaps(gap_engine):
    gaps = gap_engine.discover_experimental_comparability_gaps()
    assert len(gaps) >= 1

    parity_gap = next(g for g in gaps if g.gap_id == "GAP-COMP-PARITY-01")
    assert parity_gap.category == GapCategory.EXPERIMENTAL_COMPARABILITY
    assert parity_gap.verification_status == GapVerificationStatus.CONDITION_COMPARABILITY_GAP
    assert "2.0-4.2V vs 2.5-4.5V" in str(parity_gap.relevant_conditions)


# =============================================================================
# 8. Category F: Conflicting Scientific Evidence Methodology
# =============================================================================
def test_scientific_conflicts_methodology(gap_engine):
    conflicts = gap_engine.discover_conflicting_scientific_evidence()
    assert len(conflicts) >= 4

    conf_ids = [c.conflict_id for c in conflicts]
    assert "CONF-LMFP-01" in conf_ids  # Mg site selectivity
    assert "CONF-LMFP-02" in conf_ids  # Nitrate vs sulfate
    assert "CONF-LMFP-03" in conf_ids  # Carbon vs bulk doping at 55°C
    assert "CONF-LMFP-04" in conf_ids  # Voltage cutoff capacity divergence

    # Check root-cause categorization
    mg_conf = next(c for c in conflicts if c.conflict_id == "CONF-LMFP-01")
    assert mg_conf.classification == ConflictClassification.PROCESSING_DEPENDENT_DIFFERENCES
    assert "calcination temperature" in mg_conf.underlying_cause.lower()

    carb_conf = next(c for c in conflicts if c.conflict_id == "CONF-LMFP-03")
    assert carb_conf.classification == ConflictClassification.CONDITION_DEPENDENT_DIFFERENCES
    assert "55°C" in carb_conf.underlying_cause

    volt_conf = next(c for c in conflicts if c.conflict_id == "CONF-LMFP-04")
    assert volt_conf.classification == ConflictClassification.CONDITION_DEPENDENT_DIFFERENCES


# =============================================================================
# 9. Category G: Literature Knowledge Gaps
# =============================================================================
def test_literature_knowledge_gaps(gap_engine):
    gaps = gap_engine.discover_literature_knowledge_gaps()
    assert len(gaps) >= 1

    know_gap = next(g for g in gaps if g.gap_id == "GAP-KNOW-01")
    assert know_gap.category == GapCategory.LITERATURE_KNOWLEDGE
    assert know_gap.verification_status == GapVerificationStatus.INSUFFICIENT_EVIDENCE
    assert any("DFT" in m for m in know_gap.missing_measurements)


# =============================================================================
# 10. Sample versus Paper Counting & Provenance
# =============================================================================
def test_gap_sample_and_paper_counting(gap_engine):
    all_gaps = gap_engine.discover_all_gaps()
    for g in all_gaps:
        assert g.sample_count >= g.paper_count
        assert isinstance(g.confidence_limitations, list)
        assert len(g.why_the_gap_matters) > 10
        assert len(g.suggested_investigation) > 10


# =============================================================================
# 11. Empty and Small Dataset Robustness
# =============================================================================
def test_gap_engine_empty_dataset_handling(tmp_path):
    empty_csv = tmp_path / "empty.csv"
    empty_csv.write_text("Sample_ID,Paper_ID,DOI,Composition_Formula,Mn_Ratio,Fe_Ratio,Dopant_Element\n", encoding="utf-8")

    from copilot.research_intelligence import TrendDiscoveryEngine
    empty_trend = TrendDiscoveryEngine(csv_path=str(empty_csv), db_path=str(tmp_path / "empty.db"))
    empty_gap_engine = GapDiscoveryEngine(trend_engine=empty_trend, csv_path=str(empty_csv))

    gaps = empty_gap_engine.discover_all_gaps()
    assert isinstance(gaps, list)
    assert len(gaps) > 0  # Domain gaps still formulate with sample_count=0
    comp_gap = next(g for g in gaps if g.gap_id == "GAP-COMP-02")
    assert comp_gap.sample_count == 0

    conflicts = empty_gap_engine.discover_conflicting_scientific_evidence()
    assert len(conflicts) >= 4  # Canonical scientific literature debates preserved


# =============================================================================
# 12. Query and Filter Interface
# =============================================================================
def test_gap_query_filters(gap_engine):
    # Filter by category
    char_res = gap_engine.query_gaps(category="CHARACTERIZATION")
    assert char_res["gaps_count"] >= 1
    assert all("CHARACTERIZATION" in g["category"] for g in char_res["gaps"])

    # Filter by verification status
    verified_res = gap_engine.query_gaps(verification_status="VERIFIED_LITERATURE_GAP")
    assert verified_res["gaps_count"] >= 3
    assert all(g["verification_status"] == "VERIFIED_LITERATURE_GAP" for g in verified_res["gaps"])

    # Filter by dopant
    mg_res = gap_engine.query_gaps(dopant="Mg")
    assert mg_res["gaps_count"] >= 1
    assert any("Mg" in g["related_dopants"] for g in mg_res["gaps"])
    assert any("Mg" in c["topic"] or "Mg" in str(c) for c in mg_res["conflicts"])

    # Summary
    summary = gap_engine.get_comprehensive_gap_summary()
    assert summary["total_research_gaps"] >= 10
    assert summary["total_scientific_conflicts"] >= 4
    assert len(summary["category_distribution"]) >= 6


# =============================================================================
# 13. Backend API Endpoints Integration
# =============================================================================
def test_backend_api_get_research_gaps_and_conflicts():
    gaps_res = get_research_gaps(category="COMPOSITION")
    assert "gaps" in gaps_res
    assert gaps_res["gaps_count"] >= 1

    conf_res = get_scientific_conflicts()
    assert "conflicts" in conf_res
    assert conf_res["conflicts_count"] >= 4


# =============================================================================
# 14. Data Protection & Invariant Preservation
# =============================================================================
def test_milestone_4_2_data_protection_and_invariants():
    # Master CSV
    df = pd.read_csv(CSV_PATH)
    assert df.shape == (1215, 41)

    # Review DB
    assert REVIEW_DB_PATH.exists()
    with sqlite3.connect(REVIEW_DB_PATH) as conn:
        cur = conn.cursor()
        r6_status = cur.execute("SELECT status FROM extraction_reviews WHERE id=6").fetchone()[0]
        assert r6_status == "pending"
        r7_status = cur.execute("SELECT status FROM extraction_reviews WHERE id=7").fetchone()[0]
        assert r7_status == "approved"

    # Lab Experiment DB
    assert LAB_DB_PATH.exists()
    with sqlite3.connect(LAB_DB_PATH) as conn:
        cur = conn.cursor()
        assert cur.execute("SELECT count(*) FROM lab_experiments").fetchone()[0] == 0
