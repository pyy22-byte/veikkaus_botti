import logging
import os
import yaml
from datetime import datetime, timezone

from scraper import fetch_all
from compare import compare_moneyline, match_key_from_names
from db import (
    initialize_db,
    cleanup_old_notifications,
    upsert_event,
    should_notify,
    mark_notified,
)
from notifier import send_discord_message, build_message

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def load_config():
    with open("config.yaml", "r", encoding="utf-8") as f:
        raw = f.read()
    return yaml.safe_load(os.path.expandvars(raw))


def run_once():
    cfg = load_config()
    debug = bool(cfg.get("debug", False))
    threshold = float(cfg.get("threshold_percent", 5.0))
    p_cfg = cfg["sites"]["pinnacle"]
    v_cfg = cfg["sites"]["veikkaus"]
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")

    if not webhook_url:
        logger.warning("DISCORD_WEBHOOK_URL not set — notifications will be skipped.")

    logger.info("Fetching Pinnacle and Veikkaus concurrently...")
    try:
        pinnacle_events, veikkaus_events = fetch_all(p_cfg, v_cfg, debug=debug)
    except Exception as e:
        logger.error(f"Scraping failed: {e}", exc_info=True)
        send_discord_message(webhook_url, f"⚠️ Scraping failed: {e}")
        return

    logger.info(f"Pinnacle events: {len(pinnacle_events)}")
    logger.info(f"Veikkaus events: {len(veikkaus_events)}")

    if debug:
        for label, items in [("Pinnacle", pinnacle_events), ("Veikkaus", veikkaus_events)]:
            for it in items[:2]:
                logger.debug(f"Sample {label}: {it}")

    notifications = compare_moneyline(pinnacle_events, veikkaus_events, threshold)
    logger.info(f"Candidates over threshold: {len(notifications)}")

    now = datetime.now(timezone.utc).isoformat()

    # Persist all matched events to DB
    for p in pinnacle_events:
        key = match_key_from_names(p["home_team"], p["away_team"])
        v = next(
            (x for x in veikkaus_events
             if match_key_from_names(x["home_team"], x["away_team"]) == key),
            None
        )
        veik_home = v["home_odds"] if v else None
        veik_away = v["away_odds"] if v else None
        upsert_event(key, p["home_team"], p["away_team"],
                     p["home_odds"], p["away_odds"],
                     veik_home, veik_away, now)

    # Send notifications (with re-notify if improvement grows by 5%+)
    for ev in notifications:
        side = ev["side"]
        if should_notify(ev["match_key"], side, ev["improvement_pct"]):
            send_discord_message(webhook_url, build_message(ev))
            mark_notified(ev["match_key"], side, ev["improvement_pct"], now)
            logger.info(f"Notified: {ev['match_key']} ({side}) +{ev['improvement_pct']}%")
        else:
            logger.debug(f"Skipped (already notified): {ev['match_key']} ({side})")


if __name__ == "__main__":
    initialize_db()
    cleanup_old_notifications(ttl_hours=72)
    run_once()
