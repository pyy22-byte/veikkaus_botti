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
        # Step 1: matchups → id→teams index
        r = requests.get(
            f"https://guest.api.arcadia.pinnacle.com/0.1/leagues/{NHL_LEAGUE_ID}/matchups",
            headers=PINNACLE_HEADERS, timeout=30
        )
        r.raise_for_status()
        matchups = r.json()

        matchup_idx = {}
        for m in matchups:
            if m.get("type") != "matchup":
                continue
            participants = m.get("participants", [])
            home = next((p["name"] for p in participants if p.get("alignment") == "home"), None)
            away = next((p["name"] for p in participants if p.get("alignment") == "away"), None)
            if home and away:
                matchup_idx[m["id"]] = {"home_team": home, "away_team": away}

        logger.debug(f"Pinnacle matchups indexed: {len(matchup_idx)}")

        # Step 2: all markets
        r2 = requests.get(
            f"https://guest.api.arcadia.pinnacle.com/0.1/leagues/{NHL_LEAGUE_ID}/markets/straight",
            headers=PINNACLE_HEADERS, timeout=30
        )
        r2.raise_for_status()
        markets = r2.json()

        # Step 3: filter moneyline, period=0, not alternate
        for market in markets:
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
    if debug:
        for ev in events[:3]:
            logger.debug(f"  Pinnacle: {ev}")
    return events


def fetch_veikkaus(cfg, debug=False):
    events = []
    try:
        now = datetime.now(timezone.utc)
        # startTimeFrom = yesterday 21:00 UTC (catch late games)
        start = (now - timedelta(days=1)).replace(hour=21, minute=0, second=0, microsecond=0)
        # startTimeTo = 7 days ahead
        end = (now + timedelta(days=7)).replace(hour=21, minute=59, second=59, microsecond=0)

        fmt = "%Y-%m-%dT%H:%M:%SZ"
        params = {
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
            "marketGroupCodeCombiId": "55",  # "Voittaja" = ML market group
            "lang": "fi-FI",
            "channel": "I",
        }

        r = requests.get(
            "https://content.ob.veikkaus.fi/content-service/api/v1/q/event-list",
            headers=VEIKKAUS_HEADERS, params=params, timeout=30
        )
        logger.debug(f"Veikkaus event-list: {r.status_code}, len={len(r.text)}")
        r.raise_for_status()
        data = r.json()

        if debug:
            import json
            logger.debug(f"Veikkaus response: {json.dumps(data, ensure_ascii=False)[:1000]}")

        events = _parse_veikkaus(data, debug)

    except Exception as e:
        logger.error(f"Veikkaus fetch failed: {e}", exc_info=True)

    logger.info(f"Veikkaus events: {len(events)}")
    if debug:
        for ev in events[:3]:
            logger.debug(f"  Veikkaus: {ev}")
    return events


def _parse_veikkaus(data, debug=False):
    events = []
    if not isinstance(data, dict):
        return events

    # Unwrap GraphQL / OpenBet wrapper
    inner = data.get("data", data)
    event_list = inner.get("events") or []

    if debug:
        logger.debug(f"Veikkaus event count: {len(event_list)}")

    for event in event_list:
        markets = event.get("markets", [])
        for market in markets:
            outcomes = market.get("outcomes", [])
            # Filter out draw outcomes
            ml_outcomes = [
                o for o in outcomes
                if o.get("type", "") != "draw"
                and o.get("outcomeMeaningMinorCode", "") != "X"
                and "tasapeli" not in (o.get("name") or "").lower()
            ]
            if len(ml_outcomes) != 2:
                continue

            o1, o2 = ml_outcomes[0], ml_outcomes[1]
            try:
                p1 = float(o1.get("priceDec") or o1.get("price") or 0)
                p2 = float(o2.get("priceDec") or o2.get("price") or 0)
                n1 = (o1.get("name") or "").strip()
                n2 = (o2.get("name") or "").strip()
                if p1 > 1.0 and p2 > 1.0 and n1 and n2:
                    events.append({
                        "home_team": n1,
                        "away_team": n2,
                        "home_odds": p1,
                        "away_odds": p2,
                    })
                    break
            except (TypeError, ValueError):
                pass

    return events


def fetch_all(p_cfg, v_cfg, debug=False):
    pinnacle_events = fetch_pinnacle(p_cfg, debug=debug)
    veikkaus_events = fetch_veikkaus(v_cfg, debug=debug)
    return pinnacle_events, veikkaus_events
