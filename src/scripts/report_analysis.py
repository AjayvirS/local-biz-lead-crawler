from __future__ import annotations

import sqlite3
from pathlib import Path


def pick_db(root: Path) -> Path:
    candidates = [
        root / "src" / "data" / "leads.sqlite",
        root / "data" / "leads.sqlite",
    ]
    existing = [p for p in candidates if p.exists()]
    if not existing:
        raise FileNotFoundError("No leads.sqlite found in src/data or data")
    # pick the largest file (usually the real one)
    return sorted(existing, key=lambda p: p.stat().st_size, reverse=True)[0]


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
            (name,),
        ).fetchone()
        is not None
    )


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    db_path = pick_db(root)

    print("=" * 60)
    print("LEAD ANALYSIS REPORT")
    print("=" * 60)
    print(f"Repo root: {root}")
    print(f"Using DB:  {db_path}  ({db_path.stat().st_size} bytes)")
    print("-" * 60)

    conn = sqlite3.connect(db_path)

    for t in ["discovered_urls", "site_analysis", "crawl_log"]:
        print(f"Table {t}: {'YES' if table_exists(conn, t) else 'NO'}")

    if table_exists(conn, "discovered_urls"):
        discovered = conn.execute("SELECT COUNT(*) FROM discovered_urls").fetchone()[0]
        print(f"Discovered URLs: {discovered}")
    else:
        print("Discovered URLs: (table missing)")

    if table_exists(conn, "site_analysis"):
        analyzed = conn.execute("SELECT COUNT(*) FROM site_analysis").fetchone()[0]
        print(f"Analyzed URLs:   {analyzed}")
    else:
        print("Analyzed URLs:   (table missing)")

    print("-" * 60)

    # Show worst 10 if any
    if table_exists(conn, "site_analysis"):
        rows = conn.execute(
            """
            SELECT url, score, stack_hint
            FROM site_analysis
            ORDER BY score ASC
            LIMIT 10
            """
        ).fetchall()

        if rows:
            print("Worst 10 leads (lowest score = best opportunity):\n")
            for i, (url, score, stack) in enumerate(rows, 1):
                print(f"{i:2d}. Score: {score:3d} | Stack: {stack or '-'}")
                print(f"    {url}")
        else:
            print("No rows in site_analysis yet.")

    # If analysis is empty, show crawl errors to diagnose
    if table_exists(conn, "crawl_log"):
        err_rows = conn.execute(
            """
            SELECT error, COUNT(*) cnt
            FROM crawl_log
            WHERE error IS NOT NULL AND error != ''
            GROUP BY error
            ORDER BY cnt DESC
            LIMIT 10
            """
        ).fetchall()
        if err_rows:
            print("\nTop crawl_log errors:")
            for err, cnt in err_rows:
                print(f"  {cnt:4d}  {err}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()