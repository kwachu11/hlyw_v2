-- News o nowej edycji gier i nowościach na stronie (10.10.2026).
-- Autor: pierwszy admin w bazie. Nie dodaje drugi raz, jeśli news o tym tytule już jest.
BEGIN;

INSERT INTO news (title, description, file_path, created_at, created_by)
SELECT '🎮 NOWA EDYCJA GIER WYSTARTOWAŁA – REKORDY OD ZERA! 🏆',
'Uwaga, gracze! Od dziś Snake, Tetris i Dino startują w NOWEJ EDYCJI. Wszystkie rekordy wyzerowane, tabele czyste, chwała do zdobycia od nowa! 🔥

Co się zmieniło?
🐍 Snake, 🧱 Tetris, 🦖 Dino – nowa edycja, liczą się tylko wyniki od 10.10
📜 Stare rekordy nie przepadły – w każdym rankingu jest tabela „Poprzednia edycja”
🏆 Nowa zakładka HALL OF FAME – podium każdej gry, ranking ogólny i mistrzowie poprzedniej edycji
👤 Profile graczy – kliknij czyjąś nazwę w rankingu i zobacz wszystkie jego wyniki
🧊 Ice Tower, ⭕ Kółko i krzyżyk, 🏎️ Formuła – też walczą o punkty w rankingu ogólnym

Jak działa ranking ogólny?
Za miejsca 1–10 w każdej grze zbierasz od 10 do 1 punktu. Kto ma najwięcej, ten zostaje królem Hlywa. 👑

Dostępne wymówki po przegranej:
📱 „Telefon mi się zaciął”
🍺 „Grałem po trzech piwach”
🐍 „Ten wąż skręcił sam”
🧱 „Klocek nie wszedł, bo gra jest zbugowana”
🦖 „Kaktus wyskoczył znikąd”

A poza grami: nowa strona główna, galeria z okładkami albumów, czat z datami i reakcjami, a pod newsami możecie zostawiać reakcje 👍 😂 🔥 😮 💀 – zacznijcie od tego!

Kto pierwszy wbije się na szczyt Hall of Fame? 🥇',
'static/images/snake.svg',
datetime('now'),
(SELECT CAST(id AS TEXT) FROM user WHERE is_admin != '0' ORDER BY id LIMIT 1)
WHERE NOT EXISTS (SELECT 1 FROM news WHERE title = '🎮 NOWA EDYCJA GIER WYSTARTOWAŁA – REKORDY OD ZERA! 🏆');

COMMIT;
