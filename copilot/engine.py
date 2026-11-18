"""Core orchestration engine for the LMFP Research Copilot."""

import os
import dataclasses
import re
from typing import Any, Dict, List, Optional

from copilot.context_resolver import ConversationContextResolver
from copilot.evidence_organizer import EvidenceOrganizer
from copilot.evidence_sufficiency import EvidenceSufficiencyEvaluator
from copilot.grounding import (
    DynamicScientificSynthesizer,
    audit_citations_and_claims,
    build_comparison_table_from_matches,
    build_scientific_system_prompt,
    format_evidence_passages_for_prompt,
    synthesize_deterministic_scientific_answer,
)
from copilot.intent_classifier import ScientificIntentClassifier
from copilot.llm_client import call_qwen_model, check_ollama_status, strip_internal_reasoning
from copilot.models import (
    ConversationContextState,
    CopilotResponseData,
    EvidenceSufficiencyReport,
    RetrievalMatch,
    RetrievalPlan,
    ScientificIntent,
    ScientificIntentPayload,
    ScientificSubQuery,
    StructuredSampleProfile,
    is_synthetic_test_record,
)
from copilot.query_decomposer import ScientificQueryDecomposer
from copilot.retrieval_planner import RetrievalPlanner
from copilot.retriever import HybridRetriever


