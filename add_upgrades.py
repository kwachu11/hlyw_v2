# Dodaje wpisy do "Ostatnie Ulepszenia" o zmianach z 10.10.2026.
# Uruchomienie: python add_upgrades.py (tym samym Pythonem co aplikacja).
# Wpisy o tytule, który już jest w bazie, są pomijane - skrypt można puścić ponownie.
from app import create_app

UPGRADES = [
    ('Nowa zakładka: Hall of Fame 🏆',
     'W menu pojawiła się zakładka Hall of Fame!\n'
     '🥇🥈🥉 Podium każdej gry w jednym miejscu\n'
     '📊 Ranking ogólny - za miejsca 1-10 w każdej grze zbierasz od 10 do 1 punktu\n'
     '👑 Mistrzowie poprzedniej edycji Snake, Tetrisa i Dino\n'
     'Sprawdź, kto naprawdę rządzi na Hlywie.'),
    ('Profile graczy',
     'Kliknij nazwę gracza w dowolnym rankingu, żeby zobaczyć jego profil: miejsce, rekord i liczbę prób w każdej grze, '
     'a przy Snake, Tetrisie i Dino także wynik z poprzedniej edycji.\n'
     'Swój profil znajdziesz w ustawieniach konta.'),
    ('Nowa edycja Snake, Tetrisa i Dino',
     'Od 10.10.2026 rusza nowa edycja - rekordy liczą się od zera!\n'
     'Wyniki poprzedniej edycji nie zniknęły: w każdym rankingu pod nową tabelą jest tabela "Poprzednia edycja".'),
    ('Odświeżona strona główna',
     'Na stronie głównej znajdziesz teraz:\n'
     '📈 statystyki - użytkownicy, gry rozegrane dziś, zdjęcia, oglądający kamerę\n'
     '🎮 liderów wszystkich gier\n'
     '📅 najbliższe wydarzenia z kalendarza\n'
     '🎥 kto teraz ogląda kamerę i 💬 ostatnie wiadomości z czatu\n'
     '📰 najnowsze newsy'),
    ('Nowa galeria',
     'Albumy mają teraz okładki i własne strony z siatką zdjęć.\n'
     'Zdjęcia i filmy otwierają się na pełnym ekranie - przewijasz strzałkami, klawiaturą albo palcem na telefonie.'),
    ('Kamera i czat w nowej odsłonie',
     '🎥 Obraz z kamery obok czatu, ze znaczkiem NA ŻYWO i zegarem\n'
     '💬 Wiadomości z datą i godziną, Enter wysyła\n'
     '🔥 Szybkie reakcje emoji jednym kliknięciem\n'
     '👀 "Kto teraz patrzy" działa poprawnie i pokazuje wszystkich oglądających'),
    ('Breaking News z reakcjami',
     'Newsy dostały nowy wygląd - najnowszy jest wyróżniony, a przy każdym widać autora i datę.\n'
     'Pod każdym newsem możesz zostawić reakcję: 👍 😂 🔥 😮 💀'),
    ('Bezpieczniejsze konta',
     '🔒 Hasła są teraz zaszyfrowane\n'
     '🔑 Nie pamiętasz hasła? Ustawisz nowe po podaniu nazwy użytkownika i emaila\n'
     '⚙️ Hasło zmienisz też w ustawieniach konta\n'
     '✅ Nowe konta działają od razu, bez potwierdzania maila'),
    ('Wygodniej na telefonie',
     'Strona została dopasowana do telefonów - mniejsze marginesy, czytelniejsze tabele, kalendarz ze strzałkami '
     'i zaznaczonym dzisiejszym dniem, a przy okazji poprawiliśmy sporo drobnych błędów.'),
]

app = create_app()

with app.app_context():
    db = app.extensions['sqlalchemy']
    Upgrade = next(m.class_ for m in db.Model.registry.mappers if m.class_.__name__ == 'Upgrade')

    print(f"Baza: {app.config['SQLALCHEMY_DATABASE_URI']}")
    added = 0
    # od najstarszego, żeby na liście (sortowanej malejąco po dacie) pierwszy wpis był na górze
    for title, description in reversed(UPGRADES):
        if Upgrade.query.filter_by(title=title).first():
            print(f'  pominięto (już jest): {title}')
            continue
        db.session.add(Upgrade(title=title, description=description))
        db.session.commit()  # osobno, żeby wpisy miały kolejne daty
        added += 1
        print(f'  dodano: {title}')
    print(f'Gotowe, dodano {added}.')
