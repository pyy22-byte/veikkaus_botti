import re
import unicodedata


def _norm(s):
    s = s.strip().lower()
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')
    s = re.sub(r'[^a-z0-9 ]+', '', s)
    s = re.sub(r'\s+', ' ', s)
    return s


def match_key_from_names(home, away):
    return f"{_norm(home)}__vs__{_norm(away)}"


def compare_moneyline(p, v, thr):
    idx = {match_key_from_names(e['home_team'], e['away_team']): e for e in p}
    out = []
    for x in v:
        k = match_key_from_names(x['home_team'], x['away_team'])
        a = idx.get(k)
        if not a:
            continue
        if a['home_odds'] and x['home_odds']:
            diff = (x['home_odds'] - a['home_odds']) / a['home_odds'] * 100.0
            if diff >= thr:
                out.append({
                    'match_key': k,
                    'home_team': x['home_team'],
                    'away_team': x['away_team'],
                    'side': 'home',
                    'pinnacle': a['home_odds'],
                    'veikkaus': x['home_odds'],
                    'improvement_pct': round(diff, 2)
                })
        if a['away_odds'] and x['away_odds']:
            diff = (x['away_odds'] - a['away_odds']) / a['away_odds'] * 100.0
            if diff >= thr:
                out.append({
                    'match_key': k,
                    'home_team': x['home_team'],
                    'away_team': x['away_team'],
                    'side': 'away',
                    'pinnacle': a['away_odds'],
                    'veikkaus': x['away_odds'],
                    'improvement_pct': round(diff, 2)
                })
    return out
