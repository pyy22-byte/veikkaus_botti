"""
Main entry point for the NHL moneyline odds comparison bot.
Runs once per execution (suitable for GitHub Actions cron).
"""
import os
import yaml
from datetime import datetime, timezone

from scraper import fetch_pinnacle, fetch_veikkaus
from compare import compare_moneyline, match_key_from_names
from db import initialize_db, upsert_event, was_notified, mark_notified
from notifier import send_telegram_message, build_message

def load_config():
    from string import Template
    with open("config.yaml", "r", encoding="utf-8") as f:
        templated = Template(f.read()).substitute(os.environ)
    return yaml.safe_load(templated)

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

    # Compare and notify
    notifications = compare_moneyline(pinnacle_events, veikkaus_events, threshold)
    print(f"Candidates over threshold: {len(notifications)}")

    # Upsert & notify if not yet sent per side
    now = datetime.now(timezone.utc).isoformat()
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    for p in pinnacle_events:
        # Join with veikkaus if exists to store combined latest
        key = match_key_from_names(p["home_team"], p["away_team"])
        # find matching veikkaus
        vmatch = next((v for v in veikkaus_events
                       if match_key_from_names(v["home_team"], v["away_team"]) == key), None)
        veik_home = vmatch["home_odds"] if vmatch else None
        veik_away = vmatch["away_odds"] if vmatch else None
        upsert_event(key, p["home_team"], p["away_team"],
                     p["home_odds"], p["away_odds"],
                     veik_home, veik_away, now)

    for ev in notifications:
        side = ev["side"]
        if not was_notified(ev["match_key"], side):
            send_telegram_message(token, chat_id, build_message(ev))
            mark_notified(ev["match_key"], side)

if __name__ == "__main__":
    initialize_db()
    run_once()
