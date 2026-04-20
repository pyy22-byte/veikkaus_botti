"""Test API endpoints - diagnose response structures."""
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

print("=== PINNACLE: try different odds endpoints ===")
# Try without marketType param
r = requests.get("https://guest.api.arcadia.pinnacle.com/0.1/leagues/1456/markets/straight",
                 headers=PINNACLE_HEADERS, timeout=30)
print(f"No param: {r.status_code}, len={len(r.text)}")
if r.status_code == 200:
    data = r.json()
    print(f"Type: {type(data)}, len: {len(data) if isinstance(data, list) else 'dict'}")
    if isinstance(data, list) and data:
        print(f"First item keys: {list(data[0].keys())}")
        print(json.dumps(data[0], indent=2)[:400])

# Try with type=moneyline
r2 = requests.get("https://guest.api.arcadia.pinnacle.com/0.1/leagues/1456/markets/straight",
                  headers=PINNACLE_HEADERS, timeout=30, params={"type": "moneyline"})
print(f"\ntype=moneyline: {r2.status_code}, len={len(r2.text)}")

# Try matchups with odds embedded
r3 = requests.get("https://guest.api.arcadia.pinnacle.com/0.1/leagues/1456/matchups",
                  headers=PINNACLE_HEADERS, timeout=30, params={"withSpecials": "false"})
print(f"\nMatchups: {r3.status_code}")
matchups = r3.json()
# Show first matchup with participants
for m in matchups[:5]:
    if m.get("type") == "matchup" and m.get("participants"):
        print(f"Matchup: {json.dumps(m, indent=2)[:600]}")
        break

print("\n=== VEIKKAUS: parse GraphQL response ===")
r4 = requests.get(
    "https://content.ob.veikkaus.fi/content-service/api/v1/q/drilldown-tree"
    "?drilldownNodeIds=2&eventState=OPEN_EVENT&includeMarketGroupCodeCombis=true&lang=fi-FI&channel=I",
    headers=VEIKKAUS_HEADERS, timeout=30
)
data = r4.json()
print(f"Keys: {list(data.keys())}")
# Navigate into data
inner = data.get("data", {})
print(f"data keys: {list(inner.keys()) if isinstance(inner, dict) else type(inner)}")
print(json.dumps(inner, indent=2)[:1000])
