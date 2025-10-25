"""Scraper module for fetching odds from configured websites."""

import requests
from bs4 import BeautifulSoup


def fetch_odds(site_config):
    """
    Fetch odds from a website using requests and BeautifulSoup.

    Args:
        site_config (dict): Configuration containing URL and CSS selectors.

    Returns:
        list of dict: Each dict contains 'teams' (tuple), 'odds' (float), and 'match_id' (str).
    """
    url = site_config["url"]
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    events = []
    for event_elem in soup.select(site_config["event_selector"]):
        team_elems = event_elem.select(site_config["team_selector"])
        odds_elem = event_elem.select_one(site_config["odds_selector"])
        if len(team_elems) == 2 and odds_elem:
            home = team_elems[0].get_text(strip=True)
            away = team_elems[1].get_text(strip=True)
            try:
                odds = float(odds_elem.get_text(strip=True).replace(",", "."))
            except ValueError:
                continue
            match_id = f"{home}-{away}"
            events.append({"teams": (home, away), "odds": odds, "match_id": match_id})
    return events


def fetch_odds_selenium(site_config, driver):
    """
    Fetch odds using Selenium for websites requiring JavaScript rendering.

    Args:
        site_config (dict): Configuration containing URL and CSS selectors.
        driver (selenium.webdriver): An initialized Selenium WebDriver.

    Returns:
        list of dict: Each dict contains 'teams', 'odds', and 'match_id'.
    """
    driver.get(site_config["url"])
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    events = []
    for event_elem in soup.select(site_config["event_selector"]):
        team_elems = event_elem.select(site_config["team_selector"])
        odds_elem = event_elem.select_one(site_config["odds_selector"])
        if len(team_elems) == 2 and odds_elem:
            home = team_elems[0].get_text(strip=True)
            away = team_elems[1].get_text(strip=True)
            try:
                odds = float(odds_elem.get_text(strip=True).replace(",", "."))
            except ValueError:
                continue
            match_id = f"{home}-{away}"
            events.append({"teams": (home, away), "odds": odds, "match_id": match_id})
    return events
