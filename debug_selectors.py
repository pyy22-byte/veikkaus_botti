"""Final verification."""
import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
from scraper import fetch_all
from compare import compare_moneyline

pinnacle, veikkaus = fetch_all({}, {}, debug=True)

print(f"\nPINNACLE ({len(pinnacle)}):")
for e in pinnacle:
    print(f"  {e['home_team']} {e['home_odds']} vs {e['away_team']} {e['away_odds']}")

print(f"\nVEIKKAUS ({len(veikkaus)}):")
for e in veikkaus:
    print(f"  {e['home_team']} {e['home_odds']} vs {e['away_team']} {e['away_odds']}")

candidates = compare_moneyline(pinnacle, veikkaus, thr=3.0)
print(f"\nCANDIDATES >3%: {len(candidates)}")
for c in candidates:
    print(f"  {c['home_team']} vs {c['away_team']} ({c['side']}) Pinnacle={c['pinnacle']} Veikkaus={c['veikkaus']} +{c['improvement_pct']}%")
