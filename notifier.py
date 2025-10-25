import requests

def send_telegram_message(token: str, chat_id: str, text: str) -> None:
    if not token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    try:
        requests.post(url, data=data, timeout=15).raise_for_status()
    except Exception:
        pass

def build_message(event: dict) -> str:
    # event: dict with keys: home_team, away_team, side, pinn_odds, veik_odds, diff_pct
    side_txt = "Kotijoukkue" if event["side"] == "home" else "Vierasjoukkue"
    return (
        f"📣 <b>NHL Moneyline-ero</b>\n"
        f"{event['home_team']} vs {event['away_team']}\n"
        f"{side_txt}: Veikkaus {event['veik_odds']} vs Pinnacle {event['pinn_odds']}\n"
        f"Etu: {event['diff_pct']:.1f}%"
    )
