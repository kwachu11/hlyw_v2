# Dodaje wpisy do "Ostatnie Ulepszenia" o zmianach z 14.11.2026 (zdjęcia wydruków, liga i wybór drużyn w FIFA).
# Uruchomienie: python add_upgrades_14_11.py (tym samym Pythonem co aplikacja).
# Wpisy o tytule, który już jest w bazie, są pomijane - skrypt można puścić ponownie.
from app import create_app

# Kolejność: pierwszy element wyląduje na górze listy (ma najnowszą datę).
UPGRADES = [
    ('FIFA: wybierz drużynę jak w grze ⚽',
     'Przy zapisie na turniej FIFA wybierasz najpierw ligę, a potem klub - jak w EA SPORTS FC 26:\n'
     '🏆 ponad 25 lig (LALIGA, Premier League, Bundesliga, Serie A, Ekstraklasa i wiele innych), reprezentacje i „Inna drużyna”\n'
     '🔒 klub zajęty przez kogoś innego jest wyszarzony - nikt nie zagra tą samą drużyną\n'
     '🔄 klub zmienisz, dopóki turniej się nie zacznie'),
    ('FIFA: turniej w formie ligi 🏟️',
     'Oprócz grup z półfinałami albo ćwierćfinałami turniej może być teraz ligą:\n'
     '📋 jedna tabela, każdy gra z każdym - albo mecz i rewanż\n'
     '🗓️ mecze ułożone w kolejki, remisy się liczą\n'
     '🥇 po ostatnim meczu TOP 3 tabeli staje na podium\n'
     'Kalkulator „Ile to potrwa?” liczy też czas ligi.'),
    ('Druk 3D: zdjęcia gotowych wydruków 📸',
     '📸 Przy propozycji wydruku zobaczysz zdjęcie gotowego modelu - prosto z drukarki, zrobione zaraz po wydruku\n'
     '🏡 Autor propozycji może dodać własne zdjęcia „wydruk w akcji” - gdzie stoi, do czego się przydał\n'
     '🖨️ Na stronie kamery przy ostatnich wydrukach jest zdjęcie po wydruku i znaczek ✅ udany / ❌ nieudany, a tytuły są po angielsku zamiast po chińsku\n'
     '🖼️ Poprawki w przeglądaniu zdjęć: zawsze da się je zamknąć, a strzałki działają też na telefonie'),
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
