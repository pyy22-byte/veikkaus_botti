# NHL Moneyline Kerroinseurantabotti

Tämä projekti seuraa Pinnacle- ja Veikkaus-sivustojen **NHL**-otteluiden *moneyline* -kertoimia,
vertaa niitä, ja lähettää Telegram-viestin, kun Veikkauksen kerroin on vähintään kynnysprosentin
( oletus **5%** ) parempi kuin Pinnaclella.

- Aja paikallisesti: `python main.py`
- Aja GitHub Actionsissa: toiminto on valmiiksi ajastettu `*/10 * * * *` (10 min välein).

## Pika-asennus

1. Luo Telegram-botti (BotFather) ja ota talteen `TELEGRAM_TOKEN`.
2. Ota talteen `TELEGRAM_CHAT_ID` (esim. oman tilin chat id tai kanavan/botin id).
3. Paikallisesti: aseta ympäristömuuttujat ja asenna riippuvuudet:

```powershell
$env:TELEGRAM_TOKEN="xxx"; $env:TELEGRAM_CHAT_ID="123456"
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

4. GitHubissa: lisää repositoryyn *Settings → Secrets and variables → Actions*:  
   `TELEGRAM_TOKEN` ja `TELEGRAM_CHAT_ID`.

> **Huom:** Sivustot muuttuvat ajoittain. Jos scraper ei löydä elementtejä,
> päivitä `config.yaml`-tiedoston CSS-valitsimia (kommentit auttavat).

## Tiedostorakenne

- `main.py` – ajo-orchesteri (suorittaa yhden tarkistuksen per ajo).
- `scraper.py` – hakee moneyline-kertoimet molemmilta sivuilta.
- `compare.py` – vertaa kertoimet ja tuottaa ilmoitukset.
- `db.py` – SQLite-tietokanta: säilöö viimeisimmät kertoimet ja ilmoitusliput.
- `notifier.py` – lähettää Telegram-viestin.
- `config.yaml` – asetukset ja CSS-valitsimet (voit säätää tarvittaessa).

## Vastuuvapaus

Käyttö omalla vastuulla. Noudata sivustojen käyttöehtoja ja robots.txt -sääntöjä.
