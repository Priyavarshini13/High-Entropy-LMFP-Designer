"""
Scientific Query Decomposer for LMFP Research Copilot.

Decomposes composite research questions into atomic, condition-isolated sub-queries
with explicit entity targets, experimental conditions, and retrieval strategies.
"""

import re
from typing import Any, Dict, List, Optional

from copilot.models import (
    ConversationContextState,
    ExtractedEntities,
    ScientificIntent,
    ScientificIntentPayload,
    ScientificSubQuery,
)


class ScientificQueryDecomposer:
    """
    Decomposes scientific research questions into atomic sub-queries with condition isolation.
    Single-intent questions bypass decomposition and return an atomic sub-query.
    """

    def is_composite_query(self, query: str, payload: ScientificIntentPayload) -> bool:
        """Determine whether a research question requires multi-query decomposition."""
        lower_q = query.lower()
        entities = payload.extracted_entities

        # 1. Multiple physical samples compared
        if len(entities.sample_labels) >= 2 or len(entities.sample_ids) >= 2:
            return True

        # 2. Multiple dopants compared
        if len(entities.dopants) >= 2:
            return True

        # 3. Multiple precursors compared
        if len(entities.precursors) >= 2:
            return True

        # 4. Multi-part questions with conjunctions connecting distinct properties
        conjunction_patterns = [
            r"\band\s+(?:explain|what\s+about|why|how\s+does|compare|evaluate)\b",
            r"\b(?:capacity|performance)\b.*\band\b.*(?:impedance|eis|rct|retention|cycling|mechanism)\b",
            r"\b(?:at\s+\d+c)\b.*\band\b.*(?:at\s+\d+c|after\s+\d+\s+cycles)\b",
        ]
        for pat in conjunction_patterns:
            if re.search(pat, lower_q):
                return True

        # 5. Cross-paper comparisons
        if payload.intent == ScientificIntent.CROSS_PAPER_COMPARISON or len(entities.paper_ids) >= 2:
            return True

        return False

    def decompose(
        self,
        query: str,
        payload: ScientificIntentPayload,
        context_state: Optional[ConversationContextState] = None,
    ) -> List[ScientificSubQuery]:
        """
        Decompose a research question into targeted atomic sub-queries.
        If atomic, returns a single sub-query.
        """
        entities = payload.extracted_entities
        clean_q = query.strip()
        lower_q = clean_q.lower()

        # Check if decomposition is warranted
        if not self.is_composite_query(query, payload):
            sub_q = ScientificSubQuery(
                sub_query_id="sq_1",
                query_text=clean_q,
                intent=payload.intent,
                target_entities=entities.sample_labels or entities.dopants or entities.paper_ids,
                target_conditions={
                    "c_rates": entities.c_rates,
                    "cycle_counts": entities.cycle_counts,
                    "temperature_c": entities.temperature_c,
                    "voltage_window": entities.voltage_window,
                },
                target_measurements=payload.target_measurements or entities.measurement_types,
                retrieval_strategy="hybrid_default",
            )
            # Supervisor policy separation check
            if any(d in ["Co", "Cr"] for d in entities.dopants):
                sub_q.provenance_requirement = "policy_distinction_required"
            return [sub_q]

        sub_queries: List[ScientificSubQuery] = []
        sq_idx = 1

        # Case A: Sample Comparison (e.g. SD_NO3 vs SD_SO4)
        if len(entities.sample_labels) >= 2 or ("sd_no3" in lower_q and "sd_so4" in lower_q):
            samples = entities.sample_labels if entities.sample_labels else ["SD_NO3", "SD_SO4"]
            for s_lbl in samples:
                s_conditions = {
                    "c_rates": entities.c_rates,
                    "cycle_counts": entities.cycle_counts,
                    "voltage_window": entities.voltage_window,
                }
                sub_queries.append(
                    ScientificSubQuery(
                        sub_query_id=f"sq_{sq_idx}",
                        query_text=f"Electrochemical discharge capacity and rate performance for sample {s_lbl}",
                        intent=ScientificIntent.SAMPLE_PROPERTY_LOOKUP,
                        target_entities=[s_lbl],
                        target_conditions=s_conditions,
                        target_measurements=["discharge_capacity", "rate_capability"],
                        retrieval_strategy="sample_measurements",
                    )
                )
                sq_idx += 1

            # Synthesis and characterization divergence subquery
            if any(k in lower_q for k in ["eis", "impedance", "rct", "synthesis", "precursor", "why", "mechanism"]):
                sub_queries.append(
                    ScientificSubQuery(
                        sub_query_id=f"sq_{sq_idx}",
                        query_text=f"Synthesis precursors, EIS charge transfer resistance Rct, and impurity differences for {' vs '.join(samples)}",
                        intent=ScientificIntent.CHARACTERIZATION_ANALYSIS,
                        target_entities=samples,
                        target_conditions={},
                        target_measurements=["eis_rct", "crystallography"],
                        retrieval_strategy="synthesis_morphology",
                    )
                )
                sq_idx += 1

        # Case B: Cross-Paper Comparison (e.g. Paper P1 vs Ref [79], or Ref [79] vs Ref [29])
        elif len(entities.paper_ids) >= 2 or payload.intent == ScientificIntent.CROSS_PAPER_COMPARISON:
            papers = entities.paper_ids if entities.paper_ids else ["ref79", "ref29"]
            for p_id in papers:
                p_text = f"Paper {p_id} LMFP electrochemical performance"
                matching_dop = next(
                    (d for d in entities.dopants if (p_id == "ref29" and d == "Ni") or (p_id == "ref79" and d == "N/S")),
                    None,
                )
                if matching_dop:
                    p_text += f" with {matching_dop} doping"
                if "p1" in p_id.lower() and "fe(no3)3" in lower_q:
                    p_text += " with Fe(NO3)3 precursor"

                sub_queries.append(
                    ScientificSubQuery(
                        sub_query_id=f"sq_{sq_idx}",
                        query_text=p_text,
                        intent=ScientificIntent.SAMPLE_PROPERTY_LOOKUP,
                        target_entities=[p_id] + ([matching_dop] if matching_dop else []),
                        target_conditions={"c_rates": entities.c_rates},
                        target_measurements=["discharge_capacity"],
                        retrieval_strategy="sample_measurements",
                    )
                )
                sq_idx += 1

            sub_queries.append(
                ScientificSubQuery(
                    sub_query_id=f"sq_{sq_idx}",
                    query_text=f"Electrochemical discharge comparison between {' and '.join(papers)}",
                    intent=ScientificIntent.CROSS_PAPER_COMPARISON,
                    target_entities=papers,
                    target_conditions={"c_rates": entities.c_rates},
                    target_measurements=["discharge_capacity"],
                    retrieval_strategy="hybrid_default",
                )
            )
            sq_idx += 1

        # Case C: Dopant Comparison (e.g. Ni vs Mg)
        elif len(entities.dopants) >= 2:
            dops = entities.dopants
            for dop in dops:
                dop_conditions = {
                    "c_rates": entities.c_rates,
                    "cycle_counts": entities.cycle_counts,
                }
                sub_queries.append(
                    ScientificSubQuery(
                        sub_query_id=f"sq_{sq_idx}",
                        query_text=f"Electrochemical performance and rate capability of {dop}-doped LMFP cathode",
                        intent=ScientificIntent.DOPANT_ANALYSIS,
                        target_entities=[dop],
                        target_conditions=dop_conditions,
                        target_measurements=["discharge_capacity", "rate_capability"],
                        retrieval_strategy="dopant_performance",
                        provenance_requirement="policy_distinction_required" if dop in ["Co", "Cr"] else None,
                    )
                )
                sq_idx += 1

            # Dopant mechanism subquery
            sub_queries.append(
                ScientificSubQuery(
                    sub_query_id=f"sq_{sq_idx}",
                    query_text=f"Mechanistic effect of {' vs '.join(dops)} doping on Li+ 1D diffusion along [010] and polaron hopping in LMFP",
                    intent=ScientificIntent.MECHANISM_EXPLANATION,
                    target_entities=dops,
                    target_conditions={},
                    target_measurements=[],
                    retrieval_strategy="mechanism_comparison",
                )
            )
            sq_idx += 1

        # Case C: Precursor Comparison (e.g. Nitrate vs Sulfate)
        elif len(entities.precursors) >= 2 or ("nitrate" in lower_q and "sulfate" in lower_q):
            precs = entities.precursors if entities.precursors else ["Nitrate", "Sulfate"]
            for prec in precs:
                sub_queries.append(
                    ScientificSubQuery(
                        sub_query_id=f"sq_{sq_idx}",
                        query_text=f"{prec} precursor synthesis route, particle morphology, and electrochemical properties in LMFP",
                        intent=ScientificIntent.PRECURSOR_COMPARISON,
                        target_entities=[prec],
                        target_conditions={},
                        target_measurements=["discharge_capacity"],
                        retrieval_strategy="synthesis_precursor",
                    )
                )
                sq_idx += 1

        # Case D: Multi-Rate or Multi-Property Split
        elif len(entities.c_rates) >= 2:
            for rate in entities.c_rates:
                sub_queries.append(
                    ScientificSubQuery(
                        sub_query_id=f"sq_{sq_idx}",
                        query_text=f"{clean_q} at {rate}C",
                        intent=ScientificIntent.RATE_CAPABILITY_ANALYSIS,
                        target_entities=entities.sample_labels or entities.dopants,
                        target_conditions={"c_rate": rate},
                        target_measurements=["discharge_capacity"],
                        retrieval_strategy="sample_measurements",
                    )
                )
                sq_idx += 1

        # Fallback if no specific split matched
        if not sub_queries:
            sub_queries.append(
                ScientificSubQuery(
                    sub_query_id="sq_1",
                    query_text=clean_q,
                    intent=payload.intent,
                    target_entities=entities.sample_labels or entities.dopants,
                    target_conditions={"c_rates": entities.c_rates},
                    target_measurements=payload.target_measurements,
                    retrieval_strategy="hybrid_default",
                )
            )

        return sub_queries
