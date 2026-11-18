"""
Verify Stage 5 Phase 4 Milestone 4.4 End-to-End API Workflow:
Research Gap -> Hypothesis Generation -> Chemical Validation -> Experimental Verification Matrix
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
from fastapi.testclient import TestClient
from backend.main import app

def verify_end_to_end_api_workflow():
    print("=" * 70)
    print("STAGE 5 PHASE 4 MILESTONE 4.4 - E2E API WORKFLOW VERIFICATION")
    print("=" * 70)
    
    client = TestClient(app)
    
    # 1. Fetch research gaps from API
    print("\n[STEP 1] Fetching research gaps from /api/copilot/gaps...")
    res_gaps = client.get("/api/copilot/gaps")
    assert res_gaps.status_code == 200, f"Failed: {res_gaps.status_code}"
    gaps_data = res_gaps.json()
    gaps = gaps_data.get("gaps", [])
    print(f"  -> Total gaps retrieved: {len(gaps)}")
    assert len(gaps) > 0, "No gaps retrieved"
    
    # Pick a specific gap, e.g., GAP-ELEC-01 or GAP-COMP-01
    target_gap = None
    for g in gaps:
        if "high-voltage" in g.get("title", "").lower() or "4.5v" in g.get("title", "").lower() or g.get("gap_id") == "GAP-ELEC-01":
            target_gap = g
            break
    if not target_gap:
        target_gap = gaps[0]
        
    gap_id = target_gap["gap_id"]
    gap_title = target_gap["title"]
    gap_papers = target_gap.get("supporting_paper_ids", [])
    gap_samples = target_gap.get("supporting_sample_ids", [])
    print(f"  -> Selected Gap ID: {gap_id}")
    print(f"  -> Gap Title: {gap_title}")
    print(f"  -> Linked Papers ({len(gap_papers)}): {gap_papers[:5]}")
    print(f"  -> Linked Samples ({len(gap_samples)}): {gap_samples[:5]}")
    
    # 2. Generate hypothesis from research gap via API
    print("\n[STEP 2] Generating hypothesis from gap via /api/copilot/hypotheses/generate...")
    hyp_payload = {
        "gap_id": gap_id,
        "topic": target_gap.get("title", "High-voltage cycling stability gap")
    }
    res_hyp = client.post("/api/copilot/hypotheses/generate", json=hyp_payload)
    assert res_hyp.status_code == 200, f"Failed: {res_hyp.status_code}"
    hyp = res_hyp.json()
    hyp_id = hyp.get("hypothesis_id")
    hyp_title = hyp.get("hypothesis_statement")
    proto = hyp.get("experimental_protocol", {})
    proposed_comp = proto.get("candidate_composition")
    chem_val = hyp.get("chemical_validation", {})
    is_balanced = chem_val.get("is_charge_balanced")
    is_plausible = chem_val.get("is_chemically_plausible")
    q_m2 = chem_val.get("q_m2")
    falsification = hyp.get("falsification_criteria", [])
    
    print(f"  -> Generated Hypothesis ID: {hyp_id}")
    print(f"  -> Hypothesis Statement: {hyp_title[:80]}...")
    print(f"  -> Proposed Candidate Composition: {proposed_comp}")
    print(f"  -> Is Charge Balanced: {is_balanced}")
    print(f"  -> Is Chemically Plausible: {is_plausible}")
    print(f"  -> Q_M2 Valence: {q_m2}")
    print(f"  -> Number of Falsification Criteria: {len(falsification)}")
    assert hyp_id is not None, "Hypothesis ID is missing"
    assert is_balanced is True, f"Hypothesis not charge balanced: {chem_val}"
    assert is_plausible is True, f"Hypothesis not chemically plausible: {chem_val}"
    
    # 3. Generate verification matrix from hypothesis via API
    print("\n[STEP 3] Generating verification matrix via /api/copilot/verification-matrices/generate...")
    mat_payload = {
        "hypothesis_id": hyp_id,
        "gap_id": gap_id
    }
    res_mat = client.post("/api/copilot/verification-matrices/generate", json=mat_payload)
    assert res_mat.status_code == 200, f"Failed: {res_mat.status_code}"
    matrix = res_mat.json()
    matrix_id = matrix.get("matrix_id")
    linked_hyp_id = matrix.get("hypothesis_id")
    linked_gap_id = matrix.get("research_gap_id")
    cand_comp = matrix.get("candidate_composition")
    status_disclaimers = matrix.get("status_disclaimers", {})
    experiment_status = status_disclaimers.get("EXPERIMENT_STATUS")
    ml_status = status_disclaimers.get("ML_VALIDATION_STATUS")
    controls = matrix.get("control_samples", [])
    vars_list = matrix.get("variable_specifications", [])
    synth_steps = matrix.get("synthesis_plan", [])
    char_steps = matrix.get("characterization_plan", [])
    elec_steps = matrix.get("electrochemical_plan", [])
    lit_link = matrix.get("supporting_literature", {})
    evidence_papers = lit_link.get("paper_ids", [])
    evidence_samples = lit_link.get("sample_ids", [])
    
    print(f"  -> Generated Matrix ID: {matrix_id}")
    print(f"  -> Linked Hypothesis ID: {linked_hyp_id} (matches {hyp_id})")
    print(f"  -> Linked Gap ID: {linked_gap_id} (matches {gap_id})")
    print(f"  -> Candidate Composition: {cand_comp}")
    print(f"  -> Mandatory Experiment Status: {experiment_status}")
    print(f"  -> Mandatory ML Status: {ml_status}")
    print(f"  -> Control Samples ({len(controls)}): {[c.get('label') for c in controls]}")
    print(f"  -> Variables ({len(vars_list)}): {[v.get('variable_name') + ' (' + v.get('variable_type') + ')' for v in vars_list]}")
    print(f"  -> Synthesis Plan Steps: {len(synth_steps)}")
    print(f"  -> Characterization Battery Steps: {len(char_steps)}")
    print(f"  -> Electrochemical Protocols: {len(elec_steps)}")
    print(f"  -> Linked Evidence Papers ({len(evidence_papers)}): {evidence_papers[:5]}")
    print(f"  -> Linked Evidence Samples ({len(evidence_samples)}): {evidence_samples[:5]}")
    
    # Assertions on status and linking
    assert matrix_id is not None, "Matrix ID missing"
    assert linked_hyp_id == hyp_id, f"Hypothesis ID mismatch: {linked_hyp_id} != {hyp_id}"
    assert linked_gap_id == gap_id, f"Gap ID mismatch: {linked_gap_id} != {gap_id}"
    assert experiment_status == "PROPOSED_UNPERFORMED", f"Unexpected status: {experiment_status}"
    assert ml_status == "IN_SILICO_PREDICTION_NOT_EXPERIMENTAL_PROOF", f"Unexpected status: {ml_status}"
    assert len(controls) >= 1, "Control samples missing"
    assert len(synth_steps) >= 3, "Synthesis steps incomplete"
    assert len(char_steps) >= 2, "Characterization battery incomplete"
    assert len(elec_steps) >= 1, "Electrochemical protocols incomplete"
    
    # Check that settings distinguish evidence-supported from researcher selection
    needs_selection = matrix.get("researcher_selection_required", [])
    print(f"  -> Parameters Requiring Researcher Selection: {len(needs_selection)}")
    for req in needs_selection[:3]:
        print(f"     * {req}")
    
    print("\n[STEP 4] Querying canonical verification matrices...")
    res_canon = client.get("/api/copilot/verification-matrices")
    assert res_canon.status_code == 200
    canon_data = res_canon.json()
    canonical_matrices = canon_data.get("matrices", [])
    print(f"  -> Retrieved {len(canonical_matrices)} canonical verification matrices:")
    for m in canonical_matrices:
        print(f"     * {m.get('matrix_id')}: {m.get('title')} -> Candidate: {m.get('candidate_composition')}")
    assert len(canonical_matrices) >= 3, "Expected at least 3 canonical verification matrices"
    
    print("\n" + "=" * 70)
    print("ALL END-TO-END API WORKFLOW CHECKS COMPLETED AND VERIFIED 100%")
    print("=" * 70)

if __name__ == "__main__":
    verify_end_to_end_api_workflow()