class LMFPResearchCopilot:
    """Novyte AI-grade specialized scientific research assistant for LMFP cathode materials."""

    def __init__(
        self,
        retriever: Optional[HybridRetriever] = None,
        classifier: Optional[ScientificIntentClassifier] = None,
        context_resolver: Optional[ConversationContextResolver] = None,
        decomposer: Optional[ScientificQueryDecomposer] = None,
        planner: Optional[RetrievalPlanner] = None,
        sufficiency_evaluator: Optional[EvidenceSufficiencyEvaluator] = None,
        organizer: Optional[EvidenceOrganizer] = None,
        synthesizer: Optional[DynamicScientificSynthesizer] = None,
    ):
        self.retriever = retriever or HybridRetriever()
        self.classifier = classifier or ScientificIntentClassifier()
        self.context_resolver = context_resolver or ConversationContextResolver(self.classifier)
        self.decomposer = decomposer or ScientificQueryDecomposer()
        self.planner = planner or RetrievalPlanner(self.retriever)
        self.sufficiency_evaluator = sufficiency_evaluator or EvidenceSufficiencyEvaluator()
        self.organizer = organizer or EvidenceOrganizer()
        self.synthesizer = synthesizer or DynamicScientificSynthesizer(self.organizer)

    def resolve_followup_context(
        self,
        current_query: str,
        recent_history: Optional[List[Dict[str, Any]]],
    ) -> str:
        """Backward-compatible helper: resolve pronouns and conversational continuity."""
        effective_query, _ = self.context_resolver.resolve_context(current_query, recent_history)
        return effective_query

    def chat(
        self,
        query: str,
        current_composition: Optional[Dict[str, Any]] = None,
        recent_history: Optional[List[Dict[str, Any]]] = None,
        force_deterministic: bool = False,
    ) -> CopilotResponseData:
        """
        Process a scientific research question through intent routing, context resolution,
        decomposition, retrieval planning, evidence sufficiency evaluation, and grounded synthesis.
        """
        # Step 1: Stateful Multi-Turn Context Resolution
        effective_query, context_state = self.context_resolver.resolve_context(
            current_query=query,
            recent_history=recent_history,
            current_composition=current_composition,
        )

        # Step 2: Scientific Intent Classification & Entity Extraction
        intent_payload = self.classifier.classify_intent(
            query=effective_query,
            conversation_turn=context_state.turn_count,
        )

        # Handle referent ambiguity if flagged
        if context_state.requires_clarification and context_state.clarification_prompt:
            return CopilotResponseData(
                response=f"🔍 **Clarification Needed**:\n\n{context_state.clarification_prompt}",
                direct_answer=context_state.clarification_prompt,
                explanation=(
                    "Multiple candidate materials or samples are currently active in context. "
                    "Please specify which candidate you would like to analyze."
                ),
                comparison_table=None,
                sourced_facts=[],
                engine_facts=[],
                citations=[],
                conflicts_and_limitations="Antecedent ambiguity: multiple active referents in conversation history.",
                inference_source="conversational_context_disambiguation",
                context_state=dataclasses.asdict(context_state),
                intent_payload=dataclasses.asdict(intent_payload),
            )

        # Step 3: Scientific Query Decomposition
        sub_queries: List[ScientificSubQuery] = self.decomposer.decompose(
            query=effective_query,
            payload=intent_payload,
            context_state=context_state,
        )

        # Step 4: Intent-Driven Retrieval Planning
        retrieval_plan: RetrievalPlan = self.planner.build_plan(
            query=effective_query,
            payload=intent_payload,
            sub_queries=sub_queries,
            context_state=context_state,
        )

        # Step 5: Handle Out-of-Scope / Non-LMFP Inquiries
        if retrieval_plan.is_out_of_scope:
            report = self.sufficiency_evaluator.evaluate(retrieval_plan, [], context_state)
            abstain_answer = (
                f"The literature database does not contain experimental evidence for the requested topic ({query}). "
                "Values are not reported for this system in the verified LMFP repository."
            )
            abstain_expl = (
                "HE-LMFP-Designer specializes strictly in Lithium Manganese Iron Phosphate cathode materials. "
                f"{retrieval_plan.abstention_reason or ''} "
                "There is insufficient evidence in the verified literature repository, and values are not reported for this system."
            )
            return CopilotResponseData(
                response=f"### 🔬 LMFP Scientific Evidence Summary\n\n**Direct Answer**:\n{abstain_answer}\n\n**Scientific Explanation**:\n{abstain_expl}\n",
                direct_answer=abstain_answer,
                explanation=abstain_expl,
                comparison_table=None,
                sourced_facts=[],
                engine_facts=[],
                citations=[],
                conflicts_and_limitations=report.limitation_notes,
                inference_source="out_of_scope_abstention",
                context_state=dataclasses.asdict(context_state),
                intent_payload=dataclasses.asdict(intent_payload),
                retrieval_plan=dataclasses.asdict(retrieval_plan),
                sufficiency_report=dataclasses.asdict(report),
            )

        # Step 6: Plan Execution (BM25 + Entity + Structured without LSA by default)
        raw_matches: List[RetrievalMatch] = self.planner.execute_plan(
            plan=retrieval_plan,
            top_k_per_subquery=4,
            max_total_matches=12,
        )
        # Exclude any synthetic test fixtures from research copilot processing
        matches = [
            m for m in raw_matches
            if not is_synthetic_test_record(m.passage.paper_id, m.passage.sample_label or m.passage.sample_id, m.passage.text)
        ]

        # Step 6.5: Structured Evidence Aggregation & Profile Organization
        sample_profiles = self.organizer.organize_matches(matches)

        # Step 7: Pre-Generation Evidence Sufficiency & Parity Evaluation
        sufficiency_report: EvidenceSufficiencyReport = self.sufficiency_evaluator.evaluate(
            plan=retrieval_plan,
            matches=matches,
            context_state=context_state,
        )

        # Step 8: Multi-Turn Conversation History for LLM Prompting
        conversation_context_block = ""
        if recent_history:
            history_lines = ["RECENT CONVERSATION HISTORY:"]
            for h in recent_history[-4:]:
                r_role = h.get("role", "user").capitalize()
                r_txt = h.get("content") or h.get("text") or ""
                if r_txt:
                    history_lines.append(f"{r_role}: {r_txt[:250]}")
            conversation_context_block = "\n".join(history_lines) + "\n\n"

        # Step 9: Attempt Qwen3-4B generation if Ollama is available and not forced deterministic
        engine_mode = os.environ.get("COPILOT_ENGINE_MODE", "deterministic").lower()
        ollama_online = False if (force_deterministic or engine_mode == "deterministic") else check_ollama_status(timeout_s=1.0)
        llm_response = None
        inference_source = "deterministic_literature_rag"

        if ollama_online:
            try:
                system_prompt = build_scientific_system_prompt()
                profiles_block = self.organizer.format_profiles_for_prompt(sample_profiles)
                evidence_block = format_evidence_passages_for_prompt(matches[:4])
                policy_note = ""
                if sufficiency_report.policy_distinctions:
                    policy_note = f"\n\nPOLICY NOTICE: {sufficiency_report.policy_distinctions[0]}"

                prompt = (
                    f"{conversation_context_block}"
                    f"{profiles_block}\n\n"
                    f"{evidence_block}{policy_note}\n\n"
                    f"RESEARCH QUESTION: {effective_query}\n\n"
                    f"Be concise, scientifically rigorous, and direct.\n"
                    f"Provide an evidence-grounded response adhering strictly to the scientific rules above:"
                )
                llm_response = call_qwen_model(prompt=prompt, system_prompt=system_prompt, timeout_s=90.0)
                if llm_response:
                    inference_source = "qwen3:4b_grounded"
            except Exception as exc:
                print(f"[Copilot Engine] LLM generation error: {exc}")
                llm_response = None

        # Step 10: Dynamic Scientific Synthesis Engine
        comp_table = build_comparison_table_from_matches(matches)
        synth_data = self.synthesizer.synthesize(
            query=effective_query,
            matches=matches,
            profiles=sample_profiles,
            conversation_context=conversation_context_block,
            sufficiency_report=sufficiency_report,
            intent_payload=intent_payload,
        )

        # Combine limitation notes from sufficiency report into synth_data
        if sufficiency_report.limitation_notes:
            existing_limitations = synth_data.get("conflicts_and_limitations")
            if existing_limitations:
                synth_data["conflicts_and_limitations"] = (
                    f"{existing_limitations} · {sufficiency_report.limitation_notes}"
                )
            else:
                synth_data["conflicts_and_limitations"] = sufficiency_report.limitation_notes

        if llm_response:
            clean_llm = strip_internal_reasoning(llm_response)
            audited_text, valid_citations, audit_warnings = audit_citations_and_claims(
                clean_llm,
                matches,
                profiles=sample_profiles,
            )
            final_text = strip_internal_reasoning(audited_text)
            citations = valid_citations or synth_data["citations"]

            m_dir = re.search(
                r"(?:\(1\)\s*)?\*{0,2}Direct Answer\*{0,2}:?\s*\n*(.*?)(?=\n\n|\n(?:\([2-9]\)|\*{0,2}[A-Z]))",
                clean_llm,
                re.DOTALL | re.IGNORECASE,
            )
            if m_dir and len(m_dir.group(1).strip()) > 5:
                direct_ans = m_dir.group(1).strip()
            else:
                direct_ans = clean_llm.split("\n\n")[0].strip()

            m_expl = re.search(
                r"(?:\(2\)\s*)?\*{0,2}Scientific Explanation(?: & Mechanism)?\*{0,2}:?\s*\n*(.*?)(?=\n(?:\([3-9]\)|\*{0,2}[A-Z]))",
                clean_llm,
                re.DOTALL | re.IGNORECASE,
            )
            if m_expl and len(m_expl.group(1).strip()) > 5:
                explanation = m_expl.group(1).strip()
            else:
                explanation = clean_llm
        else:
            final_text_lines = [
                "### 🔬 LMFP Scientific Evidence Summary\n",
                f"**Direct Answer**:\n{synth_data['direct_answer']}\n",
                f"**Scientific Mechanisms & Explanation**:\n{synth_data['explanation']}\n",
            ]

            if comp_table:
                final_text_lines.append("**Experimental Condition & Property Comparison**:\n")
                final_text_lines.append(
                    "| Dopant / Composition | Category | Reported Capacity & C-rate | Cycling Retention & Conditions | Synthesis Method | Evidence Source | Limitations |"
                )
                final_text_lines.append("|:---|:---:|:---|:---|:---|:---|:---|")
                for r in comp_table:
                    dop_comp = r.get("dopant_composition") or f"**{r.get('dopant', 'Undoped')}** / `{r.get('composition', 'LMFP')}`"
                    cat = r.get("category") or "Single-Dopant"
                    rep_cap = r.get("reported_capacity") or r.get("capacity_0_1c") or "—"
                    ret = r.get("cycling_retention") or r.get("retention") or "—"
                    synth = r.get("synthesis") or "—"
                    ev_src = r.get("evidence_source") or f"[{r.get('paper_id', 'Record')}]"
                    lim = r.get("limitations") or "Experimental conditions diverge."
                    final_text_lines.append(
                        f"| {dop_comp} | {cat} | {rep_cap} | {ret} | {synth} | {ev_src} | {lim} |"
                    )
                final_text_lines.append("")

            if synth_data.get("conflicts_and_limitations"):
                final_text_lines.append(
                    f"⚠️ **Condition Differences & Limitations**:\n{synth_data['conflicts_and_limitations']}\n"
                )

            final_text = "\n".join(final_text_lines)
            citations = synth_data["citations"]
            direct_ans = synth_data["direct_answer"]
            explanation = synth_data["explanation"]

        predictions_note = None
        if sufficiency_report.is_recommendation_hypothesis:
            predictions_note = (
                "Theoretical Recommendation: Projections and mechanistic interpretations "
                "should be treated as scientific hypotheses subject to laboratory validation."
            )

        return CopilotResponseData(
            response=final_text,
            direct_answer=direct_ans,
            explanation=explanation,
            comparison_table=comp_table,
            sourced_facts=synth_data["sourced_facts"],
            engine_facts=synth_data["engine_facts"],
            citations=citations,
            conflicts_and_limitations=synth_data.get("conflicts_and_limitations"),
            inference_source=inference_source,
            predictions_note=predictions_note,
            context_state=dataclasses.asdict(context_state),
            intent_payload=dataclasses.asdict(intent_payload),
            retrieval_plan=dataclasses.asdict(retrieval_plan),
            sufficiency_report=dataclasses.asdict(sufficiency_report),
            sample_profiles=synth_data.get("sample_profiles"),
        )


# Global copilot instance
_COPILOT_INSTANCE: Optional[LMFPResearchCopilot] = None


def get_research_copilot() -> LMFPResearchCopilot:
    """Return the global LMFP Research Copilot engine instance."""
    global _COPILOT_INSTANCE
    if _COPILOT_INSTANCE is None:
        _COPILOT_INSTANCE = LMFPResearchCopilot()
    return _COPILOT_INSTANCE


def reload_copilot_index() -> LMFPResearchCopilot:
    """Reload the passage index and re-link the global copilot engine instance."""
    global _COPILOT_INSTANCE
    from copilot.index import reload_passage_index
    fresh_index = reload_passage_index()
    if _COPILOT_INSTANCE is not None:
        _COPILOT_INSTANCE.retriever = HybridRetriever(index=fresh_index)
        _COPILOT_INSTANCE.planner = RetrievalPlanner(_COPILOT_INSTANCE.retriever)
    return get_research_copilot()
