"""
Comprehensive Test Suite for Stage 5 Phase 2:
Scientific Question Intent Routing, Context Resolution, Decomposition, and Sufficiency Evaluation.
"""

import json
from pathlib import Path
import pytest

from copilot.context_resolver import ConversationContextResolver
from copilot.engine import LMFPResearchCopilot
from copilot.evidence_sufficiency import EvidenceSufficiencyEvaluator
from copilot.intent_classifier import ScientificIntentClassifier
from copilot.models import (
    ConversationContextState,
    EvidencePassage,
    RetrievalMatch,
    RetrievalPlan,
    ScientificIntent,
    ScientificIntentPayload,
    ScientificSubQuery,
)
from copilot.query_decomposer import ScientificQueryDecomposer
from copilot.retrieval_planner import RetrievalPlanner
from copilot.retriever import HybridRetriever


@pytest.fixture
def classifier():
    return ScientificIntentClassifier()


@pytest.fixture
def context_resolver(classifier):
    return ConversationContextResolver(classifier)


@pytest.fixture
def decomposer():
    return ScientificQueryDecomposer()


@pytest.fixture
def retriever():
    return HybridRetriever()


@pytest.fixture
def planner(retriever):
    return RetrievalPlanner(retriever)


@pytest.fixture
def sufficiency_evaluator():
    return EvidenceSufficiencyEvaluator()


@pytest.fixture
def copilot(retriever, classifier, context_resolver, decomposer, planner, sufficiency_evaluator):
    return LMFPResearchCopilot(
        retriever=retriever,
        classifier=classifier,
        context_resolver=context_resolver,
        decomposer=decomposer,
        planner=planner,
        sufficiency_evaluator=sufficiency_evaluator,
    )


# ---------------------------------------------------------------------------
# 1. Classification of All 18 Scientific Intents
# ---------------------------------------------------------------------------
def test_all_18_scientific_intents_classification(classifier):
    """Verify that representative LMFP research queries map to each of the 18 scientific intents."""
    intent_queries = [
        (ScientificIntent.SAMPLE_PROPERTY_LOOKUP, "What is the 0.05C discharge capacity of sample SD_NO3 in srep26686?"),
        (ScientificIntent.SAMPLE_COMPARISON, "Compare the electrochemical capacity of SD_NO3 vs SD_SO4 in srep26686."),
        (ScientificIntent.COMPOSITION_COMPARISON, "How does the performance of LiMn0.8Fe0.2PO4 compare to LiMn0.5Fe0.5PO4?"),
        (ScientificIntent.DOPANT_ANALYSIS, "How does Mg doping influence rate capability and M2 site stability?"),
        (ScientificIntent.COMPOSITE_MODIFICATION_ANALYSIS, "What is the effect of reduced graphene oxide (rGO) compared to unmodified LMFP?"),
        (ScientificIntent.SYNTHESIS_COMPARISON, "Compare solvothermal synthesis with solid-state ball-milling routes for LMFP."),
        (ScientificIntent.PRECURSOR_COMPARISON, "Do different iron precursor salts (nitrate vs sulfate) yield conflicting performance?"),
        (ScientificIntent.ELECTROCHEMICAL_PERFORMANCE_ANALYSIS, "What is the overall electrochemical discharge performance of LMFP?"),
        (ScientificIntent.RATE_CAPABILITY_ANALYSIS, "What is the rate capability of LMFP cathodes at 5C and 10C?"),
        (ScientificIntent.CYCLING_STABILITY_ANALYSIS, "What capacity retention does LMFP achieve over 1,000 cycles?"),
        (ScientificIntent.CHARACTERIZATION_ANALYSIS, "What crystal structure and space group is confirmed by XRD for srep26686?"),
        (ScientificIntent.CROSS_PAPER_COMPARISON, "Compare the 0.1C discharge capacity in Paper P1 with Reference [79]."),
        (ScientificIntent.MECHANISM_EXPLANATION, "What is the mechanism of manganese dissolution and Jahn-Teller disproportionation?"),
        (ScientificIntent.RESEARCH_GAP_ANALYSIS, "What are the primary unaddressed research gaps in high-temperature 55°C cycling of LMFP?"),
        (ScientificIntent.LITERATURE_SEARCH, "Find and show published literature papers reporting titanium doping in LMFP."),
        (ScientificIntent.EXPERIMENTAL_CONDITION_FILTER, "What samples were tested in the 2.5 to 4.5 V voltage window at 25 °C?"),
        (ScientificIntent.FOLLOW_UP_QUESTION, "What about its performance at 5C?"),
        (ScientificIntent.OUT_OF_SCOPE_OR_INSUFFICIENT_EVIDENCE, "What is the sodium-ion diffusion coefficient in propylene carbonate electrolyte?"),
    ]

    for expected_intent, query in intent_queries:
        turn = 2 if expected_intent == ScientificIntent.FOLLOW_UP_QUESTION else 1
        payload = classifier.classify_intent(query, conversation_turn=turn)
        assert payload.intent == expected_intent, f"Query '{query}' classified as {payload.intent}, expected {expected_intent}"


