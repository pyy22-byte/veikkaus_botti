from playwright.sync_api import sync_playwright


def _launch():
    """Launch headless Chromium with a desktop UA."""
    p = sync_playwright().start()
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"),
        locale="fi-FI"
    )
    page = context.new_page()
    return p, browser, context, page


def _accept_cookies(page):
    """Best-effort cookie/consent clickers (safe if not present)."""
    selectors = [
        'button:has-text("ACCEPT")',
        'button:has-text("I Accept")',
        'button:has-text("I understand")',
        'button:has-text("Hyväksy")',
        'button:has-text("Salli")',
    ]
    for sel in selectors:
        try:
            loc = page.locator(sel)
            if loc.count() and loc.first.is_visible():
                loc.first.click(timeout=1000)
                break
        except Exception:
            pass


def fetch_pinnacle(cfg):
    """
    Returns list of dicts:
      {home_team, away_team, home_odds, away_odds}
    From NHL matchups page.
    """
    p, browser, context, page = _launch()
    events = []
    try:
        page.goto(cfg["url"], wait_until="domcontentloaded", timeout=60000)
        _accept_cookies(page)
        # Odota että ensimmäinen ottelurivi ilmestyy
        page.wait_for_selector(cfg["event_selector"], timeout=60000)

        rows = page.locator(cfg["event_selector"])
        for i in range(rows.count()):
            row = rows.nth(i)

            teams = row.locator(cfg["team_selector"])
            if teams.count() < 2:
                continue
            home = teams.nth(0).inner_text().strip()
            away = teams.nth(1).inner_text().strip()

            money = row.locator(cfg["money_container_selector"])
            if money.count() == 0:
                continue
            prices = money.locator(cfg["price_selector"])
            if prices.count() < 2:
                continue

            try:
                home_odds = float(prices.nth(0).inner_text().strip())
                away_odds = float(prices.nth(1).inner_text().strip())
            except ValueError:
                continue

            events.append({
                "home_team": home,
                "away_team": away,
                "home_odds": home_odds,
                "away_odds": away_odds
            })
    finally:
        browser.close()
        context.close()
        p.stop()
    return events


def fetch_veikkaus(cfg):
    """
    Goes to Pitkäveto list page, collects match links,
    then opens each match page and reads moneyline buttons:
      button[data-test-id$="MONEY_LINE"]
    Returns list of dicts like Pinnacle.
    """
    p, browser, context, page = _launch()
    events = []
    try:
        # 1) Listanäkymä: kerää ottelulinkit
        page.goto(cfg["list_url"], wait_until="domcontentloaded", timeout=60000)
        _accept_cookies(page)
        page.wait_for_selector(cfg["list_event_selector"], timeout=60000)

        links = []
        for a in page.locator(cfg["list_event_selector"]).all():
            href = a.get_attribute("href")
            if not href:
                continue
            if href.startswith("/"):
                href = "https://www.veikkaus.fi" + href
            links.append(href)

        # 2) Käy jokainen ottelusivu ja hae moneyline
        for href in links:
            try:
                page.goto(href, wait_until="domcontentloaded", timeout=60000)
                _accept_cookies(page)
                page.wait_for_selector(cfg["ml_button_selector"], timeout=30000)

                btns = page.locator(cfg["ml_button_selector"])
                if btns.count() < 2:
                    continue

                data = []
                for j in range(2):
                    btn = btns.nth(j)
                    team_el = btn.locator(cfg["ml_team_selector"]).first
                    odd_el = btn.locator(cfg["ml_price_selector"]).first
                    if not (team_el.count() and odd_el.count()):
                        data = []
                        break
                    name = team_el.inner_text().strip()
                    txt = odd_el.inner_text().strip().replace(",", ".")
                    data.append((name, float(txt)))

                if len(data) != 2:
                    continue

                (home_name, home_odds), (away_name, away_odds) = data
                events.append({
                    "home_team": home_name,
                    "away_team": away_name,
                    "home_odds": home_odds,
                    "away_odds": away_odds
                })
            except Exception:
                # ohita yksittäisen sivun virhe ja jatka
                continue
    finally:
        browser.close()
        context.close()
        p.stop()
    return events
