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

print("=== PINNACLE matchup full structure ===")
r = requests.get("https://guest.api.arcadia.pinnacle.com/0.1/leagues/1456/matchups",
                 headers=PINNACLE_HEADERS, timeout=30)
matchups = r.json()
# Find first real matchup with prices
for m in matchups:
    if m.get("type") == "matchup" and m.get("participants"):
        print(json.dumps(m, indent=2)[:1500])
        break

print("\n=== PINNACLE: try special=false matchups with prices ===")
r2 = requests.get("https://guest.api.arcadia.pinnacle.com/0.1/leagues/1456/matchups",
                  headers=PINNACLE_HEADERS, timeout=30,
                  params={"specialsOnly": "false"})
data2 = r2.json()
# Look for prices in matchup
for m in data2[:10]:
    if "prices" in str(m):
        print(f"Found prices in matchup!")
        print(json.dumps(m, indent=2)[:800])
        break

print("\n=== VEIKKAUS GraphQL data structure ===")
r3 = requests.get(
    "https://content.ob.veikkaus.fi/content-service/api/v1/q/drilldown-tree"
    "?drilldownNodeIds=2&eventState=OPEN_EVENT&includeMarketGroupCodeCombis=true&lang=fi-FI&channel=I",
    headers=VEIKKAUS_HEADERS, timeout=30
)
data3 = r3.json()
inner = data3.get("data", {})
print(f"data keys: {list(inner.keys()) if isinstance(inner, dict) else type(inner)}")
# Print first 2000 chars of data
print(json.dumps(inner, indent=2)[:2000])
