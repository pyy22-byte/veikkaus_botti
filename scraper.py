import requests
from bs4 import BeautifulSoup

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}

def _get(url):
    resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=25)
    resp.raise_for_status()
    return resp.text

def fetch_pinnacle(cfg):
    """Palauttaa listan dict-olioita: home_team, away_team, home_odds, away_odds"""
    html = _get(cfg["url"])
    soup = BeautifulSoup(html, "html.parser")
    events = []
    for row in soup.select(cfg["event_selector"]):
        teams = [el.get_text(strip=True) for el in row.select(cfg["team_selector"])]
        if len(teams) < 2:
            continue
        home, away = teams[0], teams[1]  # Pinnacle listaa yleensä muodossa home vs away

        money = row.select_one(cfg["money_container_selector"])
        if not money:
            continue
        prices = money.select(cfg["price_selector"])
        if len(prices) < 2:
            continue
        try:
            home_odds = float(prices[0].get_text(strip=True))
            away_odds = float(prices[1].get_text(strip=True))
        except ValueError:
            continue

        events.append({
            "home_team": home,
            "away_team": away,
            "home_odds": home_odds,
            "away_odds": away_odds
        })
    return events

def fetch_veikkaus(cfg):
    """Hakee listanäkymästä ottelulinkit ja käy jokaisen ottelusivun, josta lukee moneyline-kertoimet."""
    list_html = _get(cfg["list_url"])
    soup = BeautifulSoup(list_html, "html.parser")
    events = []

    links = []
    for a in soup.select(cfg["list_event_selector"]):
        href = a.get("href")
        if not href:
            continue
        if href.startswith("/"):
            href = "https://www.veikkaus.fi" + href
        links.append(href)

    for href in links:
        try:
            html = _get(href)
        except Exception:
            continue
        psoup = BeautifulSoup(html, "html.parser")
        buttons = psoup.select(cfg["ml_button_selector"])
        if len(buttons) < 2:
            continue

        data = []
        for btn in buttons[:2]:
            team_el = btn.select_one(cfg["ml_team_selector"])
            odd_el = btn.select_one(cfg["ml_price_selector"])
            if not team_el or not odd_el:
                data.append(None); continue
            name = team_el.get_text(strip=True)
            try:
                odd = float(odd_el.get_text(strip=True).replace(",", "."))
            except ValueError:
                data.append(None); continue
            data.append((name, odd))

        if None in data or len(data) < 2:
            continue

        (home_team, home_odds), (away_team, away_odds) = data[0], data[1]
        events.append({
            "home_team": home_team,
            "away_team": away_team,
            "home_odds": home_odds,
            "away_odds": away_odds
        })

    return events
