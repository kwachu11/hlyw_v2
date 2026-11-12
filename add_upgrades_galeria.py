# Dodaje wpisy do "Ostatnie Ulepszenia" o lajkach zdjęć, zdjęciach w "Co się dzieje" i szybszej stronie głównej.
# Uruchomienie: python add_upgrades_galeria.py (tym samym Pythonem co aplikacja).
# Wpisy o tytule, który już jest w bazie, są pomijane - skrypt można puścić ponownie.
from app import create_app

# Kolejność: pierwszy element wyląduje na górze listy (ma najnowszą datę).
UPGRADES = [
    ('Lajki pod zdjęciami w galerii ❤️',
     'Zdjęcia i filmy w albumach można teraz polubić!\n'
     '❤️ Otwórz zdjęcie i kliknij serduszko na dole - drugie kliknięcie cofa lajka\n'
     '🔢 Liczbę lajków widać na miniaturze w albumie\n'
     '👀 Najedź na serduszko, żeby zobaczyć, kto polubił'),
    ('Nowe zdjęcia w „Co się dzieje” 📷',
     'Dodane zdjęcia wreszcie pokazują się w „Co się dzieje” na stronie głównej i w Ostatniej aktywności '
     '(wcześniej znikały, bo nie zapisywało się, kto je dodał).\n'
     'Widać tam też, kto polubił zdjęcia w którym albumie.'),
    ('Szybsza strona główna ⚡',
     'Karuzela zdjęć na stronie głównej ładuje się dużo szybciej - zamiast wszystkich zdjęć w pełnym rozmiarze '
     'od razu pobiera się tylko pierwsze, a kolejne doczytują się w tle. Mniej czekania i mniej zużytego internetu na telefonie.'),
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
