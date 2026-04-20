"""Final verification - both APIs should return events."""
import logging
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

from scraper import fetch_all

pinnacle, veikkaus = fetch_all({}, {}, debug=True)

print(f"\n{'='*50}")
print(f"PINNACLE: {len(pinnacle)} events")
for e in pinnacle:
    print(f"  {e['home_team']} {e['home_odds']} vs {e['away_team']} {e['away_odds']}")

print(f"\nVEIKKAUS: {len(veikkaus)} events")
for e in veikkaus:
    print(f"  {e['home_team']} {e['home_odds']} vs {e['away_team']} {e['away_odds']}")

# Show any matches between the two
from compare import compare_moneyline
candidates = compare_moneyline(pinnacle, veikkaus, thr=3.0)
print(f"\nCANDIDATES (>3% threshold): {len(candidates)}")
for c in candidates:
    print(f"  {c}")
