"""
Stress Memory Test for ECMT AI Backend.
Simulates concurrent requests to ML predictions, chemistry engine, copilot RAG,
and literature search to measure peak memory footprint under load.
"""

import os
import sys
import time
import psutil
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

process = psutil.Process(os.getpid())


def get_mem_mb():
    return process.memory_info().rss / (1024 * 1024)


def task_ml_prediction(req_id: int):
    from models.ml.predictor import predict_composition_performance
    dopants = [
        {"symbol": "Mg", "fraction": 0.03, "oxidation_state": 2},
        {"symbol": "Ti", "fraction": 0.02, "oxidation_state": 4},
    ]
    res = predict_composition_performance(
        mn_ratio=0.65,
        fe_ratio=0.25,
        dopants=dopants,
        carbon_wt=2.5,
        calc_temp=700.0,
        calc_time=8.0,
    )
    return f"req_{req_id}_ml_done"


def task_chemistry_validation(req_id: int):
    from chemistry.validation import validate_composition
    dopants = [
        {"symbol": "Mg", "fraction": 0.03, "oxidation_state": 2},
        {"symbol": "Co", "fraction": 0.02, "oxidation_state": 2},
    ]
    res = validate_composition(0.7, 0.25, dopants, 2.5, 0.0)
    return f"req_{req_id}_chem_done"


def task_copilot_rag(req_id: int):
    from copilot import get_research_copilot
    copilot = get_research_copilot()
    res = copilot.chat("Compare Mg- and Ti-doped LMFP rate kinetics")
    return f"req_{req_id}_rag_done"


def task_literature_filtering(req_id: int):
    import pandas as pd
    csv_path = PROJECT_ROOT / "data" / "literature_reference.csv"
    df = pd.read_csv(csv_path)
    filtered = df[(df["Dopant_Element"] == "Mg") | (df["Mn_Ratio"] >= 0.6)]
    return f"req_{req_id}_lit_done_rows_{len(filtered)}"


def run_stress_test(num_concurrent: int = 10):
    print(f"=== ECMT AI Peak Memory Stress Test ({num_concurrent} Concurrent Threads) ===")
    mem_init = get_mem_mb()
    print(f"[1/4] Baseline Memory before load: {mem_init:.2f} MB")

    # Preload modules
    import backend.main
    from copilot import get_research_copilot
    get_research_copilot()
    mem_loaded = get_mem_mb()
    print(f"[2/4] Memory after preloading all ML models, dataset & RAG engine: {mem_loaded:.2f} MB")

    peak_mem = mem_loaded
    mem_lock = threading.Lock()

    def mem_monitor(stop_event):
        nonlocal peak_mem
        while not stop_event.is_set():
            current = get_mem_mb()
            with mem_lock:
                if current > peak_mem:
                    peak_mem = current
            time.sleep(0.01)

    stop_evt = threading.Event()
    monitor_thread = threading.Thread(target=mem_monitor, args=(stop_evt,), daemon=True)
    monitor_thread.start()

    tasks = []
    # Create mix of concurrent workloads
    for i in range(num_concurrent):
        tasks.append((task_ml_prediction, i))
        tasks.append((task_chemistry_validation, i))
        tasks.append((task_copilot_rag, i))
        tasks.append((task_literature_filtering, i))

    print(f"[3/4] Launching {len(tasks)} simultaneous tasks across {num_concurrent} threads...")
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
        futures = [executor.submit(func, arg) for func, arg in tasks]
        results = [f.result() for f in futures]
    duration = time.time() - start_time
    stop_evt.set()
    monitor_thread.join()

    print(f"[4/4] Completed {len(results)} requests in {duration:.2f} seconds ({len(results)/duration:.1f} req/s)")
    final_mem = get_mem_mb()
    render_limit_mb = 512.0
    headroom = render_limit_mb - peak_mem

    print("\n" + "="*60)
    print("CONCURRENT PEAK MEMORY AUDIT RESULTS:")
    print(f"  Startup / Loaded Memory: {mem_loaded:.2f} MB")
    print(f"  Peak Memory Under Load : {peak_mem:.2f} MB")
    print(f"  Final Settled Memory   : {final_mem:.2f} MB")
    print(f"  Render Free RAM Ceiling: {render_limit_mb:.2f} MB")
    print(f"  Safe Headroom Remaining: {headroom:.2f} MB ({headroom/render_limit_mb*100:.1f}%)")
    print("="*60)

    assert peak_mem < 450.0, f"Peak memory {peak_mem} MB exceeds safety threshold 450 MB!"
    print("TEST PASSED: Memory remains safely below Render Free 512MB limit during concurrent load!")


if __name__ == "__main__":
    run_stress_test(num_concurrent=10)
