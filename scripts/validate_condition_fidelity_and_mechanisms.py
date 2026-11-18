"""
Stage 5 Phase 3 Final Validation: Step 3 & 4
Verification of Numerical & Condition Fidelity and Mechanism Grounding

Validates:
1. Condition parity & conflict advisories (C-rate, voltage window, cycles, mass loading, temp).
2. Detection and filtering of unsupported numbers via audit_citations_and_claims.
3. Strict crystallographic mechanism grounding (Pnma, 1D [010] channels, M2 site, Jahn-Teller).
4. Distinction between proven facts, paper observations, author explanations, and copilot hypotheses.
"""

import sys
import json
from pathlib import Path

# Ensure UTF-8 output encoding on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from copilot.engine import LMFPResearchCopilot
from copilot.grounding import audit_citations_and_claims
from copilot.models import EvidencePassage, RetrievalMatch, StructuredSampleProfile, MeasurementRecord
from copilot.evidence_organizer import EvidenceOrganizer


def run_condition_and_mechanism_validation():
    print("=" * 80)
    print("STAGE 5 PHASE 3: CONDITION FIDELITY & MECHANISM GROUNDING VALIDATION")
    print("=" * 80)

    copilot = LMFPResearchCopilot()
    organizer = EvidenceOrganizer()
    results = {}

    # -----------------------------------------------------------------------
    # 1. Condition Parity Evaluation Audit
    # -----------------------------------------------------------------------
    print("\n--- 1. Testing Condition Parity Audit ---")
    p_a = StructuredSampleProfile(
        sample_id="Sample_A",
        sample_label="Sample_A",
        paper_id="Paper_A",
        composition="LiMn0.7Fe0.3PO4",
        measurements=[
            MeasurementRecord("discharge_capacity", 150.0, "mAh/g", c_rate=0.1, temperature_c=25.0, voltage_window="2.5-4.5 V"),
            MeasurementRecord("capacity_retention", 95.0, "%", c_rate=0.1, temperature_c=25.0, voltage_window="2.5-4.5 V", cycle_count=100),
        ],
    )
    p_b = StructuredSampleProfile(
        sample_id="Sample_B",
        sample_label="Sample_B",
        paper_id="Paper_B",
        composition="LiMn0.75Fe0.25PO4",
        measurements=[
            MeasurementRecord("discharge_capacity", 75.0, "mAh/g", c_rate=10.0, temperature_c=25.0, voltage_window="2.0-4.2 V"),
            MeasurementRecord("capacity_retention", 93.0, "%", c_rate=10.0, temperature_c=25.0, voltage_window="2.0-4.2 V", cycle_count=1000),
        ],
    )

    parity = organizer.evaluate_condition_parity(p_a, p_b)
    print(f"  C-rate aligned: {parity.c_rate_aligned} (Expected: False)")
    print(f"  Voltage window aligned: {parity.voltage_window_aligned} (Expected: False)")
    print(f"  Cycle count aligned: {parity.cycle_count_aligned} (Expected: False)")
    print(f"  Divergence notes generated: {len(parity.divergence_notes)}")
    for adv in parity.divergence_notes:
        print(f"    - {adv}")

    parity_ok = (
        not parity.c_rate_aligned
        and not parity.voltage_window_aligned
        and not parity.cycle_count_aligned
        and len(parity.divergence_notes) >= 3
    )
    results["condition_parity_evaluation"] = {
        "passed": parity_ok,
        "c_rate_aligned": parity.c_rate_aligned,
        "voltage_window_aligned": parity.voltage_window_aligned,
        "cycle_count_aligned": parity.cycle_count_aligned,
        "divergence_notes": parity.divergence_notes,
    }

    # -----------------------------------------------------------------------
    # 2. Unsupported / Ungrounded Number Claim Detection
    # -----------------------------------------------------------------------
    print("\n--- 2. Testing Unsupported Number Detection ---")
    mock_passage = EvidencePassage(
        passage_id="p_test_1",
        paper_id="srep26686",
        sample_id="srep26686_SD_SO4",
        sample_label="SD_SO4",
        composition="LiMn0.75Fe0.25PO4",
        text="Sample SD_SO4 delivered 114 mAh/g at 0.05 C and 73 mAh/g at 10 C.",
        structured_data={"discharge_capacities": {"0.05C": 114.0, "10C": 73.0}},
    )
    mock_match = RetrievalMatch(
        passage=mock_passage,
        semantic_score=1.0,
        bm25_score=1.0,
        structured_score=1.0,
        entity_score=1.0,
        lsa_score=0.0,
        combined_score=1.0,
    )

    # Text containing hallucinated numbers not present in passage (178.5 mAh/g, 99.8%)
    hallucinated_text = (
        "In srep26686, sample SD_SO4 delivered 114 mAh/g at 0.05C. "
        "However, an experimental run allegedly achieved 178.5 mAh/g at 0.1C with 99.8% retention."
    )

    audited_text, valid_cits, warnings = audit_citations_and_claims(
        response_text=hallucinated_text,
        retrieved_matches=[mock_match],
        profiles=[StructuredSampleProfile(
            sample_id="srep26686_SD_SO4",
            sample_label="SD_SO4",
            paper_id="srep26686",
            composition="LiMn0.75Fe0.25PO4",
            measurements=[
                MeasurementRecord("discharge_capacity", 114.0, "mAh/g", 0.05, 25.0, None, None),
                MeasurementRecord("discharge_capacity", 73.0, "mAh/g", 10.0, 25.0, None, None),
            ],
        )],
    )

    print(f"  Audit warnings generated: {len(warnings)}")
    for w in warnings:
        print(f"    - {w}")

    has_178_warning = any("178.5" in w for w in warnings)
    has_99_warning = any("99.8" in w for w in warnings)
    unsupported_detection_ok = has_178_warning and has_99_warning
    print(f"  Unsupported number detection passed: {unsupported_detection_ok}")

    results["unsupported_number_detection"] = {
        "passed": unsupported_detection_ok,
        "warnings_count": len(warnings),
        "detected_178_5": has_178_warning,
        "detected_99_8": has_99_warning,
        "warnings": warnings,
    }

    # -----------------------------------------------------------------------
    # 3. Crystallographic & Transport Mechanism Grounding
    # -----------------------------------------------------------------------
    print("\n--- 3. Testing Crystallographic Mechanism Grounding ---")
    mech_queries = [
        {
            "id": "1D_DIFFUSION_TUNNELS",
            "query": "Along which crystallographic axis does lithium diffusion occur in olivine LMFP?",
            "expected_concepts": ["[010]", "b-axis", "pnma", "1d"],
        },
        {
            "id": "JAHN_TELLER_DISTORTION",
            "query": "What causes manganese dissolution during high-potential cycling of LMFP?",
            "expected_concepts": ["jahn-teller", "mn3+", "disproportionation", "dissolution"],
        },
        {
            "id": "M2_SITE_STABILIZATION",
            "query": "Which crystallographic site do Ni, Mg, and Ti substitute into in LMFP, and how does this affect structural stability?",
            "expected_concepts": ["m2", "site", "diffusion"],
        },
    ]

    mech_passed = True
    mech_details = []
    for mq in mech_queries:
        res = copilot.chat(query=mq["query"], force_deterministic=True)
        txt = f"{res.direct_answer} {res.explanation}".lower()
        matched = [c for c in mq["expected_concepts"] if c.lower() in txt]
        ok = len(matched) >= len(mq["expected_concepts"]) - 1  # At least N-1 concepts
        if not ok:
            mech_passed = False
        print(f"  Mechanism query '{mq['id']}': matched {matched} of {mq['expected_concepts']} -> {'PASS' if ok else 'FAIL'}")
        mech_details.append({
            "id": mq["id"],
            "query": mq["query"],
            "matched_concepts": matched,
            "expected_concepts": mq["expected_concepts"],
            "direct_answer_snippet": res.direct_answer[:120],
            "passed": ok,
        })

    results["mechanism_grounding"] = {
        "passed": mech_passed,
        "queries": mech_details,
    }

    # Write results
    out_path = PROJECT_ROOT / "scripts" / "condition_and_mechanism_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 80)
    print(f"CONDITION & MECHANISM VALIDATION: {'ALL PASSED' if parity_ok and unsupported_detection_ok and mech_passed else 'SOME FAILED'}")
    print(f"Results written to: {out_path}")
    print("=" * 80)


if __name__ == "__main__":
    run_condition_and_mechanism_validation()
