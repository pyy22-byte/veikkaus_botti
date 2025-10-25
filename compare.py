"""Comparison module for matching events and computing odds differences."""


def match_events(veikkaus_events, pinnacle_events, threshold_percent):
    """
    Compare events from Veikkaus and Pinnacle and return a list of notification dicts
    if the difference in odds is greater than or equal to the threshold.

    Args:
        veikkaus_events (list of dict): Events scraped from Veikkaus.
        pinnacle_events (list of dict): Events scraped from Pinnacle.
        threshold_percent (float): Minimum percentage difference to trigger notification.

    Returns:
        list of dict: Each dict contains match_id, home, away, veikkaus, pinnacle, difference_percent.
    """
    notifications = []
    for veikkaus in veikkaus_events:
        for pinn in pinnacle_events:
            if veikkaus["teams"] == pinn["teams"]:
                if pinn["odds"] == 0:
                    continue
                diff = (veikkaus["odds"] - pinn["odds"]) / pinn["odds"] * 100
                if diff >= threshold_percent:
                    notifications.append({
                        "match_id": veikkaus["match_id"],
                        "home": veikkaus["teams"][0],
                        "away": veikkaus["teams"][1],
                        "veikkaus": veikkaus["odds"],
                        "pinnacle": pinn["odds"],
                        "difference_percent": round(diff, 2),
                    })
    return notifications
