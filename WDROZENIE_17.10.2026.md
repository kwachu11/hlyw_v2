# Wdrożenie zmian z 17.10.2026

Wygląd w stylu GTA, „misja zaliczona” / „wasted”, kasa i gwiazdki poszukiwania, korona TOP 3, powiadomienia jak SMS-y,
dźwięki, ekran ładowania, ostatnia aktywność („Co się dzieje”), turniej Trackmania, logowanie e-mailem, zmniejszanie zdjęć przed wysłaniem, ochrona rankingów.

## 1. Kopia bazy na serwerze (przed wgraniem!)

Przy starcie aplikacja sama dokłada nowe tabele: `game_run` (bilety gier), `tm_track`, `tm_time` (Trackmania),
`camera_visit` (historia oglądania kamery) i kolumny z datami: `participant.created_at`, `fifa_participant.created_at`,
`news_reaction.created_at`, `tournament_match.score_at` (do ostatniej aktywności).
Nic nie jest zmieniane ani usuwane, ale kopia na wszelki wypadek nie zaszkodzi.

## 2. Pliki do wgrania (podmienić / dodać)

Python:
- `app/__init__.py`
- `app/forms.py`

Skrypt jednorazowy (katalog główny projektu):
- `add_upgrades_gta.py` — **nowy**

Style i skrypty:
- `app/static/css/custom.css`
- `app/static/css/gta.css` — **nowy**
- `app/static/js/gta.js` — **nowy**
- `app/static/js/game_run.js` — **nowy**
- `app/static/js/upload_resize.js` — **nowy**
- `app/static/css/fonts/pricedown.otf` — sprawdzić, czy jest na serwerze (był już wcześniej używany przez gry)

Szablony (`app/templates/`):
- `_trackmania.html` — **nowy**
- `_activity.html` — **nowy** (lista „Co się dzieje”)
- `aktywnosc.html` — **nowy** (strona `/aktywnosc`)
- `error.html` — **nowy**
- `_ranking_table.html`
- `base.html`
- `body.html`
- `breaking_news.html`
- `camera.html`
- `dino.html`
- `event.html`
- `footer.html`
- `formula.html`
- `hall_of_fame.html`
- `ice_tower.html`
- `kolko_krzyzyk.html`
- `menu.html`
- `profil.html`
- `snake.html`
- `tetris.html`
- `uzytkownicy.html`
- `view_report.html`

## 3. NIE wgrywać

- `baza.db`, `instance/` — bazy danych
- `.env` — serwer ma własny
- `CLAUDE.md`, ten plik — tylko dla nas

## 4. Po wgraniu

1. Restart aplikacji (gunicorn), żeby wczytała nowy kod i dodała tabele.
2. `python add_upgrades_gta.py` (w venv, w katalogu projektu) — 12 wpisów do „Ostatnich Ulepszeń”.
   Wpisy, które już są w bazie, są pomijane — jeśli skrypt był już raz uruchomiony, doda tylko 4 nowe.
3. **Ważne:** gry muszą mieć nowe szablony i `game_run.js` jednocześnie z nowym `__init__.py` — stara wersja gry
   (bez biletu) nie zapisze wyniku. Kto ma otwartą grę w czasie wdrożenia, musi odświeżyć stronę.
4. Sprawdzić:
   - ekran ładowania (pierwsza strona po otwarciu przeglądarki), kasa `$` i gwiazdki w stopce,
   - karta „Co się dzieje” na stronie głównej i Dodatki → „⚡ Ostatnia aktywność”,
   - jedna gra do końca: „wasted” albo „misja zaliczona!”, wynik zapisany, kasa w menu rośnie,
   - logowanie adresem e-mail,
   - dodanie zdjęcia większego niż 1 MB (pod polem pojawi się „Zdjęcie zmniejszone: …”),
   - adres, którego nie ma (np. `/xyz`) → „wasted”.

## 5. Opcjonalnie: limit wielkości plików w nginx

Zdjęcia zmniejszają się teraz w przeglądarce, ale **filmy** większe niż 1 MB nginx dalej odrzuca (domyślny limit).
Żeby wrzucać filmy, w konfiguracji nginx (`/etc/nginx/sites-available/hlyw`) w bloku `server` dodać np.:

    client_max_body_size 50M;

i przeładować: `sudo nginx -t && sudo systemctl reload nginx`.

## 6. Turniej Trackmania — jak założyć

W kalendarzu dodać wydarzenie ze słowem „Trackmania” w tytule (np. „Turniej Trackmania”). Na stronie wydarzenia
organizator (albo admin) dodaje trasy, gracze zapisują się na wydarzenie i wpisują swoje czasy, np. `1:02.345`.
