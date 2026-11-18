"""
In-Depth Audit Script for All 52 Scientific Benchmark Questions.
Inspects:
- Expected Category vs Predicted Intent
- Extracted Entities & Numerical Conditions
- Effective Query & Conversation Context State
- Decomposed Subqueries & Retrieval Plan
- Retrieved Matches (top 4 IDs, Paper IDs, Sample IDs, Ranks, Combined Scores)
- Evidence Sufficiency Decisions (Parity, Missing Counterparts, Policy Notes)
- Final Generated Answer, Citations, and Deterministic Branch Analysis
"""

import json
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from copilot.engine import LMFPResearchCopilot

copilot = LMFPResearchCopilot()

with open(WORKSPACE_ROOT / "tests" / "copilot_qa_eval.json", encoding="utf-8") as f:
    benchmarks = json.load(f)

print(f"Loaded {len(benchmarks)} questions from copilot_qa_eval.json")

audit_records = []

intent_correct = 0
entities_correct = 0
condition_correct = 0
sufficiency_correct = 0
answer_correct = 0

for item in benchmarks:
    q_id = item["id"]
    category = item.get("category", "")
    q_text = item["question"]
    expected_ans = item.get("expected_answer", "")
    req_concepts = item.get("required_concepts", [])
    prohibited_claims = item.get("prohibited_claims", [])
    req_conditions = item.get("required_numerical_conditions", {})

    history = None
    if item.get("turn_1_question"):
        t1 = item["turn_1_question"]
        history = [
            {"role": "user", "content": t1},
            {"role": "assistant", "content": f"Grounded discussion regarding {t1}."},
        ]

    # Process through Copilot
    res = copilot.chat(q_text, recent_history=history, force_deterministic=True)
    resp_text = (res.response + " " + (res.direct_answer or "") + " " + (res.explanation or "")).lower()

    # 1. Intent & Entities
    ctx = res.context_state or {}
    intent = res.intent_payload.get("intent") if res.intent_payload else None
    confidence = res.intent_payload.get("confidence") if res.intent_payload else 0.0
    extracted_entities = res.intent_payload.get("extracted_entities", {}) if res.intent_payload else {}

    # 2. Plan & Decomposed Subqueries
    plan = res.retrieval_plan or {}
    subqueries = plan.get("sub_queries", [])

    # 3. Sufficiency Report
    suff = res.sufficiency_report or {}

    # 4. Citations & Matches
    citations = res.citations or []
    top_matches = [
        f"{c.get('paper_id')} ({c.get('sample_label') or 'p. ' + str(c.get('page_number'))})"
        for c in citations[:4]
    ]

    # Concept verification
    matched_concepts = [c for c in req_concepts if c.lower() in resp_text]
    min_req = min(len(req_concepts), 2)
    has_concepts = len(matched_concepts) >= min_req

    # Prohibited claims verification
    has_prohibited = any(p.lower() in resp_text for p in prohibited_claims)
    ans_ok = has_concepts and not has_prohibited
    if ans_ok:
        answer_correct += 1

    # Condition verification
    cond_ok = True
    if req_conditions:
        for k, v in req_conditions.items():
            if k == "c_rate":
                cond_ok = (v in extracted_entities.get("c_rates", [])) or (v == ctx.get("active_conditions", {}).get("c_rate"))
            elif k == "cycles":
                cond_ok = (v in extracted_entities.get("cycle_counts", [])) or (v == ctx.get("active_conditions", {}).get("cycle_count"))

    audit_records.append({
        "id": q_id,
        "category": category,
        "question": q_text,
        "predicted_intent": intent,
        "intent_confidence": confidence,
        "effective_query": plan.get("original_query", q_text),
        "is_composite": plan.get("is_composite", False),
        "subquery_count": len(subqueries),
        "extracted_dopants": extracted_entities.get("dopants", []),
        "extracted_samples": extracted_entities.get("sample_labels", []),
        "extracted_c_rates": extracted_entities.get("c_rates", []),
        "extracted_cycles": extracted_entities.get("cycle_counts", []),
        "is_sufficient": suff.get("is_sufficient", True),
        "is_comparable": suff.get("is_comparable", True),
        "policy_distinctions": suff.get("policy_distinctions", []),
        "limitation_notes": suff.get("limitation_notes"),
        "top_matches": top_matches,
        "inference_source": res.inference_source,
        "answer_ok": ans_ok,
        "condition_ok": cond_ok,
        "direct_answer_preview": (res.direct_answer or "")[:120],
    })

print(f"Total Evaluated Questions: {len(benchmarks)}")
print(f"Concept & Prohibited Claims Pass Rate: {answer_correct}/{len(benchmarks)} ({answer_correct/len(benchmarks)*100:.1f}%)")

# Output sample records
print("\nSAMPLE DETAILED AUDIT RECORDS:")
for r in audit_records[:5]:
    print(f"\n--- [{r['id']}] {r['category']} ---")
    print(f"Question:         {r['question']}")
    print(f"Intent:           {r['predicted_intent']} (conf={r['intent_confidence']})")
    print(f"Composite Plan:   is_composite={r['is_composite']} ({r['subquery_count']} subqueries)")
    print(f"Entities:         dopants={r['extracted_dopants']}, samples={r['extracted_samples']}")
    print(f"Sufficiency:      sufficient={r['is_sufficient']}, comparable={r['is_comparable']}")
    print(f"Top Matches:      {r['top_matches']}")
    print(f"Inference Source: {r['inference_source']}")
    print(f"Direct Answer:    {r['direct_answer_preview']}...")
    print(f"Verification:     Answer_OK={r['answer_ok']}, Condition_OK={r['condition_ok']}")

# Write complete audit json
with open(WORKSPACE_ROOT / "scripts" / "audit_52_questions_output.json", "w", encoding="utf-8") as f:
    json.dump(audit_records, f, indent=2)

print(f"\nComplete 52-question audit log written to scripts/audit_52_questions_output.json")
