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

print("=== PINNACLE: try markets endpoint variations ===")
endpoints = [
    "/0.1/leagues/1456/markets/straight",
    "/0.1/leagues/1456/markets/straight?type=moneyline",
    "/0.1/leagues/1456/markets/straight?primaryOnly=true",
]
for ep in endpoints:
    r = requests.get(f"https://guest.api.arcadia.pinnacle.com{ep}",
                     headers=PINNACLE_HEADERS, timeout=30)
    print(f"{ep}: {r.status_code}, len={len(r.text)}")
    if r.status_code == 200 and r.text:
        data = r.json()
        print(f"  type={type(data)}, len={len(data) if isinstance(data, list) else 'dict'}")
        if isinstance(data, list) and data:
            print(f"  first keys: {list(data[0].keys())}")
            print(f"  first item: {json.dumps(data[0], indent=2)[:400]}")

print("\n=== PINNACLE: get a specific matchup's markets ===")
# Get first matchup ID
r = requests.get("https://guest.api.arcadia.pinnacle.com/0.1/leagues/1456/matchups",
                 headers=PINNACLE_HEADERS, timeout=30)
matchups = r.json()
first_id = None
for m in matchups:
    if m.get("type") == "matchup" and m.get("participants"):
        first_id = m["id"]
        parts = m["participants"]
        home = next((p["name"] for p in parts if p.get("alignment") == "home"), "?")
        away = next((p["name"] for p in parts if p.get("alignment") == "away"), "?")
        print(f"First matchup: {home} vs {away}, id={first_id}")
        break

if first_id:
    r2 = requests.get(f"https://guest.api.arcadia.pinnacle.com/0.1/matchups/{first_id}/markets/straight",
                      headers=PINNACLE_HEADERS, timeout=30)
    print(f"Matchup markets: {r2.status_code}, len={len(r2.text)}")
    if r2.status_code == 200 and r2.text:
        print(json.dumps(r2.json(), indent=2)[:600])

print("\n=== VEIKKAUS GraphQL full data ===")
r3 = requests.get(
    "https://content.ob.veikkaus.fi/content-service/api/v1/q/drilldown-tree"
    "?drilldownNodeIds=2&eventState=OPEN_EVENT&includeMarketGroupCodeCombis=true&lang=fi-FI&channel=I",
    headers=VEIKKAUS_HEADERS, timeout=30
)
data3 = r3.json()
inner = data3.get("data", {})
print(f"data keys: {list(inner.keys()) if isinstance(inner, dict) else type(inner)}")
# Print structured sample
print(json.dumps(inner, indent=2)[:3000])