# ---------------------------------------------------------------------------
# 2. Entity and Parameter Extraction Fidelity
# ---------------------------------------------------------------------------
def test_scientific_entity_and_condition_extraction(classifier):
    """Verify high-fidelity entity, material, and numerical condition extraction."""
    query = (
        "In srep26686, compare spray-dried SD_NO3 and SD_SO4 with rGO coating "
        "at 0.1C, 1C, and 5C after 500 cycles at 650 °C calcination between 2.5-4.5 V with 2.0 mg/cm2 mass loading."
    )
    entities = classifier.extract_entities(query)

    assert "srep26686" in entities.paper_ids
    assert "SD_NO3" in entities.sample_labels
    assert "SD_SO4" in entities.sample_labels
    assert "rGO" in entities.modifications
    assert "Spray Drying" in entities.synthesis_methods
    assert "Nitrate" in entities.precursors
    assert "Sulfate" in entities.precursors
    assert 0.1 in entities.c_rates
    assert 1.0 in entities.c_rates
    assert 5.0 in entities.c_rates
    assert 500 in entities.cycle_counts
    assert entities.temperature_c == 650.0
    assert entities.voltage_window == (2.5, 4.5)
    assert entities.mass_loading_mg_cm2 == 2.0


# ---------------------------------------------------------------------------
# 3. Multi-Turn Dialogue Continuity and Multi-Entity Memory (Ni vs Mg Turns 1-4)
# ---------------------------------------------------------------------------
def test_multi_turn_dialogue_continuity_and_multi_entity_memory(copilot):
    """
    Simulate full 4-turn researcher dialogue:
    Turn 1: Compares Ni and Mg doping.
    Turn 2: "What about their performance at 5C?" -> preserves BOTH Ni and Mg without arbitrary loss.
    Turn 3: "What about after 500 cycles?" -> carries forward 5C condition.
    Turn 4: "What is its capacity?" -> detects ambiguity between Ni and Mg and asks for clarification.
    """
    history = []

    # --- Turn 1: Initial multi-dopant comparison ---
    t1_query = "How does Ni doping in Reference [29] compare to Mg doping in LMFP?"
    t1_res = copilot.chat(t1_query, force_deterministic=True)
    assert t1_res.context_state is not None
    assert "Ni" in t1_res.context_state["active_dopants"]
    assert "Mg" in t1_res.context_state["active_dopants"]
    history.append({"role": "user", "content": t1_query})
    history.append({"role": "assistant", "content": t1_res.response})

    # --- Turn 2: Plural pronoun continuity ("their") ---
    t2_query = "What about their performance at 5C?"
    t2_res = copilot.chat(t2_query, recent_history=history, force_deterministic=True)
    t2_ctx = t2_res.context_state
    assert t2_ctx is not None
    # CRITICAL: Both Ni and Mg MUST be retained in active dopants without greedy single-element shadowing
    assert "Ni" in t2_ctx["active_dopants"], "Ni dopant was lost during plural pronoun resolution!"
    assert "Mg" in t2_ctx["active_dopants"], "Mg dopant was lost during plural pronoun resolution!"
    assert t2_ctx["active_conditions"].get("c_rate") == 5.0
    history.append({"role": "user", "content": t2_query})
    history.append({"role": "assistant", "content": t2_res.response})

    # --- Turn 3: Condition carry-forward ---
    t3_query = "What about after 500 cycles?"
    t3_res = copilot.chat(t3_query, recent_history=history, force_deterministic=True)
    t3_ctx = t3_res.context_state
    assert t3_ctx is not None
    assert t3_ctx["active_conditions"].get("c_rate") == 5.0, "5C condition was not carried forward!"
    assert t3_ctx["active_conditions"].get("cycle_count") == 500
    history.append({"role": "user", "content": t3_query})
    history.append({"role": "assistant", "content": t3_res.response})

    # --- Turn 4: Singular pronoun ambiguity disambiguation ---
    t4_query = "What is its capacity?"
    t4_res = copilot.chat(t4_query, recent_history=history, force_deterministic=True)
    t4_ctx = t4_res.context_state
    assert t4_ctx is not None
    # Because both Ni and Mg are active and user used singular 'its', copilot must flag ambiguity
    assert t4_ctx.get("requires_clarification") is True, "Expected ambiguity flag when 'its' refers to multiple active candidates"
    assert "Clarification" in t4_res.response or "clarification" in t4_res.response.lower()


