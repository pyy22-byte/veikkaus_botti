"""Debug Veikkaus response structure."""
import requests, json, logging
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
from datetime import datetime, timezone, timedelta

VEIKKAUS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://www.veikkaus.fi/fi/pitkaveto/fi/sports/competition/944/jaakiekko/usa/nhl/matches",
}

now = datetime.now(timezone.utc)
start = (now - timedelta(days=1)).replace(hour=21, minute=0, second=0, microsecond=0)
end = (now + timedelta(days=7)).replace(hour=21, minute=59, second=59, microsecond=0)
fmt = "%Y-%m-%dT%H:%M:%SZ"

r = requests.get(
    "https://content.ob.veikkaus.fi/content-service/api/v1/q/event-list",
    headers=VEIKKAUS_HEADERS,
    params={
        "startTimeFrom": start.strftime(fmt), "startTimeTo": end.strftime(fmt),
        "maxMarkets": 10, "orderMarketsBy": "displayOrder",
        "excludeEventsWithNoMarkets": "false", "eventSortsIncluded": "MTCH",
        "includeChildMarkets": "true", "prioritisePrimaryMarkets": "true",
        "includeCommentary": "false", "includeMedia": "false",
        "drilldownTagIds": "944", "useMarketGroupCodeCombis": "true",
        "marketGroupCodeCombiId": "55", "lang": "fi-FI", "channel": "I",
    }, timeout=30
)
data = r.json()
events = data["data"]["events"]
print(f"Events: {len(events)}")

# Print first event full structure
if events:
    print("\nFirst event structure:")
    print(json.dumps(events[0], ensure_ascii=False, indent=2))
