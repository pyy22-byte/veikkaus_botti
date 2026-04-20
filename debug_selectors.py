"""Debug script - tests both scrapers with current selectors."""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

VEIKKAUS_URL = "https://www.veikkaus.fi/fi/pitkaveto/fi/sports/competition/944/jaakiekko/usa/nhl/matches"
PINNACLE_URL = "https://www.pinnacle.com/en/hockey/nhl/matchups"

async def _accept_cookies(page):
    for sel in ['button#onetrust-accept-btn-handler', 'button:has-text("Hyväksy")',
                'button:has-text("Salli")', 'text=Hyväksyn', 'button:has-text("ACCEPT")']:
        try:
            loc = page.locator(sel)
            if await loc.count() and await loc.first.is_visible():
                await loc.first.click(timeout=2000)
                break
        except Exception:
            pass

async def main():
    Path("debug").mkdir(exist_ok=True)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
            locale="fi-FI"
        )

        # ── Pinnacle ──
        page = await context.new_page()
        print("=== PINNACLE ===")
        await page.goto(PINNACLE_URL, wait_until="networkidle", timeout=60000)
        await _accept_cookies(page)
        await asyncio.sleep(2)
        rows = page.locator('div[data-test-id^="row-"]')
        print(f"Rows found: {await rows.count()}")
        for i in range(min(await rows.count(), 3)):
            row = rows.nth(i)
            teams = row.locator('span.ellipsis[class^="gameInfoLabel"]')
            money = row.locator('div[data-test-id="moneyline"]')
            if await teams.count() >= 2 and await money.count() > 0:
                home = (await teams.nth(0).inner_text()).strip()
                away = (await teams.nth(1).inner_text()).strip()
                prices = money.locator('span[class^="price"]')
                if await prices.count() >= 2:
                    h = (await prices.nth(0).inner_text()).strip()
                    a = (await prices.nth(1).inner_text()).strip()
                    print(f"  MATCH: {home} {h} vs {away} {a}")
        await page.screenshot(path="debug/pinnacle.png", full_page=True)
        await page.close()

        # ── Veikkaus ──
        page2 = await context.new_page()
        print("\n=== VEIKKAUS ===")
        await page2.goto(VEIKKAUS_URL, wait_until="networkidle", timeout=60000)
        await _accept_cookies(page2)
        await asyncio.sleep(3)
        await page2.screenshot(path="debug/veikkaus.png", full_page=True)

        # Try JS extraction
        results = await page2.evaluate("""() => {
            const results = [];
            const matchContainers = document.querySelectorAll(
                '[class*="EventRow"], [class*="match-row"], [class*="event-row"], ' +
                '[class*="MarketRow"], [class*="gameRow"]'
            );
            console.log('containers found:', matchContainers.length);
            matchContainers.forEach(container => {
                const text = container.innerText;
                const lines = text.split('\\n').map(l => l.trim()).filter(Boolean);
                const odds = [];
                const teams = [];
                lines.forEach(line => {
                    const n = parseFloat(line.replace(',', '.'));
                    if (!isNaN(n) && n > 1.0 && n < 20.0) odds.push(n);
                    else if (line.length > 3) teams.push(line);
                });
                if (teams.length >= 2 && odds.length >= 3) {
                    results.push({home: teams[0], away: teams[1], h_odds: odds[0], a_odds: odds[2]});
                }
            });
            return results;
        }""")
        print(f"JS extraction: {len(results)} matches")
        for r in results[:5]:
            print(f"  {r['home']} {r['h_odds']} vs {r['away']} {r['a_odds']}")

        # Also dump all class names for debugging
        classes = await page2.evaluate("""() => {
            return [...new Set([...document.querySelectorAll('[class]')]
                .map(e => e.className)
                .filter(c => c && typeof c === 'string')
                .flatMap(c => c.split(' '))
                .filter(c => c.length > 3 && c.length < 40)
            )].slice(0, 50);
        }""")
        print(f"\nClass names sample: {classes[:20]}")

        await page2.close()
        await browser.close()

asyncio.run(main())
