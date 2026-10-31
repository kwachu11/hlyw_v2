# Dodaje wpisy do "Ostatnie Ulepszenia" o podglądzie drukarki 3D (kamera + parametry wydruku).
# Uruchomienie: python add_upgrades_kamera.py (tym samym Pythonem co aplikacja).
# Wpisy o tytule, który już jest w bazie, są pomijane - skrypt można puścić ponownie.
from app import create_app

# Kolejność: pierwszy element wyląduje na górze listy (ma najnowszą datę).
UPGRADES = [
    ('Podgląd drukarki 3D na żywo 🖨️',
     'W zakładce Kamera dorzuciliśmy podgląd drukarki 3D!\n'
     '📷 Przełącznik: kamera HLYW albo kamera drukarki - jednym kliknięciem\n'
     '🎥 Obraz z drukarki na żywo, z dowolnego miejsca i o dowolnej porze\n'
     '🔍 Pełny ekran, a na telefonie przybliżysz dwoma palcami\n'
     'Zajrzyj i zobacz, co właśnie wychodzi z drukarki.'),
    ('Parametry wydruku na żywo 📊',
     'Pod obrazem drukarki widać teraz wszystko, co się dzieje podczas druku:\n'
     '🏷️ Nazwę drukowanego modelu i aktualny stan (drukuje / wstrzymana / zakończono)\n'
     '📈 Pasek postępu - procent, szacowany czas i numer warstwy\n'
     '🌡️ Temperatury - obie dysze, stół i komora\n'
     '🧵 Filamenty w AMS - kolory, typy i ile zostało\n'
     '⚙️ Bieżący etap, np. czyszczenie dyszy czy skanowanie stołu\n'
     '⚠️ A gdy drukarka coś wykryje i wstrzyma druk (np. spaghetti) - zobaczysz alert.'),
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
