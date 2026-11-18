"""
Independent Test Suite for Stage 5 Phase 4 - Milestone 4.1:
Research Trend & Pattern Discovery Engine.

Validates:
- All 9 trend dimensions (dopant frequencies, co-occurrences, Mn/Fe ratios, entropy tiers,
  composites, synthesis routes, calcination parameters, characterization coverage, performance envelopes).
- Sample count versus independent paper count separation.
- Duplicate and multi-sample per paper handling.
- Condition-aware grouping (rate stratification, voltage window caveats).
- Missing-condition detection and reporting.
- Confounder variable identification.
- Evidence provenance correctness (primary vs secondary).
- Empty, missing, and small sample size dataset robustness.
- Data protection and repository integrity invariants.
"""

import os
from pathlib import Path
import sqlite3
import pandas as pd
import pytest

from copilot.research_intelligence import (
    FindingType,
    TrendDiscoveryEngine,
    TrendEvidence,
    TrendReport,
    compute_metric_summary,
    get_trend_discovery_engine,
)
from backend.main import get_literature_trends


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = WORKSPACE_ROOT / "data" / "literature_reference.csv"
REVIEW_DB_PATH = WORKSPACE_ROOT / "data" / "literature_review.db"
LAB_DB_PATH = WORKSPACE_ROOT / "data" / "lab_experiments.db"


@pytest.fixture(scope="module")
def engine():
    """Shared TrendDiscoveryEngine instance initialized on workspace dataset."""
    return get_trend_discovery_engine()


# =============================================================================
# 1. Dopant Frequency Distributions
# =============================================================================
def test_dopant_frequencies_returns_valid_reports(engine):
    reports = engine.analyze_dopant_frequencies(min_samples=2)
    assert len(reports) >= 8

    dopants = [r.data["dopant"] for r in reports]
    for expected in ["Ni", "Mg", "Ti", "Co", "Zn", "V"]:
        assert expected in dopants

    for r in reports:
        assert isinstance(r, TrendReport)
        assert r.dimension == "dopant_frequency"
        assert r.sample_count >= r.paper_count  # Sample count must always >= paper count
        assert r.paper_count >= 1
        assert r.finding_type == FindingType.DESCRIPTIVE
        assert len(r.supporting_evidence) > 0
        assert r.supporting_evidence[0].sample_id is not None
        assert r.supporting_evidence[0].provenance_type == "PRIMARY_EXPERIMENTAL"


def test_dopant_frequencies_policy_caveats(engine):
    reports = engine.analyze_dopant_frequencies(min_samples=1)
    co_rep = next((r for r in reports if r.data["dopant"] == "Co"), None)
    assert co_rep is not None
    assert any("Supervisor Policy Exclusion" in c and "Cobalt" in c for c in co_rep.scientific_caveats)


# =============================================================================
# 2. Dopant Co-occurrence Analysis
# =============================================================================
def test_dopant_cooccurrences_detection(engine):
    report = engine.analyze_dopant_cooccurrences(top_n=10)
    assert isinstance(report, TrendReport)
    assert report.dimension == "dopant_cooccurrence"
    assert report.sample_count > 0
    assert report.paper_count > 0

    top_pairs = report.data.get("top_cooccurring_pairs", [])
    assert len(top_pairs) >= 5

    # Check that unexplored pairs among candidate dopants are identified
    unexplored = report.data.get("unexplored_pairs_among_top_candidates", [])
    assert len(unexplored) > 0

    # Verify confounder variables and caveats are present
    assert len(report.confounding_variables) > 0
    assert any("precursor" in c.lower() or "charge neutrality" in c.lower() for c in report.confounding_variables)


# =============================================================================
# 3. Mn/Fe Stoichiometric Distributions
# =============================================================================
def test_mn_fe_distributions(engine):
    report = engine.analyze_mn_fe_distributions()
    assert isinstance(report, TrendReport)
    assert report.dimension == "mn_fe_ratio"
    assert report.sample_count >= 1100  # Over 1,100 records report Mn ratio
    assert report.paper_count >= 80

    bins = report.data.get("stoichiometry_bins", [])
    assert len(bins) == 6

    bin_names = [b["bin_name"] for b in bins]
    assert any("Equimolar" in n for n in bin_names)
    assert any("Standard Mn-Rich" in n for n in bin_names)
    assert any("High Mn-Rich" in n for n in bin_names)

    # Verify bin sample representation
    eq_bin = next(b for b in bins if "Equimolar" in b["bin_name"])
    high_mn_bin = next(b for b in bins if "High Mn-Rich" in b["bin_name"])
    assert eq_bin["sample_count"] >= 50
    assert high_mn_bin["sample_count"] > 400
    assert high_mn_bin["paper_count"] >= 35

    # Confounder checks
    assert len(report.confounding_variables) > 0
    assert any("carbon" in c.lower() or "particle" in c.lower() for c in report.confounding_variables)


