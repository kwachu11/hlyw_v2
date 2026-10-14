# Wdrożenie zmian z 14.10.2026

Wygląd i telefon, statusy zgłoszeń, nowy quiz, turniej FIFA z ćwierćfinałami, kalkulator czasu gry, usunięcie Statków.

## 1. Kopia bazy na serwerze (przed wgraniem!)

Przy starcie aplikacja sama dokłada do bazy nowe kolumny (`report.status`, `tournament.advance`) i tabele quizu (`quiz`, `quiz_item`, `quiz_response`).
To tylko dodawanie, ale kopia na wszelki wypadek nie zaszkodzi — skopiuj plik bazy z serwera.

## 2. Pliki do wgrania (podmienić / dodać)

Python:
- `app/__init__.py`

Skrypt jednorazowy (katalog główny projektu):
- `add_quiz_hlyw.py` — **nowy**

Style:
- `app/static/css/custom.css`

Szablony (`app/templates/`):
- `_fifa_timer.html` — **nowy** (kalkulator czasu gry)
- `quiz_edit.html` — **nowy**
- `quiz_host.html` — **nowy**
- `quiz.html`
- `quiz_admin.html`
- `_ranking_table.html`
- `base.html`
- `body.html`
- `breaking_news.html`
- `calendar.html`
- `camera.html`
- `event.html`
- `footer.html`
- `games.html`
- `hall_of_fame.html`
- `login.html`
- `menu.html`
- `profil.html`
- `user_settings.html`
- `uzytkownicy.html`
- `view_report.html`
- `view_report_list.html`

## 3. Pliki do usunięcia z serwera

- `app/templates/statki.html`
- `app/templates/ranking_statki.html`
- `app/static/images/statki.svg`

(Pusta tabela `statki` w bazie może zostać.)

## 4. NIE wgrywać

- `baza.db`, `instance/` — bazy danych
- `.env` — serwer ma własny
- `CLAUDE.md`, ten plik — tylko dla nas

## 5. Po wgraniu

1. Restart aplikacji (gunicorn), żeby wczytała nowy kod i dodała kolumny/tabele.
2. Raz: `python add_quiz_hlyw.py` (w venv, w katalogu projektu) — dodaje „Quiz o Hlywie” z 5 starymi pytaniami. Drugie uruchomienie nic nie robi.
3. Sprawdzić:
   - strona główna i menu (zaznaczona zakładka, „🎮 Gry” w menu, stopka „© 2024–2026”),
   - Dodatki → „🧠 Quiz — prowadzenie” (jako admin),
   - turniej FIFA: „Z grupy wychodzi” 2/4, kalkulator „⏱️ Ile to potrwa?”,
   - Dodatki → Zgłoszenia (statusy).

Jeśli na serwerze turniej ma już mecze pucharowe z wynikami, a chcesz ćwierćfinały: na stronie turnieju
„♻️ Resetuj fazę pucharową”, potem „Z grupy wychodzi: 4”.
