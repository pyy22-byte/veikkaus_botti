"""Database module for storing events and notification status."""

import sqlite3

DB_PATH = "events.db"


def initialize_db():
    """Initialize the SQLite database and create tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    with conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS events ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "match_id TEXT UNIQUE,"
            "veikkaus_odds REAL,"
            "pinnacle_odds REAL,"
            "notified INTEGER DEFAULT 0)"
        )


def insert_event(match_id, veikkaus_odds, pinnacle_odds):
    """Insert a new event into the database if it doesn't already exist."""
    conn = sqlite3.connect(DB_PATH)
    with conn:
        conn.execute(
            "INSERT OR IGNORE INTO events (match_id, veikkaus_odds, pinnacle_odds) "
            "VALUES (?, ?, ?)",
            (match_id, veikkaus_odds, pinnacle_odds),
        )


def mark_as_notified(match_id):
    """Mark an event as notified."""
    conn = sqlite3.connect(DB_PATH)
    with conn:
        conn.execute(
            "UPDATE events SET notified = 1 WHERE match_id = ?",
            (match_id,),
        )


def was_notified(match_id):
    """Check if an event has been notified."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT notified FROM events WHERE match_id = ?",
        (match_id,),
    )
    row = cur.fetchone()
    return row is not None and row[0] == 1
