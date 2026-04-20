"""Run this via GitHub Actions to discover current selectors."""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

async def _accept_cookies(page):
    for sel in ['button#onetrust-accept-btn-handler','button:has-text("ACCEPT")',
                'button:has-text("Hyväksy")','button:has-text("Salli")','text=Hyväksyn']:
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
        await page.goto("https://www.pinnacle.com/en/hockey/nhl/matchups", wait_until="networkidle", timeout=60000)
        await _accept_cookies(page)
        await asyncio.sleep(3)

        ids = await page.evaluate("""() => {
            const els = document.querySelectorAll('[data-test-id]');
            return [...new Set([...els].map(e => e.getAttribute('data-test-id')))].slice(0,60);
        }""")
        print("data-test-ids:", ids)

        classes = await page.evaluate("""() => {
            const els = document.querySelectorAll('span, div');
            return [...new Set([...els].flatMap(e => [...e.classList]))].filter(c=>c.length>3).slice(0,60);
        }""")
        print("classes sample:", classes[:30])

        # Try to find team names
        teams = await page.evaluate("""() => {
            const candidates = [];
            document.querySelectorAll('span, div, a').forEach(el => {
                const t = el.innerText?.trim();
                if (t && t.length > 3 && t.length < 40 && !t.includes('\\n')) candidates.push(t);
            });
            return candidates.slice(0,40);
        }""")
        print("Text candidates:", teams)
        await page.screenshot(path="debug/pinnacle.png", full_page=True)
        await page.close()

        # ── Veikkaus ──
        page2 = await context.new_page()
        print("\n=== VEIKKAUS ===")
        await page2.goto("https://www.veikkaus.fi/fi/vedonlyonti/pitkaveto?t=3-2-1", wait_until="networkidle", timeout=60000)
        await _accept_cookies(page2)
        await asyncio.sleep(3)

        ids2 = await page2.evaluate("""() => {
            const els = document.querySelectorAll('[data-test-id]');
            return [...new Set([...els].map(e => e.getAttribute('data-test-id')))].slice(0,60);
        }""")
        print("data-test-ids:", ids2)

        hrefs = await page2.evaluate("""() => {
            return [...document.querySelectorAll('a[href]')]
                .map(a => a.href)
                .filter(h => h.includes('kohde') || h.includes('match') || h.includes('game'))
                .slice(0,10);
        }""")
        print("Match hrefs:", hrefs)
        await page2.screenshot(path="debug/veikkaus.png", full_page=True)
        await page2.close()

        await browser.close()

asyncio.run(main())
