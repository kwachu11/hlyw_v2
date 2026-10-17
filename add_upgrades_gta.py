# Dodaje wpisy do "Ostatnie Ulepszenia" o zmianach z 17.10.2026 (wygląd GTA i nowe funkcje).
# Uruchomienie: python add_upgrades_gta.py (tym samym Pythonem co aplikacja).
# Wpisy o tytule, który już jest w bazie, są pomijane - skrypt można puścić ponownie.
from app import create_app

UPGRADES = [
    # dopisane później tego samego dnia - przy ponownym uruchomieniu dodadzą się tylko te
    ('Co się dzieje ⚡',
     'Na stronie głównej jest nowa karta „Co się dzieje” - na żywo widać, kto gra, kto bije rekordy, '
     'kto jest na kamerze, kto wrzucił zdjęcia, zareagował pod newsem albo zapisał się na wydarzenie.\n'
     'Karta odświeża się sama co minutę, a nowe wpisy podświetlają się na żółto.\n'
     '📋 Pełna lista z ostatnich 2 tygodni: Dodatki → „⚡ Ostatnia aktywność”.'),
    ('Jak liczy się kasa? 💵',
     'Na dole Hall of Fame jest wyjaśnienie, skąd się bierze kasa, wyliczenie dla Twojego konta '
     'i lista 5 najbogatszych. Wyliczenie widać też w profilu pod kwotą.\n'
     'Kliknij zieloną kwotę w menu, żeby od razu tam przejść.'),
    ('Przybliżanie zdjęć 🔍',
     'W galerii i w newsach zdjęcia można wreszcie przybliżać:\n'
     '📱 na telefonie - szczypnięcie dwoma palcami albo podwójne stuknięcie\n'
     '🖱️ na komputerze - kółko myszy, dwuklik albo przycisk z lupą\n'
     'Przybliżone zdjęcie przesuwasz palcem lub myszą, a do następnego przechodzisz dopiero po oddaleniu.'),
    ('Ekran ładowania jak w GTA',
     'Ekran ładowania trwa dłużej i pokazuje kilka wskazówek z paskiem postępu, jak w GTA.\n'
     'Zdjęcia z galerii widać w całości - już bez ucinania głów. Kliknij albo naciśnij klawisz, żeby pominąć.'),
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
