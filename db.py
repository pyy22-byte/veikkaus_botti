import sqlite3
import logging
from pathlib import Path

DB_PATH = Path('events.db')
logger = logging.getLogger(__name__)

RENOTIFY_IMPROVEMENT_DELTA = 5.0


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def initialize_db():
    conn = _connect()
    cur = conn.cursor()
    # Drop and recreate if schema is outdated
    cur.execute("DROP TABLE IF EXISTS events")
    cur.execute("DROP TABLE IF EXISTS notifications")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS events(
            match_key TEXT PRIMARY KEY,
            home_team TEXT,
            away_team TEXT,
            pinnacle_home REAL,
            pinnacle_away REAL,
            veikkaus_home REAL,
            veikkaus_away REAL,
            updated_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS notifications(
            match_key TEXT,
            side TEXT,
            last_improvement_pct REAL,
            notified_at TEXT,
            PRIMARY KEY(match_key, side)
        )
    """)
    conn.commit()
    conn.close()


def upsert_event(k, h, a, ph, pa, vh, va, ts):
    conn = _connect()
    conn.execute("""
        INSERT INTO events(match_key, home_team, away_team,
                           pinnacle_home, pinnacle_away,
                           veikkaus_home, veikkaus_away, updated_at)
        VALUES(?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(match_key) DO UPDATE SET
            home_team=excluded.home_team,
            away_team=excluded.away_team,
            pinnacle_home=excluded.pinnacle_home,
            pinnacle_away=excluded.pinnacle_away,
            veikkaus_home=excluded.veikkaus_home,
            veikkaus_away=excluded.veikkaus_away,
            updated_at=excluded.updated_at
    """, (k, h, a, ph, pa, vh, va, ts))
    conn.commit()
    conn.close()


def should_notify(match_key, side, current_improvement_pct):
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT last_improvement_pct FROM notifications WHERE match_key=? AND side=?",
        (match_key, side)
    )
    row = cur.fetchone()
    conn.close()
    if row is None:
        return True
    return current_improvement_pct >= row[0] + RENOTIFY_IMPROVEMENT_DELTA


def mark_notified(match_key, side, improvement_pct, ts):
    conn = _connect()
    conn.execute("""
        INSERT INTO notifications(match_key, side, last_improvement_pct, notified_at)
        VALUES(?, ?, ?, ?)
        ON CONFLICT(match_key, side) DO UPDATE SET
            last_improvement_pct=excluded.last_improvement_pct,
            notified_at=excluded.notified_at
    """, (match_key, side, improvement_pct, ts))
    conn.commit()
    conn.close()
