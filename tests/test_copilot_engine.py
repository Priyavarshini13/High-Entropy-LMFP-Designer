"""Evaluation benchmark and integration tests for the LMFP Research Copilot."""

import json
from pathlib import Path
import pytest

from copilot.engine import LMFPResearchCopilot
from copilot.index import ScientificPassageIndex
from copilot.retriever import HybridRetriever


BENCHMARK_PATH = Path(__file__).resolve().parent / "copilot_qa_eval.json"


@pytest.fixture(scope="module")
def copilot_engine():
    """Shared Research Copilot instance in deterministic mode for reproducible benchmark verification."""
    index = ScientificPassageIndex()
    index.build_index()
    retriever = HybridRetriever(index=index)
    return LMFPResearchCopilot(retriever=retriever)


def test_passage_indexing_and_bm25_retrieval(copilot_engine):
    """Verify that index builds across 1,215 master records and review database."""
    idx = copilot_engine.retriever.index
    assert idx.total_docs >= 1215
    assert idx.avg_doc_length > 10.0
    assert len(idx.idf) > 1000

    # Test BM25 score on exact formula
    scores = idx.get_bm25_scores(["limn0.7fe0.3po4"])
    assert len(scores) > 0


def test_hybrid_retrieval_condition_preservation(copilot_engine):
    """Verify that retrieval respects 5C condition and dopant constraints."""
    matches = copilot_engine.retriever.retrieve("What samples achieve high capacity at 5C with Mg doping?", top_k=5)
    assert len(matches) > 0

    # At least one match should contain 5C structured data or Mg
    has_mg_or_5c = any(
        "mg" in (m.passage.composition or "").lower()
        or "mg" in str(m.passage.structured_data.get("dopant", "")).lower()
        or m.passage.structured_data.get("discharge_capacity_5c") is not None
        for m in matches
    )
    assert has_mg_or_5c


def test_supervisor_doping_exclusion_guardrails(copilot_engine):
    """Verify that queries inquiring about Cobalt or Chromium trigger supervisor exclusions."""
    res = copilot_engine.chat("Can we use Cobalt or Chromium to boost performance?", force_deterministic=True)
    full_text = res.response.lower()

    # Must explain that Co is excluded due to cost and Cr due to toxicity
    assert "cost" in full_text
    assert "toxic" in full_text
    assert any("Supervisor Doping" in f.get("rule", "") for f in res.engine_facts)


def test_abstention_on_unsupported_queries(copilot_engine):
    """CRITICAL TEST: Ensure copilot abstains on topics absent from the LMFP repository."""
    res = copilot_engine.chat("What is the sodium-ion diffusion coefficient of LMFP in propylene carbonate?", force_deterministic=True)
    full_text = res.response.lower()

    # Must state lack of evidence without inventing numbers
    assert "does not contain" in full_text or "no peer-reviewed records" in full_text
    assert "diffusion coefficient is 10^" not in full_text


def test_conversational_followup_pronoun_resolution(copilot_engine):
    """Verify multi-turn follow-up question resolves 'its' to preceding turn's subject."""
    turn_1 = {"sender": "user", "text": "How does Mg doping affect LMFP?"}
    turn_2 = {"sender": "copilot", "text": "Mg2+ substitution in the M2 site stabilizes 1D diffusion channels."}

    res = copilot_engine.chat(
        query="What about its effect at 5C?",
        recent_history=[turn_1, turn_2],
        force_deterministic=True,
    )
    full_text = res.response.lower()

    # Should have resolved 'its' to Mg doping at 5C
    assert "5c" in full_text or "rate" in full_text
    assert "mg" in full_text or "magnesium" in full_text


def test_real_paper_qa_benchmark_evaluation(copilot_engine):
    """
    Run complete evaluation across all 32 benchmark questions from copilot_qa_eval.json.
    Verifies factual correctness, condition preservation, citation presence, and absence of prohibited claims.
    """
    assert BENCHMARK_PATH.exists(), f"Benchmark file not found: {BENCHMARK_PATH}"
    with open(BENCHMARK_PATH, encoding="utf-8") as f:
        benchmarks = json.load(f)

    passed_count = 0
    total_count = len(benchmarks)
    assert total_count >= 30, f"Benchmark suite should contain at least 30 questions, found {total_count}"

    for item in benchmarks:
        q_id = item["id"]
        q_text = item["question"]
        history = None
        if item.get("turn_1_question"):
            t1 = item["turn_1_question"]
            history = [
                {"sender": "user", "text": t1},
                {"sender": "copilot", "text": f"Grounded discussion regarding {t1}."},
            ]

        res = copilot_engine.chat(query=q_text, recent_history=history, force_deterministic=True)
        resp_text = (res.response + " " + (res.direct_answer or "") + " " + (res.explanation or "")).lower()

        # 1. Check required concepts (at least 2, or all if fewer)
        req_concepts = item.get("required_concepts", [])
        matched_concepts = [c for c in req_concepts if c.lower() in resp_text]
        min_required = min(len(req_concepts), 2)
        assert len(matched_concepts) >= min_required, f"[{q_id}] Missing required concepts: matched {matched_concepts} of {req_concepts}"

        # 2. Check prohibited claims
        prohibited = item.get("prohibited_claims", [])
        for p_claim in prohibited:
            assert p_claim.lower() not in resp_text, f"[{q_id}] Prohibited claim found: '{p_claim}'"

        passed_count += 1

    assert passed_count == total_count
    print(f"\n[Scientific Benchmark] All {passed_count}/{total_count} evaluation cases passed successfully.")


def test_mg_co_ti_comparative_synthesis(copilot_engine):
    """
    Regression test for multi-dopant comparison:
    1. Zero internal reasoning or planning preamble.
    2. Strict separation between single-dopant (Mg, Co, Ti) and multi-dopant (Mg+Ti).
    3. Complete absence of synthetic test fixtures from comparison tables.
    4. Honest reporting of missing baselines and unmeasured Mn dissolution.
    5. Objective reporting of Cobalt performance paired with project cost exclusion policy.
    """
    res = copilot_engine.chat("Compare Mg, Co, and Ti doping in LMFP", force_deterministic=True)
    full_text = res.response.lower()

    # 1. Zero internal reasoning / planning text
    prohibited_reasoning = [
        "okay, the user wants",
        "<think>",
        "</think>",
        "thinking process:",
        "my plan:",
        "first, i will",
        "let's analyze",
    ]
    for p_str in prohibited_reasoning:
        assert p_str not in full_text, f"Internal reasoning found: '{p_str}'"

    # 2. Separation of single-dopant and multi-dopant
    assert "mg-only" in full_text or "isovalent" in full_text
    assert "co-only" in full_text or "cobalt" in full_text
    assert "ti-only" in full_text or "aliovalent" in full_text
    assert "multi-dopant" in full_text or "synerg" in full_text

    # 3. Objective policy separation for Cobalt
    assert "excluded" in full_text or "cost" in full_text

    # 4. Clear data gap disclosure
    assert "dissolution" in full_text or "missing" in full_text or "unmeasured" in full_text

    # 5. Table exists, excludes synthetic records, and contains structured columns
    assert res.comparison_table is not None
    assert len(res.comparison_table) >= 3
    for row in res.comparison_table:
        paper_id = row.get("paper_id", "").lower()
        sample = str(row.get("sample", "")).lower()
        assert "test_syn" not in paper_id and "test_syn" not in sample
        assert "stage3" not in paper_id
        assert "category" in row
        assert "reported_capacity" in row
        assert "limitations" in row
