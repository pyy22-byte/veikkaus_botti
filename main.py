"""
Main entry point for the NHL moneyline odds comparison bot.
Runs once per execution (suitable for GitHub Actions cron or local run).
"""
import os
import yaml
from datetime import datetime, timezone

from scraper import fetch_pinnacle, fetch_veikkaus
from compare import compare_moneyline, match_key_from_names
from db import initialize_db, upsert_event, was_notified, mark_notified
from notifier import send_telegram_message, build_message


def load_config():
    """Read config.yaml and expand $ENV variables safely (won't break CSS $=)."""
    with open("config.yaml", "r", encoding="utf-8") as f:
        raw = f.read()
    expanded = os.path.expandvars(raw)
    return yaml.safe_load(expanded)


def run_once():
    cfg = load_config()
    threshold = float(cfg.get("threshold_percent", 5.0))
    p_cfg = cfg["sites"]["pinnacle"]
    v_cfg = cfg["sites"]["veikkaus"]

    print("Fetching Pinnacle...")
    pinnacle_events = fetch_pinnacle(p_cfg)
    print(f"Pinnacle events: {len(pinnacle_events)}")

    print("Fetching Veikkaus...")
    veikkaus_events = fetch_veikkaus(v_cfg)
    print(f"Veikkaus events: {len(veikkaus_events)}")

    # Compare and compute notifications
    notifications = compare_moneyline(pinnacle_events, veikkaus_events, threshold)
    print(f"Candidates over threshold: {len(notifications)}")

    # Upsert latest snapshot + notify once per side
    now = datetime.now(timezone.utc).isoformat()
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    for p in pinnacle_events:
        key = match_key_from_names(p["home_team"], p["away_team"])
        v = next((x for x in veikkaus_events
                  if match_key_from_names(x["home_team"], x["away_team"]) == key), None)
        veik_home = v["home_odds"] if v else None
        veik_away = v["away_odds"] if v else None
        upsert_event(key, p["home_team"], p["away_team"],
                     p["home_odds"], p["away_odds"], veik_home, veik_away, now)

    for ev in notifications:
        side = ev["side"]
        if not was_notified(ev["match_key"], side):
            send_telegram_message(token, chat_id, build_message(ev))
            mark_notified(ev["match_key"], side)


if __name__ == "__main__":
    initialize_db()
    run_once()
