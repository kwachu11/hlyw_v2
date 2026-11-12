# Dodaje wpisy do "Ostatnie Ulepszenia" o kolejnych zmianach w druku 3D (miniatury STL, edycja, filamenty, MakerWorld).
# Uruchomienie: python add_upgrades_druk3d_2.py (tym samym Pythonem co aplikacja).
# Wpisy o tytule, który już jest w bazie, są pomijane - skrypt można puścić ponownie.
from app import create_app

# Kolejność: pierwszy element wyląduje na górze listy (ma najnowszą datę).
UPGRADES = [
    ('Druk 3D: wybierz filament, który jest od ręki 🧵',
     'Przy propozycji wydruku wybierasz teraz konkretny filament i kolor:\n'
     '✅ Dostępne od ręki - to, co jest w drukarce albo na półce\n'
     '🛒 Na życzenie - trzeba dokupić, więc wydruk potrwa dłużej\n'
     '🎨 Podgląd 3D od razu pokazuje model w wybranym kolorze'),
    ('Więcej informacji z MakerWorld ⭐',
     'Po wklejeniu linku z MakerWorld przy każdym profilu druku widzisz teraz:\n'
     '⚙️ ustawienia - wysokość warstwy, liczba ścianek, wypełnienie, dysza\n'
     '✓ H2C - czy profil pasuje do naszej drukarki\n'
     '⭐ ocenę i ile razy był już drukowany\n'
     '📝 opis profilu, a na stronie propozycji także opis modelu od autora, tagi i licencję'),
    ('Edycja propozycji i miniatury z plików STL ✏️',
     '✏️ Swoją propozycję możesz teraz edytować, dopóki ma status „Nowa” - tytuł, ustawienie modelu, skalę, filament, a nawet podmienić plik\n'
     '🖼️ Wrzucony plik STL ma wreszcie miniaturę na liście propozycji (zdjęcie z podglądu 3D)\n'
     '⏎ Enter w formularzu już nie wysyła propozycji za wcześnie - np. przy zmianie skali tylko ją zatwierdza'),
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
