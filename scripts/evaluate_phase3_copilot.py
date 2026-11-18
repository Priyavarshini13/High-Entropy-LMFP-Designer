"""
Comprehensive Evaluation Harness for Stage 5 Phase 3:
Evaluates all 62 questions across 8 categories:
1. Single-Paper Numerical & Condition-Bound Questions
2. Multi-Paper Comparative Questions
3. Complex Multi-Part & Composite Questions
4. Multi-Turn Conversational Follow-Up Questions
5. Condition-Sensitive & Parity Disagreement Questions
6. Provenance & Secondary Citation Handling
7. Negative Controls, Missing Evidence & Abstention
8. Dynamic Generalization to Unseen / Uploaded Papers
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from copilot.engine import LMFPResearchCopilot
from copilot.llm_client import check_ollama_status

BENCHMARK_FILE = WORKSPACE_ROOT / "tests" / "phase3_eval_benchmark.json"
RESULTS_FILE = WORKSPACE_ROOT / "scripts" / "phase3_eval_results.json"


def evaluate_phase3_benchmark(force_deterministic: bool = True):
    assert BENCHMARK_FILE.exists(), f"Benchmark file missing: {BENCHMARK_FILE}"
    with open(BENCHMARK_FILE, "r", encoding="utf-8") as f:
        questions = json.load(f)

    copilot = LMFPResearchCopilot()
    ollama_available = check_ollama_status()
    print("=" * 75)
    print("STAGE 5 PHASE 3: COMPREHENSIVE 62-QUESTION SCIENTIFIC BENCHMARK EVALUATION")
    print(f"Total Benchmark Questions: {len(questions)}")
    print(f"Execution Mode: {'Deterministic Fallback Engine' if force_deterministic else 'Hybrid (Qwen3-4B + Fallback)'}")
    print(f"Ollama Online: {ollama_available}")
    print("=" * 75)

    category_stats: Dict[str, Dict[str, int]] = {}
    detailed_results: List[Dict[str, Any]] = []

    total_concept_correct = 0
    total_numerical_correct = 0
    total_numerical_checked = 0
    total_prohibited_clean = 0
    total_citations_valid = 0
    total_abstention_correct = 0
    total_abstention_checked = 0
    total_sample_id_correct = 0
    total_sample_id_checked = 0

    for idx, q in enumerate(questions, start=1):
        q_id = q["id"]
        cat = q["category"]
        if cat not in category_stats:
            category_stats[cat] = {"total": 0, "passed": 0}
        category_stats[cat]["total"] += 1

        history = None
        if q.get("turn_1_question"):
            t1 = q["turn_1_question"]
            history = [
                {"role": "user", "content": t1},
                {"role": "assistant", "content": f"Grounded discussion regarding {t1}."},
            ]

        res = copilot.chat(
            query=q["question"],
            recent_history=history,
            force_deterministic=force_deterministic,
        )

        resp_full = f"{res.response} {res.direct_answer} {res.explanation}".lower()

        # 1. Concept match
        req_concepts = q.get("required_concepts", [])
        matched_concepts = [c for c in req_concepts if c.lower() in resp_full]
        min_required = min(len(req_concepts), 2) if req_concepts else 0
        concept_ok = len(matched_concepts) >= min_required
        if concept_ok:
            total_concept_correct += 1

        # 2. Prohibited claims
        prohibited = q.get("prohibited_claims", [])
        prohibited_present = [p for p in prohibited if p.lower() in resp_full]
        prohibited_clean = len(prohibited_present) == 0
        if prohibited_clean:
            total_prohibited_clean += 1

        # 3. Numerical accuracy & condition preservation
        num_cond = q.get("expected_numerical_conditions")
        num_ok = True
        if num_cond:
            total_numerical_checked += 1
            # Check numbers in response
            for k, val in num_cond.items():
                if isinstance(val, (int, float)):
                    val_str = str(val)
                    if val_str.endswith(".0"):
                        val_str_alt = val_str[:-2]
                    else:
                        val_str_alt = val_str
                    if val_str not in resp_full and val_str_alt not in resp_full:
                        # Check in structured sample profiles
                        found_in_profiles = False
                        if res.sample_profiles:
                            for sp in res.sample_profiles:
                                for m in sp.get("measurements", []):
                                    if m.get("value") == val or m.get("c_rate") == val or m.get("cycle_count") == val:
                                        found_in_profiles = True
                                        break
                        if not found_in_profiles:
                            num_ok = False
                            break
            if num_ok:
                total_numerical_correct += 1

        # 4. Sample ID accuracy
        sample_lbl = q.get("expected_sample_label")
        sample_ok = True
        if sample_lbl:
            total_sample_id_checked += 1
            sample_ok = sample_lbl.lower() in resp_full or (
                res.context_state and any(sample_lbl.lower() in s.lower() for s in res.context_state.get("active_sample_labels", []))
            )
            if sample_ok:
                total_sample_id_correct += 1

        # 5. Abstention accuracy
        is_abstention_q = cat == "abstention_negative_control"
        abstention_ok = True
        if is_abstention_q:
            total_abstention_checked += 1
            abstention_ok = (
                res.inference_source == "out_of_scope_abstention"
                or "does not contain" in resp_full
                or "insufficient evidence" in resp_full
            )
            if abstention_ok:
                total_abstention_correct += 1

        # 6. Citations
        citations_ok = len(res.citations) > 0 or res.inference_source in {"out_of_scope_abstention", "conversational_context_disambiguation"}
        if citations_ok:
            total_citations_valid += 1

        # Overall question pass
        overall_pass = concept_ok and prohibited_clean and num_ok and sample_ok and abstention_ok
        if overall_pass:
            category_stats[cat]["passed"] += 1

        detailed_results.append({
            "id": q_id,
            "category": cat,
            "question": q["question"],
            "passed": overall_pass,
            "concept_ok": concept_ok,
            "matched_concepts": matched_concepts,
            "missing_concepts": [c for c in req_concepts if c.lower() not in resp_full],
            "prohibited_clean": prohibited_clean,
            "numerical_ok": num_ok,
            "sample_id_ok": sample_ok,
            "abstention_ok": abstention_ok,
            "inference_source": res.inference_source,
            "citations_count": len(res.citations),
            "direct_answer_snippet": res.direct_answer[:120] if res.direct_answer else "",
        })

    # Summary Metrics
    print("\n" + "-" * 75)
    print("CATEGORY PERFORMANCE BREAKDOWN:")
    print("-" * 75)
    total_passed = 0
    total_qs = len(questions)
    for cat, stats in category_stats.items():
        pct = (stats["passed"] / stats["total"]) * 100.0 if stats["total"] > 0 else 0.0
        total_passed += stats["passed"]
        cat_name = cat.replace("_", " ").title()
        print(f"  {cat_name:<45}: {stats['passed']:>2}/{stats['total']:<2} ({pct:>5.1f}%)")

    overall_accuracy = (total_passed / total_qs) * 100.0
    concept_acc = (total_concept_correct / total_qs) * 100.0
    num_acc = (total_numerical_correct / total_numerical_checked) * 100.0 if total_numerical_checked > 0 else 100.0
    sample_acc = (total_sample_id_correct / total_sample_id_checked) * 100.0 if total_sample_id_checked > 0 else 100.0
    abstention_acc = (total_abstention_correct / total_abstention_checked) * 100.0 if total_abstention_checked > 0 else 100.0

    print("-" * 75)
    print("KEY SCIENTIFIC PERFORMANCE METRICS:")
    print(f"  Overall Benchmark Accuracy:      {overall_accuracy:.1f}% ({total_passed}/{total_qs})")
    print(f"  Concept & Factual Grounding:     {concept_acc:.1f}% ({total_concept_correct}/{total_qs})")
    print(f"  Numerical Condition Precision:   {num_acc:.1f}% ({total_numerical_correct}/{total_numerical_checked})")
    print(f"  Sample Identity Fidelity:        {sample_acc:.1f}% ({total_sample_id_correct}/{total_sample_id_checked})")
    print(f"  Abstention / Negative Control:   {abstention_acc:.1f}% ({total_abstention_correct}/{total_abstention_checked})")
    print(f"  Prohibited Claim Freedom:        {(total_prohibited_clean/total_qs)*100.0:.1f}% ({total_prohibited_clean}/{total_qs})")
    print(f"  Citation Verification Rate:      {(total_citations_valid/total_qs)*100.0:.1f}% ({total_citations_valid}/{total_qs})")
    print("=" * 75)

    # Save to JSON
    report = {
        "benchmark_total": total_qs,
        "benchmark_passed": total_passed,
        "overall_accuracy_percent": round(overall_accuracy, 2),
        "concept_accuracy_percent": round(concept_acc, 2),
        "numerical_precision_percent": round(num_acc, 2),
        "sample_id_fidelity_percent": round(sample_acc, 2),
        "abstention_accuracy_percent": round(abstention_acc, 2),
        "prohibited_claim_freedom_percent": round((total_prohibited_clean / total_qs) * 100.0, 2),
        "citation_verification_rate_percent": round((total_citations_valid / total_qs) * 100.0, 2),
        "category_breakdown": category_stats,
        "detailed_results": detailed_results,
    }
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"Detailed evaluation report written to {RESULTS_FILE}")

    return overall_accuracy >= 90.0


if __name__ == "__main__":
    success = evaluate_phase3_benchmark(force_deterministic=True)
    sys.exit(0 if success else 1)
