import sqlite3
from pathlib import Path
from typing import Iterable, Optional, Tuple


SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS discovered_urls (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT NOT NULL UNIQUE,
  discovered_from TEXT,
  discovered_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS crawl_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT NOT NULL,
  status_code INTEGER,
  final_url TEXT,
  error TEXT,
  fetched_at TEXT DEFAULT (datetime('now'))
);
"""


class Store:
    def __init__(self, db_path: str = "data/leads.sqlite"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA foreign_keys=ON;")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def log_fetch(self, url: str, status_code: Optional[int], final_url: Optional[str], error: Optional[str]) -> None:
        self.conn.execute(
            "INSERT INTO crawl_log(url, status_code, final_url, error) VALUES (?,?,?,?)",
            (url, status_code, final_url, error),
        )
        self.conn.commit()

    def upsert_discovered(self, url: str, discovered_from: Optional[str]) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO discovered_urls(url, discovered_from) VALUES (?,?)",
            (url, discovered_from),
        )
        self.conn.commit()

    def bulk_upsert_discovered(self, rows: Iterable[Tuple[str, Optional[str]]]) -> None:
        self.conn.executemany(
            "INSERT OR IGNORE INTO discovered_urls(url, discovered_from) VALUES (?,?)",
            rows,
        )
        self.conn.commit()
