from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright

def _safe_close(browser=None, context=None, p=None):
    for obj in (context, browser):
        try:
            if obj: obj.close()
        except Exception:
            pass
    try:
        if p: p.stop()
    except Exception:
        pass

def _launch(headless=True, slow_mo=0):
    p = sync_playwright().start()
    browser = p.chromium.launch(headless=headless, slow_mo=slow_mo)
    context = browser.new_context(
        user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
        locale="fi-FI"
    )
    page = context.new_page()
    return p, browser, context, page

def _accept_cookies(page):
    selectors = [
        'button#onetrust-accept-btn-handler',
        'button:has-text("ACCEPT")','button:has-text("I Accept")',
        'button:has-text("I understand")','button:has-text("Hyväksy")','button:has-text("Salli")','text=Hyväksyn',
    ]
    for sel in selectors:
        try:
            loc = page.locator(sel)
            if loc.count() and loc.first.is_visible():
                loc.first.click(timeout=1500); break
        except Exception: pass

def _dbg_dump(page, name, debug_dir):
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    try:
        (debug_dir/f"{name}_{ts}.html").write_text(page.content(), encoding="utf-8")
        page.screenshot(path=str(debug_dir/f"{name}_{ts}.png"), full_page=True)
    except Exception: pass

def fetch_pinnacle(cfg, debug=False):
    p, browser, context, page = _launch(headless=True)
    events = []
    debug_dir = Path("debug"); 
    if debug: debug_dir.mkdir(exist_ok=True)
    try:
        try:
            page.goto(cfg["url"], wait_until="networkidle", timeout=60000)
            _accept_cookies(page)
            page.wait_for_selector(cfg["event_selector"], timeout=60000)
        except Exception as e:
            if debug:
                print(f"[DEBUG] Pinnacle navigation/wait failed: {e}")
                _dbg_dump(page, "pinnacle_nav_fail", debug_dir)
            return []
        rows = page.locator(cfg["event_selector"])
        if debug: print(f"[DEBUG] Pinnacle rows: {rows.count()}")
        for i in range(rows.count()):
            row = rows.nth(i)
            teams = row.locator(cfg["team_selector"])
            if teams.count()<2: continue
            home = teams.nth(0).inner_text().strip()
            away = teams.nth(1).inner_text().strip()
            money = row.locator(cfg["money_container_selector"])
            if money.count()==0: continue
            prices = money.locator(cfg["price_selector"])
            if prices.count()<2: continue
            try:
                home_odds = float(prices.nth(0).inner_text().strip())
                away_odds = float(prices.nth(1).inner_text().strip())
            except ValueError:
                continue
            events.append({"home_team":home,"away_team":away,"home_odds":home_odds,"away_odds":away_odds})
        if debug and not events:
            print("[DEBUG] Pinnacle returned 0 events → dumping snapshot")
            _dbg_dump(page, "pinnacle_empty", debug_dir)
    finally:
        _safe_close(browser=browser, context=context, p=p)

    return events


def fetch_veikkaus(cfg, debug=False):
    p, browser, context, page = _launch(headless=True)
    events = []
    debug_dir = Path("debug"); 
    if debug: debug_dir.mkdir(exist_ok=True)
    try:
        try:
            page.goto(cfg["list_url"], wait_until="networkidle", timeout=60000)
            _accept_cookies(page)
            page.wait_for_selector(cfg["list_event_selector"], timeout=60000)
        except Exception as e:
            if debug:
                print(f"[DEBUG] Veikkaus list navigation/wait failed: {e}")
                _dbg_dump(page, "veikkaus_list_nav_fail", debug_dir)
            return []
        anchors = page.locator(cfg["list_event_selector"])
        link_count = anchors.count()
        links = []
        for i in range(link_count):
            a = anchors.nth(i)
            href = a.get_attribute("href")
            if not href: continue
            if href.startswith("/"):
                href = "https://www.veikkaus.fi"+href
            links.append(href)
        if debug: print(f"[DEBUG] Veikkaus match links: {len(links)}")
        for href in links:
            try:
                page.goto(href, wait_until="networkidle", timeout=60000)
                _accept_cookies(page)
                page.wait_for_selector(cfg["ml_button_selector"], timeout=30000)
            except Exception as e:
                if debug:
                    print(f"[DEBUG] Veikkaus nav to match failed: {e} ({href})")
                    _dbg_dump(page, "veikkaus_match_nav_fail", debug_dir)
                continue
            btns = page.locator(cfg["ml_button_selector"])
            if btns.count()<2:
                if debug: print(f"[DEBUG] No ML buttons on {href}")
                continue
            data = []
            for j in range(2):
                btn = btns.nth(j)
                team_el = btn.locator(cfg["ml_team_selector"]).first
                odd_el = btn.locator(cfg["ml_price_selector"]).first
                if not (team_el.count() and odd_el.count()):
                    data=[]; break
                name = team_el.inner_text().strip()
                txt = odd_el.inner_text().strip().replace(",", ".")
                try:
                    odd = float(txt)
                except ValueError:
                    data=[]; break
                data.append((name, odd))
            if len(data)!=2: continue
            (home_name, home_odds), (away_name, away_odds) = data
            events.append({"home_team":home_name,"away_team":away_name,"home_odds":home_odds,"away_odds":away_odds})
        if debug and not events:
            print("[DEBUG] Veikkaus returned 0 events → dumping snapshot")
            _dbg_dump(page, "veikkaus_empty", debug_dir)
    finally:
        _safe_close(browser=browser, context=context, p=p)
    return events
