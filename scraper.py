import logging
import requests

logger = logging.getLogger(__name__)

PINNACLE_SPORTS_URL = "https://guest.api.arcadia.pinnacle.com/0.1/sports"
PINNACLE_LEAGUES_URL = "https://guest.api.arcadia.pinnacle.com/0.1/leagues/{league_id}/matchups"
PINNACLE_ODDS_URL = "https://guest.api.arcadia.pinnacle.com/0.1/leagues/{league_id}/markets/straight"

VEIKKAUS_EVENTS_URL = (
    "https://content.ob.veikkaus.fi/content-service/api/v1/q/drilldown-tree"
    "?drilldownNodeIds=2&eventState=OPEN_EVENT"
    "&includeMarketGroupCodeCombis=true&lang=fi-FI&channel=I"
)

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

# Pinnacle NHL league ID
NHL_LEAGUE_ID = 1456  # NHL


def fetch_pinnacle(cfg, debug=False):
    """Fetch NHL moneyline odds from Pinnacle public API."""
    events = []
    try:
        # Get matchups
        matchups_url = PINNACLE_LEAGUES_URL.format(league_id=NHL_LEAGUE_ID)
        r = requests.get(matchups_url, headers=PINNACLE_HEADERS, timeout=30)
        r.raise_for_status()
        matchups = r.json()
        logger.debug(f"Pinnacle matchups: {len(matchups)}")

        # Get moneyline odds
        odds_url = PINNACLE_ODDS_URL.format(league_id=NHL_LEAGUE_ID)
        r2 = requests.get(odds_url, headers=PINNACLE_HEADERS, timeout=30,
                          params={"marketType": "moneyline"})
        r2.raise_for_status()
        odds_data = r2.json()
        logger.debug(f"Pinnacle odds response keys: {list(odds_data.keys()) if isinstance(odds_data, dict) else type(odds_data)}")

        # Build matchup index
        matchup_idx = {}
        for m in matchups:
            if m.get("type") != "matchup":
                continue
            participants = m.get("participants", [])
            if len(participants) < 2:
                continue
            home = next((p["name"] for p in participants if p.get("alignment") == "home"), None)
            away = next((p["name"] for p in participants if p.get("alignment") == "away"), None)
            if home and away:
                matchup_idx[m["id"]] = {"home_team": home, "away_team": away}

        # Parse odds
        odds_list = odds_data if isinstance(odds_data, list) else odds_data.get("markets", [])
        for market in odds_list:
            matchup_id = market.get("matchupId")
            if matchup_id not in matchup_idx:
                continue
            prices = market.get("prices", [])
            home_price = next((p["price"] for p in prices if p.get("designation") == "home"), None)
            away_price = next((p["price"] for p in prices if p.get("designation") == "away"), None)
            if home_price and away_price:
                m = matchup_idx[matchup_id]
                # Convert American odds to decimal
                events.append({
                    "home_team": m["home_team"],
                    "away_team": m["away_team"],
                    "home_odds": _american_to_decimal(home_price),
                    "away_odds": _american_to_decimal(away_price),
                })

    except Exception as e:
        logger.error(f"Pinnacle API fetch failed: {e}", exc_info=True)

    logger.info(f"Pinnacle events fetched: {len(events)}")
    return events


def _american_to_decimal(american):
    """Convert American odds to decimal odds."""
    if american > 0:
        return round(american / 100 + 1, 3)
    else:
        return round(100 / abs(american) + 1, 3)


def fetch_veikkaus(cfg, debug=False):
    """Fetch NHL odds from Veikkaus OpenBet content API."""
    events = []
    try:
        r = requests.get(VEIKKAUS_EVENTS_URL, headers=VEIKKAUS_HEADERS, timeout=30)
        r.raise_for_status()
        data = r.json()
        logger.debug(f"Veikkaus API response type: {type(data)}")

        # Parse the OpenBet drilldown-tree response
        # Structure varies but typically: SSResponse > {types, events, markets, children}
        events = _parse_veikkaus_response(data, debug)

    except Exception as e:
        logger.error(f"Veikkaus API fetch failed: {e}", exc_info=True)

    logger.info(f"Veikkaus events fetched: {len(events)}")
    return events


def _parse_veikkaus_response(data, debug=False):
    """Parse OpenBet drilldown-tree JSON to extract NHL ML events."""
    events = []

    # Log structure for debugging
    if debug:
        if isinstance(data, dict):
            logger.debug(f"Top-level keys: {list(data.keys())[:20]}")
        elif isinstance(data, list):
            logger.debug(f"Top-level list length: {len(data)}")
            if data:
                logger.debug(f"First item keys: {list(data[0].keys())[:20] if isinstance(data[0], dict) else type(data[0])}")

    # Try different response structures
    # OpenBet typically wraps in SSResponse
    if isinstance(data, dict):
        # Try direct access to events
        raw_events = (data.get("SSResponse", {}).get("children", []) or
                      data.get("events", []) or
                      data.get("children", []))

        for item in raw_events:
            parsed = _extract_event(item)
            if parsed:
                events.append(parsed)

    elif isinstance(data, list):
        for item in data:
            parsed = _extract_event(item)
            if parsed:
                events.append(parsed)

    return events


def _extract_event(item):
    """Try to extract a matchup with ML odds from an OpenBet event object."""
    if not isinstance(item, dict):
        return None

    # Look for event name and children (markets)
    name = item.get("name", "") or item.get("eventName", "")
    children = item.get("children", []) or item.get("markets", [])

    # Check if this looks like an NHL match (two teams vs each other)
    if " v " not in name and " vs " not in name:
        # Recurse into children
        for child in children:
            result = _extract_event(child)
            if result:
                return result
        return None

    # Try to find ML market (2-way, no draw)
    for market in children:
        market_name = market.get("name", "") or market.get("marketName", "")
        if "Money" in market_name or "moneyline" in market_name.lower() or "ML" in market_name:
            outcomes = market.get("children", []) or market.get("outcomes", [])
            if len(outcomes) == 2:
                o1, o2 = outcomes[0], outcomes[1]
                try:
                    p1 = float(o1.get("priceDec", 0) or o1.get("price", 0))
                    p2 = float(o2.get("priceDec", 0) or o2.get("price", 0))
                    n1 = o1.get("name", "") or o1.get("outcomeName", "")
                    n2 = o2.get("name", "") or o2.get("outcomeName", "")
                    if p1 > 1.0 and p2 > 1.0 and n1 and n2:
                        return {
                            "home_team": n1,
                            "away_team": n2,
                            "home_odds": p1,
                            "away_odds": p2,
                        }
                except (TypeError, ValueError):
                    pass

    return None


def fetch_all(p_cfg, v_cfg, debug=False):
    """Fetch Pinnacle and Veikkaus. Returns (pinnacle_events, veikkaus_events)."""
    pinnacle_events = fetch_pinnacle(p_cfg, debug=debug)
    veikkaus_events = fetch_veikkaus(v_cfg, debug=debug)
    return pinnacle_events, veikkaus_events
