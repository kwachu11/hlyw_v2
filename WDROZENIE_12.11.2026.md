# Wdrożenie zmian z 08–12.11.2026 (ostatnie wdrożenie: 31.10.2026 ok. 15:00)

Co wchodzi: miniatury w galerii, trwałe logowanie, ukryta gra Pod Górkę, **Druk 3D** (propozycje, zdjęcia i profile
z MakerWorld, podgląd i ustawianie modelu 3D, edycja, miniatury STL, filamenty z AMS), lajki zdjęć, zdjęcia
w „Co się dzieje”, **panel sterowania** `/panel`, karuzela z bazy (szybsza strona główna).
Commity od `77e7a91` do `ea503d3` (77e7a91 z 31.10 15:18 jest w paczce na wszelki wypadek - nadpisanie tym samym nic nie psuje).

## 1. Kopia bazy na serwerze (przed wgraniem!)

Przy starcie aplikacja sama dokłada nowe tabele: `print_request`, `image_like`, `site_setting`, `carousel_image`,
`filament` oraz kolumny w `print_request` (m.in. `color_hex`, `model_info`). Jednorazowo wpisuje też 23 dotychczasowe
zdjęcia karuzeli i startową listę filamentów (PLA w 10 kolorach „na życzenie”). Nic nie jest usuwane, ale kopia nie zaszkodzi:

    cp instance/baza.db instance/baza.db.bak-12.11.2026

(albo plik bazy wskazany w `DATABASE_URI` w `.env` serwera)

## 2. Nowa biblioteka: Pillow

W venv na serwerze, w katalogu projektu:

    pip install pillow==11.3.0

Bez niej strona działa, ale bez miniatur: galeria i karuzela ładują pełne zdjęcia, a propozycje STL/3MF nie mają miniatur.

## 3. Pliki do wgrania (podmienić / dodać)

Wszystkie są w paczce `wdrozenie_12.11.2026.zip` w tych samych ścieżkach - wystarczy rozpakować w katalogu projektu.

Python:
- `app/__init__.py`
- `app/forms.py`
- `requirements.txt`

Skrypty jednorazowe (katalog główny projektu) - **nowe**:
- `add_upgrades_druk3d.py`
- `add_upgrades_galeria.py`
- `add_upgrades_druk3d_2.py`

Style, skrypty, obrazki:
- `app/static/css/custom.css`, `app/static/css/gta.css`
- `app/static/js/upload_resize.js`
- `app/static/js/model_viewer.js` — **nowy**
- `app/static/favicon.svg` — **nowy**
- `app/static/images/gorka.svg` — **nowy**

Szablony (`app/templates/`):
- **nowe:** `_model_viewer.html`, `druk3d.html`, `druk3d_nowa.html`, `druk3d_szczegoly.html`, `druk3d_filamenty.html`,
  `panel.html`, `gorka.html`, `ranking_gorka.html`
- zmienione: `_lightbox.html`, `_thumb.html`, `albums.html`, `base.html`, `body.html`, `camera.html`, `menu.html`

## 4. NIE wgrywać

- `baza.db`, `instance/` — bazy danych i pliki propozycji druku
- `.env` — serwer ma własny
- `CLAUDE.md`, `.gitignore`, pliki `WDROZENIE_*` — tylko dla nas
- zdjęcia z albumów (`app/static/images/0/`, `1/` …) — serwer ma swoje

## 5. Sprawdzić na serwerze przed restartem

- **`.env` serwera** musi mieć (od wdrożenia drukarki 31.10 - jeśli kamera drukarki na `/camera` działa, to są):
  `PRINTER_STATUS_URL`, `PRINTER_CONTROL_TOKEN` (ten sam co na malince), `PRINTER_STREAM_URL`.
  Bez dwóch pierwszych nie zadziała pobieranie zdjęć/profili z MakerWorld ani podgląd i import AMS.
- **nginx:** propozycje druku przyjmują pliki do 50 MB. Jeśli w `/etc/nginx/sites-available/hlyw` nie ma jeszcze
  `client_max_body_size`, dodać w bloku `server`:

      client_max_body_size 55M;

  i przeładować: `sudo nginx -t && sudo systemctl reload nginx`. Bez tego większe STL-e skończą się błędem 413.

## 6. Po wgraniu

1. Restart aplikacji (gunicorn) - wczyta nowy kod i dołoży tabele.
2. W venv, w katalogu projektu (każdy pomija wpisy, które już są):

       python add_upgrades_druk3d.py
       python add_upgrades_galeria.py
       python add_upgrades_druk3d_2.py

3. Jako admin: **Dodatki → 🧵 Filamenty do druku 3D → „Wczytaj z AMS”** - szpule z drukarki staną się
   „Dostępne od ręki”; nazwy kolorów można poprawić (np. Pomarańczowy → Brzoskwiniowy).
4. Sprawdzić:
   - strona główna: karuzela i baner „Nowość: Druk 3D”; **Dodatki → ⚙️ Panel sterowania** się otwiera,
   - galeria: miniatury w albumie, ❤ pod zdjęciem w przeglądarce zdjęć, nowe zdjęcie pojawia się w „Co się dzieje”,
   - **Dodatki → 🖨️ Druk 3D → Zaproponuj wydruk**: wklejony link z MakerWorld pobiera zdjęcia i profile (z „✓ H2C”),
     wrzucony STL pokazuje podgląd 3D, a po wysłaniu ma miniaturę na liście,
   - edycja własnej propozycji (✏️) i zmiana filamentu.
