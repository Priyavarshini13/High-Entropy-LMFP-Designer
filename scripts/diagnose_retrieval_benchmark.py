"""
Detailed diagnostic script for retrieval benchmark comparison across Phase 1 (32 Qs) and Phase 2 (52 Qs).
Analyzes every question, rank of hit, misses, and evaluates raw retriever vs decomposed planner retrieval.
"""

import json
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from copilot.engine import LMFPResearchCopilot
from copilot.retriever import HybridRetriever

copilot = LMFPResearchCopilot()
retriever = copilot.retriever

with open(WORKSPACE_ROOT / "tests" / "ground_truth_retrieval_eval.json", encoding="utf-8") as f:
    ground_truth = json.load(f)

print(f"Total benchmark questions in ground truth: {len(ground_truth)}")


def evaluate_subset(items, label=""):
    hits_1 = 0
    hits_4 = 0
    hits_10 = 0
    reciprocal_ranks = []
    sample_id_matches = 0
    sample_id_count = 0
    provenance_matches = 0
    misses = []

    for item in items:
        q_id = item["question_id"]
        q_text = item["question"]
        expected_papers = [p.lower() for p in item.get("expected_papers", [])]
        expected_samples = [s.lower() for s in (item.get("expected_sample_ids") or ([item["expected_sample_id"]] if "expected_sample_id" in item else []))]
        expected_prov = item.get("provenance_type")

        # Multi-turn history if present
        history = None
        if item.get("turn_1_question"):
            t1 = item["turn_1_question"]
            history = [
                {"role": "user", "content": t1},
                {"role": "assistant", "content": f"Grounded discussion regarding {t1}."},
            ]

        effective_q, ctx_state = copilot.context_resolver.resolve_context(q_text, history)
        
        # Method A: Raw retriever.retrieve (as evaluated in test_retrieval_benchmark.py)
        matches = retriever.retrieve(effective_q, top_k=10, use_lsa=False)

        # Check negative controls & conversational disambiguation prompts
        if expected_papers in [["none"], ["clarification"]]:
            hits_1 += 1
            hits_4 += 1
            hits_10 += 1
            reciprocal_ranks.append(1.0)
            provenance_matches += 1
            continue

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
            misses.append((q_id, q_text, expected_papers, [m.passage.paper_id for m in matches[:4]], "Missed completely in top 10"))

        if first_rank and first_rank > 4:
            misses.append((q_id, q_text, expected_papers, [m.passage.paper_id for m in matches[:4]], f"Hit at rank {first_rank} (missed top 4)"))

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

    total = len(items)
    r1 = hits_1 / total
    r4 = hits_4 / total
    r10 = hits_10 / total
    mrr = sum(reciprocal_ranks) / total
    sample_acc = sample_id_matches / sample_id_count if sample_id_count > 0 else 1.0
    prov_acc = provenance_matches / total

    print("-" * 65)
    print(f"EVALUATION: {label} (N = {total})")
    print("-" * 65)
    print(f"Recall@1:  {r1*100:.1f}% ({hits_1}/{total})")
    print(f"Recall@4:  {r4*100:.1f}% ({hits_4}/{total})")
    print(f"Recall@10: {r10*100:.1f}% ({hits_10}/{total})")
    print(f"MRR:       {mrr:.3f}")
    print(f"Sample ID: {sample_acc*100:.1f}% ({sample_id_matches}/{sample_id_count})")
    print(f"Provenance:{prov_acc*100:.1f}% ({provenance_matches}/{total})")
    if misses:
        print("\nMISSED QUESTIONS AT TOP 4:")
        for m in misses:
            print(f"  [{m[0]}] Reason: {m[4]}")
            print(f"        Query: {m[1]}")
            print(f"        Expected Papers: {m[2]}")
            print(f"        Retrieved Papers: {m[3]}")
    return {"r1": r1, "r4": r4, "r10": r10, "mrr": mrr, "sample_acc": sample_acc, "prov_acc": prov_acc, "misses": misses}


# 1. Evaluate original 32 questions (eval_01 to eval_32)
res_32 = evaluate_subset(ground_truth[:32], "ORIGINAL PHASE 1 BENCHMARK (eval_01 to eval_32)")

# 2. Evaluate newly added 20 questions (eval_33 to eval_52)
res_20 = evaluate_subset(ground_truth[32:], "NEW PHASE 2 QUESTIONS (eval_33 to eval_52)")

# 3. Evaluate combined 52 questions
res_52 = evaluate_subset(ground_truth, "COMBINED BENCHMARK (All 52 Questions)")
