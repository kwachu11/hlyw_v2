# Dodaje wpisy do "Ostatnie Ulepszenia" o propozycjach do druku 3D (zdjęcia, profile, ustawianie modelu).
# Uruchomienie: python add_upgrades_druk3d.py (tym samym Pythonem co aplikacja).
# Wpisy o tytule, który już jest w bazie, są pomijane - skrypt można puścić ponownie.
from app import create_app

# Kolejność: pierwszy element wyląduje na górze listy (ma najnowszą datę).
UPGRADES = [
    ('Druk 3D - zaproponuj, co wydrukować 🖨️',
     'W menu Dodatki jest nowa zakładka Druk 3D! Możesz tam zaproponować, co wydrukować na drukarce HLYW.\n'
     '🔗 Wklej link do modelu albo 📎 wrzuć własny plik (STL, 3MF, OBJ, STEP)\n'
     '🎨 Wybierz jakość, filament, kolor i liczbę sztuk\n'
     '📋 Status propozycji i odpowiedź admina zobaczysz na jej stronie\n'
     'Modeli szukaj np. na MakerWorld, Thingiverse, Thangs, MyMiniFactory albo GrabCAD.'),
    ('Zdjęcia, czas druku i filament same z linku 📷',
     'Wklejasz link do modelu, a reszta dzieje się sama:\n'
     '📷 Wszystkie zdjęcia ze strony modelu w galerii - wybierasz, które ma być główne ⭐\n'
     '🏷️ Tytuł wpisuje się automatycznie\n'
     '⏱️ Z MakerWorld wybierasz profil druku i od razu widzisz czas oraz zużycie filamentu\n'
     'Działa z MakerWorld, Thingiverse, Thangs, MyMiniFactory i GrabCAD.'),
    ('Ustaw model, zanim go wyślesz 🔄',
     'Po wrzuceniu pliku zobaczysz model w 3D i możesz go ustawić tak, jak ma leżeć na stole:\n'
     '⟳ obrót o 90° wokół osi X, Y i Z\n'
     '⇋ odbicie lustrzane\n'
     '📏 skala w procentach - wymiary, waga i czas druku przeliczają się na bieżąco\n'
     'Kolorowe strzałki w rogu stołu pokazują, gdzie jest która oś.'),
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
