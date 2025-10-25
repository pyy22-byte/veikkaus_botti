import sqlite3
from contextlib import closing

DB_PATH = "events.db"

def initialize_db():
    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                match_key TEXT PRIMARY KEY,
                home_team TEXT,
                away_team TEXT,
                pinn_home REAL,
                pinn_away REAL,
                veik_home REAL,
                veik_away REAL,
                notified_home INTEGER DEFAULT 0,
                notified_away INTEGER DEFAULT 0,
                updated_at TEXT
            )
        """)

def upsert_event(match_key, home_team, away_team, pinn_home, pinn_away, veik_home, veik_away, updated_at):
    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        conn.execute("""
            INSERT INTO events(match_key, home_team, away_team, pinn_home, pinn_away, veik_home, veik_away, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(match_key) DO UPDATE SET
                home_team=excluded.home_team,
                away_team=excluded.away_team,
                pinn_home=excluded.pinn_home,
                pinn_away=excluded.pinn_away,
                veik_home=excluded.veik_home,
                veik_away=excluded.veik_away,
                updated_at=excluded.updated_at
        """, (match_key, home_team, away_team, pinn_home, pinn_away, veik_home, veik_away, updated_at))

def get_event(match_key):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.execute("SELECT * FROM events WHERE match_key=?", (match_key,))
        return cur.fetchone()

def mark_notified(match_key, side):  # side: "home" tai "away"
    col = "notified_home" if side == "home" else "notified_away"
    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        conn.execute(f"UPDATE events SET {col}=1 WHERE match_key=?", (match_key,))

def was_notified(match_key, side):
    col = "notified_home" if side == "home" else "notified_away"
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.execute(f"SELECT {col} FROM events WHERE match_key=?", (match_key,))
        row = cur.fetchone()
        return bool(row and row[0])
