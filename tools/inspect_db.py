import sqlite3
import sys

path = sys.argv[1]
conn = sqlite3.connect(path)
rows = [r[0] for r in conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
)]
print(f"{path}: {len(rows)} tables")
for name in rows:
    print("  -", name)