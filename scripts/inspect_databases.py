import sqlite3
from pathlib import Path

db_files = [
    Path('data/lab_experiments.db'),
    Path('data/literature_review.db'),
    Path('data/backups/lab_experiments_backup_zero_cost_20261118_191821.db'),
]

for db in db_files:
    print(f"\n=== Database: {db} (Size: {db.stat().st_size if db.exists() else 0} bytes) ===")
    if not db.exists():
        continue
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cur.fetchall()]
    print(f"Tables found: {tables}")
    for t in tables:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        cnt = cur.fetchone()[0]
        print(f"  Table '{t}': {cnt} records")
        # Sample schema
        cur.execute(f"PRAGMA table_info({t})")
        cols = [c[1] for c in cur.fetchall()]
        print(f"    Columns: {cols[:8]}...")
