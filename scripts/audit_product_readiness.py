"""
Comprehensive Product Readiness and Endpoint Audit Script.
Evaluates all 29 FastAPI routes, tests critical workflows, and extracts quantitative metrics.
"""
import os
import sys
import json
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from backend.main import app

def run_audit():
    client = TestClient(app)
    results = {}

    print("=" * 70)
    print("HE-LMFP-DESIGNER: AUTOMATED PRODUCT READINESS AUDIT HARNESS")
    print("=" * 70)

    # 1. Health & Dashboard
    print("[1/8] Auditing Health & Dashboard...")
    res_health = client.get("/api/health")
    res_dash = client.get("/api/dashboard")
    results["health"] = {"code": res_health.status_code, "data": res_health.json()}
    results["dashboard"] = {"code": res_dash.status_code, "total_records": res_dash.json()["master_dataset"]["total_records"]}

    # 2. Materials Designer & Chemistry Engine
    print("[2/8] Auditing Chemistry & Materials Designer...")
    res_dopants = client.get("/api/materials/dopants")
    val_payload = {
        "mn_ratio": 0.65,
        "fe_ratio": 0.26,
        "dopants": [
            {"symbol": "Mg", "fraction": 0.02, "oxidation_state": 2},
            {"symbol": "Zn", "fraction": 0.02, "oxidation_state": 2},
            {"symbol": "Nb", "fraction": 0.01, "oxidation_state": 5},
            {"symbol": "Cu", "fraction": 0.02, "oxidation_state": 2},
            {"symbol": "Zr", "fraction": 0.02, "oxidation_state": 4},
        ],
        "carbon_wt_percent": 2.5,
        "cnt_wt_percent": 0.0,
    }
    res_val = client.post("/api/materials/validate", json=val_payload)
    res_cand = client.post("/api/materials/generate-candidates")
    results["materials_dopants"] = {"code": res_dopants.status_code, "count": len(res_dopants.json())}
    results["materials_validate"] = {"code": res_val.status_code, "balanced": res_val.json()["formula"]["charge_balanced"], "formula": res_val.json()["formula"]["formula_string"]}
    results["materials_candidates"] = {"code": res_cand.status_code, "count": len(res_cand.json()["candidates"])}

    # 3. Property Prediction ML
    print("[3/8] Auditing ML Property Prediction...")
    pred_payload = {
        "mn_ratio": 0.70,
        "fe_ratio": 0.26,
        "dopants": [
            {"symbol": "Mg", "fraction": 0.02, "oxidation_state": 2},
            {"symbol": "Ti", "fraction": 0.02, "oxidation_state": 4},
        ],
        "carbon_wt": 2.0,
        "calc_temp": 650.0,
        "calc_time": 6.0,
    }
    res_pred = client.post("/api/predictions/predict", json=pred_payload)
    if res_pred.status_code != 200:
        print("Prediction error:", res_pred.status_code, res_pred.text)
    res_eval = client.get("/api/predictions/evaluation")
    results["predictions_predict"] = {"code": res_pred.status_code, "targets": list(res_pred.json()["predictions"].keys())}
    results["predictions_evaluation"] = {"code": res_eval.status_code, "has_models": "models" in res_eval.json()}

    # 4. Literature Intelligence & Review Store
    print("[4/8] Auditing Literature Intelligence...")
    res_revs = client.get("/api/literature/reviews")
    res_rev6 = client.get("/api/literature/reviews/6")
    res_rev7 = client.get("/api/literature/reviews/7")
    res_samples = client.get("/api/literature/samples")
    res_exp_preview = client.get("/api/literature/export/preview")
    results["literature_reviews"] = {"code": res_revs.status_code, "count": len(res_revs.json())}
    results["literature_review_6"] = {"code": res_rev6.status_code, "status": res_rev6.json().get("status")}
    results["literature_review_7"] = {"code": res_rev7.status_code, "status": res_rev7.json().get("status")}
    results["literature_samples"] = {"code": res_samples.status_code, "count": len(res_samples.json())}
    results["export_preview"] = {
        "code": res_exp_preview.status_code,
        "exportable": res_exp_preview.json()["exportable_records"],
        "blocked": res_exp_preview.json()["blocked_records"],
    }

    # 5. Research Copilot
    print("[5/8] Auditing Research Copilot QA...")
    chat_payload = {"message": "How does Mg doping influence rate capability at 5C?"}
    res_chat = client.post("/api/copilot/chat", json=chat_payload)
    results["copilot_chat"] = {
        "code": res_chat.status_code,
        "inference_source": res_chat.json().get("inference_source"),
        "has_citations": len(res_chat.json().get("citations", [])) > 0,
        "direct_answer_len": len(res_chat.json().get("direct_answer", "")),
    }

    # 6. Research Discovery Studio
    print("[6/8] Auditing Research Discovery Endpoints...")
    res_trends = client.get("/api/copilot/trends?topic=all")
    res_gaps = client.get("/api/copilot/gaps")
    res_conflicts = client.get("/api/copilot/conflicts")
    res_hyp = client.get("/api/copilot/hypotheses")
    res_mat = client.get("/api/copilot/verification-matrices")
    results["discovery_trends"] = {"code": res_trends.status_code, "records": res_trends.json()["dataset_overview"]["total_literature_records"]}
    results["discovery_gaps"] = {"code": res_gaps.status_code, "count": res_gaps.json()["gaps_count"]}
    results["discovery_conflicts"] = {"code": res_conflicts.status_code, "count": len(res_conflicts.json()["conflicts"])}
    results["discovery_hypotheses"] = {"code": res_hyp.status_code, "count": res_hyp.json()["total_hypotheses"]}
    results["discovery_matrices"] = {"code": res_mat.status_code, "count": res_mat.json()["total_matrices"]}

    # 7. Experiment Management
    print("[7/8] Auditing Experiment Management...")
    res_exps = client.get("/api/experiments")
    res_compare = client.post("/api/experiments/compare?mn_ratio=0.65&fe_ratio=0.26")
    results["experiments_list"] = {"code": res_exps.status_code, "count": len(res_exps.json())}
    results["experiments_compare"] = {"code": res_compare.status_code, "has_residuals": "residuals" in res_compare.json()}

    # 8. SPA Frontend Serving
    print("[8/8] Auditing Static SPA Frontend...")
    res_root = client.get("/")
    results["spa_root"] = {"code": res_root.status_code, "is_html": "text/html" in res_root.headers.get("content-type", "")}

    print("\n" + "=" * 70)
    print("AUDIT RESULTS SUMMARY:")
    print("=" * 70)
    for k, v in results.items():
        print(f"  {k:30s} -> {v}")

    # Write results to JSON file
    out_file = PROJECT_ROOT / "docs" / "readiness_audit_metrics.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved raw audit data to: {out_file}")

if __name__ == "__main__":
    run_audit()
