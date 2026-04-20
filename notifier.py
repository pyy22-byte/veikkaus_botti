import logging
import requests

logger = logging.getLogger(__name__)

DISCORD_USERNAME = "NHL Moneyline Bot"


def build_message(ev):
    side = 'KOTI' if ev['side'] == 'home' else 'VIERAS'
    return (
        f"**NHL moneyline etu** ({side})\n"
        f"{ev['home_team']} vs {ev['away_team']}\n"
        f"Veikkaus: **{ev['veikkaus']}**  •  Pinnacle: {ev['pinnacle']}\n"
        f"Parannus: **{ev['improvement_pct']}%**"
    )


def send_discord_message(webhook_url, message):
    if not webhook_url:
        logger.warning("Missing DISCORD_WEBHOOK_URL; skipping send.")
        return
    payload = {
        "username": DISCORD_USERNAME,
        "content": message,
    }
    try:
        r = requests.post(webhook_url, json=payload, timeout=20)
        if r.ok:
            logger.info("Discord message sent.")
        else:
            logger.warning(f"Discord API error: {r.status_code} {r.text}")
    except Exception as e:
        logger.warning(f"Discord send failed: {e}")
