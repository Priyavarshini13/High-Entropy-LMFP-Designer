"""
Stage 5 Phase 3 Final Validation: Step 1
Comparative Evaluation of Qwen3-4B vs Deterministic Synthesis Fallback

Tests 6 representative scientific questions:
1. Single-sample capacity & rate capability
2. Direct sample-to-sample comparison
3. Precursor salt & phase purity synthesis inquiry
4. Olivine crystallographic & kinetic mechanism inquiry
5. Stateful multi-turn condition follow-up
6. Non-LMFP out-of-scope inquiry (abstention)
"""

import sys
import time
import json
from pathlib import Path

# Ensure UTF-8 output encoding on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from copilot.engine import LMFPResearchCopilot
from copilot.llm_client import check_ollama_status


def run_comparative_validation():
    print("=" * 80)
    print("STAGE 5 PHASE 3: QWEN3-4B VS DETERMINISTIC FALLBACK VALIDATION")
    print("=" * 80)

    # 1. Verify Ollama connectivity
    ollama_ok = check_ollama_status(timeout_s=3.0)
    print(f"Ollama Service Status: {'ONLINE' if ollama_ok else 'OFFLINE'}")
    if not ollama_ok:
        print("ERROR: Ollama is not accessible on localhost:11434. Check port or sandbox bypass.")
        return

    copilot = LMFPResearchCopilot()

    test_cases = [
        {
            "id": "Q1_SAMPLE_NUMERICAL",
            "category": "Single Sample Numerical",
            "query": "What is the 0.05C discharge capacity of sample SD_NO3 in srep26686?",
            "history": None,
            "expected_value": "45.0",
            "expected_unit": "mAh/g",
            "expected_paper": "srep26686",
            "expected_sample": "SD_NO3",
        },
        {
            "id": "Q2_COMPARATIVE",
            "category": "Sample Comparison",
            "query": "Compare the discharge capacity of SD_SO4 and SD_NO3 at 0.05C and high rates.",
            "history": None,
            "expected_value": "114",
            "expected_unit": "mAh/g",
            "expected_paper": "srep26686",
            "expected_sample": "SD_SO4",
        },
        {
            "id": "Q3_SYNTHESIS_PRECURSOR",
            "category": "Synthesis & Impurity Mechanism",
            "query": "How does the iron nitrate precursor affect the phase purity of LMFP compared to iron sulfate in srep26686?",
            "history": None,
            "expected_value": "Fe2O3",
            "expected_unit": "impurity",
            "expected_paper": "srep26686",
            "expected_sample": "SD_NO3",
        },
        {
            "id": "Q4_CRYSTALLOGRAPHIC_MECHANISM",
            "category": "Crystallographic Mechanism",
            "query": "What crystallographic mechanism explains the improved rate capability and stability of olivine LMFP?",
            "history": None,
            "expected_value": "Pnma",
            "expected_unit": "diffusion",
            "expected_paper": "Literature",
            "expected_sample": "LMFP",
        },
        {
            "id": "Q5_STATEFUL_FOLLOWUP",
            "category": "Multi-turn Condition Follow-up",
            "query": "What is its capacity at 10C and what was the voltage window?",
            "history": [
                {"role": "user", "content": "What is the discharge capacity of SD_SO4 in srep26686?"},
                {"role": "assistant", "content": "Sample SD_SO4 delivered 114.0 mAh/g at 0.05C in srep26686."},
            ],
            "expected_value": "73",
            "expected_unit": "mAh/g",
            "expected_paper": "srep26686",
            "expected_sample": "SD_SO4",
        },
        {
            "id": "Q6_OUT_OF_SCOPE",
            "category": "Abstention Guardrail",
            "query": "What is the cycling performance of nickel-rich NMC811 synthesized by dry battery electrode technology?",
            "history": None,
            "expected_value": "abstain",
            "expected_unit": "out_of_scope",
            "expected_paper": "None",
            "expected_sample": "NMC811",
        },
    ]

    results = []

    for tc in test_cases:
        qid = tc["id"]
        query = tc["query"]
        history = tc["history"]
        print(f"\n--- Testing {qid}: '{query[:65]}...' ---")

        # Run with Qwen3-4B (force_deterministic=False)
        print("  Executing Qwen3-4B...")
        t0 = time.perf_counter()
        res_qwen = copilot.chat(
            query=query,
            recent_history=history,
            force_deterministic=False,
        )
        t_qwen = time.perf_counter() - t0

        # Run with Deterministic Synthesis Fallback (force_deterministic=True)
        print("  Executing Deterministic Synthesis Fallback...")
        t0 = time.perf_counter()
        res_det = copilot.chat(
            query=query,
            recent_history=history,
            force_deterministic=True,
        )
        t_det = time.perf_counter() - t0

        # Evaluate Qwen results
        qwen_src = res_qwen.inference_source
        qwen_ans = res_qwen.direct_answer
        qwen_cits = res_qwen.citations
        qwen_passages_count = len(res_qwen.sourced_facts)

        # Evaluate Fallback results
        det_src = res_det.inference_source
        det_ans = res_det.direct_answer
        det_cits = res_det.citations
        det_passages_count = len(res_det.sourced_facts)

        print(f"  [Qwen] Time: {t_qwen:.2f}s | Source: {qwen_src} | Citations: {len(qwen_cits)}")
        print(f"  [Qwen] Direct Answer: {qwen_ans[:120]}...")
        print(f"  [Det]  Time: {t_det:.2f}s | Source: {det_src} | Citations: {len(det_cits)}")
        print(f"  [Det]  Direct Answer: {det_ans[:120]}...")

        results.append({
            "test_id": qid,
            "category": tc["category"],
            "query": query,
            "has_history": bool(history),
            "expected": {
                "value": tc["expected_value"],
                "unit": tc["expected_unit"],
                "paper": tc["expected_paper"],
                "sample": tc["expected_sample"],
            },
            "qwen": {
                "duration_seconds": round(t_qwen, 3),
                "inference_source": qwen_src,
                "direct_answer": qwen_ans,
                "explanation_snippet": res_qwen.explanation[:250],
                "citation_count": len(qwen_cits),
                "citations": qwen_cits,
                "sourced_facts_count": qwen_passages_count,
                "conflicts_and_limitations": res_qwen.conflicts_and_limitations,
            },
            "deterministic_fallback": {
                "duration_seconds": round(t_det, 3),
                "inference_source": det_src,
                "direct_answer": det_ans,
                "explanation_snippet": res_det.explanation[:250],
                "citation_count": len(det_cits),
                "citations": det_cits,
                "sourced_facts_count": det_passages_count,
                "conflicts_and_limitations": res_det.conflicts_and_limitations,
            },
        })

    out_path = PROJECT_ROOT / "scripts" / "qwen_vs_fallback_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n[OK] Comparative validation complete. Saved to {out_path}")


if __name__ == "__main__":
    run_comparative_validation()
