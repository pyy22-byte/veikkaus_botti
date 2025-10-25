"""Notifier module for sending messages via Telegram."""

import requests


def send_telegram_message(token, chat_id, message):
    """Send a Markdown-formatted message to a Telegram chat."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
    }
    response = requests.post(url, data=payload)
    response.raise_for_status()


def build_notification_message(event):
    """Construct a notification message for an arbitrage opportunity."""
    return (
        f"📢 Arbitraasimahdollisuus havaittu!\n\n"
        f"Ottelu: {event['home']} – {event['away']}\n"
        f"Veikkaus: {event['veikkaus']}\n"
        f"Pinnacle: {event['pinnacle']}\n"
        f"Ero: +{event['difference_percent']} %\n"
    )
