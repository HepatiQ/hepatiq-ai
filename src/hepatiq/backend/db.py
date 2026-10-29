"""SQLite prediction history for HepatiQ."""
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

RISK_BAND_INTERMEDIATE = 0.15
RISK_BAND_HIGH = 0.40


def _compute_risk_band(probability: float) -> str:
    if probability >= RISK_BAND_HIGH:
        return "high"
    elif probability >= RISK_BAND_INTERMEDIATE:
        return "intermediate"
    else:
        return "low"


SCHEMA = """
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    request_json TEXT NOT NULL,
    probability REAL NOT NULL,
    contributions_json TEXT NOT NULL,
    risk_band TEXT,
    model_version TEXT,
    session_id TEXT,
    latency_ms REAL,
    age REAL,
    sex TEXT,
    bili REAL,
    albumin REAL,
    edema REAL
)
"""


def _migrate_schema(conn: sqlite3.Connection) -> None:
    cursor = conn.execute("PRAGMA table_info(predictions)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    new_columns = [
        ("risk_band", "TEXT"),
        ("model_version", "TEXT"),
        ("session_id", "TEXT"),
        ("latency_ms", "REAL"),
        ("age", "REAL"),
        ("sex", "TEXT"),
        ("bili", "REAL"),
        ("albumin", "REAL"),
        ("edema", "REAL"),
    ]
    for col_name, col_type in new_columns:
        if col_name not in existing_columns:
            try:
                conn.execute(f"ALTER TABLE predictions ADD COLUMN {col_name} {col_type}")
            except Exception:
                pass


def init_db(path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path, timeout=5.0)) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute(SCHEMA)
        _migrate_schema(conn)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_predictions_created_at ON predictions(created_at DESC);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_predictions_risk_band ON predictions(risk_band);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_predictions_session_id ON predictions(session_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_predictions_probability ON predictions(probability);")
        conn.commit()


def log_prediction(
    path,
    request: dict,
    probability: float,
    contributions: List[dict],
    model_version: Optional[str] = None,
    session_id: Optional[str] = None,
    latency_ms: Optional[float] = None,
) -> None:
    risk_band = _compute_risk_band(float(probability))
    age = request.get("age")
    sex = request.get("sex")
    bili = request.get("bili")
    albumin = request.get("albumin")
    edema = request.get("edema")
    with closing(sqlite3.connect(path, timeout=5.0)) as conn:
        conn.execute(
            (
                "INSERT INTO predictions "
                "(created_at, request_json, probability, contributions_json, risk_band, "
                "model_version, session_id, latency_ms, age, sex, bili, albumin, edema) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            ),
            (
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                json.dumps(request, default=str),
                float(probability),
                json.dumps(contributions, default=str),
                risk_band,
                model_version,
                session_id,
                latency_ms,
                age,
                sex,
                bili,
                albumin,
                edema,
            ),
        )
        conn.commit()


def clear_predictions(path) -> int:
    with closing(sqlite3.connect(path, timeout=5.0)) as conn:
        cursor = conn.execute("DELETE FROM predictions")
        conn.commit()
    return cursor.rowcount


def fetch_recent(
    path,
    limit: int = 20,
    risk_band: Optional[str] = None,
    session_id: Optional[str] = None,
) -> List[dict]:
    with closing(sqlite3.connect(path, timeout=5.0)) as conn:
        conn.row_factory = sqlite3.Row
        query = (
            "SELECT id, created_at, request_json, probability, contributions_json, "
            "risk_band, model_version, session_id, latency_ms FROM predictions"
        )
        conditions = []
        params = []
        if risk_band:
            conditions.append("risk_band = ?")
            params.append(risk_band)
        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
    return [
        {
            "id": row["id"],
            "created_at": row["created_at"],
            "request": json.loads(row["request_json"]),
            "probability": row["probability"],
            "contributions": json.loads(row["contributions_json"]),
            "risk_band": row["risk_band"],
            "model_version": row["model_version"],
            "session_id": row["session_id"],
            "latency_ms": row["latency_ms"],
        }
        for row in rows
    ]


def get_stats(path) -> dict:
    with closing(sqlite3.connect(path, timeout=5.0)) as conn:
        conn.row_factory = sqlite3.Row
        total = conn.execute("SELECT COUNT(*) as cnt FROM predictions").fetchone()["cnt"]
        if total == 0:
            return {
                "total": 0,
                "avg_probability": 0,
                "high_risk_count": 0,
                "intermediate_risk_count": 0,
                "low_risk_count": 0,
                "high_risk_pct": 0,
            }
        avg_prob = conn.execute("SELECT AVG(probability) as avg FROM predictions").fetchone()["avg"]
        high_risk = conn.execute("SELECT COUNT(*) as cnt FROM predictions WHERE risk_band = 'high'").fetchone()["cnt"]
        intermediate = conn.execute(
            "SELECT COUNT(*) as cnt FROM predictions WHERE risk_band = 'intermediate'"
        ).fetchone()["cnt"]
        low_risk = conn.execute("SELECT COUNT(*) as cnt FROM predictions WHERE risk_band = 'low'").fetchone()["cnt"]
        return {
            "total": total,
            "avg_probability": round(avg_prob, 4) if avg_prob else 0,
            "high_risk_count": high_risk,
            "intermediate_risk_count": intermediate,
            "low_risk_count": low_risk,
            "high_risk_pct": round((high_risk / total) * 100, 1),
        }
