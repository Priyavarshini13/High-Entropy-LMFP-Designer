import sqlite3
from pathlib import Path

DB_PATH = Path("data/literature_review.db")

def restore_baseline():
    papers = (
        'jacs_6c05295_spin_state',
        'adv_sustain_syst_2022_minnetti',
        'rsc_adv_c7ra08993g_nanosized',
        'sust_energy_d4su00125g_ammonia_free',
        'molecules_26_07641_solgel'
    )
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM extraction_reviews WHERE id > 38")
        conn.execute(f"DELETE FROM entity_samples WHERE paper_id IN {papers}")
        conn.execute(f"DELETE FROM entity_measurements WHERE paper_id IN {papers}")
        conn.execute(f"DELETE FROM entity_evidence WHERE paper_id IN {papers}")
        conn.execute(f"DELETE FROM entity_papers WHERE paper_id IN {papers}")
        conn.execute("DELETE FROM entity_compositions WHERE composition_id NOT IN (SELECT DISTINCT composition_id FROM entity_samples WHERE composition_id IS NOT NULL)")
        conn.execute("DELETE FROM entity_synthesis_profiles WHERE synthesis_profile_id NOT IN (SELECT DISTINCT synthesis_profile_id FROM entity_samples WHERE synthesis_profile_id IS NOT NULL)")
        conn.execute("DELETE FROM entity_characterization_profiles WHERE characterization_profile_id NOT IN (SELECT DISTINCT characterization_profile_id FROM entity_samples WHERE characterization_profile_id IS NOT NULL)")
        conn.commit()

    with sqlite3.connect(DB_PATH) as conn:
        revs = conn.execute("SELECT COUNT(*) FROM extraction_reviews").fetchone()[0]
        samples = conn.execute("SELECT COUNT(*) FROM entity_samples").fetchone()[0]
        r6 = conn.execute("SELECT status FROM extraction_reviews WHERE id=6").fetchone()
        r7 = conn.execute("SELECT status FROM extraction_reviews WHERE id=7").fetchone()
        print(f"Restored DB: {revs} reviews, {samples} entity samples")
        print(f"Review 6: {r6[0] if r6 else None}, Review 7: {r7[0] if r7 else None}")

if __name__ == "__main__":
    restore_baseline()
