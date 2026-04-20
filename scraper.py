import asyncio
import logging
from pathlib import Path
from datetime import datetime

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

VEIKKAUS_NHL_URL = "https://www.veikkaus.fi/fi/pitkaveto/fi/sports/competition/944/jaakiekko/usa/nhl/matches"


async def _accept_cookies(page):
    for sel in [
        'button#onetrust-accept-btn-handler',
        'button:has-text("ACCEPT")',
        'button:has-text("Hyväksy")',
        'button:has-text("Salli")',
        'text=Hyväksyn',
    ]:
        try:
            loc = page.locator(sel)
            if await loc.count() and await loc.first.is_visible():
                await loc.first.click(timeout=2000)
                break
        except Exception:
            pass


async def _dbg_dump(page, name, debug_dir):
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    try:
        (debug_dir / f"{name}_{ts}.html").write_text(await page.content(), encoding="utf-8")
        await page.screenshot(path=str(debug_dir / f"{name}_{ts}.png"), full_page=True)
    except Exception:
        pass


async def _fetch_pinnacle_async(cfg, browser, debug, debug_dir):
    context = await browser.new_context(
        user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
        locale="fi-FI"
    )
    page = await context.new_page()
    events = []
    try:
        try:
            await page.goto(cfg["url"], wait_until="networkidle", timeout=60000)
            await _accept_cookies(page)
            await page.wait_for_selector(cfg["event_selector"], timeout=60000)
        except Exception as e:
            logger.error(f"Pinnacle navigation failed: {e}")
            if debug:
                await _dbg_dump(page, "pinnacle_nav_fail", debug_dir)
            return []

        rows = page.locator(cfg["event_selector"])
        count = await rows.count()
        logger.debug(f"Pinnacle rows: {count}")

        for i in range(count):
            row = rows.nth(i)
            teams = row.locator(cfg["team_selector"])
            if await teams.count() < 2:
                continue
            home = (await teams.nth(0).inner_text()).strip()
            away = (await teams.nth(1).inner_text()).strip()
            money = row.locator(cfg["money_container_selector"])
            if await money.count() == 0:
                continue
            prices = money.locator(cfg["price_selector"])
            if await prices.count() < 2:
                continue
            try:
                home_odds = float((await prices.nth(0).inner_text()).strip())
                away_odds = float((await prices.nth(1).inner_text()).strip())
            except ValueError:
                continue
            events.append({
                "home_team": home,
                "away_team": away,
                "home_odds": home_odds,
                "away_odds": away_odds,
            })

        if debug and not events:
            await _dbg_dump(page, "pinnacle_empty", debug_dir)
    finally:
        await context.close()
    return events


async def _fetch_veikkaus_async(cfg, browser, debug, debug_dir):
    """
    Scrape Veikkaus NHL list page directly.
    The list page shows 1X2 odds per match in a single pass — no need to visit each match page.
    We use kertoimet 1 (home win) and 2 (away win), ignoring X (draw).
    """
    context = await browser.new_context(
        user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
        locale="fi-FI"
    )
    page = await context.new_page()
    events = []
    try:
        url = cfg.get("list_url", VEIKKAUS_NHL_URL)
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
            await _accept_cookies(page)
            # Wait for match rows to appear
            await page.wait_for_selector('[class*="EventRow"], [class*="eventRow"], td', timeout=60000)
            await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"Veikkaus navigation failed: {e}")
            if debug:
                await _dbg_dump(page, "veikkaus_fail", debug_dir)
            return []

        if debug:
            await _dbg_dump(page, "veikkaus_list", debug_dir)

        # Parse via JavaScript — most reliable for dynamic React pages
        events = await page.evaluate("""() => {
            const results = [];
            
            // Each match block has two team names and three odds cells (1, X, 2)
            // Find all rows that contain team pair + odds
            const allText = document.body.innerText;
            
            // Strategy: find elements containing team names paired with odds
            // Look for the match containers
            const matchContainers = document.querySelectorAll(
                '[class*="EventRow"], [class*="match-row"], [class*="event-row"], ' +
                '[class*="MarketRow"], [class*="gameRow"]'
            );
            
            matchContainers.forEach(container => {
                const text = container.innerText;
                const lines = text.split('\\n').map(l => l.trim()).filter(Boolean);
                
                // Look for pattern: team1, team2, then three numbers (1X2 odds)
                const odds = [];
                const teams = [];
                
                lines.forEach(line => {
                    const n = parseFloat(line.replace(',', '.'));
                    if (!isNaN(n) && n > 1.0 && n < 20.0) {
                        odds.push(n);
                    } else if (line.length > 3 && isNaN(parseFloat(line))) {
                        teams.push(line);
                    }
                });
                
                // We need 2 teams and at least 3 odds (1, X, 2)
                if (teams.length >= 2 && odds.length >= 3) {
                    results.push({
                        home_team: teams[0],
                        away_team: teams[1],
                        home_odds: odds[0],   // "1" = home win
                        away_odds: odds[2],   // "2" = away win
                    });
                }
            });
            
            return results;
        }""")

        logger.debug(f"Veikkaus parsed {len(events)} events via JS")

        # If JS approach fails, try Python fallback
        if not events:
            logger.debug("JS approach returned 0, trying Python fallback")
            events = await _parse_veikkaus_fallback(page, debug)

        if debug and not events:
            logger.debug("Veikkaus returned 0 events after all attempts")

    finally:
        await context.close()
    return events


async def _parse_veikkaus_fallback(page, debug):
    """Fallback: extract raw text and parse manually."""
    events = []
    try:
        raw = await page.evaluate("""() => {
            // Get all text nodes with structure
            const rows = [];
            document.querySelectorAll('tr, [class*="row"], [class*="Row"]').forEach(el => {
                const t = el.innerText?.trim();
                if (t && t.length > 10) rows.push(t);
            });
            return rows.slice(0, 100);
        }""")

        for row_text in raw:
            lines = [l.strip() for l in row_text.split('\n') if l.strip()]
            teams = []
            odds = []
            for line in lines:
                try:
                    n = float(line.replace(',', '.'))
                    if 1.0 < n < 20.0:
                        odds.append(n)
                except ValueError:
                    if len(line) > 3 and not any(c.isdigit() for c in line[:2]):
                        teams.append(line)

            if len(teams) >= 2 and len(odds) >= 3:
                events.append({
                    "home_team": teams[0],
                    "away_team": teams[1],
                    "home_odds": odds[0],
                    "away_odds": odds[2],
                })
    except Exception as e:
        logger.warning(f"Veikkaus fallback failed: {e}")
    return events


async def _run_both(p_cfg, v_cfg, debug):
    debug_dir = Path("debug")
    if debug:
        debug_dir.mkdir(exist_ok=True)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        pinnacle_task = asyncio.create_task(
            _fetch_pinnacle_async(p_cfg, browser, debug, debug_dir)
        )
        veikkaus_task = asyncio.create_task(
            _fetch_veikkaus_async(v_cfg, browser, debug, debug_dir)
        )
        pinnacle_events, veikkaus_events = await asyncio.gather(
            pinnacle_task, veikkaus_task
        )
        await browser.close()

    return pinnacle_events, veikkaus_events


def fetch_all(p_cfg, v_cfg, debug=False):
    """Fetch Pinnacle and Veikkaus concurrently. Returns (pinnacle_events, veikkaus_events)."""
    return asyncio.run(_run_both(p_cfg, v_cfg, debug))
