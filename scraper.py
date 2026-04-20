import asyncio
import logging
from pathlib import Path
from datetime import datetime

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)


async def _accept_cookies(page):
    selectors = [
        'button#onetrust-accept-btn-handler',
        'button:has-text("ACCEPT")',
        'button:has-text("I Accept")',
        'button:has-text("I understand")',
        'button:has-text("Hyväksy")',
        'button:has-text("Salli")',
        'text=Hyväksyn',
    ]
    for sel in selectors:
        try:
            loc = page.locator(sel)
            if await loc.count() and await loc.first.is_visible():
                await loc.first.click(timeout=1500)
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
            logger.debug("Pinnacle returned 0 events — dumping snapshot")
            await _dbg_dump(page, "pinnacle_empty", debug_dir)
    finally:
        await context.close()
    return events


async def _fetch_single_veikkaus_match(page, href, cfg, debug, debug_dir):
    try:
        await page.goto(href, wait_until="networkidle", timeout=60000)
        await _accept_cookies(page)
        await page.wait_for_selector(cfg["ml_button_selector"], timeout=30000)
    except Exception as e:
        if debug:
            logger.debug(f"Veikkaus nav to match failed: {e} ({href})")
            await _dbg_dump(page, "veikkaus_match_nav_fail", debug_dir)
        return None

    btns = page.locator(cfg["ml_button_selector"])
    if await btns.count() < 2:
        if debug:
            logger.debug(f"No ML buttons on {href}")
        return None

    data = []
    for j in range(2):
        btn = btns.nth(j)
        team_el = btn.locator(cfg["ml_team_selector"]).first
        odd_el = btn.locator(cfg["ml_price_selector"]).first
        if not (await team_el.count() and await odd_el.count()):
            return None
        name = (await team_el.inner_text()).strip()
        txt = (await odd_el.inner_text()).strip().replace(",", ".")
        try:
            odd = float(txt)
        except ValueError:
            return None
        data.append((name, odd))

    if len(data) != 2:
        return None

    (home_name, home_odds), (away_name, away_odds) = data
    return {
        "home_team": home_name,
        "away_team": away_name,
        "home_odds": home_odds,
        "away_odds": away_odds,
    }


async def _fetch_veikkaus_async(cfg, browser, debug, debug_dir, concurrency=4):
    # Step 1: collect all match links using one page
    context = await browser.new_context(
        user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
        locale="fi-FI"
    )
    list_page = await context.new_page()
    links = []
    try:
        try:
            await list_page.goto(cfg["list_url"], wait_until="networkidle", timeout=60000)
            await _accept_cookies(list_page)
            await list_page.wait_for_selector(cfg["list_event_selector"], timeout=60000)
        except Exception as e:
            logger.error(f"Veikkaus list navigation failed: {e}")
            if debug:
                await _dbg_dump(list_page, "veikkaus_list_nav_fail", debug_dir)
            await context.close()
            return []

        anchors = list_page.locator(cfg["list_event_selector"])
        for i in range(await anchors.count()):
            href = await anchors.nth(i).get_attribute("href")
            if not href:
                continue
            if href.startswith("/"):
                href = "https://www.veikkaus.fi" + href
            links.append(href)
    finally:
        await list_page.close()

    logger.debug(f"Veikkaus match links: {len(links)}")

    # Step 2: scrape match pages concurrently with a semaphore
    semaphore = asyncio.Semaphore(concurrency)
    events = []

    async def scrape_one(href):
        async with semaphore:
            page = await context.new_page()
            try:
                result = await _fetch_single_veikkaus_match(page, href, cfg, debug, debug_dir)
                if result:
                    events.append(result)
            finally:
                await page.close()

    await asyncio.gather(*[scrape_one(href) for href in links])

    if debug and not events:
        logger.debug("Veikkaus returned 0 events")

    await context.close()
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
