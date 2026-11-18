"""
Scientific Retrieval Planner for LMFP Research Copilot.

Formulates an intent-driven retrieval execution plan across Stage 4 entity tables
and the hybrid passage index, enforcing condition parity checks, sample-aware deduplication,
and supervisor policy separation.
"""

from typing import Any, Dict, List, Optional, Set

from copilot.models import (
    ConversationContextState,
    EvidencePassage,
    RetrievalMatch,
    RetrievalPlan,
    ScientificIntent,
    ScientificIntentPayload,
    ScientificSubQuery,
)
from copilot.retriever import HybridRetriever


class RetrievalPlanner:
    """
    Creates and executes retrieval plans based on scientific intents and decomposed sub-queries.
    Maintains Combined BM25 + Entity + Structured without LSA as default.
    """

    def __init__(self, retriever: Optional[HybridRetriever] = None):
        self.retriever = retriever or HybridRetriever()

    def build_plan(
        self,
        query: str,
        payload: ScientificIntentPayload,
        sub_queries: List[ScientificSubQuery],
        context_state: Optional[ConversationContextState] = None,
    ) -> RetrievalPlan:
        """Construct the retrieval plan identifying boundaries, comparability, and policy checks."""
        # 1. Out-of-scope check
        if payload.intent == ScientificIntent.OUT_OF_SCOPE_OR_INSUFFICIENT_EVIDENCE:
            return RetrievalPlan(
                original_query=query,
                primary_intent=payload.intent,
                is_composite=False,
                sub_queries=[],
                requires_comparability_check=False,
                requires_policy_separation=False,
                is_out_of_scope=True,
                abstention_reason=(
                    "This inquiry pertains to a non-LMFP chemistry or out-of-scope system "
                    "(e.g., sodium-ion without LMFP, pure LCO pouch cells, or commercial nail safety testing). "
                    "HE-LMFP-Designer Copilot specializes strictly in Lithium Manganese Iron Phosphate cathode research."
                ),
            )

        # 2. Check for comparability requirements
        requires_comp = payload.intent in [
            ScientificIntent.SAMPLE_COMPARISON,
            ScientificIntent.COMPOSITION_COMPARISON,
            ScientificIntent.DOPANT_ANALYSIS,
            ScientificIntent.SYNTHESIS_COMPARISON,
            ScientificIntent.PRECURSOR_COMPARISON,
            ScientificIntent.CROSS_PAPER_COMPARISON,
        ] or len(sub_queries) > 1

        # 3. Check for policy separation requirement (Co or Cr doping)
        entities = payload.extracted_entities
        requires_policy = any(d in ["Co", "Cr"] for d in entities.dopants)
        if context_state and any(d in ["Co", "Cr"] for d in context_state.active_dopants):
            requires_policy = True

        return RetrievalPlan(
            original_query=query,
            primary_intent=payload.intent,
            is_composite=len(sub_queries) > 1,
            sub_queries=sub_queries,
            requires_comparability_check=requires_comp,
            requires_policy_separation=requires_policy,
            is_out_of_scope=False,
        )

    def execute_plan(
        self,
        plan: RetrievalPlan,
        top_k_per_subquery: int = 4,
        max_total_matches: int = 10,
    ) -> List[RetrievalMatch]:
        """
        Execute retrieval across all sub-queries in the plan.
        Aggregates results using sample-aware deduplication.
        """
        if plan.is_out_of_scope or not plan.sub_queries:
            return []

        subquery_results: List[List[RetrievalMatch]] = []

        for sq in plan.sub_queries:
            # Determine filters for subquery
            sample_filter = sq.target_entities[0] if (sq.target_entities and "SD_" in sq.target_entities[0]) else None
            dopant_filter = None
            for ent in sq.target_entities:
                if ent in ["Mg", "Ti", "Nb", "Co", "Cr", "Al", "Zr", "Zn", "Ni", "Cu", "V", "Mo", "W", "N/S"]:
                    dopant_filter = ent
                    break

            sq_matches = self.retriever.retrieve(
                query=sq.query_text,
                top_k=top_k_per_subquery,
                dopant_filter=dopant_filter,
                sample_id_filter=sample_filter,
                use_lsa=False,  # Phase 1 verified default: Combined BM25 + Entity + Structured without LSA
            )
            subquery_results.append(sq_matches)

        # Interleave top matches across subqueries to ensure representation of all comparison entities
        interleaved_matches: List[RetrievalMatch] = []
        seen_keys: Set[str] = set()
        max_depth = max((len(res) for res in subquery_results), default=0)

        for depth in range(max_depth):
            for res_list in subquery_results:
                if depth < len(res_list):
                    m = res_list[depth]
                    p = m.passage
                    unique_key = f"{p.paper_id}_{p.sample_id or ''}_{p.synthesis_profile_id or ''}_{p.section_type}_{p.page_number}"
                    if unique_key not in seen_keys:
                        seen_keys.add(unique_key)
                        interleaved_matches.append(m)

        return interleaved_matches[:max_total_matches]