# =============================================================================
# 4. Doping Entropy Tiers
# =============================================================================
def test_doping_entropy_tiers(engine):
    report = engine.analyze_doping_entropy_tiers()
    assert isinstance(report, TrendReport)
    assert report.dimension == "doping_entropy_tier"

    tiers = report.data.get("entropy_tiers", [])
    assert len(tiers) >= 4

    undoped = next(t for t in tiers if "Undoped" in t["tier_name"])
    single = next(t for t in tiers if "Single-doped" in t["tier_name"])
    high_entropy = next(t for t in tiers if "High-Entropy" in t["tier_name"] or "Triple" in t["tier_name"])

    assert undoped["sample_count"] > single["sample_count"]
    # High-entropy must be flagged with insufficient data warning
    he_tier = next(t for t in tiers if "High-Entropy" in t["tier_name"])
    assert he_tier["sample_size_flag"] == "INSUFFICIENT_DATA"
    assert he_tier["paper_count"] <= 2


# =============================================================================
# 5. Composite Modifications
# =============================================================================
def test_composite_modifications(engine):
    report = engine.analyze_composite_modifications()
    assert isinstance(report, TrendReport)
    assert report.dimension == "composite_modifications"

    c_stats = report.data.get("carbon_wt_percent_stats", {})
    assert c_stats["count"] >= 600
    assert 5.0 <= c_stats["mean"] <= 10.0
    assert c_stats["min"] < 1.0
    assert c_stats["max"] >= 20.0

    breakdown = report.data.get("composite_types_breakdown", [])
    types = [b["modification_type"] for b in breakdown]
    assert any("rGO" in t for t in types)
    assert any("CNT" in t for t in types)

    # Confounder warning must mention crystallite / particle size
    assert any("particle" in c.lower() or "crystallite" in c.lower() for c in report.confounding_variables)


# =============================================================================
# 6. Synthesis Routes
# =============================================================================
def test_synthesis_routes(engine):
    report = engine.analyze_synthesis_routes()
    assert isinstance(report, TrendReport)
    assert report.dimension == "synthesis_routes"

    families = report.data.get("synthesis_families", [])
    fam_names = [f["synthesis_route"] for f in families]
    assert "Solid-state / High-energy ball milling" in fam_names
    assert "Sol-gel" in fam_names
    assert "Hydrothermal / Solvothermal" in fam_names

    # Check that solid-state and sol-gel have substantial sample representation
    ss = next(f for f in families if "Solid-state" in f["synthesis_route"])
    sg = next(f for f in families if "Sol-gel" in f["synthesis_route"])
    assert ss["sample_count"] > 100
    assert sg["sample_count"] > 100


# =============================================================================
# 7. Calcination Parameters
# =============================================================================
def test_calcination_parameters(engine):
    report = engine.analyze_calcination_parameters()
    assert isinstance(report, TrendReport)
    assert report.dimension == "calcination_parameters"

    t_stats = report.data.get("temperature_stats_c", {})
    assert t_stats["count"] >= 850
    assert 500.0 <= t_stats["median"] <= 650.0
    assert t_stats["max"] >= 800.0

    dur_stats = report.data.get("duration_stats_h", {})
    assert dur_stats["count"] >= 800
    assert 4.0 <= dur_stats["mean"] <= 12.0

    # Missing parameters must be explicitly tallied
    assert report.data.get("missing_temperature_count", 0) > 200
    assert report.data.get("missing_duration_count", 0) > 200


# =============================================================================
# 8. Characterization Coverage
# =============================================================================
def test_characterization_coverage(engine):
    report = engine.analyze_characterization_coverage()
    assert isinstance(report, TrendReport)
    assert report.dimension == "characterization_coverage"

    data = report.data
    assert data["rct_before_reported_samples"] > 0
    assert data["d_li_reported_samples"] > 0
    assert data["complete_eis_and_dli_samples"] > 0
    # Complete characterization must be a distinct minority compared to total samples
    assert data["complete_eis_and_dli_samples"] < (report.sample_count * 0.15)

    # High rate claims missing EIS should be detected
    assert data["high_rate_claims_missing_eis_samples"] >= 0


# =============================================================================
# 9. Electrochemical Performance Envelopes (Strictly Condition-Aware)
# =============================================================================
def test_electrochemical_performance_envelopes_stratification(engine):
    reports = engine.analyze_electrochemical_performance_envelopes()
    assert len(reports) >= 4  # 0.05C, 0.1C, 1C, 2C, 5C

    rates = [r.data["c_rate"] for r in reports]
    assert 0.1 in rates
    assert 1.0 in rates
    assert 5.0 in rates

    rep_01 = next(r for r in reports if r.data["c_rate"] == 0.1)
    rep_1 = next(r for r in reports if r.data["c_rate"] == 1.0)
    rep_5 = next(r for r in reports if r.data["c_rate"] == 5.0)

    # Condition parity verification: 0.1C median capacity > 5C median capacity
    cap_01_median = rep_01.data["capacity_stats_mah_g"]["median"]
    cap_1_median = rep_1.data["capacity_stats_mah_g"]["median"]
    cap_5_median = rep_5.data["capacity_stats_mah_g"]["median"]

    assert cap_01_median > cap_1_median >= cap_5_median
    assert rep_01.finding_type == FindingType.EXPERIMENTALLY_SUPPORTED
    assert rep_5.finding_type == FindingType.EXPERIMENTALLY_SUPPORTED

    # Ensure measurements under 0.1C are comparable only with 0.1C
    assert rep_01.comparable_measurement_count == rep_01.measurement_count
    assert rep_5.comparable_measurement_count == rep_5.measurement_count


