# NHL Moneyline kerroinseuranta

Bot vertaa Pinnaclen ja Veikkauksen NHL moneyline -kertoimia ja lähettää
Discord-ilmoituksen kun Veikkaus tarjoaa selvästi paremman kertoimen kuin
Pinnacle (oletus: vähintään 5 % parannus).

Pyörii GitHub Actionsissa cron-aikataululla (5 min välein) — paikallista
konetta ei tarvita.

## Stack

- Python 3.10+
- `requests` + `PyYAML` (ei Playwrightia, ei selainta)
- SQLite (`events.db`) — tila säilyy ajojen välillä GitHub Actions cachen kautta
- Discord webhook ilmoituksiin

## Tietolähteet

- **Pinnacle:** `guest.api.arcadia.pinnacle.com` — suora JSON-API
- **Veikkaus:** `content.ob.veikkaus.fi/content-service/api/v1/q/event-list`
  parametreilla `drilldownTagIds=944` (NHL) ja `marketGroupCodeCombiId=55`
  (moneyline)

Molemmissa suodatetaan jo alkaneet pelit pois (Pinnacle: `cutoffAt`,
Veikkaus: `started`/`liveNow`).

## Tiedostot

| Tiedosto | Tehtävä |
|---|---|
| `main.py` | Päärunko: hae → vertaa → tallenna → ilmoita |
| `scraper.py` | Pinnacle- ja Veikkaus-API-kutsut |
| `compare.py` | Joukkueiden nimien normalisointi + erotuslaskenta |
| `db.py` | SQLite — events + notifications + 72 h TTL |
| `notifier.py` | Discord webhook -lähetys |
| `config.yaml` | Threshold ja API-asetukset |
| `debug_selectors.py` | Manuaalinen debug-ajo (Actions → Run workflow) |
| `test_bot.py` | Yksikkötestit (offline) |
| `.github/workflows/kerroinseuranta.yml` | GitHub Actions -ajastus |

## Asetukset

`config.yaml`:

```yaml
sport: "NHL"
threshold_percent: 5.0   # ilmoituskynnys prosentteina
debug: true
```

GitHub Secrets:

- `DISCORD_WEBHOOK_URL` — pakollinen, ilmoituskanavan webhook

## Paikallinen ajo (vapaaehtoinen)

```bash
pip install -r requirements.txt
set DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
python main.py
```

## Testit

```bash
python -m unittest test_bot.py -v
```

## Debug-ajo

GitHub → Actions → **kerroinseuranta** → Run workflow → `debug_selectors: yes`.
Tämä ajaa `debug_selectors.py`:n joka tulostaa kummankin lähteen raakadatat ja
matchatut ehdokkaat ilman kynnystä.

## Re-notify -logiikka

Sama match + side ilmoitetaan uudelleen vain jos parannus kasvaa **vähintään
5 prosenttiyksikköä** edellisestä ilmoituksesta. Vanhat ilmoitustietueet
poistetaan 72 tunnin jälkeen, jotta sama peli voi taas notifioida jos se
palaa esiin myöhemmin.
