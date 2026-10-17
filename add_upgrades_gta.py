# Dodaje wpisy do "Ostatnie Ulepszenia" o zmianach z 17.10.2026 (wygląd GTA i nowe funkcje).
# Uruchomienie: python add_upgrades_gta.py (tym samym Pythonem co aplikacja).
# Wpisy o tytule, który już jest w bazie, są pomijane - skrypt można puścić ponownie.
from app import create_app

UPGRADES = [
    ('Hlyw w stylu GTA 🌴',
     'Strona dostała nowy wygląd prosto z Los Santos:\n'
     '🔤 czcionka z logo GTA w nagłówkach, menu i przyciskach\n'
     '🌃 ciemny motyw z żółtymi akcentami\n'
     '🎬 ekran ładowania z losowym zdjęciem z galerii i wskazówką\n'
     '💀 zgubiłeś się? Strona, której nie ma, kończy się napisem WASTED'),
    ('Misja zaliczona!',
     'Pobij swój rekord w dowolnej grze, a dostaniesz „misja zaliczona!” z fanfarą.\n'
     'Przegrana kończy się klasycznym WASTED.\n'
     '🔊 Dźwięki wyłączysz w stopce strony.'),
    ('Kasa i gwiazdki poszukiwania 💵⭐',
     '💵 W menu widać Twoją kasę: 1,000 $ za każdy punkt w rankingu ogólnym Hall of Fame i 10 $ za każdą grę.\n'
     '⭐ Gwiazdki poszukiwania (1-5) rosną, im więcej grasz, piszesz na czacie, wrzucasz zdjęć i newsów. '
     'Liczy się ostatni tydzień - jak nic nie robisz, gwiazdki gasną.\n'
     'Gwiazdki i kasę widać w profilu, gwiazdki także na liście użytkowników.'),
    ('Korona dla TOP 3 👑',
     'Trzy najlepsze osoby z rankingu ogólnego Hall of Fame noszą koronę przy nicku - złotą, srebrną i brązową. '
     'Widać ją w rankingach, na czacie, w profilu i przy newsach.'),
    ('Powiadomienia jak SMS-y 📱',
     'Gdy ktoś doda newsa, wydarzenie, zdjęcia albo napisze na czacie, w rogu ekranu wyskoczy wiadomość '
     'jak z telefonu w GTA. Kliknij ją, żeby przejść od razu na miejsce.'),
    ('Turniej Trackmania 🏁',
     'Wydarzenie z „Trackmania” w tytule ma własny turniej: organizator dodaje trasy, a zapisani gracze wpisują '
     'swoje czasy (np. 1:02.345). Za miejsca na każdej trasie są punkty jak w F1 (25, 18, 15...), '
     'a z sumy wychodzi klasyfikacja generalna z podium.'),
    ('Logowanie e-mailem i większe zdjęcia',
     '✉️ Zalogujesz się nazwą użytkownika albo adresem e-mail.\n'
     '📷 Duże zdjęcia zmniejszają się same przed wysłaniem - koniec z błędem „413 Request Entity Too Large”.'),
    ('Uczciwe rankingi',
     'Wyniki gier są teraz sprawdzane przez serwer - nie da się już wysłać wymyślonego wyniku ani zapisać '
     'tej samej gry tysiące razy. Liczy się tylko to, co naprawdę wyjeździsz.'),
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
