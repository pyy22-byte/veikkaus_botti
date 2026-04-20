"""Test API endpoints directly."""
import requests, json

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

print("=== PINNACLE API ===")
# Get matchups
r = requests.get("https://guest.api.arcadia.pinnacle.com/0.1/leagues/1456/matchups",
                 headers=PINNACLE_HEADERS, timeout=30)
print(f"Matchups status: {r.status_code}")
matchups = r.json()
print(f"Matchups count: {len(matchups)}")
for m in matchups[:3]:
    if m.get("type") == "matchup":
        parts = m.get("participants", [])
        home = next((p["name"] for p in parts if p.get("alignment") == "home"), "?")
        away = next((p["name"] for p in parts if p.get("alignment") == "away"), "?")
        print(f"  Match: {home} vs {away} (id={m['id']})")

# Get odds
r2 = requests.get("https://guest.api.arcadia.pinnacle.com/0.1/leagues/1456/markets/straight",
                  headers=PINNACLE_HEADERS, timeout=30, params={"marketType": "moneyline"})
print(f"Odds status: {r2.status_code}")
odds = r2.json()
print(f"Odds type: {type(odds)}, length: {len(odds) if isinstance(odds, list) else 'N/A'}")
if isinstance(odds, list) and odds:
    print(f"First odds item keys: {list(odds[0].keys())}")
    print(f"First odds sample: {json.dumps(odds[0], indent=2)[:300]}")

print("\n=== VEIKKAUS API ===")
r3 = requests.get(
    "https://content.ob.veikkaus.fi/content-service/api/v1/q/drilldown-tree"
    "?drilldownNodeIds=2&eventState=OPEN_EVENT&includeMarketGroupCodeCombis=true&lang=fi-FI&channel=I",
    headers=VEIKKAUS_HEADERS, timeout=30
)
print(f"Veikkaus status: {r3.status_code}")
data = r3.json()
print(f"Response type: {type(data)}")
if isinstance(data, dict):
    print(f"Top keys: {list(data.keys())[:10]}")
    print(f"Sample: {json.dumps(data, indent=2)[:500]}")
elif isinstance(data, list):
    print(f"List length: {len(data)}")
    if data:
        print(f"First item: {json.dumps(data[0], indent=2)[:500]}")
