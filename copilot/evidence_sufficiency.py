"""
Evidence Sufficiency Evaluator for LMFP Research Copilot.

Validates pre-generation parity, condition completeness, missing comparison counterparts,
provenance boundaries, and supervisor policy distinctions.
"""

from typing import Any, Dict, List, Optional, Set

from copilot.models import (
    ConversationContextState,
    EvidencePassage,
    EvidenceSufficiencyReport,
    RetrievalMatch,
    RetrievalPlan,
    ScientificIntent,
)


class EvidenceSufficiencyEvaluator:
    """
    Evaluates evidence retrieved for a research question prior to LLM/deterministic generation.
    Enforces scientific publication standards, voltage window parity, and policy separation.
    """

    def evaluate(
        self,
        plan: RetrievalPlan,
        matches: List[RetrievalMatch],
        context_state: Optional[ConversationContextState] = None,
    ) -> EvidenceSufficiencyReport:
        """Evaluate retrieved matches against retrieval plan and return sufficiency report."""
        report = EvidenceSufficiencyReport()

        if plan.is_out_of_scope:
            report.is_sufficient = False
            report.is_comparable = False
            report.limitation_notes = plan.abstention_reason
            return report

        if not matches:
            report.is_sufficient = False
            report.is_comparable = False
            report.limitation_notes = (
                "No direct experimental literature evidence matching all specified criteria was found in the indexed database."
            )
            return report

        # 1. Counterpart Completeness in Comparisons
        if plan.requires_comparability_check:
            # Check target entities across subqueries
            target_entities: List[str] = []
            for sq in plan.sub_queries:
                for ent in sq.target_entities:
                    if ent not in target_entities:
                        target_entities.append(ent)

            if len(target_entities) >= 2:
                # Check which entities are actually represented in matches
                represented_entities: Set[str] = set()
                for m in matches:
                    p_text = (m.passage.text + " " + (m.passage.sample_label or "") + " " + (m.passage.composition or "")).lower()
                    for ent in target_entities:
                        if ent.lower() in p_text or (m.passage.sample_id and ent.lower() in m.passage.sample_id.lower()):
                            represented_entities.add(ent)

                for ent in target_entities:
                    if ent not in represented_entities:
                        report.missing_counterparts.append(ent)

                if report.missing_counterparts:
                    report.is_comparable = False
                    report.condition_parity = False
                    missing_str = ", ".join(report.missing_counterparts)
                    report.condition_divergences.append(
                        f"Incomplete comparison counterpart: Missing direct experimental data for [{missing_str}] under matching conditions."
                    )

        # 2. Voltage Window & Condition Parity
        voltage_windows_found: Set[str] = set()
        c_rates_found: Set[float] = set()
        for m in matches:
            # Check voltage window in structured data
            st = m.passage.structured_data
            vw = st.get("voltage_window") or st.get("voltage_range")
            if vw:
                voltage_windows_found.add(str(vw))
            cr = st.get("c_rate")
            if cr is not None:
                try:
                    c_rates_found.add(float(cr))
                except (ValueError, TypeError):
                    pass

        if len(voltage_windows_found) > 1:
            report.condition_parity = False
            report.condition_divergences.append(
                f"Divergent voltage windows across retrieved evidence: {', '.join(sorted(voltage_windows_found))}."
            )

        # 3. Provenance Parity and Warnings
        for m in matches:
            p = m.passage
            if p.provenance_type == "SECONDARY_REVIEW" or "review" in (p.source_type or "").lower():
                warn = f"Secondary review provenance in [{p.paper_id}]: verify primary experimental source"
                if warn not in report.provenance_warnings:
                    report.provenance_warnings.append(warn)
            if p.is_unresolved:
                warn = f"Sample [{p.sample_label or p.sample_id}] is currently marked unconfirmed/unresolved"
                if warn not in report.provenance_warnings:
                    report.provenance_warnings.append(warn)

        # 4. Supervisor Policy Separation
        if plan.requires_policy_separation:
            policy_msg = (
                "Supervisor Design Policy: Cobalt (Co) and Chromium (Cr) substitutions are prohibited "
                "by internal project guidelines due to commercial cost and environmental toxicity constraints, "
                "notwithstanding published literature demonstrating enhanced rate capability and electronic conductivity."
            )
            report.policy_distinctions.append(policy_msg)

        # 5. Recommendation / Hypothesis Labeling
        if plan.primary_intent in [
            ScientificIntent.RESEARCH_GAP_ANALYSIS,
            ScientificIntent.MECHANISM_EXPLANATION,
        ] or "recommend" in plan.original_query.lower() or "suggest" in plan.original_query.lower():
            report.is_recommendation_hypothesis = True

        # 6. Limitation Notes Construction
        limitation_parts: List[str] = []
        if report.missing_counterparts:
            limitation_parts.append(
                f"Missing direct literature counterpart for {', '.join(report.missing_counterparts)}."
            )
        if report.condition_divergences:
            limitation_parts.extend(report.condition_divergences)
        if report.provenance_warnings:
            limitation_parts.extend(report.provenance_warnings)
        if report.policy_distinctions:
            limitation_parts.extend(report.policy_distinctions)

        if limitation_parts:
            report.limitation_notes = " · ".join(limitation_parts)

        return report
