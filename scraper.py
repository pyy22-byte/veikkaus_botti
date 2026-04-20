import logging
import requests
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

PINNACLE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Accept": "application/json",
    "X-Device-UUID": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
}
VEIKKAUS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://www.veikkaus.fi/fi/pitkaveto/fi/sports/competition/944/jaakiekko/usa/nhl/matches",
}

NHL_LEAGUE_ID = 1456


def _american_to_decimal(american):
    if american > 0:
        return round(american / 100 + 1, 3)
    else:
        return round(100 / abs(american) + 1, 3)


def fetch_pinnacle(cfg, debug=False):
    events = []
    try:
        r = requests.get(
            f"https://guest.api.arcadia.pinnacle.com/0.1/leagues/{NHL_LEAGUE_ID}/matchups",
            headers=PINNACLE_HEADERS, timeout=30
        )
        r.raise_for_status()

        matchup_idx = {}
        for m in r.json():
            if m.get("type") != "matchup":
                continue
            parts = m.get("participants", [])
            home = next((p["name"] for p in parts if p.get("alignment") == "home"), None)
            away = next((p["name"] for p in parts if p.get("alignment") == "away"), None)
            if home and away:
                matchup_idx[m["id"]] = {"home_team": home, "away_team": away}

        logger.debug(f"Pinnacle matchups: {len(matchup_idx)}")

        r2 = requests.get(
            f"https://guest.api.arcadia.pinnacle.com/0.1/leagues/{NHL_LEAGUE_ID}/markets/straight",
            headers=PINNACLE_HEADERS, timeout=30
        )
        r2.raise_for_status()

        for market in r2.json():
            if market.get("type") != "moneyline":
                continue
            if market.get("period", 0) != 0:
                continue
            if market.get("isAlternate", False):
                continue
            matchup_id = market.get("matchupId")
            if matchup_id not in matchup_idx:
                continue
            prices = market.get("prices", [])
            home_price = next((p["price"] for p in prices if p.get("designation") == "home"), None)
            away_price = next((p["price"] for p in prices if p.get("designation") == "away"), None)
            if home_price is None or away_price is None:
                continue
            m = matchup_idx[matchup_id]
            events.append({
                "home_team": m["home_team"],
                "away_team": m["away_team"],
                "home_odds": _american_to_decimal(home_price),
                "away_odds": _american_to_decimal(away_price),
            })

    except Exception as e:
        logger.error(f"Pinnacle fetch failed: {e}", exc_info=True)

    logger.info(f"Pinnacle events: {len(events)}")
    return events


def fetch_veikkaus(cfg, debug=False):
    events = []
    try:
        now = datetime.now(timezone.utc)
        start = (now - timedelta(days=1)).replace(hour=21, minute=0, second=0, microsecond=0)
        end = (now + timedelta(days=7)).replace(hour=21, minute=59, second=59, microsecond=0)
        fmt = "%Y-%m-%dT%H:%M:%SZ"

        r = requests.get(
            "https://content.ob.veikkaus.fi/content-service/api/v1/q/event-list",
            headers=VEIKKAUS_HEADERS,
            params={
                "startTimeFrom": start.strftime(fmt),
                "startTimeTo": end.strftime(fmt),
                "maxMarkets": 10,
                "orderMarketsBy": "displayOrder",
                "excludeEventsWithNoMarkets": "false",
                "eventSortsIncluded": "MTCH",
                "includeChildMarkets": "true",
                "prioritisePrimaryMarkets": "true",
                "includeCommentary": "false",
                "includeMedia": "false",
                "drilldownTagIds": "944",
                "useMarketGroupCodeCombis": "true",
                "marketGroupCodeCombiId": "55",
                "lang": "fi-FI",
                "channel": "I",
            },
            timeout=30
        )
        r.raise_for_status()
        event_list = r.json().get("data", {}).get("events") or []
        logger.debug(f"Veikkaus events received: {len(event_list)}")

        for event in event_list:
            teams = event.get("teams", [])
            home_name = next((t["name"] for t in teams if t.get("side") == "HOME"), None)
            away_name = next((t["name"] for t in teams if t.get("side") == "AWAY"), None)

            for market in event.get("markets", []):
                # Use MONEY_LINE market (2-way, no draw)
                if market.get("groupCode") != "MONEY_LINE":
                    continue

                outcomes = market.get("outcomes", [])
                if len(outcomes) != 2:
                    continue

                # Get prices using subType: H=home, A=away
                home_dec = None
                away_dec = None
                home_out = None
                away_out = None

                for o in outcomes:
                    prices = o.get("prices", [])
                    if not prices:
                        continue
                    dec = prices[0].get("decimal")
                    sub = o.get("subType", "")
                    name = o.get("name", "")
                    if sub == "H":
                        home_dec = dec
                        home_out = name
                    elif sub == "A":
                        away_dec = dec
                        away_out = name

                if home_dec and away_dec:
                    events.append({
                        "home_team": home_name or home_out,
                        "away_team": away_name or away_out,
                        "home_odds": float(home_dec),
                        "away_odds": float(away_dec),
                    })
                    break  # one ML market per event

    except Exception as e:
        logger.error(f"Veikkaus fetch failed: {e}", exc_info=True)

    logger.info(f"Veikkaus events: {len(events)}")
    return events


def fetch_all(p_cfg, v_cfg, debug=False):
    pinnacle_events = fetch_pinnacle(p_cfg, debug=debug)
    veikkaus_events = fetch_veikkaus(v_cfg, debug=debug)
    return pinnacle_events, veikkaus_events
