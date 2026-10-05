import sqlite3
import sys

path = sys.argv[1]
conn = sqlite3.connect(path)
tables = [
    r[0]
    for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
]
total = 0
for t in tables:
    n = conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
    total += n
    print(f"{t:<18} {n}")
print(f"{'TOTAL':<18} {total}")