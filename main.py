"""Main entry point for the odds comparison bot."""

import yaml
import schedule
import time

from scraper import fetch_odds
from compare import match_events
from notifier import send_telegram_message, build_notification_message
from db import initialize_db, insert_event, mark_as_notified, was_notified


def load_config():
    """Load configuration from config.yaml."""
    with open("config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_check():
    """Perform a single check of odds and send notifications."""
    config = load_config()
    threshold = config.get("threshold_percent", 5.0)
    sites = config.get("sites", {})
    veikkaus_config = sites.get("veikkaus")
    pinnacle_config = sites.get("pinnacle")
    if not (veikkaus_config and pinnacle_config):
        return
    # Fetch events from both sites
    veikkaus_events = fetch_odds(veikkaus_config)
    pinnacle_events = fetch_odds(pinnacle_config)
    # Compare events and prepare notifications
    notifications = match_events(veikkaus_events, pinnacle_events, threshold)
    # Send notifications
    for event in notifications:
        if not was_notified(event["match_id"]):
            insert_event(event["match_id"], event["veikkaus"], event["pinnacle"])
            message = build_notification_message(event)
            send_telegram_message(
                config["telegram"]["token"],
                config["telegram"]["chat_id"],
                message,
            )
            mark_as_notified(event["match_id"])


if __name__ == "__main__":
    initialize_db()
    run_check()  # Run once on start
    schedule.every(1).hours.do(run_check)
    while True:
        schedule.run_pending()
        time.sleep(1)
