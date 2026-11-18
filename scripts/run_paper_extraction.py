import sys
import io
import os
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.main import extract_pdf
from fastapi import UploadFile

papers = [
    "jacs_6c05295_spin_state.pdf",
    "adv_sustain_syst_2022_minnetti.pdf",
    "rsc_adv_c7ra08993g_nanosized.pdf",
    "sust_energy_d4su00125g_ammonia_free.pdf",
    "molecules_26_07641_solgel.pdf",
]

for p in papers:
    full_path = os.path.join("data/real_papers", p)
    print(f"\n=======================================================")
    print(f"Extraction Test: {p}")
    print(f"=======================================================")
    with open(full_path, "rb") as f:
        content = f.read()
    uf = UploadFile(filename=p, file=io.BytesIO(content))
    res = extract_pdf(uf)
    print("Status:", res.get("status"))
    print("Total Pages:", res.get("total_pages"))
    print("Pages with text:", res.get("pages_with_text"))
    print("Candidate Pages Count:", len(res.get("candidate_pages", [])))
    print("Records Extracted:", res.get("records_extracted"))
    print("Saved Reviews Count:", res.get("saved_reviews_count"))
    for r in res.get("saved_reviews", [])[:5]:
        rid = r.get("id")
        comp = r.get("composition")
        page = r.get("page")
        is_new = r.get("is_new")
        print(f"  -> Review ID {rid}: Composition='{comp}', Page={page}, IsNew={is_new}")
    
    struct_meas = res.get("structured_measurements", [])
    print(f"Structured Measurements: {len(struct_meas)}")
    for m in struct_meas[:3]:
        print(f"  -> {m.get('measurement_type')}: {m.get('reported_value')} (C-rate: {m.get('c_rate')}, Page: {m.get('source_page')})")
    
    synth_prof = res.get("synthesis_profiles", [])
    print(f"Synthesis Profiles: {len(synth_prof)}")
    for s in synth_prof[:2]:
        print(f"  -> Method: {s.get('method')}, Temp: {s.get('calcination_temp_c')} C, Precursors: {s.get('precursor_salts')}")
