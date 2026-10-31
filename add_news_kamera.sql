-- News o podglądzie drukarki 3D na żywo. Pomija, jeśli news o tym tytule już istnieje.
-- WYMAGA: plik obrazka app/static/images/newsy/drukarka.jpg (ścieżka jak w file_path poniżej).
-- Uruchomienie (dev):  sqlite3 instance/baza.db < add_news_kamera.sql
-- Na produkcji podaj właściwą ścieżkę bazy, np.:  sqlite3 /sciezka/do/instance/baza.db < add_news_kamera.sql

BEGIN;

INSERT INTO news (title, description, file_path, created_at, created_by)
SELECT 'Drukarka 3D live na HLYW! 🖨️🔴',
'Mamy to. Drukarka 3D wjeżdża na HLYW — i to na żywo! 🎥

Wchodzisz w zakładkę Kamera, przełączasz na „Kamera Drukarka" i oglądasz co właśnie wychodzi z drukarki — z kanapy, z roboty, z wychodka, skądkolwiek. Nie trzeba nic włączać, śmiga 24/7.

A pod obrazem komplet info na żywo:
🏷️ co się aktualnie drukuje
📈 postęp, czas do końca i numer warstwy
🌡️ temperatury obu dysz, stołu i komory
🧵 jakie filamenty siedzą w AMS (z kolorami!)
⚙️ aktualny etap roboty drukarki

Zaglądajcie i patrzcie, jak rośnie kolejne arcydzieło. 🫡',
'static/images/newsy/drukarka.jpg',
datetime('now'),
'1'
WHERE NOT EXISTS (SELECT 1 FROM news WHERE title = 'Drukarka 3D live na HLYW! 🖨️🔴');

COMMIT;
