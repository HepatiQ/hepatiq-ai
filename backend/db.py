"""SQLite prediction history for HepatiQ.

Stdlib sqlite3 only -- deliberately not SQLAlchemy: this is one table and
three operations, and an ORM dependency for that would be dead weight.

Connections are opened per call (sqlite3.connect is cheap for a local
file) so the FastAPI threadpool never shares a connection across threads,
and are always closed explicitly -- sqlite3's `with connect(...)` context
manager only commits/rollbacks, it does NOT close. The runtime database
lives at data/hepatiq.db by default and is gitignored -- never commit
prediction logs.
"""

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import List

DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "hepatiq.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    request_json TEXT NOT NULL,
    probability REAL NOT NULL,
    contributions_json TEXT NOT NULL
)
"""


def init_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as conn:
        conn.execute(SCHEMA)
        conn.commit()


def log_prediction(path: Path, request: dict, probability: float, contributions: List[dict]) -> None:
    with closing(sqlite3.connect(path)) as conn:
        conn.execute(
            "INSERT INTO predictions (created_at, request_json, probability, contributions_json) "
            "VALUES (?, ?, ?, ?)",
            (
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                json.dumps(request, default=str),
                float(probability),
                json.dumps(contributions, default=str),
            ),
        )
        conn.commit()


def clear_predictions(path: Path) -> int:
    """Delete every logged prediction; returns the number of rows removed."""
    with closing(sqlite3.connect(path)) as conn:
        cursor = conn.execute("DELETE FROM predictions")
        conn.commit()
    return cursor.rowcount


def fetch_recent(path: Path, limit: int = 20) -> List[dict]:
    with closing(sqlite3.connect(path)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, created_at, request_json, probability, contributions_json "
            "FROM predictions ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "created_at": row["created_at"],
            "request": json.loads(row["request_json"]),
            "probability": row["probability"],
            "contributions": json.loads(row["contributions_json"]),
        }
        for row in rows
    ]