# ---------------------------------------------------------------------------
# 4. Single Entity Pronoun Resolution and Sample Identity Pinning
# ---------------------------------------------------------------------------
def test_single_entity_pronoun_resolution_and_sample_identity_pinning(copilot):
    """
    Verify that when only one sample is active, singular 'it' resolves directly to that sample,
    and subsequent retrieval stays pinned to that sample without switching.
    """
    history = [
        {"role": "user", "content": "What are the discharge properties of SD_NO3 in srep26686?"},
        {"role": "assistant", "content": "In srep26686, SD_NO3 delivered 45 mAh/g at 0.05C."},
    ]
    t2_res = copilot.chat("What about its performance at 1C?", recent_history=history, force_deterministic=True)
    assert t2_res.context_state is not None
    assert "SD_NO3" in t2_res.context_state["active_sample_labels"]
    # Verify that the response specifically discusses SD_NO3 rather than switching to SD_SO4
    assert "sd_no3" in t2_res.response.lower()


# ---------------------------------------------------------------------------
# 5. In-Scope Cell Testing vs Out-of-Scope Rejection
# ---------------------------------------------------------------------------
def test_in_scope_cell_testing_vs_out_of_scope_rejection(copilot):
    """
    CRITICAL PRODUCT RULE:
    LMFP cell-level / pouch-cell / electrolyte interaction questions ARE IN SCOPE!
    Only non-LMFP domains (pure Na-ion, pure LCO, pure NCM811 without LMFP, nail test without cathode data) abstain.
    """
    # In-Scope LMFP Cell Testing (MUST NOT ABSTAIN)
    pouch_res = copilot.chat("How does pouch cell cycling perform with carbon-coated LMFP cathodes?", force_deterministic=True)
    assert pouch_res.inference_source != "out_of_scope_abstention"
    assert "pouch" in pouch_res.response.lower()
    assert "does not contain" not in pouch_res.direct_answer.lower()

    electrolyte_res = copilot.chat("What electrolyte additives help stabilize LMFP pouch cells during high-temperature cycling?", force_deterministic=True)
    assert electrolyte_res.inference_source != "out_of_scope_abstention"
    assert "does not contain" not in electrolyte_res.direct_answer.lower()

    # Out-of-Scope Topics (MUST CLEANLY ABSTAIN)
    na_res = copilot.chat("What is the sodium-ion diffusion coefficient of hard carbon in propylene carbonate?", force_deterministic=True)
    assert na_res.inference_source == "out_of_scope_abstention"
    assert "does not contain" in na_res.direct_answer.lower()
    assert "insufficient evidence" in na_res.explanation.lower()

    nail_res = copilot.chat("What are the nail penetration safety test results for pure commercial NCM811 cells?", force_deterministic=True)
    assert nail_res.inference_source == "out_of_scope_abstention"
    assert "does not contain" in nail_res.direct_answer.lower()


# ---------------------------------------------------------------------------
# 6. Supervisor Policy vs Universal Scientific Separation
# ---------------------------------------------------------------------------
def test_supervisor_policy_vs_universal_science_separation(copilot):
    """
    Verify that Cobalt and Chromium queries report published scientific findings
    while strictly separating internal supervisor industrial policies (cost & toxicity).
    """
    res = copilot.chat("Can we dope LMFP with Cobalt and Chromium to maximize rate performance?", force_deterministic=True)

    resp_lower = res.response.lower()
    # Must report literature effects (e.g. Paper P4: 143.6 mAh/g @ 5C)
    assert "143.6" in resp_lower or "rate" in resp_lower or "conductivity" in resp_lower
    # Must identify supervisor policy exclusion reasons
    assert "cost" in resp_lower
    assert "toxic" in resp_lower
    # Prohibited claim: Do NOT claim Co/Cr are recommended or physically incapable
    assert "cobalt and chromium are recommended for target alloy" not in resp_lower

    # Verify retrieval plan and sufficiency report flagged policy separation
    assert res.retrieval_plan is not None
    assert res.retrieval_plan.get("requires_policy_separation") is True
    assert res.sufficiency_report is not None
    assert len(res.sufficiency_report.get("policy_distinctions", [])) >= 1


