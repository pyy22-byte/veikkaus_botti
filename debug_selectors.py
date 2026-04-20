"""
Network request interceptor - finds the actual API endpoints both sites use.
"""
import asyncio, json
from playwright.async_api import async_playwright
from pathlib import Path

async def main():
    Path("debug").mkdir(exist_ok=True)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
            locale="fi-FI"
        )

        # ── Pinnacle: intercept network requests ──
        print("=== PINNACLE API REQUESTS ===")
        pinnacle_requests = []
        page = await context.new_page()

        def handle_pinnacle_request(request):
            url = request.url
            if any(x in url for x in ['api', 'graphql', 'matchups', 'odds', 'json', 'v3', 'feed']):
                pinnacle_requests.append(url)

        page.on("request", handle_pinnacle_request)
        await page.goto("https://www.pinnacle.com/en/hockey/nhl/matchups", wait_until="networkidle", timeout=60000)
        await asyncio.sleep(3)
        await page.screenshot(path="debug/pinnacle.png", full_page=True)

        print(f"Interesting requests ({len(pinnacle_requests)}):")
        for r in pinnacle_requests[:20]:
            print(f"  {r}")
        await page.close()

        # ── Veikkaus: intercept network requests ──
        print("\n=== VEIKKAUS API REQUESTS ===")
        veikkaus_requests = []
        page2 = await context.new_page()

        def handle_veikkaus_request(request):
            url = request.url
            if any(x in url for x in ['api', 'json', 'odds', 'fixture', 'market', 'event', 'competition', 'v1', 'v2']):
                veikkaus_requests.append(url)

        page2.on("request", handle_veikkaus_request)
        await page2.goto(
            "https://www.veikkaus.fi/fi/pitkaveto/fi/sports/competition/944/jaakiekko/usa/nhl/matches",
            wait_until="networkidle", timeout=60000
        )
        await asyncio.sleep(3)
        await page2.screenshot(path="debug/veikkaus.png", full_page=True)

        print(f"Interesting requests ({len(veikkaus_requests)}):")
        for r in veikkaus_requests[:20]:
            print(f"  {r}")

        # Try fetching one of the API responses
        if veikkaus_requests:
            try:
                resp = await page2.evaluate(f"""async () => {{
                    const r = await fetch('{veikkaus_requests[0]}');
                    const text = await r.text();
                    return text.substring(0, 500);
                }}""")
                print(f"\nFirst API response sample:\n{resp}")
            except Exception as e:
                print(f"Could not fetch: {e}")

        await page2.close()
        await browser.close()

asyncio.run(main())