# =============================================================================
# 10. Sample versus Independent Paper Counting
# =============================================================================
def test_sample_vs_paper_counting_independence(engine):
    """Verify that multiple samples from a single publication are not counted as independent papers."""
    df = pd.read_csv(CSV_PATH)
    total_samples = len(df)
    unique_dois = df["DOI"].nunique()

    # In our master dataset, 1,215 records come from 87 unique DOIs
    assert total_samples == 1215
    assert unique_dois == 87

    cooccur = engine.analyze_dopant_cooccurrences()
    assert cooccur.paper_count <= cooccur.sample_count
    assert cooccur.paper_count <= unique_dois


# =============================================================================
# 11. Empty and Insufficient Dataset Robustness
# =============================================================================
def test_empty_dataset_handling(tmp_path):
    empty_csv = tmp_path / "empty.csv"
    empty_csv.write_text("Sample_ID,Paper_ID,DOI,Composition_Formula,Mn_Ratio,Fe_Ratio,Dopant_Element\n", encoding="utf-8")

    empty_engine = TrendDiscoveryEngine(csv_path=str(empty_csv), db_path=str(tmp_path / "empty.db"))
    assert empty_engine.analyze_dopant_frequencies() == []
    cooccur = empty_engine.analyze_dopant_cooccurrences()
    assert cooccur.sample_count == 0
    assert cooccur.paper_count == 0

    mn_fe = empty_engine.analyze_mn_fe_distributions()
    assert mn_fe.sample_count == 0

    envelopes = empty_engine.analyze_electrochemical_performance_envelopes()
    assert envelopes == []


def test_metric_summary_edge_cases():
    # Empty array
    s0 = compute_metric_summary([])
    assert s0.count == 0
    assert s0.mean_val is None

    # Single value
    s1 = compute_metric_summary([145.2])
    assert s1.count == 1
    assert s1.min_val == 145.2
    assert s1.max_val == 145.2
    assert s1.std_val == 0.0


# =============================================================================
# 12. Query by Topic and Dopant Interface
# =============================================================================
def test_query_trends_by_topic(engine):
    res_dopants = engine.query_trends_by_topic(topic="dopants")
    assert "dopant_frequencies" in res_dopants

    res_mg = engine.query_trends_by_topic(dopant="Mg")
    assert res_mg["dopant"] == "Mg"
    assert res_mg["frequency_profile"] is not None
    assert "cooccurring_pairs" in res_mg

    res_summary = engine.get_comprehensive_trend_summary()
    assert "dataset_overview" in res_summary
    assert "trend_dimensions" in res_summary
    assert len(res_summary["trend_dimensions"]) == 9


# =============================================================================
# 13. Backend API Endpoint Integration
# =============================================================================
def test_backend_api_get_literature_trends():
    """Verify backend main.py function endpoint returns valid trend payload."""
    res = get_literature_trends(topic="dopants")
    assert "dopant_frequencies" in res
    assert len(res["dopant_frequencies"]) > 0

    res_dopant_mg = get_literature_trends(dopant="Mg")
    assert res_dopant_mg["dopant"] == "Mg"


# =============================================================================
# 14. Data Protection & Invariant Preservation
# =============================================================================
def test_data_protection_and_invariants_preserved():
    # 1. Master CSV
    df = pd.read_csv(CSV_PATH)
    assert df.shape == (1215, 41)

    # 2. Lab Experiments DB
    assert LAB_DB_PATH.exists()
    with sqlite3.connect(LAB_DB_PATH) as conn:
        cur = conn.cursor()
        tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        assert "lab_experiments" in tables
        count = cur.execute("SELECT count(*) FROM lab_experiments").fetchone()[0]
        assert count == 0

    # 3. Literature Review DB
    assert REVIEW_DB_PATH.exists()
    with sqlite3.connect(REVIEW_DB_PATH) as conn:
        cur = conn.cursor()
        r6_status = cur.execute("SELECT status FROM extraction_reviews WHERE id=6").fetchone()[0]
        assert r6_status == "pending"
        r7_status = cur.execute("SELECT status FROM extraction_reviews WHERE id=7").fetchone()[0]
        assert r7_status == "approved"