# ---------------------------------------------------------------------------
# 7. Composite Query Decomposition
# ---------------------------------------------------------------------------
def test_composite_query_decomposition(decomposer, classifier):
    """Verify that composite questions decompose into condition-isolated sub-queries."""
    query = (
        "Compare discharge capacity of SD_NO3 and SD_SO4 at 0.1C and 1C, "
        "and explain the difference in EIS Rct impedance."
    )
    payload = classifier.classify_intent(query)
    sub_queries = decomposer.decompose(query, payload)

    assert len(sub_queries) >= 3, f"Expected at least 3 sub-queries, got {len(sub_queries)}"
    sq_texts = [sq.query_text.lower() for sq in sub_queries]
    # Check that individual samples are isolated
    assert any("sd_no3" in t for t in sq_texts)
    assert any("sd_so4" in t for t in sq_texts)
    # Check that characterization / EIS is isolated
    assert any("rct" in t or "eis" in t for t in sq_texts)


# ---------------------------------------------------------------------------
# 8. Evidence Sufficiency Pre-Generation Evaluation
# ---------------------------------------------------------------------------
def test_evidence_sufficiency_evaluation(sufficiency_evaluator):
    """Verify evidence sufficiency checks condition parity, missing counterparts, and provenance."""
    # Create mock plan with comparison requirement
    plan = RetrievalPlan(
        original_query="Compare Ni and Mg doping at 5C",
        primary_intent=ScientificIntent.DOPANT_ANALYSIS,
        is_composite=True,
        sub_queries=[
            ScientificSubQuery(sub_query_id="sq_1", query_text="Ni doping at 5C", intent=ScientificIntent.DOPANT_ANALYSIS, target_entities=["Ni"]),
            ScientificSubQuery(sub_query_id="sq_2", query_text="Mg doping at 5C", intent=ScientificIntent.DOPANT_ANALYSIS, target_entities=["Mg"]),
        ],
        requires_comparability_check=True,
        requires_policy_separation=False,
    )

    # Provide matches containing only Ni, missing Mg
    p_ni = EvidencePassage(
        passage_id="p_ni_1",
        paper_id="Ref29",
        sample_label="Ref29_LiMn0.8Fe0.2PO4_Ni",
        text="Ni-doped LMFP delivered 119.5 mAh/g at 2C across a 2.5-4.5 V window.",
        structured_data={"voltage_window": "2.5-4.5V", "c_rate": 2.0},
        provenance_type="SECONDARY_REVIEW",
    )
    matches = [RetrievalMatch(passage=p_ni, combined_score=0.9)]

    report = sufficiency_evaluator.evaluate(plan, matches)
    assert report.is_comparable is False
    assert "Mg" in report.missing_counterparts
    assert report.limitation_notes is not None
    assert "Missing direct literature counterpart for Mg" in report.limitation_notes
    assert len(report.provenance_warnings) >= 1


# ---------------------------------------------------------------------------
# 9. Explicit Regression for eval_06 and eval_10
# ---------------------------------------------------------------------------
def test_regression_eval_06_and_eval_10(copilot):
    """Ensure eval_06 (policy separation) and eval_10 (5C Mg follow-up) pass with 100% fidelity."""
    # eval_06
    res_06 = copilot.chat("Can we dope LMFP with Cobalt and Chromium to maximize rate performance?", force_deterministic=True)
    resp_06 = res_06.response.lower()
    assert "cobalt" in resp_06
    assert "chromium" in resp_06
    assert "cost" in resp_06
    assert "toxicity" in resp_06 or "toxic" in resp_06

    # eval_10
    history_10 = [
        {"role": "user", "content": "How does Mg doping affect LMFP?"},
        {"role": "assistant", "content": "Mg doping reduces polarization and stabilizes the M2 site."},
    ]
    res_10 = copilot.chat("What about its effect at 5C?", recent_history=history_10, force_deterministic=True)
    resp_10 = res_10.response.lower()
    assert "mg" in resp_10
    assert "5c" in resp_10
