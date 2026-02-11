import csv
import sqlite3
from pathlib import Path

DB = "src/data/leads.sqlite"
OUT = "src/data/discovered.csv"

Path("src/data").mkdir(exist_ok=True)

con = sqlite3.connect(DB)
rows = con.execute(
    "select url, discovered_from, discovered_at from discovered_urls order by discovered_at desc"
).fetchall()

with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["url", "discovered_from", "discovered_at"])
    w.writerows(rows)

print(f"Wrote {len(rows)} rows to {OUT}")
