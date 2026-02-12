from __future__ import annotations

import json
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

CREATE TABLE IF NOT EXISTS site_analysis (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT NOT NULL UNIQUE,
  final_url TEXT,
  status_code INTEGER,
  https INTEGER,
  title TEXT,
  has_viewport_meta INTEGER,
  has_email INTEGER,
  has_phone INTEGER,
  has_address INTEGER,
  stack_hint TEXT,
  score INTEGER,
  reasons_json TEXT,
  analyzed_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS llm_insights (
  url TEXT PRIMARY KEY,
  bullets_json TEXT,
  email_opener TEXT,
  model TEXT,
  generated_at TEXT DEFAULT (datetime('now'))
);
"""


class Store:
    def __init__(self, db_path: str = "src/data/leads.sqlite"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA foreign_keys=ON;")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # -------------------------
    # Logging
    # -------------------------
    def log_fetch(
        self,
        url: str,
        status_code: Optional[int],
        final_url: Optional[str],
        error: Optional[str],
    ) -> None:
        self.conn.execute(
            "INSERT INTO crawl_log(url, status_code, final_url, error) VALUES (?,?,?,?)",
            (url, status_code, final_url, error),
        )
        self.conn.commit()

    # -------------------------
    # Discovery persistence
    # -------------------------
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

    def get_discovered_urls(self, limit: int = 500) -> list[str]:
        rows = self.conn.execute(
            "SELECT url FROM discovered_urls ORDER BY discovered_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [r[0] for r in rows]

    # -------------------------
    # Analysis persistence
    # -------------------------
    def upsert_site_analysis(
        self,
        *,
        url: str,
        final_url: Optional[str],
        status_code: Optional[int],
        https: bool,
        title: Optional[str],
        has_viewport: bool,
        has_email: bool,
        has_phone: bool,
        has_address: bool,
        stack_hint: Optional[str],
        score: int,
        reasons: list[str],
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO site_analysis(
              url, final_url, status_code, https, title, has_viewport_meta,
              has_email, has_phone, has_address, stack_hint, score, reasons_json
            )
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(url) DO UPDATE SET
              final_url=excluded.final_url,
              status_code=excluded.status_code,
              https=excluded.https,
              title=excluded.title,
              has_viewport_meta=excluded.has_viewport_meta,
              has_email=excluded.has_email,
              has_phone=excluded.has_phone,
              has_address=excluded.has_address,
              stack_hint=excluded.stack_hint,
              score=excluded.score,
              reasons_json=excluded.reasons_json,
              analyzed_at=datetime('now')
            """,
            (
                url,
                final_url,
                status_code,
                1 if https else 0,
                title,
                1 if has_viewport else 0,
                1 if has_email else 0,
                1 if has_phone else 0,
                1 if has_address else 0,
                stack_hint,
                int(score),
                json.dumps(reasons, ensure_ascii=False),
            ),
        )
        self.conn.commit()