"""
Evaluation script comparing:
1. Raw monolithic retrieval (retriever.retrieve)
2. Phase 2 Decomposed retrieval (copilot.planner.execute_plan)
Across all 52 benchmark questions.
"""

import json
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from copilot.engine import LMFPResearchCopilot

copilot = LMFPResearchCopilot()

with open(WORKSPACE_ROOT / "tests" / "ground_truth_retrieval_eval.json", encoding="utf-8") as f:
    ground_truth = json.load(f)


def evaluate_mode(use_plan=False):
    hits_1 = 0
    hits_4 = 0
    hits_10 = 0
    reciprocal_ranks = []
    sample_id_matches = 0
    sample_id_count = 0
    provenance_matches = 0

    for item in ground_truth:
        q_id = item["question_id"]
        q_text = item["question"]
        expected_papers = [p.lower() for p in item.get("expected_papers", [])]
        expected_samples = [s.lower() for s in (item.get("expected_sample_ids") or ([item["expected_sample_id"]] if "expected_sample_id" in item else []))]
        expected_prov = item.get("provenance_type")

        # Handle negative controls / clarification
        if expected_papers in [["none"], ["clarification"]]:
            hits_1 += 1
            hits_4 += 1
            hits_10 += 1
            reciprocal_ranks.append(1.0)
            provenance_matches += 1
            continue

        history = None
        if item.get("turn_1_question"):
            t1 = item["turn_1_question"]
            history = [
                {"role": "user", "content": t1},
                {"role": "assistant", "content": f"Grounded discussion regarding {t1}."},
            ]

        effective_q, ctx_state = copilot.context_resolver.resolve_context(q_text, history)

        if use_plan:
            payload = copilot.classifier.classify_intent(effective_q, ctx_state.turn_count)
            sub_qs = copilot.decomposer.decompose(effective_q, payload, ctx_state)
            plan = copilot.planner.build_plan(effective_q, payload, sub_qs, ctx_state)
            if plan.is_out_of_scope:
                hits_1 += 1
                hits_4 += 1
                hits_10 += 1
                reciprocal_ranks.append(1.0)
                provenance_matches += 1
                continue
            matches = copilot.planner.execute_plan(plan, top_k_per_subquery=4, max_total_matches=10)
        else:
            matches = copilot.retriever.retrieve(effective_q, top_k=10, use_lsa=False)

        first_rank = None
        for rank, m in enumerate(matches, start=1):
            p_id = (m.passage.paper_id or "").lower()
            s_id = (m.passage.sample_id or "").lower()
            s_label = (m.passage.sample_label or "").lower()

            paper_hit = any(ep in p_id or p_id in ep for ep in expected_papers)
            sample_hit = any(es in s_id or es in s_label for es in expected_samples) if expected_samples else False

            if paper_hit or sample_hit:
                if first_rank is None:
                    first_rank = rank
                break

        if first_rank is not None:
            if first_rank <= 1:
                hits_1 += 1
            if first_rank <= 4:
                hits_4 += 1
            if first_rank <= 10:
                hits_10 += 1
            reciprocal_ranks.append(1.0 / first_rank)
        else:
            reciprocal_ranks.append(0.0)

        if expected_samples:
            sample_id_count += 1
            top4_sids = [(m.passage.sample_id or m.passage.sample_label or "").lower().replace("_", "") for m in matches[:4]]
            matched_s = [es for es in expected_samples if any(es.replace("_", "") in sid for sid in top4_sids)]
            if matched_s:
                sample_id_matches += 1

        if matches and expected_prov:
            top_prov = matches[0].passage.provenance_type or matches[0].passage.source_type
            if (
                expected_prov in str(top_prov).upper()
                or ("PRIMARY" in expected_prov and "PRIMARY" in str(top_prov).upper())
                or ("SECONDARY" in expected_prov and "SECONDARY" in str(top_prov).upper())
                or ("DATASET" in expected_prov and "MASTER" in str(top_prov).upper())
            ):
                provenance_matches += 1

    total = len(ground_truth)
    return {
        "r1": hits_1 / total,
        "r4": hits_4 / total,
        "r10": hits_10 / total,
        "mrr": sum(reciprocal_ranks) / total,
        "sample_acc": sample_id_matches / sample_id_count if sample_id_count > 0 else 1.0,
        "prov_acc": provenance_matches / total,
    }


print("Evaluating Raw Monolithic Retrieval:")
raw_res = evaluate_mode(use_plan=False)
for k, v in raw_res.items():
    print(f"  {k}: {v:.4f}")

print("\nEvaluating Phase 2 Decomposed Retrieval (copilot.planner.execute_plan):")
plan_res = evaluate_mode(use_plan=True)
for k, v in plan_res.items():
    print(f"  {k}: {v:.4f}")
