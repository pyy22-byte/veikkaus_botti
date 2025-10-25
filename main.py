"""Main entry point for the odds comparison bot."""

import yaml
import schedule
import time
import os


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
# Resolve Telegram credentials from environment variables or config
token = os.environ.get("TELEGRAM_TOKEN")
chat_id = os.environ.get("TELEGRAM_CHAT_ID")
telegram_config = config.get("telegram", {})
if token is None:
    token = telegram_config.get("token")
if chat_id is None:
    chat_id = telegram_config.get("chat_id")

# Send notifications
for event in notifications:
    match_id = event["match_id"]
    if not was_notified(match_id):
        insert_event(match_id, event["veikkaus"], event["pinnacle"])
        message = build_notification_message(event)
        # Only send a message if both token and chat_id are available
        if token and chat_id:
            send_telegram_message(token, chat_id, message)
        mark_as_notified(match_id)


if __name__ == "__main__":
    initialize_db()
    run_check()  # Run once on start
    schedule.every(1).hours.do(run_check)
    while True:
        schedule.run_pending()
        time.sleep(1)
