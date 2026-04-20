import logging
import requests

logger = logging.getLogger(__name__)

PINNACLE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Accept": "application/json",
    "X-Device-UUID": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
}
VEIKKAUS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://www.veikkaus.fi/",
}

NHL_LEAGUE_ID = 1456
# Veikkaus NHL competition node ID (from drilldown-tree: USA/NHL)
VEIKKAUS_NHL_NODE_ID = "944"


def _american_to_decimal(american):
    if american > 0:
        return round(american / 100 + 1, 3)
    else:
        return round(100 / abs(american) + 1, 3)


def fetch_pinnacle(cfg, debug=False):
    events = []
    try:
        # Step 1: get matchups to build id→teams index
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

        # Step 2: get all markets (no param = all types)
        r2 = requests.get(
            f"https://guest.api.arcadia.pinnacle.com/0.1/leagues/{NHL_LEAGUE_ID}/markets/straight",
            headers=PINNACLE_HEADERS, timeout=30
        )
        r2.raise_for_status()
        markets = r2.json()

        # Step 3: filter moneyline markets, period=0 (full game), not alternate
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
            logger.debug(f"  Pinnacle sample: {ev}")
    return events


def fetch_veikkaus(cfg, debug=False):
    """
    Fetch Veikkaus NHL odds using the events API.
    The drilldown-tree only gives hierarchy — we need the events endpoint.
    """
    events = []
    try:
        # Use the grouped-event-list endpoint with NHL competition node
        url = (
            "https://content.ob.veikkaus.fi/content-service/api/v1/q/grouped-event-list"
            f"?drilldownNodeIds={VEIKKAUS_NHL_NODE_ID}"
            "&eventState=OPEN_EVENT"
            "&marketGroupCodeCombis=MATCH_RESULT_NO_OVERTIME,MONEY_LINE"
            "&lang=fi-FI&channel=I"
            "&maxMarkets=1"
        )
        r = requests.get(url, headers=VEIKKAUS_HEADERS, timeout=30)
        logger.debug(f"Veikkaus grouped-event-list: {r.status_code}, len={len(r.text)}")

        if r.status_code != 200:
            # Fallback: try filtered-event-list
            url2 = (
                "https://content.ob.veikkaus.fi/content-service/api/v1/q/filtered-event-list"
                f"?drilldownNodeIds={VEIKKAUS_NHL_NODE_ID}"
                "&eventState=OPEN_EVENT"
                "&marketGroupCodeCombis=MATCH_RESULT_NO_OVERTIME"
                "&lang=fi-FI&channel=I"
            )
            r = requests.get(url2, headers=VEIKKAUS_HEADERS, timeout=30)
            logger.debug(f"Veikkaus filtered-event-list: {r.status_code}, len={len(r.text)}")

        r.raise_for_status()
        data = r.json()

        if debug:
            import json
            logger.debug(f"Veikkaus response keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
            if isinstance(data, dict):
                logger.debug(f"Veikkaus sample: {json.dumps(data, ensure_ascii=False)[:1000]}")

        events = _parse_veikkaus_events(data, debug)

    except Exception as e:
        logger.error(f"Veikkaus fetch failed: {e}", exc_info=True)

    logger.info(f"Veikkaus events: {len(events)}")
    if debug:
        for ev in events[:3]:
            logger.debug(f"  Veikkaus sample: {ev}")
    return events


def _parse_veikkaus_events(data, debug=False):
    events = []
    if not isinstance(data, dict):
        return events

    # GraphQL wrapper
    inner = data.get("data", data)

    # Find events list
    event_list = (
        inner.get("events") or
        inner.get("filteredEventList", {}).get("events") or
        inner.get("groupedEventList", {}).get("events") or
        []
    )

    # Also search nested
    if not event_list:
        for v in inner.values():
            if isinstance(v, dict):
                event_list = v.get("events", [])
                if event_list:
                    break

    for event in event_list:
        name = event.get("name", "") or event.get("eventName", "")
        markets = event.get("markets", []) or event.get("children", [])

        for market in markets:
            market_name = market.get("name", "") or market.get("marketName", "")
            group_code = market.get("marketGroupCode", "")

            # Match ML market: MONEY_LINE or MATCH_RESULT_NO_OVERTIME (2-way)
            if group_code not in ("MONEY_LINE", "MATCH_RESULT_NO_OVERTIME"):
                continue

            outcomes = market.get("outcomes", []) or market.get("children", [])
            # Filter out draw
            outcomes = [o for o in outcomes if o.get("type", "") != "draw"
                       and "tasapeli" not in (o.get("name", "") or "").lower()
                       and o.get("name", "") not in ("X", "Draw", "Tasapeli")]

            if len(outcomes) != 2:
                continue

            o1, o2 = outcomes[0], outcomes[1]
            try:
                p1 = float(o1.get("priceDec") or o1.get("price") or 0)
                p2 = float(o2.get("priceDec") or o2.get("price") or 0)
                n1 = (o1.get("name") or o1.get("outcomeName") or "").strip()
                n2 = (o2.get("name") or o2.get("outcomeName") or "").strip()
                if p1 > 1.0 and p2 > 1.0 and n1 and n2:
                    events.append({
                        "home_team": n1,
                        "away_team": n2,
                        "home_odds": p1,
                        "away_odds": p2,
                    })
                    break  # one ML market per event is enough
            except (TypeError, ValueError):
                pass

    return events


def fetch_all(p_cfg, v_cfg, debug=False):
    pinnacle_events = fetch_pinnacle(p_cfg, debug=debug)
    veikkaus_events = fetch_veikkaus(v_cfg, debug=debug)
    return pinnacle_events, veikkaus_events
