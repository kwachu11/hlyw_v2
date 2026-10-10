-- Wpisy do 'Ostatnie Ulepszenia' (10.10.2026). Pomija wpisy, których tytuł już jest w bazie.

BEGIN;

INSERT INTO upgrade (title, description, date)
SELECT 'Nowa zakładka: Hall of Fame 🏆',
'W menu pojawiła się zakładka Hall of Fame!
🥇🥈🥉 Podium każdej gry w jednym miejscu
📊 Ranking ogólny - za miejsca 1-10 w każdej grze zbierasz od 10 do 1 punktu
👑 Mistrzowie poprzedniej edycji Snake, Tetrisa i Dino
Sprawdź, kto naprawdę rządzi na Hlywie.',
datetime('now', '-0 seconds')
WHERE NOT EXISTS (SELECT 1 FROM upgrade WHERE title = 'Nowa zakładka: Hall of Fame 🏆');

INSERT INTO upgrade (title, description, date)
SELECT 'Profile graczy',
'Kliknij nazwę gracza w dowolnym rankingu, żeby zobaczyć jego profil: miejsce, rekord i liczbę prób w każdej grze, a przy Snake, Tetrisie i Dino także wynik z poprzedniej edycji.
Swój profil znajdziesz w ustawieniach konta.',
datetime('now', '-1 seconds')
WHERE NOT EXISTS (SELECT 1 FROM upgrade WHERE title = 'Profile graczy');

INSERT INTO upgrade (title, description, date)
SELECT 'Nowa edycja Snake, Tetrisa i Dino',
'Od 10.10.2026 rusza nowa edycja - rekordy liczą się od zera!
Wyniki poprzedniej edycji nie zniknęły: w każdym rankingu pod nową tabelą jest tabela "Poprzednia edycja".',
datetime('now', '-2 seconds')
WHERE NOT EXISTS (SELECT 1 FROM upgrade WHERE title = 'Nowa edycja Snake, Tetrisa i Dino');

INSERT INTO upgrade (title, description, date)
SELECT 'Odświeżona strona główna',
'Na stronie głównej znajdziesz teraz:
📈 statystyki - użytkownicy, gry rozegrane dziś, zdjęcia, oglądający kamerę
🎮 liderów wszystkich gier
📅 najbliższe wydarzenia z kalendarza
🎥 kto teraz ogląda kamerę i 💬 ostatnie wiadomości z czatu
📰 najnowsze newsy',
datetime('now', '-3 seconds')
WHERE NOT EXISTS (SELECT 1 FROM upgrade WHERE title = 'Odświeżona strona główna');

INSERT INTO upgrade (title, description, date)
SELECT 'Nowa galeria',
'Albumy mają teraz okładki i własne strony z siatką zdjęć.
Zdjęcia i filmy otwierają się na pełnym ekranie - przewijasz strzałkami, klawiaturą albo palcem na telefonie.',
datetime('now', '-4 seconds')
WHERE NOT EXISTS (SELECT 1 FROM upgrade WHERE title = 'Nowa galeria');

INSERT INTO upgrade (title, description, date)
SELECT 'Kamera i czat w nowej odsłonie',
'🎥 Obraz z kamery obok czatu, ze znaczkiem NA ŻYWO i zegarem
💬 Wiadomości z datą i godziną, Enter wysyła
🔥 Szybkie reakcje emoji jednym kliknięciem
👀 "Kto teraz patrzy" działa poprawnie i pokazuje wszystkich oglądających',
datetime('now', '-5 seconds')
WHERE NOT EXISTS (SELECT 1 FROM upgrade WHERE title = 'Kamera i czat w nowej odsłonie');

INSERT INTO upgrade (title, description, date)
SELECT 'Breaking News z reakcjami',
'Newsy dostały nowy wygląd - najnowszy jest wyróżniony, a przy każdym widać autora i datę.
Pod każdym newsem możesz zostawić reakcję: 👍 😂 🔥 😮 💀',
datetime('now', '-6 seconds')
WHERE NOT EXISTS (SELECT 1 FROM upgrade WHERE title = 'Breaking News z reakcjami');

INSERT INTO upgrade (title, description, date)
SELECT 'Bezpieczniejsze konta',
'🔒 Hasła są teraz zaszyfrowane
🔑 Nie pamiętasz hasła? Ustawisz nowe po podaniu nazwy użytkownika i emaila
⚙️ Hasło zmienisz też w ustawieniach konta
✅ Nowe konta działają od razu, bez potwierdzania maila',
datetime('now', '-7 seconds')
WHERE NOT EXISTS (SELECT 1 FROM upgrade WHERE title = 'Bezpieczniejsze konta');

INSERT INTO upgrade (title, description, date)
SELECT 'Wygodniej na telefonie',
'Strona została dopasowana do telefonów - mniejsze marginesy, czytelniejsze tabele, kalendarz ze strzałkami i zaznaczonym dzisiejszym dniem, a przy okazji poprawiliśmy sporo drobnych błędów.',
datetime('now', '-8 seconds')
WHERE NOT EXISTS (SELECT 1 FROM upgrade WHERE title = 'Wygodniej na telefonie');

COMMIT;
