import requests, json

VEIKKAUS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://www.veikkaus.fi/",
}

print("=== PINNACLE: verify moneyline parsing ===")
from scraper import fetch_pinnacle
events = fetch_pinnacle({}, debug=True)
print(f"Pinnacle events: {len(events)}")
for e in events[:5]:
    print(f"  {e['home_team']} {e['home_odds']} vs {e['away_team']} {e['away_odds']}")

print("\n=== VEIKKAUS: try events endpoints ===")
base = "https://content.ob.veikkaus.fi/content-service/api/v1/q"
endpoints = [
    f"{base}/grouped-event-list?drilldownNodeIds=944&eventState=OPEN_EVENT&marketGroupCodeCombis=MATCH_RESULT_NO_OVERTIME,MONEY_LINE&lang=fi-FI&channel=I&maxMarkets=1",
    f"{base}/filtered-event-list?drilldownNodeIds=944&eventState=OPEN_EVENT&marketGroupCodeCombis=MATCH_RESULT_NO_OVERTIME&lang=fi-FI&channel=I",
    f"{base}/event-list?drilldownNodeIds=944&eventState=OPEN_EVENT&lang=fi-FI&channel=I",
]
for url in endpoints:
    r = requests.get(url, headers=VEIKKAUS_HEADERS, timeout=30)
    print(f"\n{url.split('?')[0].split('/')[-1]}: {r.status_code}, len={len(r.text)}")
    if r.status_code == 200 and r.text:
        data = r.json()
        print(f"  keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
        print(json.dumps(data, ensure_ascii=False, indent=2)[:1500])
