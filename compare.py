def normalize_team(name: str) -> str:
    return " ".join(name.lower().split())

def match_key_from_names(home: str, away: str) -> str:
    # Avain sama riippumatta järjestyksestä: a|b (a<b)
    a, b = sorted([normalize_team(home), normalize_team(away)])
    return f"{a}|{b}"

def build_index(events):
    idx = {}
    for e in events:
        key = match_key_from_names(e["home_team"], e["away_team"])
        idx[key] = e
    return idx

def compare_moneyline(pinn_events, veik_events, threshold_percent):
    """Palauttaa listan ilmoituksista: dict jossa mm. side=home/away, diff_pct jne."""
    res = []
    p_idx = build_index(pinn_events)
    v_idx = build_index(veik_events)

    for key, p in p_idx.items():
        if key not in v_idx:
            continue
        v = v_idx[key]

        # home side
        if p["home_odds"] and v["home_odds"]:
            diff_home = (v["home_odds"] - p["home_odds"]) / p["home_odds"] * 100.0
            if diff_home >= threshold_percent:
                res.append({
                    "match_key": key,
                    "home_team": p["home_team"],
                    "away_team": p["away_team"],
                    "side": "home",
                    "pinn_odds": p["home_odds"],
                    "veik_odds": v["home_odds"],
                    "diff_pct": diff_home
                })

        # away side
        if p["away_odds"] and v["away_odds"]:
            diff_away = (v["away_odds"] - p["away_odds"]) / p["away_odds"] * 100.0
            if diff_away >= threshold_percent:
                res.append({
                    "match_key": key,
                    "home_team": p["home_team"],
                    "away_team": p["away_team"],
                    "side": "away",
                    "pinn_odds": p["away_odds"],
                    "veik_odds": v["away_odds"],
                    "diff_pct": diff_away
                })

    return res
