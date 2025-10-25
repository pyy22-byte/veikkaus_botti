# Kerroinseurantabotti

Tämä projekti sisältää Python-skriptit, jotka seuraavat Pinnacle- ja Veikkaus-sivustojen NHL-otteluiden kertoimia,
vertaavat kertoimia ja lähettävät ilmoituksia Telegramiin, kun Veikkauksen kerroin on vähintään 5 % parempi kuin Pinnaclen.

## Asennus

1. Varmista, että sinulla on Python 3 asennettuna.
2. Suorita alla olevat komennot projektin juurikansiossa:

   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Muokkaa `config.yaml`-tiedostoa:
   - Aseta `token` ja `chat_id` Telegram-bottisi asetuksista.
   - Päivitä CSS-valitsimet vastaamaan nykyisiä sivustojen HTML-rakenteita.

4. Käynnistä botti:

   ```bash
   python main.py
   ```

Botti suorittaa tarkistuksen heti käynnistyessään ja sen jälkeen tunnin välein.

## Tiedostot

- `config.yaml` – Asetustiedosto, jossa määritellään laji, kertoimet ja Telegram-tunnukset.
- `requirements.txt` – Asennettavat Python-kirjastot.
- `scraper.py` – Sisältää funktiot kertoimien noutamiseen sivuilta.
- `compare.py` – Sisältää logiikan kertoimien vertailuun ja ilmoituksien listaukseen.
- `notifier.py` – Sisältää funktiot Telegram-viestien lähettämiseen ja viestien rakentamiseen.
- `db.py` – Sisältää tietokantafunktiot ilmoitusten seurantaan.
- `main.py` – Orkestroi skriptin suorittamisen ja ajastuksen.

## Laajennus

Voit lisätä uusia urheilulajeja tai sivustoja muokkaamalla `config.yaml`-tiedostoa. Lisää uusi osio `sites`-kohtaan ja varmista, että lisäät vastaavat CSS-valitsimet.
