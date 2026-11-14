
from dotenv import load_dotenv
import os
import glob
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import json
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, true
import re
import unicodedata
import uuid
import io
import zipfile
from urllib.parse import urlparse
from sqlalchemy.exc import IntegrityError, OperationalError
from flask import render_template, redirect, url_for, request
from flask_login import login_user, login_required, logout_user
from werkzeug.security import generate_password_hash, check_password_hash

from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, abort, send_file
from markupsafe import Markup
from flask_login import login_user, logout_user, login_required, current_user, LoginManager, UserMixin
from .forms import LoginForm, RegistrationForm
from itsdangerous import URLSafeTimedSerializer

from app.forms import AlbumForm, ImageForm, NewsForm, CalendarForm, UserSettingsForm, ReportForm, CommentForm, TestEmail, \
    ForgotPasswordForm, ResetPasswordForm, ChangePasswordForm, UpgradeForm, PrintRequestForm, PrintStatusForm, \
    PrintDeleteForm, PRINT_EXTENSIONS, PRINT_MAX_MB, PRINT_QUALITIES, PRINT_COLORS, PRINT_STATUSES

from datetime import datetime, timedelta
import calendar as callendar
from datetime import date

MONTH_NAMES_PL = ['', 'Styczeń', 'Luty', 'Marzec', 'Kwiecień', 'Maj', 'Czerwiec',
                  'Lipiec', 'Sierpień', 'Wrzesień', 'Październik', 'Listopad', 'Grudzień']

# pbkdf2 zamiast domyślnego scrypt - hash scrypt ma ~160 znaków i nie mieści się w kolumnie password (150)
PASSWORD_HASH_METHOD = 'pbkdf2:sha256'


def hash_password(password):
    return generate_password_hash(password, method=PASSWORD_HASH_METHOD)


def is_password_hash(value):
    return value.startswith(('pbkdf2:', 'scrypt:'))

from flask_mail import Mail, Message as Message_
import base64
from ftplib import FTP
from flask import session
import time
import hashlib
from itertools import combinations
import random

# Wczytaj zmienne środowiskowe z pliku .env





def _load_env():
    # Szukamy .env w app/ i w głównym katalogu projektu; .env.bak jako zapas
    app_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(app_dir)
    candidates = [os.path.join(d, name) for name in ('.env', '.env.bak') for d in (app_dir, base_dir)]
    for path in candidates:
        if os.path.isfile(path):
            load_dotenv(path)
            print(f'[hlyw] Zmienne środowiskowe wczytane z {path}')
            break
    if not os.getenv('SECRET_KEY'):
        raise RuntimeError('Brak SECRET_KEY - nie znaleziono pliku .env (szukano: ' + ', '.join(candidates) + ')')


# Bieżąca edycja Snake, Tetris i Dino liczy się od 10.10.2026
CURRENT_EDITION_START = datetime(2026, 10, 10)
# Poprzednia edycja (tabela w rankingach i "poprzedni rekord" na stronie z grami) to gry sprzed 09.10.2026
PREVIOUS_EDITION_END = datetime(2026, 10, 9)

ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'jfif', 'bmp', 'heic'}
ALLOWED_MEDIA_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | {'mp4', 'mov', 'webm'}
THUMBNAIL_SIZE = 480  # dłuższy bok miniatury w galerii (px)
CAROUSEL_SIZE = 1600  # dłuższy bok zdjęcia w karuzeli na stronie głównej (oryginały mają po kilka MB)
PRINT_THUMB_MAX_BYTES = 10 * 1024 * 1024  # większego obrazka z pliku 3MF nie rozpakowujemy

# Panel sterowania (/panel, tylko admin): ustawienia trzymane w tabeli site_setting.
# (klucz, typ, wartość domyślna, etykieta, grupa). Typy: bool, text, textarea, date (RRRR-MM-DD, puste = bez limitu), int.
SITE_SETTINGS = [
    ('marquee_on', 'bool', True, 'Pokazuj pasek', 'Pasek przewijany na górze strony głównej'),
    ('marquee_text', 'text', '🔥 Witaj na hlyw.pl v2! 🔥 | Nowy wygląd, nowe gry i stare rankingi wróciły — sprawdź, '
                             'czy wciąż jesteś na szczycie! 🏆', 'Treść paska', 'Pasek przewijany na górze strony głównej'),
    ('hero_title', 'text', 'Witaj na stronie hlyw.pl', 'Nagłówek', 'Powitanie'),
    ('hero_greeting', 'text', 'Zobacz, co słychać na Hlywie.', 'Tekst po „Cześć, <nick>!”', 'Powitanie'),
    ('promo_on', 'bool', True, 'Pokazuj baner', 'Baner na stronie głównej'),
    ('promo_until', 'date', '2026-11-30', 'Pokazuj do (włącznie; puste = bez końca)', 'Baner na stronie głównej'),
    ('promo_icon', 'text', '🖨️', 'Ikona (emoji)', 'Baner na stronie głównej'),
    ('promo_title', 'text', 'Nowość: Druk 3D', 'Tytuł', 'Baner na stronie głównej'),
    ('promo_text', 'textarea', 'Masz pomysł, co wydrukować na drukarce HLYW? Wklej link do modelu albo wrzuć plik STL - '
                               'zdjęcia, czas druku i zużycie filamentu policzą się same, a admin da znać, kiedy będzie gotowe.',
     'Treść', 'Baner na stronie głównej'),
    ('promo_btn1_text', 'text', 'Zaproponuj wydruk', 'Przycisk 1 - napis (puste = bez przycisku)', 'Baner na stronie głównej'),
    ('promo_btn1_url', 'text', '/druk3d/nowa', 'Przycisk 1 - adres', 'Baner na stronie głównej'),
    ('promo_btn2_text', 'text', 'Zobacz propozycje', 'Przycisk 2 - napis (puste = bez przycisku)', 'Baner na stronie głównej'),
    ('promo_btn2_url', 'text', '/druk3d', 'Przycisk 2 - adres', 'Baner na stronie głównej'),
    ('print_badge_on', 'bool', True, 'Plakietka NOWE przy „Druk 3D”', 'Menu'),
    ('print_badge_until', 'date', '2026-11-30', 'Plakietka do (włącznie; puste = bez końca)', 'Menu'),
    ('home_stats', 'bool', True, 'Liczniki (użytkownicy, gry, zdjęcia, kamera)', 'Sekcje strony głównej'),
    ('home_carousel', 'bool', True, 'Karuzela zdjęć', 'Sekcje strony głównej'),
    ('carousel_shuffle', 'bool', False, 'Losowa kolejność zdjęć', 'Karuzela'),
    ('carousel_seconds', 'int', 5, 'Zmiana zdjęcia co (s)', 'Karuzela'),
    ('home_leaders', 'bool', True, 'Liderzy gier', 'Sekcje strony głównej'),
    ('home_activity', 'bool', True, 'Co się dzieje', 'Sekcje strony głównej'),
    ('home_events', 'bool', True, 'Najbliższe wydarzenia', 'Sekcje strony głównej'),
    ('home_camera', 'bool', True, 'Teraz na kamerze', 'Sekcje strony głównej'),
    ('home_chat', 'bool', True, 'Ostatnio na czacie', 'Sekcje strony głównej'),
    ('home_news', 'bool', True, 'Breaking News', 'Sekcje strony głównej'),
    ('loading_on', 'bool', True, 'Ekran ładowania (raz na sesję)', 'Efekty'),
    ('loading_seconds', 'int', 6, 'Czas ekranu ładowania (s)', 'Efekty'),
    ('notify_on', 'bool', True, 'Powiadomienia SMS o aktywności innych', 'Efekty'),
]
# zdjęcia, które karuzela miała w kodzie - przy pierwszym starcie trafiają do tabeli carousel_image
CAROUSEL_DEFAULT_IMAGES = ['static/images/hlyw_1.png'] + [f'static/images/hlyw_{i}.jpg' for i in range(2, 24)]
SITE_SETTINGS_CACHE_SECONDS = 10

# Menu (zakładki): znane pozycje - klucz: (nazwa, endpoint, początki adresów podświetlających zakładkę, plakietka).
# Układ (kolejność, grupy rozwijane, własne nazwy, ukryte) ustawia admin w /panel/menu - zapis w site_setting 'menu_layout'.
# Plakietki: 'upgrade' = NOWE przy świeżym ulepszeniu, 'print' = NOWE w czasie promocji druku 3D, 'quiz' = LIVE (i tylko wtedy widać).
MENU_ITEMS = {
    'home': ('Strona Główna', 'index', ('/',), None),
    'albums': ('Galeria', 'albums', ('/album', '/add_album', '/add_image'), None),
    'news': ('Breaking News', 'news', ('/news', '/add_new'), None),
    'games': ('🎮 Gry', 'games', ('/games', '/ranking_', '/snake', '/tetris', '/dino', '/ice_tower', '/kolko_krzyzyk',
                                 '/formula', '/gorka'), None),
    'camera': ('Kamera', 'camera', ('/camera',), None),
    'calendar': ('Kalendarz', 'calendar', ('/calendar', '/add_entry', '/event'), None),
    'hof': ('🏆 Hall of Fame', 'hall_of_fame', ('/hall_of_fame', '/profil'), None),
    'upgrades': ('Ostatnie Ulepszenia', 'ostatnie_ulepszenia', ('/ostatnie-ulepszenia',), 'upgrade'),
    'quiz': ('🧠 Quiz', 'quiz', ('/quiz',), 'quiz'),
    'activity': ('⚡ Ostatnia aktywność', 'activity', ('/aktywnosc',), None),
    'print': ('🖨️ Druk 3D', 'print_list', ('/druk3d',), 'print'),
    'reports': ('Zgłoszenia', 'view_report_list', ('/report',), None),
    'users': ('Użytkownicy', 'users', ('/users',), None),
}
MENU_DEFAULT_LAYOUT = [{'key': k} for k in ('home', 'albums', 'news', 'games', 'camera', 'calendar', 'hof', 'upgrades', 'quiz')] + \
    [{'group': 'Dodatki', 'items': [{'key': k} for k in ('activity', 'print', 'reports', 'users')]}]
MENU_MAX_GROUPS = 8

# Zdjęcia propozycji druku 3D: 'wydruk' = gotowy wydruk (admin: kamera drukarki, chmura Bambu, plik),
# 'uzytkownik' = autor pokazuje, co zrobił z modelem. Pliki w static/images/druk3d/, dłuższy bok PRINT_PHOTO_SIZE.
PRINT_PHOTO_KINDS = {'wydruk': '📸 Gotowy wydruk', 'uzytkownik': '🏡 Wydruk w akcji'}
PRINT_PHOTO_SIZE = 1600
PRINT_PHOTO_MAX_BYTES = 15 * 1024 * 1024

# Druk 3D: filamenty do wyboru w propozycji (tabela filament, zarządza admin w /druk3d/filamenty)
OUR_PRINTER = 'H2C'   # nasza drukarka - profil MakerWorld z nią zgodny dostaje znaczek
FILAMENT_STATUSES = {'dostepny': 'Dostępne od ręki', 'na_zyczenie': 'Na życzenie', 'ukryty': 'Ukryte'}
FILAMENT_MATERIALS = ['PLA', 'PLA Matte', 'PLA Silk', 'PLA-CF', 'PETG', 'PETG-CF', 'TPU', 'ABS', 'ASA', 'PC', 'PA']  # podpowiedzi
FILAMENT_ANY, FILAMENT_OTHER, FILAMENT_KEEP = 'obojetnie', 'inny', 'obecny'   # specjalne wartości wyboru w formularzu   # każdy worker gunicorna trzyma ustawienia tyle sekund
# galeria zdjęć ze strony modelu: serwis na Raspberry Pi (headless Chromium), domyślnie obok PRINTER_STATUS_URL
# (Printables i Cults3D pokazują automatom stronę ochrony przed botami, Creality Cloud się nie doładowuje - pominięte)
MODEL_IMAGES_SITES = ('makerworld.com', 'thingiverse.com', 'thangs.com', 'myminifactory.com', 'grabcad.com')

NEWS_REACTIONS = ['👍', '😂', '🔥', '😮', '💀']

# Ochrona rankingów (zgłoszenie #22 - ktoś wysyłał tysiące wymyślonych wyników do Dino).
# Gra przy starcie dostaje jednorazowy bilet (GameRun), a zapis wyniku musi go oddać.
# Wynik nie może być większy niż: zapas + tempo * sekundy od startu (tempa z dużym zapasem
# względem tego, co da się realnie wyciągnąć w danej grze).
GAME_SCORE_LIMITS = {          # gra: (zapas, punktów na sekundę)
    'snake': (5, 6),           # 1 pkt za jabłko
    'tetris': (2000, 400),     # linie x poziom + punkty za twarde zrzucanie
    'dino': (100, 125),        # wynik = dystans / 8, maks. prędkość 920 px/s -> 115 pkt/s
    'ice_tower': (1000, 1500), # piętra + kombo (kwadrat długości)
    'kolko_krzyzyk': (5, 3),   # maks. 5 pkt za wygraną partię na trudnym
    'formula': (10, 20),
    'gorka': (50, 25),         # wynik = dystans w metrach; maks. prędkość ~18 m/s
}
# Kasa w stylu GTA (pasek w menu): za punkt w rankingu ogólnym Hall of Fame i za każdą rozegraną grę
CASH_PER_HOF_POINT = 1000
CASH_PER_GAME = 10
# "Gwiazdki poszukiwania" (1-5) za aktywność z ostatnich 7 dni: punkty za akcję i progi gwiazdek
WANTED_DAYS = 7
WANTED_WEIGHTS = {'gry': 1, 'czat': 2, 'zdjęcia': 1, 'newsy': 5, 'komentarze': 2, 'wydarzenia': 5}
WANTED_THRESHOLDS = [1, 15, 40, 100, 200]
# Ekran ładowania jak w GTA V (raz na sesję przeglądarki): losowe zdjęcie z galerii + wskazówka
LOADING_TIPS = [
    'Pobij rekord w dowolnej grze, a dostaniesz „misja zaliczona” i kasę na koncie.',
    'TOP 3 rankingu ogólnego Hall of Fame nosi koronę przy nicku.',
    'Za każdy punkt w Hall of Fame wpada 1,000 $, za każdą grę 10 $.',
    'Im więcej piszesz, grasz i wrzucasz zdjęć, tym więcej gwiazdek poszukiwania.',
    'Gwiazdki poszukiwania gasną, jeśli przez tydzień nic nie robisz.',
    'Coś nie działa? Zgłoś to w Dodatki → Zgłoszenia.',
    'Na kamerze widać, kto akurat ogląda.',
    'W kalendarzu zapiszesz się na turniej FIFA i Trackmanię.',
    'Kliknij nick w rankingu, żeby zobaczyć profil gracza.',
    'Reakcje pod newsami: 👍 😂 🔥 😮 💀 - wybierz mądrze.',
]
# Turniej Trackmania (wydarzenie z "trackmania" w tytule): punkty za miejsce na każdej trasie, jak w F1
TM_POINTS = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]
# Rodzaje aktywności, o których przychodzą powiadomienia (gry pomijamy - byłoby ich za dużo)
NOTIFY_KINDS = {'news', 'event', 'chat', 'photos', 'upgrade', 'tm', 'user', 'camera', 'album', 'match', 'print'}
CAMERA_VISIT_GAP = timedelta(minutes=2)   # dłuższa przerwa w oglądaniu kamery = nowe wejście
CAMERA_STREAM_URL = 'https://rtsp.me/embed/62bBnQNN'   # drugi obraz (drukarka) - PRINTER_STREAM_URL w .env
GAME_RUN_MAX_AGE = timedelta(hours=6)   # dłużej nikt nie gra jednej partii
GAME_RUN_STARTS_PER_MINUTE = 40
# Ulepszenie jest "nowe" (plakietka w menu i na liście) przez tyle dni
UPGRADE_NEW_DAYS = 14
# Statusy zgłoszeń: wartość w bazie -> (etykieta, klasa plakietki Bootstrapa). Zmienia je admin.
REPORT_STATUSES = {
    'nowe': ('Nowe', 'badge-primary'),
    'w_trakcie': ('W trakcie', 'badge-warning'),
    'zrobione': ('Zrobione', 'badge-success'),
    'odrzucone': ('Odrzucone', 'badge-secondary'),
}


def parse_tm_time(text):
    """'1:02.345', '62.345', '62,3' albo '1:02' -> milisekundy; None, gdy format jest zły."""
    m = re.fullmatch(r'\s*(?:(\d{1,2}):)?(\d{1,3})(?:[.,](\d{1,3}))?\s*', text or '')
    if not m:
        return None
    minutes, seconds, fraction = int(m.group(1) or 0), int(m.group(2)), (m.group(3) or '0').ljust(3, '0')
    if m.group(1) and seconds >= 60:
        return None
    total = (minutes * 60 + seconds) * 1000 + int(fraction)
    return total if total > 0 else None


def format_tm_time(ms):
    """62345 -> '1:02.345', 9876 -> '9.876'."""
    if ms is None:
        return '–'
    minutes, rest = divmod(int(ms), 60000)
    seconds, millis = divmod(rest, 1000)
    return f'{minutes}:{seconds:02d}.{millis:03d}' if minutes else f'{seconds}.{millis:03d}'


def to_local(dt):
    """Daty w bazie są w UTC (datetime.utcnow) - zamiana na czas serwera."""
    return dt + (datetime.now() - datetime.utcnow())


def when_label(dt):
    """'dziś 18:30', 'wczoraj 18:30', '08.10 18:30' albo '08.10.2025 18:30'."""
    local = to_local(dt)
    today = datetime.now().date()
    hour = local.strftime('%H:%M')
    if local.date() == today:
        return 'dziś ' + hour
    if local.date() == today - timedelta(days=1):
        return 'wczoraj ' + hour
    if local.year == today.year:
        return local.strftime('%d.%m ') + hour
    return local.strftime('%d.%m.%Y ') + hour


def create_app():
    _load_env()
    app = Flask(__name__)
    db = SQLAlchemy()

    app.secret_key = os.getenv('SECRET_KEY')  # Ustawienie secret key do sesji
    app.config['SECURITY_PASSWORD_SALT'] = os.getenv('SECURITY_PASSWORD_SALT')
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    # Ścieżka do bazy z DATABASE_URI w .env (osobny .env na serwerze i lokalnie);
    # gdy jej brak - baza.db w głównym katalogu projektu
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI') or 'sqlite:///' + os.path.join(base_dir, 'baza.db')
    db.init_app(app)

    # Tworzymy instancję LoginManager
    login_manager = LoginManager(app)
    login_manager.login_view = 'login'  # Widok logowania, jeśli użytkownik nie jest zalogowany
    login_manager.login_message = os.getenv('LOGIN_MESSAGE')  # Niestandardowy komunikat
    login_manager.login_message_category = os.getenv('LOGIN_MESSAGE_CATEGORY') # Opcjonalna kategoria (np. warning)

    # Inicjalizujemy login_manager z aplikacją
    login_manager.init_app(app)

    #maile
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
    app.config['MAIL_PORT'] = os.getenv('MAIL_PORT')
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS')
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')  # Twój adres email
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')  # Hasło do konta
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

    #test git

    mail = Mail(app)

    def convert_to_unix_path(path):
        return path.replace('\\', '/')

    def create_directory_if_not_exists(path):
        """Utwórz katalog, jeśli nie istnieje."""
        if not os.path.exists(path):
            os.makedirs(path)

    def save_upload(file, folder, allowed_extensions):
        """Zapisuje plik w app/static/images/<folder> pod losową nazwą i zwraca ścieżkę na dysku.
        Nazwy od użytkownika nie używamy - mogłaby wskazać inny katalog albo nadpisać cudzy plik.
        Zwraca None, gdy rozszerzenie jest niedozwolone."""
        ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
        if ext not in allowed_extensions:
            return None
        file_path = os.path.join('app', 'static', 'images', folder, uuid.uuid4().hex + '.' + ext)
        create_directory_if_not_exists(os.path.dirname(file_path))
        file.save(file_path)
        return file_path

    def get_event_days(year, month):
        events = Calendar.query.filter(
            db.extract('year', Calendar.date) == year,
            db.extract('month', Calendar.date) == month
        ).all()

        # dzień -> lista tytułów, żeby kalendarz pokazywał, co się dzieje, a nie tylko zielone pole
        event_days = {}
        for event in sorted(events, key=lambda e: e.date):
            event_days.setdefault(event.date.day, []).append(event.title)
        return event_days

    def generate_confirmation_token(email):
        serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
        return serializer.dumps(email, salt=app.config['SECURITY_PASSWORD_SALT'])

    def confirm_token(token, expiration=3600):
        serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
        try:
            email = serializer.loads(token, salt=app.config['SECURITY_PASSWORD_SALT'], max_age=expiration)
        except:
            return False
        return email

    def send_confirmation_email(user_email):
        token = generate_confirmation_token(user_email)
        confirm_url = url_for('confirm_email', token=token, _external=True)
        html = render_template('confirm.html', confirm_url=confirm_url)
        subject = "Proszę potwierdzić swoje konto"
        msg = Message_(subject=subject, recipients=[user_email], html=html)
        mail.send(msg)

    def generate_groups_and_matches(tournament, players):
        random.shuffle(players)
        half = len(players) // 2
        groups = {
            "A": players[:half],
            "B": players[half:]
        }

        for name, group_players in groups.items():
            group = TournamentGroup(tournament_id=tournament.id, name=name)
            db.session.add(group)
            db.session.flush()  # żeby mieć group.id

            # każdy z każdym
            for i in range(len(group_players)):
                for j in range(i + 1, len(group_players)):
                    match = TournamentMatch(
                        tournament_id=tournament.id,
                        group_id=group.id,
                        round="grupa",
                        home_player_id=group_players[i].user_id,
                        away_player_id=group_players[j].user_id
                    )
                    db.session.add(match)

    def round_robin(items):
        """Terminarz „każdy z każdym” metodą koła: lista kolejek z parami - w kolejce każdy gra najwyżej raz."""
        items = list(items)
        if len(items) % 2:
            items.append(None)
        rounds = []
        for _ in range(len(items) - 1):
            rounds.append([(items[i], items[-1 - i]) for i in range(len(items) // 2)
                           if items[i] is not None and items[-1 - i] is not None])
            items.insert(1, items.pop())
        return rounds

    def generate_league(tournament, players, legs):
        """Liga: jedna „grupa” ze wszystkimi graczami, mecze po kolejkach; przy rewanżu druga runda z zamienionym gospodarzem."""
        random.shuffle(players)
        group = TournamentGroup(tournament_id=tournament.id, name='Liga')
        db.session.add(group)
        db.session.flush()
        rounds = round_robin(p.user_id for p in players)
        if legs == 2:
            rounds += [[(away, home) for home, away in r] for r in rounds]
        for r in rounds:
            for home, away in r:
                db.session.add(TournamentMatch(tournament_id=tournament.id, group_id=group.id, round='grupa',
                                               home_player_id=home, away_player_id=away))

    KNOCKOUT_ROUNDS = ['1/4 finału', '1/2 finału', 'o 3. miejsce', 'finał']

    def match_winner_loser(match):
        """(zwycięzca, przegrany) meczu pucharowego albo (None, None), jeśli jeszcze nie rozegrany."""
        if match is None or match.home_score is None or match.away_score is None or match.home_score == match.away_score:
            return None, None
        if match.home_score > match.away_score:
            return match.home_player_id, match.away_player_id
        return match.away_player_id, match.home_player_id

    def has_score(match):
        return match.home_score is not None or match.away_score is not None

    def set_round(tournament, round_name, pairs):
        """Ustawia mecze rundy na podane pary [(gospodarz, gość)]; pairs=None = runda jeszcze niegotowa.
        Mecze z wynikiem zostawia - zwraca False, jeśli przez to drabinka nie zgadza się z tabelą."""
        matches = TournamentMatch.query.filter_by(tournament_id=tournament.id, round=round_name) \
            .order_by(TournamentMatch.id).all()
        pairs = pairs or []
        ok = True
        for i, match in enumerate(matches):
            if i >= len(pairs):          # ta runda nie powinna (jeszcze) istnieć albo ma za dużo meczów
                if has_score(match):
                    ok = False
                else:
                    db.session.delete(match)
            elif (match.home_player_id, match.away_player_id) != pairs[i]:
                if has_score(match):
                    ok = False           # już rozegrany - nie ruszamy, admin musi poprawić ręcznie
                else:
                    match.home_player_id, match.away_player_id = pairs[i]
        for home_id, away_id in pairs[len(matches):]:
            db.session.add(TournamentMatch(tournament_id=tournament.id, round=round_name,
                                           home_player_id=home_id, away_player_id=away_id))
        db.session.flush()
        return ok

    def round_results(tournament, round_name):
        matches = TournamentMatch.query.filter_by(tournament_id=tournament.id, round=round_name) \
            .order_by(TournamentMatch.id).all()
        return [match_winner_loser(m) for m in matches]

    def sync_knockout(tournament):
        """Uzupełnia drabinkę po każdym wpisanym wyniku. Z każdej z 2 grup wychodzi tournament.advance graczy:
        2 -> półfinały A1-B2, B1-A2; 4 -> ćwierćfinały A1-B4, B2-A3, B1-A4, A2-B3 (zwycięzcy grup w różnych
        połówkach). Potem finał i mecz o 3. miejsce. Zwraca komunikat dla admina albo None."""
        if tournament.is_league:
            return None                     # liga nie ma fazy pucharowej
        advance = 4 if tournament.advance == 4 else 2
        groups = TournamentGroup.query.filter_by(tournament_id=tournament.id).order_by(TournamentGroup.name).all()
        group_matches = TournamentMatch.query.filter_by(tournament_id=tournament.id, round='grupa').all()
        tables = [calculate_group_table(g) for g in groups]
        groups_done = len(groups) == 2 and group_matches and all(len(t) >= advance for t in tables) \
            and not any(m.home_score is None or m.away_score is None for m in group_matches)

        plan = dict.fromkeys(KNOCKOUT_ROUNDS)   # runda -> pary albo None (niegotowa)
        if groups_done:
            a, b = [[row['player'].id for row in t[:advance]] for t in tables]
            if advance == 4:
                plan['1/4 finału'] = [(a[0], b[3]), (b[1], a[2]), (b[0], a[3]), (a[1], b[2])]
            else:
                plan['1/2 finału'] = [(a[0], b[1]), (b[0], a[1])]

        ok = set_round(tournament, '1/4 finału', plan['1/4 finału'])
        if advance == 4 and plan['1/4 finału']:
            winners = [w for w, _ in round_results(tournament, '1/4 finału')]
            if len(winners) == 4 and all(winners):
                plan['1/2 finału'] = [(winners[0], winners[1]), (winners[2], winners[3])]
        ok &= set_round(tournament, '1/2 finału', plan['1/2 finału'])

        if plan['1/2 finału']:
            results = round_results(tournament, '1/2 finału')
            if len(results) == 2 and all(w for w, _ in results):
                plan['finał'] = [(results[0][0], results[1][0])]
                plan['o 3. miejsce'] = [(results[0][1], results[1][1])]
        ok &= set_round(tournament, 'finał', plan['finał'])
        ok &= set_round(tournament, 'o 3. miejsce', plan['o 3. miejsce'])
        return None if ok else 'Drabinka nie zgadza się z wynikami, bo któryś mecz pucharowy ma już wynik - ' \
                               'popraw go albo zresetuj fazę pucharową.'

    def calculate_group_table(group):
        players = set()
        for match in group.matches:
            players.add(match.home_player)
            players.add(match.away_player)

        table = []
        for player in players:
            points = 0
            goals_for = 0
            goals_against = 0
            wins = 0
            draws = 0
            losses = 0

            for match in group.matches:
                if match.home_score is None or match.away_score is None:
                    continue
                if match.home_player == player:
                    goals_for += match.home_score
                    goals_against += match.away_score
                    if match.home_score > match.away_score:
                        points += 3;
                        wins += 1
                    elif match.home_score == match.away_score:
                        points += 1;
                        draws += 1
                    else:
                        losses += 1
                elif match.away_player == player:
                    goals_for += match.away_score
                    goals_against += match.home_score
                    if match.away_score > match.home_score:
                        points += 3;
                        wins += 1
                    elif match.away_score == match.home_score:
                        points += 1;
                        draws += 1
                    else:
                        losses += 1

            table.append({
                "player": player,
                "points": points,
                "wins": wins,
                "draws": draws,
                "losses": losses,
                "goals_for": goals_for,
                "goals_against": goals_against,
                "goal_diff": goals_for - goals_against
            })

        return sorted(table, key=lambda x: (x["points"], x["goal_diff"], x["goals_for"]), reverse=True)


    class User(db.Model, UserMixin):
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(150), unique=True, nullable=False)
        email = db.Column(db.String(150), nullable=False)
        password = db.Column(db.String(150), nullable=False)
        photo=db.Column(db.String(150), nullable=False, default='default.jpg')
        confirmed = db.Column(db.Boolean, default=False)
        confirmed_on = db.Column(db.DateTime, nullable=True)
        is_admin = db.Column(db.String(10), default="0")

    class Albums(db.Model):
        __tablename__ = 'albums'
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(100), nullable=False)
        description = db.Column(db.String(200))
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        created_by = db.Column(db.String(500))


        # Relacja z tabelą Image
        images = db.relationship('Images', backref='albums', lazy=True)

    # Model Obrazka
    class Images(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        file_path = db.Column(db.String(200), nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        created_by = db.Column(db.String(500))

        # Kolumna klucza obcego do tabeli Album
        album_id = db.Column(db.Integer, db.ForeignKey('albums.id'), nullable=False)

    # Model Newsu
    class News(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        title = db.Column(db.String(200), nullable=False)
        description = db.Column(db.String(2000), nullable=False)
        file_path = db.Column(db.String(200), nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        created_by = db.Column(db.String(500))



    class Calendar(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        title = db.Column(db.String(100), nullable=False)
        description = db.Column(db.String(500))
        date = db.Column(db.DateTime, nullable=False)
        created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
        created_by = db.Column(db.String(500))
        participants = db.relationship('Participant', backref='calendar', lazy=True)

    class Participant(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.String(100), nullable=False)
        event_id = db.Column(db.Integer, db.ForeignKey('calendar.id'),
                             nullable=False)  # Klucz obcy odnoszący się do wydarzenia
        created_at = db.Column(db.DateTime, default=datetime.utcnow)   # kiedy się zapisał (starsze wpisy: brak)

    class Message(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        content = db.Column(db.String(500), nullable=False)
        timestamp = db.Column(db.DateTime, default=datetime.utcnow)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Powiązanie z User
        user = db.relationship('User', backref=db.backref('messages', lazy=True))  # Powiązanie odwrotne do User

    class NewsReaction(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        news_id = db.Column(db.Integer, db.ForeignKey('news.id'), nullable=False, index=True)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        emoji = db.Column(db.String(16), nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)   # starsze reakcje: brak
        __table_args__ = (db.UniqueConstraint('news_id', 'user_id', 'emoji'),)

    class ImageLike(db.Model):
        """Polubienie zdjęcia / filmu z galerii (❤)."""
        id = db.Column(db.Integer, primary_key=True)
        image_id = db.Column(db.Integer, db.ForeignKey('images.id'), nullable=False, index=True)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        __table_args__ = (db.UniqueConstraint('image_id', 'user_id'),)

    class Filament(db.Model):
        """Filament (materiał + kolor) do wyboru w propozycji druku 3D."""
        id = db.Column(db.Integer, primary_key=True)
        material = db.Column(db.String(30), nullable=False)
        name = db.Column(db.String(40), nullable=False)        # nazwa koloru, np. Czerwony
        hex = db.Column(db.String(7), nullable=False)          # #RRGGBB
        status = db.Column(db.String(20), nullable=False, default='dostepny')
        created_at = db.Column(db.DateTime, default=datetime.utcnow)

    class CarouselImage(db.Model):
        """Zdjęcie w karuzeli na stronie głównej (kolejność: position)."""
        id = db.Column(db.Integer, primary_key=True)
        file_path = db.Column(db.String(200), nullable=False)
        position = db.Column(db.Integer, nullable=False, default=0)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        created_by = db.Column(db.Integer, db.ForeignKey('user.id'))

    class SiteSetting(db.Model):
        """Ustawienie z panelu sterowania (wartość jako tekst, typ z SITE_SETTINGS)."""
        key = db.Column(db.String(50), primary_key=True)
        value = db.Column(db.Text)
        updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))

    class Presence(db.Model):
        """Kiedy użytkownik ostatnio był na stronie kamery. W bazie, a nie w pamięci,
        bo każdy worker gunicorna ma własną pamięć i widziałby innych oglądających."""
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
        last_seen = db.Column(db.DateTime, nullable=False)
        user = db.relationship('User')

    class CameraVisit(db.Model):
        """Jedno oglądanie kamery: od wejścia do ostatniego sygnału (strona kamery pinguje co 5 s).
        Presence mówi tylko, kto ogląda teraz - to jest historia do ostatniej aktywności."""
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
        started_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
        last_seen = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
        user = db.relationship('User')

    class Upgrade(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        title = db.Column(db.String(150), nullable=False)
        description = db.Column(db.Text, nullable=False)
        date = db.Column(db.DateTime, default=datetime.utcnow)

        def __repr__(self):
            return f'<Upgrade {self.title}>'

    class Report(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        title = db.Column(db.String(150), nullable=False)
        description = db.Column(db.Text, nullable=False)
        created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
        status = db.Column(db.String(20), nullable=False, default='nowe', server_default='nowe')

        # Powiązanie z użytkownikiem - klucz obcy
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

        # Relacja odwrotna
        user = db.relationship('User', backref='reports', lazy=True)

    class PrintRequest(db.Model):
        """Propozycja do druku 3D: plik w instance/druk3d i/lub link do modelu."""
        __tablename__ = 'print_request'
        id = db.Column(db.Integer, primary_key=True)
        title = db.Column(db.String(150), nullable=False)
        description = db.Column(db.Text)
        file_path = db.Column(db.String(100))     # losowa nazwa na dysku
        file_name = db.Column(db.String(200))     # oryginalna nazwa do pobrania
        link = db.Column(db.String(500))
        image_url = db.Column(db.String(1000))    # zdjęcie osadzane bezpośrednio z serwisu z modelem
        thumb_path = db.Column(db.String(100))    # miniatura wyciągnięta z pliku 3MF (instance/druk3d)
        gallery = db.Column(db.Text)              # JSON z adresami zdjęć ze strony modelu (pobrane przez Pi)
        print_profile = db.Column(db.Text)        # JSON: wybrany profil druku z MakerWorld (czas, gramy, filamenty)
        print_transform = db.Column(db.Text)      # JSON {ops, scale}: ustawienie modelu z podglądu (obroty, odbicia, skala)
        quality = db.Column(db.String(20), nullable=False)
        material = db.Column(db.String(30), nullable=False)
        color = db.Column(db.String(40), nullable=False)
        model_info = db.Column(db.Text)             # JSON z MakerWorld: opis autora, tagi, licencja
        color_hex = db.Column(db.String(9))         # kolor wybranego filamentu (starsze: z PRINT_COLORS po nazwie)
        quantity = db.Column(db.Integer, nullable=False, default=1)
        status = db.Column(db.String(20), nullable=False, default='nowa')
        admin_note = db.Column(db.String(500))
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        status_at = db.Column(db.DateTime)        # ostatnia zmiana statusu (do aktywności)
        status_by = db.Column(db.Integer, db.ForeignKey('user.id'))
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        user = db.relationship('User', foreign_keys=[user_id], lazy=True)

    class PrintPhoto(db.Model):
        """Zdjęcie propozycji druku: gotowy wydruk albo autor pokazujący, co z nim zrobił."""
        __tablename__ = 'print_photo'
        id = db.Column(db.Integer, primary_key=True)
        request_id = db.Column(db.Integer, db.ForeignKey('print_request.id'), nullable=False, index=True)
        file_path = db.Column(db.String(200), nullable=False)    # static/images/druk3d/<losowa>.jpg
        kind = db.Column(db.String(20), nullable=False, default='wydruk')
        source = db.Column(db.String(20))                        # kamera / chmura / plik
        caption = db.Column(db.String(200))
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
        author = db.relationship('User', foreign_keys=[created_by], lazy=True)
        request = db.relationship('PrintRequest', backref=db.backref('photos', lazy=True, order_by='PrintPhoto.created_at'))

    class Comment(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        content = db.Column(db.Text, nullable=False)
        created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

        # Powiązanie z raportem (jeśli komentarze są powiązane z raportami)
        report_id = db.Column(db.Integer, db.ForeignKey('report.id'), nullable=False)

        # Powiązanie z użytkownikiem - klucz obcy
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

        # Relacja odwrotna do użytkownika
        user = db.relationship('User', backref='comments', lazy=True)

    class Snake(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        points = db.Column(db.Integer)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        created_by = db.Column(db.String(500))

    class Tetris(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        points = db.Column(db.Integer)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        created_by = db.Column(db.String(500))

    class Dino(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        points = db.Column(db.Integer)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        created_by = db.Column(db.String(500))

    class IceTower(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        points = db.Column(db.Integer)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        created_by = db.Column(db.String(500))

    class KolkoKrzyzyk(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        points = db.Column(db.Integer)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        created_by = db.Column(db.String(500))

    class Formula(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        points = db.Column(db.Integer)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        created_by = db.Column(db.String(500))

    class Gorka(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        points = db.Column(db.Integer)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        created_by = db.Column(db.String(500))

    class GameRun(db.Model):
        """Jednorazowy bilet na jedną partię gry - patrz GAME_SCORE_LIMITS."""
        id = db.Column(db.String(32), primary_key=True)
        user_id = db.Column(db.Integer, nullable=False, index=True)
        game = db.Column(db.String(30), nullable=False)
        started_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
        used = db.Column(db.Boolean, nullable=False, default=False)

    # Quiz na żywo: admin układa pytania i prowadzi quiz pytanie po pytaniu, gracze odpowiadają z telefonów.
    # (Stare tabele quiz_question / quiz_answer / quiz_participant zostają w bazie, ale nie są już używane.)
    class Quiz(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        title = db.Column(db.String(150), nullable=False)
        state = db.Column(db.String(20), nullable=False, default='szkic')  # szkic / trwa / koniec
        current_item_id = db.Column(db.Integer, nullable=True)   # pytanie wyświetlane teraz graczom
        revealed = db.Column(db.Boolean, nullable=False, default=False)  # czy pokazano poprawną odpowiedź
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        items = db.relationship('QuizItem', backref='quiz', order_by='QuizItem.position, QuizItem.id',
                                cascade='all, delete-orphan')

    class QuizItem(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False, index=True)
        position = db.Column(db.Integer, nullable=False, default=0)
        text = db.Column(db.Text, nullable=False)
        kind = db.Column(db.String(10), nullable=False, default='abcd')  # abcd / otwarte
        options = db.Column(db.Text, nullable=True)        # JSON: {"a": "...", "b": "..."} dla abcd
        correct_answer = db.Column(db.String(500), nullable=False)  # litera albo tekst; kilka wariantów po |
        points = db.Column(db.Integer, nullable=False, default=1)
        responses = db.relationship('QuizResponse', backref='item', cascade='all, delete-orphan')

        @property
        def options_dict(self):
            return json.loads(self.options) if self.options else {}

        def correct_label(self):
            if self.kind == 'abcd':
                return f"{self.correct_answer.upper()}) {self.options_dict.get(self.correct_answer, '')}"
            return self.correct_answer.replace('|', ' / ')

    class QuizResponse(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        item_id = db.Column(db.Integer, db.ForeignKey('quiz_item.id'), nullable=False, index=True)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        answer = db.Column(db.String(500), nullable=False)
        is_correct = db.Column(db.Boolean, nullable=False, default=False)  # liczone automatycznie, admin może zmienić
        answered_at = db.Column(db.DateTime, default=datetime.utcnow)
        user = db.relationship('User')
        __table_args__ = (db.UniqueConstraint('item_id', 'user_id'),)

    class FifaParticipant(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        event_id = db.Column(db.Integer, db.ForeignKey('calendar.id'))
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
        role = db.Column(db.String(20))  # "player" albo "observer"
        club = db.Column(db.String(100), nullable=True)  # tylko jeśli player
        created_at = db.Column(db.DateTime, default=datetime.utcnow)   # kiedy się zapisał (starsze wpisy: brak)

    class Tournament(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        event_id = db.Column(db.Integer, db.ForeignKey('calendar.id'))
        started = db.Column(db.Boolean, default=False)
        finished = db.Column(db.Boolean, default=False)
        advance = db.Column(db.Integer, nullable=False, default=2, server_default='2')  # ilu wychodzi z grupy: 2 albo 4; 0 = liga
        legs = db.Column(db.Integer, nullable=False, default=1, server_default='1')        # liga: 1 = raz, 2 = mecz i rewanż

        @property
        def is_league(self):
            return self.advance == 0

        groups = db.relationship('TournamentGroup', backref='tournament')
        matches = db.relationship('TournamentMatch', backref='tournament')

    class TournamentGroup(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'))
        name = db.Column(db.String(10))  # np. "Grupa A"

        matches = db.relationship('TournamentMatch', backref='group')

    class TournamentMatch(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'))
        group_id = db.Column(db.Integer, db.ForeignKey('tournament_group.id'), nullable=True)
        round = db.Column(db.String(50))  # "grupy", "1/2 finału", "finał"
        home_player_id = db.Column(db.Integer, db.ForeignKey('user.id'))
        away_player_id = db.Column(db.Integer, db.ForeignKey('user.id'))
        home_score = db.Column(db.Integer, nullable=True)
        away_score = db.Column(db.Integer, nullable=True)
        score_at = db.Column(db.DateTime, nullable=True)   # kiedy wpisano wynik - do ostatniej aktywności

        home_player = db.relationship('User', foreign_keys=[home_player_id])
        away_player = db.relationship('User', foreign_keys=[away_player_id])

    class TmTrack(db.Model):
        """Trasa w turnieju Trackmania (wydarzenie z "trackmania" w tytule)."""
        id = db.Column(db.Integer, primary_key=True)
        event_id = db.Column(db.Integer, db.ForeignKey('calendar.id'), nullable=False, index=True)
        name = db.Column(db.String(100), nullable=False)
        times = db.relationship('TmTime', backref='track', cascade='all, delete-orphan')

    class TmTime(db.Model):
        """Czas gracza na trasie - jeden na gracza i trasę, nowy wpis zastępuje stary."""
        id = db.Column(db.Integer, primary_key=True)
        track_id = db.Column(db.Integer, db.ForeignKey('tm_track.id'), nullable=False, index=True)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        time_ms = db.Column(db.Integer, nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        user = db.relationship('User')
        __table_args__ = (db.UniqueConstraint('track_id', 'user_id'),)

    # Tworzenie tabel w bazie danych przy starcie aplikacji
    # Kilka workerów (gunicorn) startuje naraz i każdy woła create_all - gdy dwa jednocześnie
    # zobaczą brak nowej tabeli, drugi dostaje "table already exists". Wtedy ponawiamy:
    # create_all pomija tabele, które już istnieją.
    with app.app_context():
        for attempt in range(3):
            try:
                db.create_all()
                break
            except OperationalError as e:
                if 'already exists' not in str(e) or attempt == 2:
                    raise

        # create_all nie dodaje kolumn do istniejących tabel - brakujące dokładamy ręcznie.
        # "duplicate column" = inny worker zdążył pierwszy, wtedy nic nie robimy.
        for table, column, ddl in ([
            ('report', 'status', "VARCHAR(20) NOT NULL DEFAULT 'nowe'"),
            ('tournament', 'advance', "INTEGER NOT NULL DEFAULT 2"),
            ('tournament', 'legs', "INTEGER NOT NULL DEFAULT 1"),
            ('participant', 'created_at', "DATETIME"),
            ('fifa_participant', 'created_at', "DATETIME"),
            ('news_reaction', 'created_at', "DATETIME"),
            ('tournament_match', 'score_at', "DATETIME"),
            ('print_request', 'image_url', "VARCHAR(1000)"),
            ('print_request', 'thumb_path', "VARCHAR(100)"),
            ('print_request', 'gallery', "TEXT"),
            ('print_request', 'print_profile', "TEXT"),
            ('print_request', 'print_transform', "TEXT"),
            ('print_request', 'color_hex', "VARCHAR(9)"),
            ('print_request', 'model_info', "TEXT"),
        ] if db.engine.dialect.name == 'sqlite' else []):
            existing = [row[1] for row in db.session.execute(db.text(f'PRAGMA table_info({table})'))]
            if column not in existing:
                try:
                    db.session.execute(db.text(f'ALTER TABLE {table} ADD COLUMN {column} {ddl}'))
                    db.session.commit()
                except OperationalError as e:
                    db.session.rollback()
                    if 'duplicate column' not in str(e):
                        raise

        if not db.session.get(SiteSetting, 'filaments_seeded'):
            try:
                db.session.add(SiteSetting(key='filaments_seeded', value='1'))
                db.session.add_all(Filament(material='PLA', name=name, hex=hex_, status='na_zyczenie')
                                   for name, hex_ in PRINT_COLORS.items() if hex_.startswith('#'))
                db.session.commit()
            except IntegrityError:
                db.session.rollback()

        # Karuzela była wpisana na sztywno w kodzie - raz przenosimy te zdjęcia do bazy.
        # Flaga w site_setting (klucz główny) pilnuje, żeby zrobił to tylko jeden worker i tylko raz,
        # więc usunięcie wszystkich zdjęć w panelu nie przywróci ich przy restarcie.
        if not db.session.get(SiteSetting, 'carousel_seeded'):
            try:
                db.session.add(SiteSetting(key='carousel_seeded', value='1'))
                db.session.add_all(CarouselImage(file_path=path, position=i)
                                   for i, path in enumerate(CAROUSEL_DEFAULT_IMAGES))
                db.session.commit()
            except IntegrityError:
                db.session.rollback()


    @app.template_filter('media_url')
    def media_url(path):
        """Ścieżka z bazy (np. static\\images\\3\\x.jpg z Windowsa) jako adres od katalogu głównego,
        żeby działała też na podstronach typu /albums/3."""
        return '/' + (path or '').replace('\\', '/').lstrip('/')

    @app.template_filter('avatar_url')
    def avatar_url(photo):
        """Adres zdjęcia profilowego; bez zdjęcia - domyślny awatar."""
        return url_for('static', filename='images/profile_pics/' + (photo or 'default.jpg'))

    @app.template_filter('plural')
    def plural(n, one, few, many):
        """Polska odmiana: 1 zdjęcie, 2 zdjęcia, 5 zdjęć."""
        if n == 1:
            word = one
        elif n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
            word = few
        else:
            word = many
        return f'{n} {word}'

    @app.template_filter('br_to_newline')
    def br_to_newline(text):
        """Zamienia <br> z opisów na nowe linie. Reszta HTML jest potem escapowana przez Jinja,
        więc np. <script> w opisie wyświetli się jako tekst, a nie uruchomi."""
        return re.sub(r'<br\s*/?>', '\n', text or '', flags=re.IGNORECASE)

    app.add_template_filter(when_label, 'when')
    app.add_template_filter(format_tm_time, 'tm_time')

    # ===================== Panel sterowania =====================

    settings_cache = {'at': 0, 'data': None}

    def setting_to_text(kind, value):
        """Wartość w postaci tekstowej, tak jak trafia do bazy."""
        return ('1' if value else '0') if kind == 'bool' else str(value)

    def setting_from_text(kind, raw, default):
        if raw is None:
            return default
        if kind == 'bool':
            return raw == '1'
        if kind == 'int':
            try:
                return int(raw)
            except ValueError:
                return default
        return raw

    def site_settings():
        """Wszystkie ustawienia panelu: {klucz: wartość}, z bazy albo domyślne."""
        if settings_cache['data'] is None or time.time() - settings_cache['at'] > SITE_SETTINGS_CACHE_SECONDS:
            stored = {s.key: s.value for s in SiteSetting.query.all()}
            settings_cache.update(at=time.time(), raw=stored, data={key: setting_from_text(kind, stored.get(key), default)
                                                                    for key, kind, default, _, _ in SITE_SETTINGS})
        return settings_cache['data']

    def setting_active(on_key, until_key):
        """Włączone i (jeśli podano datę) jeszcze nie minął ten dzień."""
        settings = site_settings()
        if not settings[on_key]:
            return False
        try:
            return not settings[until_key] or date.today() <= date.fromisoformat(settings[until_key])
        except ValueError:
            return True

    PROMO_VERSION_KEYS = ('promo_title', 'promo_text', 'promo_btn1_url')
    PROMO_DEFAULT_VERSION = '|'.join(str(d) for k, _, d, _, _ in SITE_SETTINGS if k in PROMO_VERSION_KEYS)

    @app.context_processor
    def inject_site_settings():
        settings = site_settings()
        promo_version = None
        if setting_active('promo_on', 'promo_until'):
            # zmiana treści banera = nowa wersja, więc wraca też u tych, którzy schowali poprzedni
            text = '|'.join(str(settings[k]) for k in PROMO_VERSION_KEYS)
            # stary baner chował się kluczem hl-promo-druk3d - przy niezmienionej treści dalej go honorujemy
            promo_version = 'druk3d' if text == PROMO_DEFAULT_VERSION else hashlib.md5(text.encode()).hexdigest()[:10]
        return {'site': settings, 'promo_version': promo_version}

    # ===================== Menu (zakładki) =====================

    def clean_menu_layout(raw):
        """Układ menu z edytora / bazy -> (układ, ukryte klucze); nieznane klucze i powtórki odpadają,
        a pozycje, których nie ma ani w układzie, ani w ukrytych (np. nowa zakładka w kodzie), dochodzą na końcu."""
        used, layout = set(), []

        def item(entry):
            key = entry.get('key') if isinstance(entry, dict) else None
            if key not in MENU_ITEMS or key in used:
                return None
            used.add(key)
            label = ' '.join(str(entry.get('label') or '').split())[:40]
            return {'key': key, 'label': label} if label and label != MENU_ITEMS[key][0] else {'key': key}

        entries = raw.get('layout') if isinstance(raw, dict) else None
        for entry in entries if isinstance(entries, list) else []:
            if isinstance(entry, dict) and 'group' in entry:
                if sum(1 for e in layout if 'group' in e) >= MENU_MAX_GROUPS:
                    continue
                name = ' '.join(str(entry.get('group') or '').split())[:30] or 'Więcej'
                children = [c for c in (item(x) for x in entry.get('items') or [] if isinstance(entry.get('items'), list)) if c]
                layout.append({'group': name, 'items': children})
            else:
                one = item(entry)
                if one:
                    layout.append(one)
        hidden = [k for k in (raw.get('hidden') if isinstance(raw, dict) and isinstance(raw.get('hidden'), list) else [])
                  if k in MENU_ITEMS and k not in used]
        used.update(hidden)
        layout += [{'key': k} for k in MENU_ITEMS if k not in used]
        return layout, hidden

    def menu_layout():
        try:
            raw = json.loads(site_settings_raw('menu_layout') or 'null')
        except ValueError:
            raw = None
        return clean_menu_layout(raw if raw else {'layout': MENU_DEFAULT_LAYOUT})

    def site_settings_raw(key):
        """Surowa wartość z site_setting spoza listy SITE_SETTINGS (np. układ menu) - z tą samą pamięcią podręczną."""
        site_settings()
        return settings_cache.get('raw', {}).get(key)

    @app.context_processor
    def inject_menu():
        """Menu dla menu.html: lista pozycji i grup z gotowymi adresami i podświetleniem bieżącej zakładki."""
        path = request.path

        def entry(e):
            label, endpoint, prefixes, badge = MENU_ITEMS[e['key']]
            active = path == '/' if e['key'] == 'home' else path.startswith(prefixes)
            return {'key': e['key'], 'label': e.get('label') or label, 'url': url_for(endpoint), 'active': active,
                    'badge': badge}

        menu = []
        for e in menu_layout()[0]:
            if 'group' in e:
                items = [entry(i) for i in e['items']]
                menu.append({'group': e['group'], 'items': items, 'active': any(i['active'] for i in items)})
            else:
                menu.append(entry(e))
        return {'nav_menu': menu}

    @app.route('/panel/menu', methods=['GET', 'POST'])
    @login_required
    def menu_editor():
        """Edytor zakładek: kolejność, grupy rozwijane, własne nazwy, ukrywanie."""
        if current_user.is_admin == "0":
            flash('Menu ustawia tylko admin.', 'danger')
            return redirect(url_for('index'))
        if request.method == 'POST':
            row = db.session.get(SiteSetting, 'menu_layout')
            if request.form.get('reset'):
                if row:
                    db.session.delete(row)
                flash('Przywrócono domyślne menu.', 'success')
            else:
                try:
                    raw = json.loads(request.form.get('layout') or 'null')
                except ValueError:
                    raw = None
                if not isinstance(raw, dict):
                    flash('Nie udało się odczytać układu - spróbuj jeszcze raz.', 'danger')
                    return redirect(url_for('menu_editor'))
                layout, hidden = clean_menu_layout(raw)
                if row is None:
                    row = SiteSetting(key='menu_layout')
                    db.session.add(row)
                row.value, row.updated_by = json.dumps({'layout': layout, 'hidden': hidden}, ensure_ascii=False), current_user.id
                flash('Menu zapisane.', 'success')
            db.session.commit()
            settings_cache['data'] = None
            return redirect(url_for('menu_editor'))
        layout, hidden = menu_layout()
        items = {k: {'key': k, 'default': v[0]} for k, v in MENU_ITEMS.items()}
        return render_template('panel_menu.html', layout=layout, hidden=hidden, items=items, max_groups=MENU_MAX_GROUPS)

    @app.route('/panel', methods=['GET', 'POST'])
    @login_required
    def control_panel():
        """Panel sterowania stroną: pasek, baner, sekcje strony głównej, efekty."""
        if current_user.is_admin == "0":
            flash('Panel sterowania jest tylko dla admina.', 'danger')
            return redirect(url_for('index'))
        if request.method == 'POST':
            stored = {s.key: s for s in SiteSetting.query.all()}
            if request.form.get('reset_all'):
                panel_keys = {key for key, *_ in SITE_SETTINGS}
                for row in stored.values():
                    if row.key in panel_keys:        # techniczne flagi (np. carousel_seeded) zostają
                        db.session.delete(row)
                db.session.commit()
                settings_cache['data'] = None
                flash('Przywrócono ustawienia domyślne.', 'success')
                return redirect(url_for('control_panel'))
            for key, kind, default, label, _ in SITE_SETTINGS:
                if kind == 'bool':
                    value = '1' if request.form.get(key) else '0'
                else:
                    value = (request.form.get(key) or '').strip()
                    if kind == 'int' and not value.isdigit():
                        flash(f'„{label}” musi być liczbą - zostawiam poprzednią wartość.', 'warning')
                        continue
                    if kind == 'date' and value:
                        try:
                            date.fromisoformat(value)
                        except ValueError:
                            flash(f'„{label}”: zła data - zostawiam poprzednią wartość.', 'warning')
                            continue
                row = stored.get(key)
                if row is None:
                    if value == setting_to_text(kind, default):
                        continue              # domyślna wartość - nie ma czego zapisywać
                    row = SiteSetting(key=key)
                    db.session.add(row)
                if row.value != value:
                    row.value, row.updated_by = value, current_user.id
            db.session.commit()
            settings_cache['data'] = None
            flash('Zapisane. Zmiany widać od razu (na innych workerach do 10 s).', 'success')
            return redirect(url_for('control_panel'))
        stored = {s.key: s for s in SiteSetting.query.all()}
        authors = {u.id: u.username for u in User.query.filter(
            User.id.in_([s.updated_by for s in stored.values() if s.updated_by])).all()}
        groups = {}
        for key, kind, default, label, group in SITE_SETTINGS:
            row = stored.get(key)
            changed = row is not None and row.value != setting_to_text(kind, default)
            groups.setdefault(group, []).append({
                'key': key, 'kind': kind, 'label': label, 'default': default, 'changed': changed,
                'changed_info': f'zmienione {when_label(row.updated_at)} przez {authors.get(row.updated_by, "?")}'
                                if changed and row.updated_at else ''})
        gallery = [i for i in Images.query.order_by(Images.created_at.desc()).limit(60).all()
                   if not is_video(i.file_path)][:36]
        return render_template('panel.html', groups=groups, settings=site_settings(),
                               carousel=CarouselImage.query.order_by(CarouselImage.position, CarouselImage.id).all(),
                               gallery=gallery,
                               promo_live=setting_active('promo_on', 'promo_until'),
                               badge_live=setting_active('print_badge_on', 'print_badge_until'))

    def panel_admin_json():
        """Dla tras JSON panelu: odpowiedź z błędem, gdy to nie admin."""
        if current_user.is_admin == "0":
            return jsonify({'status': 'error', 'message': 'Tylko dla admina.'}), 403
        return None

    def carousel_add(file_path):
        last = db.session.query(func.max(CarouselImage.position)).scalar()
        item = CarouselImage(file_path=file_path, position=(last if last is not None else -1) + 1,
                             created_by=current_user.id)
        db.session.add(item)
        db.session.commit()
        return item

    @app.route('/panel/karuzela/dodaj', methods=['POST'])
    @login_required
    def carousel_upload():
        """Jedno zdjęcie na zapytanie (nginx przyjmuje maks. 1 MB), strona wysyła pliki po kolei."""
        denied = panel_admin_json()
        if denied:
            return denied
        file = request.files.get('file')
        file_path = save_upload(file, 'karuzela', ALLOWED_IMAGE_EXTENSIONS) if file else None
        if not file_path:
            return jsonify({'status': 'error', 'message': 'Dozwolone: ' + ', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))}), 400
        item = carousel_add(file_path[4:].replace('\\', '/'))   # do bazy bez "app/"
        return jsonify({'status': 'success', 'id': item.id})

    @app.route('/panel/karuzela/z-galerii/<int:image_id>', methods=['POST'])
    @login_required
    def carousel_from_gallery(image_id):
        denied = panel_admin_json()
        if denied:
            return denied
        image = Images.query.get_or_404(image_id)
        if is_video(image.file_path):
            return jsonify({'status': 'error', 'message': 'Filmy nie mogą być w karuzeli.'}), 400
        item = carousel_add(image.file_path)
        return jsonify({'status': 'success', 'id': item.id})

    @app.route('/panel/karuzela/<int:item_id>/usun', methods=['POST'])
    @login_required
    def carousel_delete(item_id):
        denied = panel_admin_json()
        if denied:
            return denied
        item = CarouselImage.query.get_or_404(item_id)
        path = item.file_path.replace('\\', '/')
        db.session.delete(item)
        db.session.commit()
        for prefix in ('k', 'kd'):
            if os.path.exists(thumbnail_path(prefix + str(item_id))):
                os.remove(thumbnail_path(prefix + str(item_id)))
        # plik wgrany w panelu usuwamy z dysku; zdjęcia z galerii i stare hlyw_N zostają
        if path.startswith('static/images/karuzela/') and not CarouselImage.query.filter_by(file_path=item.file_path).first():
            full = os.path.join(app.root_path, path)
            if os.path.exists(full):
                os.remove(full)
        return jsonify({'status': 'success'})

    @app.route('/panel/karuzela/kolejnosc', methods=['POST'])
    @login_required
    def carousel_order():
        denied = panel_admin_json()
        if denied:
            return denied
        ids = (request.get_json(silent=True) or {}).get('ids') or []
        items = {c.id: c for c in CarouselImage.query.all()}
        for position, item_id in enumerate(ids):
            if item_id in items:
                items[item_id].position = position
        db.session.commit()
        return jsonify({'status': 'success'})

    @app.context_processor
    def inject_upgrade_badge():
        """Plakietka NOWE przy 'Ostatnie Ulepszenia' w menu, gdy jest świeży wpis."""
        latest = db.session.query(func.max(Upgrade.date)).scalar()
        return {'has_new_upgrade': bool(latest and latest >= datetime.utcnow() - timedelta(days=UPGRADE_NEW_DAYS)),
                'current_year': datetime.now().year,
                'print_promo': setting_active('print_badge_on', 'print_badge_until'),
                'report_statuses': REPORT_STATUSES}

    @app.template_filter('print_time')
    def print_time_filter(seconds):
        # 5244 -> "1 h 27 min"
        minutes = max(1, round((seconds or 0) / 60))
        return f'{minutes} min' if minutes < 60 else f'{minutes // 60} h {minutes % 60} min'

    @app.template_filter('is_video')
    def is_video(path):
        return (path or '').rsplit('.', 1)[-1].lower() in {'mp4', 'mov', 'webm'}

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('error.html', code=404, message='Tej strony nie ma — zgubiłeś się w Los Santos.'), 404

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        try:
            return render_template('error.html', code=500, message='Coś wybuchło po stronie serwera. Spróbuj za chwilę.'), 500
        except Exception:
            return 'WASTED — błąd serwera (500)', 500

    def carousel_images():
        images = [url_for('carousel_photo', item_id=c.id)
                  for c in CarouselImage.query.order_by(CarouselImage.position, CarouselImage.id).all()]
        if site_settings()['carousel_shuffle']:
            random.shuffle(images)
        return images

    @app.route('/')
    def index():
        images = carousel_images()
        today = datetime.combine(date.today(), datetime.min.time())
        upcoming_events = Calendar.query.filter(Calendar.date >= today).order_by(Calendar.date).limit(3).all()
        if not current_user.is_authenticated:
            return render_template('index.html', images=images, upcoming_events=upcoming_events, today=today)

        # Wyniki gier zapisują się w UTC, więc "dziś" też liczymy od północy UTC
        today_utc = datetime.combine(datetime.utcnow().date(), datetime.min.time())
        games = game_catalog()
        leaders = []
        for game in games:
            ranking_data, _ = game_ranking(game['model'], game['current'])
            leaders.append({'game': game, 'leader': ranking_data[0] if ranking_data else None})
        stats = {
            'users': User.query.count(),
            'games_today': sum(g['model'].query.filter(g['model'].created_at >= today_utc).count() for g in games),
            'photos': Images.query.count(),
            'albums': Albums.query.count(),
        }
        return render_template('index.html', images=images, upcoming_events=upcoming_events, today=today,
                               stats=stats, leaders=leaders,
                               latest_news=News.query.order_by(News.created_at.desc()).limit(3).all(),
                               latest_messages=Message.query.order_by(Message.timestamp.desc()).limit(4).all(),
                               viewers=camera_viewers(),
                               activity=recent_activity(datetime.utcnow() - timedelta(days=3), limit=8))

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        form = LoginForm()
        if form.validate_on_submit():
            login, password = form.username.data.strip(), form.password.data

            def password_ok(u):
                return is_password_hash(u.password) and check_password_hash(u.password, password)

            user = User.query.filter_by(username=login).first()
            if user and not password_ok(user):
                user = None
            if not user and '@' in login:
                # Logowanie e-mailem (zgłoszenie #10). Jeden e-mail może mieć kilka kont - wpuszczamy na to,
                # do którego pasuje hasło; gdy pasuje do kilku, trzeba podać nazwę użytkownika.
                matches = [u for u in User.query.filter(func.lower(func.trim(User.email)) == login.lower()).all()
                           if password_ok(u)]
                if len(matches) > 1:
                    flash('Na ten e-mail jest kilka kont z tym samym hasłem - zaloguj się nazwą użytkownika: '
                          + ', '.join(u.username for u in matches), 'warning')
                    return render_template('login.html', form=form)
                user = matches[0] if matches else None
            if not user:
                flash('Niepoprawna nazwa użytkownika / e-mail lub hasło', 'danger')
            else:
                login_user(user, remember=True)  # ciasteczko "remember" - logowanie trzyma 365 dni, też po zamknięciu przeglądarki
                next_page = request.args.get('next') or request.form.get('next')
                # Tylko ścieżki lokalne (np. /calendar), żeby nie dało się przekierować na obcą domenę
                if next_page and next_page.startswith('/') and not next_page.startswith('//') \
                        and '\\' not in next_page:
                    return redirect(next_page)
                return redirect(url_for('index'))
        return render_template('login.html', form=form)

    @app.route('/forgot_password', methods=['GET', 'POST'])
    def forgot_password():
        form = ForgotPasswordForm()
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data.strip()).first()
            if user and user.email.strip().lower() == form.email.data.strip().lower():
                session['reset_user_id'] = user.id
                session['reset_expires'] = (datetime.now() + timedelta(minutes=10)).timestamp()
                return redirect(url_for('reset_password'))
            flash('Nazwa użytkownika i email do siebie nie pasują.', 'danger')
        return render_template('forgot_password.html', form=form)

    @app.route('/reset_password', methods=['GET', 'POST'])
    def reset_password():
        user_id = session.get('reset_user_id')
        if not user_id or datetime.now().timestamp() > session.get('reset_expires', 0):
            session.pop('reset_user_id', None)
            session.pop('reset_expires', None)
            flash('Najpierw podaj nazwę użytkownika i email.', 'warning')
            return redirect(url_for('forgot_password'))

        form = ResetPasswordForm()
        if form.validate_on_submit():
            user = User.query.get(user_id)
            user.password = hash_password(form.password.data)
            db.session.commit()
            session.pop('reset_user_id', None)
            session.pop('reset_expires', None)
            flash('Hasło zostało zmienione. Możesz się zalogować.', 'success')
            return redirect(url_for('login'))
        return render_template('reset_password.html', form=form)

    @app.route('/logout')
    def logout():
        logout_user()
        return render_template('logout.html')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        form = RegistrationForm()
        if form.validate_on_submit():
            if User.query.filter_by(username=form.username.data).first():
                flash('Użytkownik już istnieje', 'danger')
                return redirect(url_for('register'))

            if form.password.data != form.confirm_password.data:
                flash('Hasła nie są zgodne.', 'danger')
                return redirect(url_for('register'))

            else:
                new_user = User(username=form.username.data, email=form.email.data,
                                password=hash_password(form.password.data),
                                confirmed=True, confirmed_on=datetime.utcnow())
                db.session.add(new_user)
                db.session.commit()
                flash('Zarejestrowano pomyślnie! Możesz się zalogować.', 'success')
                return redirect(url_for('login'))
        return render_template('register.html', form=form)

    @app.route('/albums', methods=['GET'])
    @login_required
    def albums():
        all_album = Albums.query.order_by(Albums.created_at.desc()).all()
        images_no_album=Images.query.filter_by(album_id=0).order_by(Images.created_at.desc()).all()
        return render_template('albums.html', album=all_album, images=images_no_album,
                               likes=image_likes([i.id for i in images_no_album]))

    @app.route('/albums/<int:album_id>')
    @login_required
    def album(album_id):
        album = Albums.query.get_or_404(album_id)
        images = Images.query.filter_by(album_id=album.id).order_by(Images.created_at).all()
        return render_template('album.html', album=album, images=images, likes=image_likes([i.id for i in images]))

    def image_likes(image_ids):
        """{image_id: {'count': n, 'mine': bool, 'who': 'ala, ola'}} dla podanych zdjęć."""
        result = {i: {'count': 0, 'mine': False, 'who': []} for i in image_ids}
        if image_ids:
            rows = db.session.query(ImageLike.image_id, ImageLike.user_id, User.username) \
                .join(User, User.id == ImageLike.user_id).filter(ImageLike.image_id.in_(image_ids)) \
                .order_by(ImageLike.created_at).all()
            for image_id, user_id, username in rows:
                r = result[image_id]
                r['count'] += 1
                r['mine'] = r['mine'] or user_id == current_user.id
                r['who'].append(username)
        for r in result.values():
            r['who'] = ', '.join(r['who'])
        return result

    @app.route('/zdjecie/<int:image_id>/like', methods=['POST'])
    @login_required
    def like_image(image_id):
        """Przełącza ❤ zalogowanego użytkownika pod zdjęciem."""
        Images.query.get_or_404(image_id)
        existing = ImageLike.query.filter_by(image_id=image_id, user_id=current_user.id).first()
        if existing:
            db.session.delete(existing)
        else:
            db.session.add(ImageLike(image_id=image_id, user_id=current_user.id))
        try:
            db.session.commit()
        except IntegrityError:          # podwójne kliknięcie - polubienie już jest
            db.session.rollback()
        return jsonify({'status': 'success', **image_likes([image_id])[image_id]})

    def save_jpeg_thumbnail(source, thumb_path, size=THUMBNAIL_SIZE, quality=78):
        """Zapisuje miniaturę JPEG obrazka (ścieżka albo plik w pamięci); przy błędzie rzuca wyjątek."""
        # zapis przez plik tymczasowy - kilka workerów może generować tę samą miniaturę naraz
        tmp_path = thumb_path + '.' + uuid.uuid4().hex + '.tmp'
        try:
            from PIL import Image, ImageOps
            with Image.open(source) as original:
                picture = ImageOps.exif_transpose(original).convert('RGBA')
            picture.thumbnail((size, size))
            # JPEG nie ma przezroczystości - podkładamy tło
            background = Image.new('RGB', picture.size, (52, 58, 64))
            background.paste(picture, mask=picture.getchannel('A'))
            background.save(tmp_path, 'JPEG', quality=quality, optimize=True)
            os.replace(tmp_path, thumb_path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    @app.route('/miniatura/<int:image_id>')
    @login_required
    def thumbnail(image_id):
        """Miniatura zdjęcia do siatki galerii. Generowana przy pierwszym wyświetleniu i trzymana na dysku,
        więc obejmuje też stare zdjęcia. Gdy się nie uda (np. HEIC, brak Pillow) - przekierowanie na oryginał."""
        image = Images.query.get_or_404(image_id)
        return send_thumbnail(str(image.id), image.file_path)

    @app.route('/miniatura/karuzela/<int:item_id>')
    @login_required
    def carousel_thumbnail(item_id):
        """Miniatura zdjęcia karuzeli do panelu sterowania (pełne zdjęcia przycinały stronę)."""
        item = CarouselImage.query.get_or_404(item_id)
        return send_thumbnail('k' + str(item.id), item.file_path)

    @app.route('/karuzela/<int:item_id>.jpg')
    def carousel_photo(item_id):
        """Zdjęcie karuzeli zmniejszone do CAROUSEL_SIZE (strona główna jest też dla niezalogowanych)."""
        item = CarouselImage.query.get_or_404(item_id)
        return send_thumbnail('kd' + str(item.id), item.file_path, size=CAROUSEL_SIZE, quality=82)

    def thumbnail_path(name):
        return os.path.join(app.static_folder, 'images', 'thumbs', name + '.jpg')

    def send_thumbnail(name, file_path, size=THUMBNAIL_SIZE, quality=78):
        """Miniatura JPEG pliku `file_path` zapisana jako thumbs/<name>.jpg (tworzona przy pierwszym użyciu)."""
        thumb_path = thumbnail_path(name)
        if not os.path.exists(thumb_path):
            source = os.path.join(app.root_path, file_path.replace('\\', '/').lstrip('/'))
            create_directory_if_not_exists(os.path.dirname(thumb_path))
            try:
                save_jpeg_thumbnail(source, thumb_path, size, quality)
            except Exception as e:
                app.logger.warning('Nie udało się utworzyć miniatury %s: %s', name, e)
                return redirect(media_url(file_path))
        return send_file(thumb_path, mimetype='image/jpeg', max_age=30 * 24 * 3600)

    @app.route('/add_album', methods=['GET', 'POST'])
    @login_required
    def add_album():
        form = AlbumForm()
        if form.validate_on_submit():
            albums = Albums(name=form.title.data, description=form.description.data, created_by=current_user.id)
            db.session.add(albums)
            db.session.commit()
            return redirect(url_for('albums'))
        return render_template('add_album.html', form=form)

    @app.route('/add_images', methods=['GET', 'POST'])
    @login_required
    def add_image():
        form = ImageForm()
        if form.validate_on_submit():
            album_id = str(request.args.get('album_id', 0, type=int))

            file_path = save_upload(form.file.data, album_id, ALLOWED_MEDIA_EXTENSIONS)
            if not file_path:
                flash('Niedozwolony typ pliku. Dozwolone: ' + ', '.join(sorted(ALLOWED_MEDIA_EXTENSIONS)), 'danger')
                return render_template('add_images.html', form=form)
            file_path=file_path[4:] #do bazy bez app

            image = Images(file_path=file_path, album_id=album_id, created_by=str(current_user.id))
            db.session.add(image)
            db.session.commit()
            return redirect(url_for('albums'))
        return render_template('add_images.html', form=form)

    @app.route('/news', methods=['GET'])
    @login_required
    def news():
        all_news = News.query.order_by(News.created_at.desc()).all()
        authors = {str(u.id): u for u in User.query.filter(User.id.in_([int(n.created_by) for n in all_news if (n.created_by or '').isdigit()])).all()}
        reactions = {n.id: news_reactions(n.id) for n in all_news}
        return render_template('breaking_news.html', news=all_news, authors=authors, reactions=reactions,
                               emojis=NEWS_REACTIONS)

    def news_reactions(news_id):
        """{emoji: {'count': n, 'mine': bool}} dla wszystkich dozwolonych emoji."""
        rows = db.session.query(NewsReaction.emoji, NewsReaction.user_id).filter_by(news_id=news_id).all()
        return {e: {'count': sum(1 for emoji, _ in rows if emoji == e),
                    'mine': any(emoji == e and uid == current_user.id for emoji, uid in rows)}
                for e in NEWS_REACTIONS}

    @app.route('/news/<int:news_id>/react', methods=['POST'])
    @login_required
    def react_news(news_id):
        News.query.get_or_404(news_id)
        emoji = (request.get_json(silent=True) or {}).get('emoji')
        if emoji not in NEWS_REACTIONS:
            return jsonify({'status': 'error'}), 400
        existing = NewsReaction.query.filter_by(news_id=news_id, user_id=current_user.id, emoji=emoji).first()
        if existing:
            db.session.delete(existing)
        else:
            db.session.add(NewsReaction(news_id=news_id, user_id=current_user.id, emoji=emoji))
        db.session.commit()
        return jsonify({'status': 'success', 'reactions': news_reactions(news_id)})

    @app.route('/add_new', methods=['GET', 'POST'])
    @login_required
    def add_new():
        form = NewsForm()
        if form.validate_on_submit():
            title = form.title.data
            description = form.description.data
            file_path = save_upload(form.file.data, 'newsy', ALLOWED_IMAGE_EXTENSIONS)
            if not file_path:
                flash('Niedozwolony typ pliku. Dozwolone: ' + ', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS)), 'danger')
                return render_template('add_new.html', form=form)
            file_path = file_path[4:]  # do bazy bez app

            news = News(title=title, description=description, file_path=file_path, created_by=current_user.id)
            db.session.add(news)
            db.session.commit()
            return redirect(url_for('news'))
        return render_template('add_new.html', form=form)

    @app.route('/calendar', methods=['GET'])
    @login_required
    def calendar():
        # Ustawienie domyślnego miesiąca i roku
        now = datetime.now()
        month = request.args.get('month', now.month, type=int)
        year = request.args.get('year', now.year, type=int)

        # Oblicz poprzedni miesiąc i rok
        if month == 1:
            previous_month = 12
            previous_year = year - 1
        else:
            previous_month = month - 1
            previous_year = year

        # Oblicz następny miesiąc i rok
        if month == 12:
            next_month = 1
            next_year = year + 1
        else:
            next_month = month + 1
            next_year = year

        # Generowanie kalendarza
        cal = callendar.monthcalendar(year, month)
        event_days = get_event_days(year, month)

        return render_template('calendar.html',
                               calendar=cal,
                               year=year,
                               month=month,
                               month_name=MONTH_NAMES_PL[month],
                               previous_month=previous_month,
                               previous_year=previous_year,
                               next_month=next_month,
                               next_year=next_year,
                               event_days=event_days,
                               today_day=now.day if (month, year) == (now.month, now.year) else None)

    @app.route('/add_entry', methods=['GET', 'POST'])
    @login_required
    def add_entry():
        form = CalendarForm()
        if form.validate_on_submit():
            title = form.title.data
            description = form.description.data
            date = form.date.data
            user_id = current_user.id
            new_entry = Calendar(title=title, description=description, date=date, created_by=user_id)
            db.session.add(new_entry)
            db.session.commit()
            return redirect(url_for('calendar'))
        return render_template('add_entry.html', form=form)

    @app.route('/event', methods=['GET', 'POST'])
    @login_required
    def event():
        day = request.args.get('day', type=int)
        month = request.args.get('month', type=int)
        year = request.args.get('year', type=int)

        query_date = date(year, month, day)
        event = Calendar.query.filter(Calendar.date.like(str(query_date) + '%')).first_or_404()
        owner = User.query.get(event.created_by)

        fifa_mode = "fifa" in event.title.lower()
        tm = trackmania_data(event) if "trackmania" in event.title.lower() else None
        czy_zapisany = False
        participants_names = []

        if fifa_mode:
            fifa_participants = FifaParticipant.query.filter_by(event_id=event.id).all()
            for fp in fifa_participants:
                user = User.query.get(fp.user_id)
                participants_names.append({
                    "username": user.username,
                    "role": fp.role,
                    "club": fp.club
                })
                if fp.user_id == current_user.id:
                    czy_zapisany = True

            # Turniej
            tournament = Tournament.query.filter_by(event_id=event.id).first()
            groups = []
            knockout = []   # [(nazwa rundy, [mecze])] w kolejności rozgrywania
            knockout_warning = None
            podium = []

            if tournament:
                if not tournament.finished:
                    # np. wyniki grup wpisane przed tą wersją strony - drabinka ułoży się przy wejściu
                    knockout_warning = sync_knockout(tournament)
                    db.session.commit()
                groups = TournamentGroup.query.filter_by(tournament_id=tournament.id).order_by(TournamentGroup.name).all()
                for group in groups:
                    # osobny atrybut - przypisanie do relacji group.matches mogłoby zmienić dane w bazie
                    group.match_list = sorted(group.matches, key=lambda m: m.id)
                    group.table = calculate_group_table(group)

                for round_name in KNOCKOUT_ROUNDS:
                    matches = TournamentMatch.query.filter_by(tournament_id=tournament.id, round=round_name) \
                        .order_by(TournamentMatch.id).all()
                    if matches:
                        knockout.append((round_name, matches))

                if tournament.is_league:
                    league_matches = [m for g in groups for m in g.matches]
                    done = tournament.finished or (league_matches and all(m.home_score is not None for m in league_matches))
                    top = [row['player'].id for row in groups[0].table[:3]] if groups and done else []
                    first_id, second_id, third_id = (top + [None, None, None])[:3]
                else:
                    final = TournamentMatch.query.filter_by(tournament_id=tournament.id, round="finał").first()
                    third = TournamentMatch.query.filter_by(tournament_id=tournament.id, round="o 3. miejsce").first()
                    first_id, second_id = match_winner_loser(final)
                    third_id = match_winner_loser(third)[0]
                # (miejsce, gracz) - numer miejsca stały, żeby np. sam mecz o 3. miejsce nie dawał złota
                podium = [(place, User.query.get(uid))
                          for place, uid in enumerate((first_id, second_id, third_id), 1) if uid]

        else:
            add_user = request.args.get('add_user', type=int)
            if add_user:
                if not Participant.query.filter_by(event_id=event.id, user_id=add_user).first():
                    new_participant = Participant(user_id=add_user, event_id=event.id)
                    db.session.add(new_participant)
                    db.session.commit()
                    flash('Zapisałeś się na wydarzenie!', 'success')

            participants = Participant.query.filter_by(event_id=event.id).all()
            for p in participants:
                user = User.query.get(p.user_id)
                participants_names.append({"username": user.username})
                if p.user_id == str(current_user.id):   # Participant.user_id to tekst
                    czy_zapisany = True

        return render_template(
            'event.html',
            day=day, month=month, year=year,
            event=event,
            owner=owner,
            participants_names=participants_names,
            fifa_mode=fifa_mode,
            czy_zapisany=czy_zapisany,
            current_user=current_user,
            tournament=tournament if fifa_mode else None,
            groups=groups if fifa_mode else [],
            knockout=knockout if fifa_mode else [],
            podium=podium if fifa_mode else [],
            knockout_warning=knockout_warning if fifa_mode else None,
            tm=tm,
        )

    @app.route('/camera')
    @login_required
    def camera():
        # źródła obrazu: (klucz, etykieta, adres, typ); typ 'iframe' = osadzony player (kamera),
        # 'video' = natywny strumień H.264 przez odtwarzacz go2rtc (MSE, fallback MJPEG) - adres websocketu /api/ws.
        # Przełącznik pojawia się dopiero z PRINTER_STREAM_URL w .env (np. https://drukarka.hlyw.pl/api/ws?src=drukarka).
        sources = [('kamera', '📷 Kamera HLYW', CAMERA_STREAM_URL, 'iframe')]
        if os.getenv('PRINTER_STREAM_URL'):
            sources.append(('drukarka', '🖨️ Kamera Drukarka', os.getenv('PRINTER_STREAM_URL'), 'video'))
        # panel statusu drukarki (temperatury, filamenty, co się drukuje) - JSON z serwisu na Raspberry; pokazuje się tylko gdy ustawione
        return render_template('camera.html', sources=sources,
                               printer_status_url=os.getenv('PRINTER_STATUS_URL'),
                               printer_light=bool(os.getenv('PRINTER_STATUS_URL') and os.getenv('PRINTER_CONTROL_TOKEN')))

    @app.route('/api/drukarka/swiatlo', methods=['POST'])
    @login_required
    def drukarka_swiatlo():
        # sterowanie światłem komory - token dokładamy serwerowo (nigdy nie trafia do przeglądarki)
        status_url = os.getenv('PRINTER_STATUS_URL')
        token = os.getenv('PRINTER_CONTROL_TOKEN')
        if not status_url or not token:
            return jsonify(ok=False, error='not_configured'), 503
        mode = (request.get_json(silent=True) or {}).get('mode', 'toggle')
        if mode not in ('on', 'off', 'toggle'):
            return jsonify(ok=False, error='bad_mode'), 400
        import urllib.request as _ur, urllib.parse as _up, urllib.error as _ue
        light_url = status_url.replace('/status', '/light') + '?' + _up.urlencode({'mode': mode})
        try:
            # User-Agent jawnie - domyślny "Python-urllib" bywa blokowany przez Cloudflare jako bot (403)
            req = _ur.Request(light_url, data=b'', method='POST',
                              headers={'X-Control-Token': token, 'User-Agent': 'hlyw-camera/1.0'})
            with _ur.urlopen(req, timeout=8) as resp:
                return app.response_class(resp.read(), content_type='application/json')
        except _ue.HTTPError as e:
            return jsonify(ok=False, error='pi_http_%d' % e.code), 502
        except Exception as e:
            return jsonify(ok=False, error='pi_unreachable', detail=str(e)[:160]), 502

    _bambu_tasks = {'at': 0.0, 'data': None}   # cache listy zadań z chmury Bambu (60 s)

    def _bambu_tasks_data():
        # lista ostatnich zadań z chmury Bambu; None gdy brak tokenu lub błąd (UI chowa się wtedy łagodnie)
        import time as _t, urllib.request as _ur
        token = os.getenv('BAMBU_TOKEN')
        if not token:
            return None
        now = _t.time()
        if now - _bambu_tasks['at'] > 60 or not _bambu_tasks['data']:
            try:
                req = _ur.Request('https://api.bambulab.com/v1/user-service/my/tasks?limit=20',
                                  headers={'Authorization': 'Bearer ' + token, 'User-Agent': 'hlyw-camera/1.0'})
                _bambu_tasks['data'] = json.loads(_ur.urlopen(req, timeout=10).read())
                _bambu_tasks['at'] = now
            except Exception:
                return None
        return _bambu_tasks['data']

    @app.route('/api/drukarka/okladka')
    @login_required
    def drukarka_okladka():
        # miniatura (okładka) wydruku z chmury Bambu - po id albo nazwie; token zostaje po stronie serwera
        import urllib.request as _ur
        data = _bambu_tasks_data()
        if data is None:
            abort(404)
        hits = data.get('hits', []) or []
        tid = (request.args.get('id') or '').strip()
        name = (request.args.get('name') or '').strip().lower()
        cover = None
        field = 'snapShot' if request.args.get('rodzaj') == 'zdjecie' else 'cover'   # zdjęcie z kamery po wydruku / render z slicera
        for h in hits:
            if tid and str(h.get('id')) == tid:
                cover = h.get(field); break
            if not tid and name and (h.get('title') or '').strip().lower() == name:
                cover = h.get('cover'); break
        if not cover and not tid and not name and hits:
            cover = hits[0].get('cover')          # fallback: najnowsze
        if not cover:
            abort(404)
        try:
            img = _ur.urlopen(_ur.Request(cover, headers={'User-Agent': 'hlyw-camera/1.0'}), timeout=10).read()
        except Exception:
            abort(502)
        resp = app.response_class(img, content_type='image/jpeg' if img[:3] == b'\xff\xd8\xff' else 'image/png')
        resp.headers['Cache-Control'] = 'public, max-age=300'
        return resp

    @app.route('/api/drukarka/wydruki')
    @login_required
    def drukarka_wydruki():
        # ostatnie wydruki z chmury Bambu (lista do sekcji na /camera)
        data = _bambu_tasks_data()
        if data is None:
            return jsonify(wydruki=[])
        out = []
        for h in (data.get('hits', []) or [])[:8]:
            # wynik po zdjęciu: drukarka robi je tylko po udanym wydruku (status 2); 4 = jeszcze się drukuje
            result = 'drukuje' if h.get('status') == 4 else 'udany' if h.get('snapShot') else 'nieudany'
            out.append({
                'id': h.get('id'),
                'title': bambu_task_title(h),
                'raw_title': h.get('title') or '',          # tak jak podaje drukarka (panel statusu tłumaczy po nim)
                'status': h.get('status'),
                'result': result,
                'photo': bool(h.get('snapShot')),
                'start': h.get('startTime'),
                'cost': h.get('costTime'),
                'weight': h.get('weight'),
            })
        return jsonify(wydruki=out)

    @app.route('/user_settings', methods=['GET', 'POST'])
    @login_required
    def user_settings():
        form = UserSettingsForm()
        password_form = ChangePasswordForm(prefix='pw')

        if password_form.submit.data and password_form.validate_on_submit():
            if not check_password_hash(current_user.password, password_form.current_password.data):
                flash('Obecne hasło jest niepoprawne.', 'danger')
            else:
                current_user.password = hash_password(password_form.password.data)
                db.session.commit()
                flash('Hasło zostało zmienione.', 'success')
                return redirect(url_for('user_settings'))

        elif form.submit.data and form.validate_on_submit():
            new_username = form.username.data.strip()
            if new_username != current_user.username and User.query.filter_by(username=new_username).first():
                flash('Ta nazwa użytkownika jest już zajęta.', 'danger')
                return redirect(url_for('user_settings'))
            current_user.username = new_username

            # Zaktualizuj zdjęcie, jeśli użytkownik je dodał
            if form.photo.data:
                file_path = save_upload(form.photo.data, 'profile_pics', ALLOWED_IMAGE_EXTENSIONS)
                if not file_path:
                    flash('Niedozwolony typ pliku. Dozwolone: ' + ', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS)), 'danger')
                    return redirect(url_for('user_settings'))
                current_user.photo = os.path.basename(file_path)

            # Zapisz zmiany w bazie danych
            db.session.commit()
            flash('Zapisano zmiany.', 'success')
            return redirect(url_for('user_settings'))  # Przekieruj po zapisaniu zmian

        # Ustaw pola formularza na obecne dane użytkownika
        form.username.data = current_user.username

        return render_template('user_settings.html', form=form, password_form=password_form)

    @app.route('/send_message', methods=['POST'])
    @login_required
    def send_message():
        data = request.get_json()
        message_content = data.get('message')
        user_id = current_user.id  # Przypisanie ID zalogowanego użytkownika

        if message_content:
            # Zapisz wiadomość w bazie danych
            new_message = Message(content=message_content, user_id=user_id)
            db.session.add(new_message)
            db.session.commit()

            return jsonify({"status": "success", "message": message_content})
        return jsonify({"status": "error"}), 400

    @app.route('/get_messages')
    @login_required
    def get_messages():
        # Pobierz wszystkie wiadomości z bazy danych
        messages = Message.query.order_by(Message.timestamp.desc()).limit(30).all()
        messages_data = []

        for msg in messages:
            user = msg.user  # Dostęp do użytkownika powiązanego z wiadomością
            place = standings().get(user.id, {}).get('place')
            messages_data.append({
                "content": msg.content,
                "timestamp": msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                "time": when_label(msg.timestamp),
                "username": user.username,  # Dodajemy nazwę użytkownika
                "crown": place if place and place <= 3 else None,  # korona TOP 1-3 Hall of Fame
                "photo": user.photo  # Dodajemy zdjęcie użytkownika
            })

        return jsonify({"messages": messages_data})

    @app.route('/ostatnie-ulepszenia', methods=['GET', 'POST'])
    def ostatnie_ulepszenia():
        form = UpgradeForm()
        if form.validate_on_submit():
            if not current_user.is_authenticated or current_user.is_admin == "0":
                flash('Brak uprawnień do dodawania ulepszeń', 'danger')
            else:
                db.session.add(Upgrade(title=form.title.data.strip(), description=form.description.data.strip()))
                db.session.commit()
                flash('Dodano ulepszenie.', 'success')
            return redirect(url_for('ostatnie_ulepszenia'))

        # Pobierz ostatnie ulepszenia z bazy danych i pogrupuj po miesiącach
        upgrades = Upgrade.query.order_by(Upgrade.date.desc()).all()
        months = []
        for upgrade in upgrades:
            label = f'{MONTH_NAMES_PL[upgrade.date.month]} {upgrade.date.year}'
            if not months or months[-1][0] != label:
                months.append((label, []))
            months[-1][1].append(upgrade)
        new_since = datetime.utcnow() - timedelta(days=UPGRADE_NEW_DAYS)
        return render_template('ostatnie_ulepszenia.html', months=months, form=form, new_since=new_since)

    @app.route('/confirm/<token>')
    def confirm_email(token):
        try:
            email = confirm_token(token)
        except:
            flash('Link potwierdzający jest nieważny lub wygasł.', 'danger')
            return redirect(url_for('login'))

        # Znajdź użytkownika po emailu
        user = User.query.filter_by(email=email).first_or_404()

        if user.confirmed:
            flash('Konto już zostało potwierdzone.', 'success')
        else:
            user.confirmed = True
            user.confirmed_on = datetime.utcnow()
            db.session.add(user)
            db.session.commit()
            flash('Twoje konto zostało potwierdzone!', 'success')

        return redirect(url_for('login'))

    @app.route('/resend_confirmation')
    def resend_confirmation():
        email = request.args.get('email')
        user = User.query.filter_by(email=email).first_or_404()

        if user.confirmed:
            flash('Twoje konto już zostało potwierdzone.', 'success')
        else:
            send_confirmation_email(user.email)
            flash('Mail potwierdzający został wysłany ponownie.', 'success')

        return redirect(url_for('login'))

    @app.route('/report', methods=['GET', 'POST'])
    @login_required
    def report():
        form = ReportForm()
        if form.validate_on_submit():
            new_report = Report(
                title=form.title.data,
                description=form.description.data,
                user_id=current_user.id  # Powiązanie zgłoszenia z użytkownikiem
            )
            db.session.add(new_report)
            db.session.commit()
            flash('Zgłoszenie zostało dodane!', 'success')
            return redirect(url_for('view_report', report_id=new_report.id))
        return render_template('report.html', form=form)

    @app.route('/report/<int:report_id>', methods=['GET', 'POST'])
    def view_report(report_id):
        report = Report.query.get_or_404(report_id)
        form = CommentForm()
        if form.validate_on_submit():
            new_comment = Comment(
                content=form.content.data,
                user_id=current_user.id,
                report_id=report.id
            )
            db.session.add(new_comment)
            db.session.commit()
            flash('Komentarz dodany!', 'success')
            return redirect(url_for('view_report', report_id=report.id))
        comments = Comment.query.filter_by(report_id=report.id).all()
        return render_template('view_report.html', report=report, form=form, comments=comments)

    @app.route('/reports')
    @login_required
    def view_report_list():
        reports = Report.query.order_by(Report.created_at.desc()).all()
        comment_counts = dict(db.session.query(Comment.report_id, func.count(Comment.id))
                              .group_by(Comment.report_id).all())
        return render_template('view_report_list.html', reports=reports, comment_counts=comment_counts)

    @app.route('/report/<int:report_id>/status', methods=['POST'])
    @login_required
    def set_report_status(report_id):
        report = Report.query.get_or_404(report_id)
        status = request.form.get('status')
        if current_user.is_admin == "0":
            flash('Tylko admin może zmieniać status zgłoszenia.', 'danger')
        elif status not in REPORT_STATUSES:
            flash('Nieznany status.', 'danger')
        else:
            report.status = status
            db.session.commit()
            flash(f'Status zmieniony na: {REPORT_STATUSES[status][0]}.', 'success')
        return redirect(url_for('view_report', report_id=report.id))

    @app.route('/add_comment/<int:report_id>', methods=['POST'])
    @login_required
    def add_comment(report_id):
        report = Report.query.get_or_404(report_id)
        comment_content = request.form['content']
        new_comment = Comment(content=comment_content, user_id=current_user.id, report_id=report.id)
        db.session.add(new_comment)
        db.session.commit()
        flash('Komentarz został dodany!', 'success')
        return redirect(url_for('view_report', report_id=report.id))

    # ===================== Propozycje do druku 3D =====================

    def print_file_path(name):
        # poza static: plik da się pobrać tylko przez trasę dla zalogowanych, zawsze jako załącznik
        return os.path.join(app.instance_path, 'druk3d', name)

    def clean_print_link(link):
        """Adres http(s) z formularza; None, gdy to nie jest poprawny link (np. javascript:)."""
        link = link.strip()
        if '://' not in link and ':' not in link.split('/')[0]:
            link = 'https://' + link
        parsed = urlparse(link)
        if parsed.scheme not in ('http', 'https') or '.' not in parsed.netloc or re.search(r'\s', link):
            return None
        return link

    def extract_3mf_thumbnail(stored):
        """Wyciąga obrazek zapisany w pliku 3MF i zwraca nazwę miniatury; None, gdy go nie ma lub plik jest uszkodzony."""
        def rank(name):
            # plate_1.png = widok modelu z Bambu Studio; pick_* to mapy kolorów, a nie obrazki do pokazania
            lower = name.lower().replace('\\', '/')
            base = lower.rsplit('/', 1)[-1]
            if not base.endswith(('.png', '.jpg', '.jpeg')) or not lower.startswith(('metadata/', 'thumbnails/', '/metadata/')):
                return None
            if base.startswith('pick') or 'no_light' in base or base.endswith('_small.png'):
                return None
            return 0 if base == 'plate_1.png' else 1 if base.startswith('plate_') else 2 if 'thumbnail' in lower else 3
        thumb = stored + '.jpg'
        try:
            with zipfile.ZipFile(print_file_path(stored)) as archive:
                candidates = [(rank(i.filename), i) for i in archive.infolist()
                              if rank(i.filename) is not None and i.file_size <= PRINT_THUMB_MAX_BYTES]
                if not candidates:
                    return None
                with archive.open(min(candidates, key=lambda c: c[0])[1]) as image:
                    save_jpeg_thumbnail(io.BytesIO(image.read()), print_file_path(thumb))
            return thumb
        except Exception as e:
            app.logger.warning('Nie udało się wyciągnąć miniatury z 3MF %s: %s', stored, e)
            return None

    PRINT_SNAPSHOT_SUFFIX = '.view.jpg'   # miniatura zrobiona z podglądu 3D (a nie wyciągnięta z 3MF)

    def save_print_snapshot(stored, data_url):
        """Zapisuje zdjęcie podglądu 3D (data URL z formularza) jako miniaturę propozycji; zwraca jej nazwę albo None.
        Nazwa jest za każdym razem nowa, więc po edycji przeglądarka nie pokaże starej miniatury z pamięci."""
        match = re.fullmatch(r'data:image/(?:jpeg|png);base64,([A-Za-z0-9+/=]+)', (data_url or '').strip())
        if not stored or not match or len(match.group(1)) > 4 * 1024 * 1024:
            return None
        thumb = stored + '.' + uuid.uuid4().hex[:8] + PRINT_SNAPSHOT_SUFFIX
        try:
            save_jpeg_thumbnail(io.BytesIO(base64.b64decode(match.group(1))), print_file_path(thumb), size=640, quality=82)
        except Exception as e:
            app.logger.warning('Nie udało się zapisać miniatury z podglądu dla %s: %s', stored, e)
            return None
        return thumb

    def remove_print_file(name):
        if name and os.path.exists(print_file_path(name)):
            os.remove(print_file_path(name))

    app.jinja_env.globals['our_printer'] = OUR_PRINTER   # znaczek „✓ H2C” przy zgodnych profilach MakerWorld

    @app.template_global('print_thumb_url')
    def print_thumb_url(entry):
        """Adres miniatury z pliku; ?v= zmienia się razem z miniaturą (np. po edycji), więc nie wisi stara z pamięci."""
        if not entry.thumb_path:
            return None
        return url_for('print_thumbnail', request_id=entry.id, v=hashlib.md5(entry.thumb_path.encode()).hexdigest()[:8])

    def model_images_supported(link):
        host = (urlparse(link or '').hostname or '').lower()
        return any(host == d or host.endswith('.' + d) for d in MODEL_IMAGES_SITES)

    def fetch_model_images(link):
        """Same zdjęcia ze strony z modelem - stronę otwiera headless Chromium na Pi.
        Zwraca (zdjęcia, błąd, tytuł strony, profile druku z MakerWorld, informacje o modelu z MakerWorld)."""
        import urllib.request as _ur, urllib.parse as _up, urllib.error as _ue
        base = os.getenv('MODEL_IMAGES_URL') or (os.getenv('PRINTER_STATUS_URL') or '').replace('/status', '/zdjecia')
        token = os.getenv('PRINTER_CONTROL_TOKEN')
        if not base or not token:
            return None, 'not_configured', None, [], None
        if not model_images_supported(link):
            return None, 'site_not_allowed', None, [], None
        try:
            # User-Agent jawnie - domyślny "Python-urllib" Cloudflare blokuje jako bota (403)
            req = _ur.Request(base + '?' + _up.urlencode({'url': link}),
                              headers={'X-Control-Token': token, 'User-Agent': 'hlyw-druk3d/1.0'})
            with _ur.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read())
        except _ue.HTTPError as e:
            try:
                return None, json.loads(e.read()).get('error') or 'pi_http_%d' % e.code, None, [], None
            except Exception:
                return None, 'pi_http_%d' % e.code, None, [], None
        except Exception as e:
            app.logger.warning('Pobieranie zdjęć modelu %s nie powiodło się: %s', link, e)
            return None, 'pi_unreachable', None, [], None
        images = [u for u in data.get('images') or [] if isinstance(u, str) and clean_print_link(u)]
        title = ' '.join(str(data.get('title') or '').split())[:150] or None
        return images, (None if images else data.get('error') or 'no_images'), title, clean_profiles(data.get('profiles')), \
            clean_model_info(data.get('info'))

    def clean_model_info(raw):
        """Opis modelu od autora, tagi i licencja z MakerWorld; None, gdy nic z tego nie ma."""
        if not isinstance(raw, dict):
            return None
        description = raw.get('description') if isinstance(raw.get('description'), str) else ''
        description = '\n'.join(' '.join(line.split()) for line in description.split('\n') if line.strip())[:2000]
        tags = raw.get('tags') if isinstance(raw.get('tags'), list) else []
        tags = [' '.join(t.split())[:30] for t in tags if isinstance(t, str) and t.strip()][:15]
        info = {'description': description, 'tags': tags, 'license': ' '.join(str(raw.get('license') or '').split())[:20]}
        return info if any(info.values()) else None

    def to_number(value, kind=float):
        try:
            return kind(float(value or 0))
        except (TypeError, ValueError):
            return kind(0)

    def describe_print_settings(settings, nozzle):
        """Ustawienia profilu MakerWorld po ludzku: [„warstwa 0,2 mm”, „3 ścianki”, „wypełnienie 20%”, „dysza 0,4 mm”]."""
        def number(v):
            return ('%g' % to_number(v)).replace('.', ',')
        parts = []
        if to_number(settings.get('layerHeight')):
            parts.append(f"warstwa {number(settings['layerHeight'])} mm")
        if to_number(settings.get('wallLoops'), int):
            walls = to_number(settings['wallLoops'], int)
            parts.append(plural(walls, 'ścianka', 'ścianki', 'ścianek'))
        if settings.get('sparseInfillDensity'):
            parts.append('wypełnienie ' + settings['sparseInfillDensity'].replace(' ', ''))
        if str(settings.get('enableSupport', '')).lower() in ('1', 'true'):
            parts.append('z podporami')
        if nozzle:
            parts.append(f'dysza {number(nozzle)} mm')
        return parts

    def clean_profiles(raw):
        """Profile druku (MakerWorld) z Pi albo z formularza - tylko znane pola o rozsądnych wartościach."""
        profiles = []
        for p in raw if isinstance(raw, list) else []:
            if not isinstance(p, dict):
                continue
            try:
                seconds, grams = int(p.get('seconds') or 0), float(p.get('grams') or 0)
            except (TypeError, ValueError):
                continue
            if not 0 < seconds < 30 * 24 * 3600 or not 0 <= grams < 100000:
                continue
            filaments = []
            for f in p.get('filaments') or []:
                if isinstance(f, dict):
                    color = str(f.get('color') or '')
                    try:
                        used = round(float(f.get('grams') or 0), 1)
                    except (TypeError, ValueError):
                        used = 0
                    filaments.append({'type': str(f.get('type') or '')[:20],
                                      'color': color if re.fullmatch(r'#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?', color) else '',
                                      'grams': used})
            settings = {str(k)[:30]: str(v)[:30] for k, v in list((p.get('settings') or {}).items())[:12]} \
                if isinstance(p.get('settings'), dict) else {}
            nozzle = to_number(p.get('nozzle')) or None
            printer = str(p.get('printer') or '')[:30]
            printers = [str(x)[:30] for x in p.get('printers') or [] if isinstance(x, str)][:25]
            plates = []
            for pl in p.get('plates') or []:
                if isinstance(pl, dict):
                    image = clean_print_link(str(pl.get('image') or '')) if pl.get('image') else None
                    plates.append({'seconds': max(0, to_number(pl.get('seconds'), int)),
                                   'grams': round(max(0.0, to_number(pl.get('grams'))), 1), 'image': (image or '')[:500]})
            ratings = max(0, to_number(p.get('ratings'), int))
            profiles.append({'title': ' '.join(str(p.get('title') or '').split())[:150], 'seconds': seconds,
                             'grams': round(grams, 1), 'filaments': filaments[:16], 'ams': bool(p.get('ams')),
                             'printer': printer, 'settings': settings, 'nozzle': nozzle,
                             'settings_text': describe_print_settings(settings, nozzle),
                             'fits_ours': OUR_PRINTER in [printer] + printers,
                             'plates': plates[:20], 'prints': max(0, to_number(p.get('prints'), int)),
                             'ratings': ratings, 'rating': min(5.0, max(0.0, round(to_number(p.get('rating')), 1))) if ratings else 0,
                             'summary': '\n'.join(' '.join(l.split()) for l in str(p.get('summary') or '').split('\n') if l.strip())[:400]})
        return profiles[:20]

    PRINT_TRANSFORM_OPS = ('rx', 'ry', 'rz', 'mx', 'my', 'mz')

    def clean_print_transform(raw):
        """Ustawienie modelu z podglądu 3D: lista operacji (obrót o 90° / odbicie w osi) + skala w %; None = bez zmian."""
        if not isinstance(raw, dict):
            return None
        ops = [op for op in raw.get('ops') or [] if op in PRINT_TRANSFORM_OPS][:60]
        try:
            scale = min(500, max(10, int(round(float(raw.get('scale') or 100)))))
        except (TypeError, ValueError):
            scale = 100
        return {'ops': ops, 'scale': scale} if ops or scale != 100 else None

    def describe_print_transform(t):
        """„obrót X 90° → Z 180°, odbicie X, skala 120%” - to samo co describeTransform w model_viewer.js."""
        if not t:
            return ''
        steps = []
        for op in t['ops']:
            if steps and steps[-1][0] == op:
                steps[-1][1] += 1
            else:
                steps.append([op, 1])
        rotations = [f'{op[1].upper()} {(n % 4) * 90}°' for op, n in steps if op[0] == 'r' and n % 4]
        mirrors = [op[1].upper() for op, n in steps if op[0] == 'm' and n % 2]
        parts = []
        if rotations:
            parts.append('obrót ' + ' → '.join(rotations))
        if mirrors:
            parts.append('odbicie ' + ', '.join(mirrors))
        if t['scale'] != 100:
            parts.append(f"skala {t['scale']}%")
        return ', '.join(parts)

    def print_transform(entry):
        try:
            return clean_print_transform(json.loads(entry.print_transform)) if entry.print_transform else None
        except ValueError:
            return None

    def print_profile(entry):
        try:
            return json.loads(entry.print_profile) if entry.print_profile else None
        except ValueError:
            return None

    def print_model_info(entry):
        try:
            return clean_model_info(json.loads(entry.model_info)) if entry.model_info else None
        except ValueError:
            return None

    def print_gallery(entry):
        try:
            return json.loads(entry.gallery) if entry.gallery else None
        except ValueError:
            return None

    @app.route('/druk3d/zdjecia')
    @login_required
    def print_images_preview():
        # podgląd w formularzu: wklejony link -> zdjęcia do wyboru głównego
        link = clean_print_link(request.args.get('url', '')) if request.args.get('url', '').strip() else None
        if not link:
            return jsonify(ok=False, error='bad_url'), 400
        images, error, title, profiles, info = fetch_model_images(link)
        return jsonify(ok=bool(images), images=images or [], error=error, title=title, profiles=profiles, info=info)

    @app.route('/druk3d/<int:request_id>/zdjecia')
    @login_required
    def print_images(request_id):
        # galeria wpisu: pobierana raz i zapamiętywana w bazie; admin może odświeżyć (?odswiez=1)
        entry = PrintRequest.query.get_or_404(request_id)
        images = print_gallery(entry)
        if images is None or (request.args.get('odswiez') == '1' and current_user.is_admin != "0"):
            if not entry.link:
                return jsonify(ok=False, images=[], error='no_link')
            images, error, _, profiles, info = fetch_model_images(entry.link)
            if not images:
                return jsonify(ok=False, images=[], error=error)
            entry.gallery = json.dumps(images)
            if info:
                entry.model_info = json.dumps(info)
            if profiles and not entry.print_profile:
                entry.print_profile = json.dumps(profiles[0])   # domyślny profil autora
            elif profiles:
                # ten sam profil co wybrany, ale z nowszymi danymi (np. ustawienia, płyty, oceny)
                chosen = print_profile(entry) or {}
                fresh = next((p for p in profiles if p['title'] == chosen.get('title')), None)
                if fresh:
                    entry.print_profile = json.dumps(fresh)
            if not entry.image_url and not entry.thumb_path:
                entry.image_url = images[0][:1000]     # miniatura na liście propozycji
            db.session.commit()
        return jsonify(ok=True, images=images)

    @app.route('/druk3d/<int:request_id>/miniatura')
    @login_required
    def print_thumbnail(request_id):
        entry = PrintRequest.query.get_or_404(request_id)
        if not entry.thumb_path or not os.path.exists(print_file_path(entry.thumb_path)):
            abort(404)
        return send_file(print_file_path(entry.thumb_path), mimetype='image/jpeg', max_age=24 * 3600)

    @app.route('/druk3d/<int:request_id>/miniatura', methods=['POST'])
    @login_required
    def print_thumbnail_save(request_id):
        """Propozycja z plikiem bez miniatury (np. STL sprzed tej zmiany): zdjęcie podglądu ze strony szczegółów."""
        entry = PrintRequest.query.get_or_404(request_id)
        if entry.thumb_path or not entry.file_path:
            return jsonify(ok=False, error='not_needed')
        thumb = save_print_snapshot(entry.file_path, (request.get_json(silent=True) or {}).get('image'))
        if not thumb:
            return jsonify(ok=False, error='bad_image'), 400
        entry.thumb_path = thumb
        db.session.commit()
        return jsonify(ok=True)

    @app.route('/druk3d')
    @login_required
    def print_list():
        status = request.args.get('status')
        mine = request.args.get('moje') == '1'
        query = PrintRequest.query
        if status in PRINT_STATUSES:
            query = query.filter_by(status=status)
        else:
            status = None
        if mine:
            query = query.filter_by(user_id=current_user.id)
        counts = dict(db.session.query(PrintRequest.status, func.count()).group_by(PrintRequest.status).all())
        return render_template('druk3d.html', requests=query.order_by(PrintRequest.created_at.desc()).all(), counts=counts,
                               profile_of=print_profile,
                               active_status=status, mine=mine, print_statuses=PRINT_STATUSES, qualities=PRINT_QUALITIES,
                               colors=PRINT_COLORS)

    @app.route('/druk3d/nowa', methods=['GET', 'POST'])
    @login_required
    def print_new():
        limit_bytes = PRINT_MAX_MB * 1024 * 1024
        if request.method == 'POST' and (request.content_length or 0) > limit_bytes + 1024 * 1024:
            flash(f'Plik jest za duży - limit to {PRINT_MAX_MB} MB.', 'danger')
            return redirect(url_for('print_new'))
        form = PrintRequestForm()
        if request.method == 'GET':
            # dane z zakładki „Wyślij do druku” - tylko wypełniają formularz, zapisuje dopiero użytkownik
            form.title.data = request.args.get('title', '')[:150]
            form.link.data = request.args.get('link', '')[:500]
            form.image_url.data = request.args.get('image', '')[:1000]
        # plik albo link (przełącznik w formularzu); pola drugiej opcji przeglądarka i tak nie wysyła
        source = request.form.get('source')
        if source not in ('plik', 'link'):
            source = 'link'
        if form.validate_on_submit():
            if source == 'plik':
                form.link.data = form.image_url.data = None
            else:
                form.file.data = None
            image_url = clean_print_link(form.image_url.data) if (form.image_url.data or '').strip() else None
            chosen = apply_filament(request.form.get('filament'))
            upload = form.file.data if form.file.data and form.file.data.filename else None
            ext = upload.filename.rsplit('.', 1)[-1].lower() if upload and '.' in upload.filename else ''
            link = clean_print_link(form.link.data) if (form.link.data or '').strip() else None
            if not upload and not (form.link.data or '').strip():
                flash('Wybierz plik z modelem.' if source == 'plik' else 'Wklej link do strony z modelem.', 'danger')
            elif upload and ext not in PRINT_EXTENSIONS:
                flash('Niedozwolony typ pliku. Dozwolone: ' + ', '.join(sorted(PRINT_EXTENSIONS)), 'danger')
            elif (form.link.data or '').strip() and not link:
                flash('To nie wygląda na poprawny link - wklej pełny adres strony z modelem.', 'danger')
            elif (form.image_url.data or '').strip() and not image_url:
                flash('To nie wygląda na poprawny link do zdjęcia.', 'danger')
            elif not chosen:
                flash('Wybierz filament z listy.', 'danger')
            else:
                stored = None
                if upload:
                    stored = uuid.uuid4().hex + '.' + ext
                    create_directory_if_not_exists(os.path.dirname(print_file_path(stored)))
                    upload.save(print_file_path(stored))
                thumb = extract_3mf_thumbnail(stored) if ext == '3mf' else None
                if upload and not thumb:
                    # STL / OBJ (i 3MF bez obrazka): zdjęcie podglądu 3D zrobione w przeglądarce przy wysyłaniu
                    thumb = save_print_snapshot(stored, request.form.get('snapshot'))
                # galeria pobrana już w formularzu - strona propozycji nie musi jej ściągać drugi raz
                gallery = None
                if link:
                    try:
                        sent = json.loads(request.form.get('gallery') or 'null')
                    except ValueError:
                        sent = None
                    if isinstance(sent, list):
                        gallery = [u[:1000] for u in sent[:40] if isinstance(u, str) and clean_print_link(u)] or None
                if gallery and not image_url:
                    image_url = gallery[0]
                # ustawienie modelu z podglądu 3D (tylko dla wgranego pliku)
                transform = None
                if upload:
                    try:
                        transform = clean_print_transform(json.loads(request.form.get('transform') or 'null'))
                    except ValueError:
                        transform = None
                # wybrany w formularzu profil druku z MakerWorld (czas i filament)
                profile = None
                if link:
                    try:
                        profile = (clean_profiles([json.loads(request.form.get('profile') or 'null')]) or [None])[0]
                    except ValueError:
                        profile = None
                material, color, color_hex = chosen
                model_info = None
                if link:
                    try:
                        model_info = clean_model_info(json.loads(request.form.get('model_info') or 'null'))
                    except ValueError:
                        model_info = None
                entry = PrintRequest(thumb_path=thumb, gallery=json.dumps(gallery) if gallery else None, color_hex=color_hex,
                                     model_info=json.dumps(model_info) if model_info else None,
                                     print_profile=json.dumps(profile) if profile else None,
                                     print_transform=json.dumps(transform) if transform else None, title=form.title.data.strip(), description=(form.description.data or '').strip() or None,
                                     file_path=stored, link=link, image_url=image_url, quality=form.quality.data, material=material,
                                     file_name=upload.filename.replace('\\', '/').rsplit('/', 1)[-1][:200] if upload else None,
                                     color=color, quantity=form.quantity.data, user_id=current_user.id)
                db.session.add(entry)
                db.session.commit()
                flash('Propozycja wysłana! Status zobaczysz na tej stronie.', 'success')
                return redirect(url_for('print_detail', request_id=entry.id))
        return render_template('druk3d_nowa.html', form=form, max_mb=PRINT_MAX_MB, source=source, entry=None,
                               filaments=filament_groups(), filament_selected=request.form.get('filament') or FILAMENT_ANY)

    def clean_hex(value):
        """'#f72323', 'F72323FF' -> '#F72323'; None, gdy to nie kolor."""
        value = (value or '').strip().lstrip('#')
        return '#' + value[:6].upper() if re.fullmatch(r'[0-9a-fA-F]{6}([0-9a-fA-F]{2})?', value) else None

    def color_name_from_hex(hex_):
        """Polska nazwa koloru z odcienia (do filamentów z AMS - admin może ją potem zmienić)."""
        import colorsys
        r, g, b = (int(hex_[i:i + 2], 16) / 255 for i in (1, 3, 5))
        h, l, sat = colorsys.rgb_to_hls(r, g, b)
        h *= 360
        if sat < 0.15 or l < 0.08 or l > 0.94:
            return 'Czarny' if l < 0.2 else 'Biały' if l > 0.85 else 'Szary'
        if 15 <= h < 45 and l < 0.4:
            return 'Brązowy'
        for limit, name in ((15, 'Czerwony'), (45, 'Pomarańczowy'), (70, 'Żółty'), (170, 'Zielony'), (200, 'Turkusowy'),
                            (255, 'Niebieski'), (290, 'Fioletowy'), (345, 'Różowy'), (361, 'Czerwony')):
            if h < limit:
                return name

    def fetch_ams():
        """Szpule w drukarce z serwisu statusu na Pi: lista {slot, material, hex, remain}; None, gdy się nie da."""
        import urllib.request as _ur
        url = os.getenv('PRINTER_STATUS_URL')
        if not url:
            return None
        try:
            # User-Agent jawnie - domyślny "Python-urllib" Cloudflare blokuje jako bota (403)
            with _ur.urlopen(_ur.Request(url, headers={'User-Agent': 'hlyw-druk3d/1.0'}), timeout=6) as resp:
                data = json.loads(resp.read())
        except Exception as e:
            app.logger.warning('Nie udało się odczytać AMS z %s: %s', url, e)
            return None
        trays = []
        for f in data.get('filaments') or []:
            hex_ = clean_hex(f.get('color'))
            material = ' '.join(str(f.get('type') or '').split())[:30]
            if not hex_ or not material:
                continue
            try:
                number = int(f.get('id'))
            except (TypeError, ValueError):
                number = -1
            if f.get('external') or number >= 254:
                slot = 'szpula zewnętrzna'
            elif number >= 4:
                slot = f'AMS {number // 4 + 1}, slot {number % 4 + 1}'
            else:
                slot = f'AMS, slot {number + 1}'
            remain = f.get('remain')
            trays.append({'slot': slot, 'material': material, 'hex': hex_,
                          'remain': remain if isinstance(remain, int) and 0 <= remain <= 100 else None})
        return trays

    def match_filament(filaments, material, hex_):
        """Filament z listy pasujący do szpuli: ten sam materiał i kolor (dokładnie albo ta sama nazwa koloru)."""
        same = [f for f in filaments if f.material.lower() == material.lower()]
        return next((f for f in same if f.hex.upper() == hex_), None) or \
            next((f for f in same if f.name == color_name_from_hex(hex_)), None)

    def filament_groups(include_hidden=False):
        query = Filament.query.order_by(Filament.material, Filament.name)
        items = query.all() if include_hidden else query.filter(Filament.status != 'ukryty').all()
        return {status: [f for f in items if f.status == status] for status in FILAMENT_STATUSES
                if include_hidden or status != 'ukryty'}

    def filament_choice(entry):
        """Która opcja formularza odpowiada propozycji (przy edycji)."""
        if entry.material == 'Obojętnie' and entry.color == 'Obojętnie':
            return FILAMENT_ANY
        f = Filament.query.filter_by(material=entry.material, name=entry.color).first()
        if f and f.status != 'ukryty':
            return str(f.id)
        return FILAMENT_KEEP

    def apply_filament(value, entry=None):
        """Wybór z formularza -> (materiał, kolor, hex); None, gdy wybór jest nieprawidłowy."""
        if value == FILAMENT_ANY:
            return 'Obojętnie', 'Obojętnie', None
        if value == FILAMENT_OTHER:
            return 'Inny', 'Inny (opisz w uwagach)', None
        if value == FILAMENT_KEEP and entry is not None:
            return entry.material, entry.color, entry.color_hex
        f = db.session.get(Filament, int(value)) if (value or '').isdigit() else None
        if not f or f.status == 'ukryty':
            return None
        return f.material, f.name, f.hex

    @app.template_global('print_color_hex')
    def print_color_hex(entry):
        return entry.color_hex or PRINT_COLORS.get(entry.color, 'transparent')

    @app.route('/druk3d/filamenty', methods=['GET', 'POST'])
    @login_required
    def print_filaments():
        """Panel admina: lista filamentów do wyboru w propozycjach + podgląd i import z AMS."""
        if current_user.is_admin == "0":
            flash('Filamentami zarządza tylko admin.', 'danger')
            return redirect(url_for('print_list'))
        if request.method == 'POST':
            action = request.form.get('action')
            if action == 'ams':
                trays = fetch_ams()
                if trays is None:
                    flash('Nie udało się odczytać AMS - drukarka albo malinka nie odpowiada.', 'danger')
                else:
                    filaments, added, updated = Filament.query.all(), 0, 0
                    for t in trays:
                        f = match_filament(filaments, t['material'], t['hex'])
                        if f is None:
                            f = Filament(material=t['material'], name=color_name_from_hex(t['hex']), hex=t['hex'])
                            db.session.add(f)
                            filaments.append(f)
                            added += 1
                        elif f.status != 'dostepny' or f.hex != t['hex']:
                            f.status, f.hex = 'dostepny', t['hex']
                            updated += 1
                    db.session.commit()
                    flash(f'AMS: {plural(len(trays), "szpula", "szpule", "szpul")}, nowych na liście: {added}, '
                          f'oznaczonych jako dostępne: {updated}.', 'success')
            elif action in ('add', 'save'):
                material = ' '.join((request.form.get('material') or '').split())[:30]
                name = ' '.join((request.form.get('name') or '').split())[:40]
                hex_ = clean_hex(request.form.get('hex'))
                status = request.form.get('status')
                if not material or not name or not hex_ or status not in FILAMENT_STATUSES:
                    flash('Uzupełnij materiał, nazwę koloru i kolor.', 'danger')
                elif action == 'add':
                    db.session.add(Filament(material=material, name=name, hex=hex_, status=status))
                    db.session.commit()
                    flash(f'Dodano: {material} · {name}.', 'success')
                else:
                    f = Filament.query.get_or_404(request.form.get('id', type=int))
                    f.material, f.name, f.hex, f.status = material, name, hex_, status
                    db.session.commit()
                    flash(f'Zapisano: {material} · {name}.', 'success')
            elif action == 'delete':
                f = Filament.query.get_or_404(request.form.get('id', type=int))
                db.session.delete(f)
                db.session.commit()
                flash(f'Usunięto: {f.material} · {f.name}. Propozycje z tym filamentem go zachowują.', 'success')
            return redirect(url_for('print_filaments'))
        trays = fetch_ams()
        filaments = Filament.query.all()
        for t in trays or []:
            t['filament'] = match_filament(filaments, t['material'], t['hex'])
            t['suggested_name'] = color_name_from_hex(t['hex'])
        return render_template('druk3d_filamenty.html', groups=filament_groups(include_hidden=True), trays=trays,
                               statuses=FILAMENT_STATUSES, materials=FILAMENT_MATERIALS)

    def can_edit_print(entry):
        return current_user.is_admin != "0" or (entry.user_id == current_user.id and entry.status == 'nowa')

    @app.route('/druk3d/<int:request_id>/edytuj', methods=['GET', 'POST'])
    @login_required
    def print_edit(request_id):
        """Edycja propozycji: autor, dopóki ma status „Nowa”, admin zawsze. Rodzaj (plik / link) zostaje ten sam."""
        entry = PrintRequest.query.get_or_404(request_id)
        if not can_edit_print(entry):
            flash('Możesz edytować tylko własną propozycję, dopóki ma status „Nowa”.', 'danger')
            return redirect(url_for('print_detail', request_id=entry.id))
        if request.method == 'POST' and (request.content_length or 0) > PRINT_MAX_MB * 1024 * 1024 + 1024 * 1024:
            flash(f'Plik jest za duży - limit to {PRINT_MAX_MB} MB.', 'danger')
            return redirect(url_for('print_edit', request_id=entry.id))
        source = 'plik' if entry.file_path else 'link'
        # przy wysyłaniu tylko to, co przyszło z formularza - brakujące pole nie może wrócić ze starej wersji
        form = PrintRequestForm(obj=entry) if request.method == 'GET' else PrintRequestForm()
        if form.validate_on_submit():
            upload = form.file.data if source == 'plik' and form.file.data and form.file.data.filename else None
            ext = upload.filename.rsplit('.', 1)[-1].lower() if upload and '.' in upload.filename else ''
            link_text = (form.link.data or '').strip() if source == 'link' else ''
            image_text = (form.image_url.data or '').strip() if source == 'link' else ''
            link = clean_print_link(link_text) if link_text else None
            image_url = clean_print_link(image_text) if image_text else None
            chosen = apply_filament(request.form.get('filament'), entry)
            if source == 'link' and not link:
                flash('Wklej poprawny link do strony z modelem.', 'danger')
            elif upload and ext not in PRINT_EXTENSIONS:
                flash('Niedozwolony typ pliku. Dozwolone: ' + ', '.join(sorted(PRINT_EXTENSIONS)), 'danger')
            elif image_text and not image_url:
                flash('To nie wygląda na poprawny link do zdjęcia.', 'danger')
            elif not chosen:
                flash('Wybierz filament z listy.', 'danger')
            else:
                if source == 'plik':
                    if upload:
                        # nowy plik zastępuje stary razem z miniaturą
                        stored = uuid.uuid4().hex + '.' + ext
                        upload.save(print_file_path(stored))
                        remove_print_file(entry.file_path)
                        remove_print_file(entry.thumb_path)
                        entry.file_path, entry.thumb_path = stored, None
                        entry.file_name = upload.filename.replace('\\', '/').rsplit('/', 1)[-1][:200]
                        if ext == '3mf':
                            entry.thumb_path = extract_3mf_thumbnail(stored)
                    try:
                        transform = clean_print_transform(json.loads(request.form.get('transform') or 'null'))
                    except ValueError:
                        transform = None
                    entry.print_transform = json.dumps(transform) if transform else None
                    # miniatura z podglądu odświeża się (np. po zmianie koloru czy ustawienia); obrazka z 3MF nie ruszamy
                    if not entry.thumb_path or entry.thumb_path.endswith(PRINT_SNAPSHOT_SUFFIX):
                        thumb = save_print_snapshot(entry.file_path, request.form.get('snapshot'))
                        if thumb:
                            remove_print_file(entry.thumb_path)
                            entry.thumb_path = thumb
                else:
                    try:
                        sent = json.loads(request.form.get('gallery') or 'null')
                    except ValueError:
                        sent = None
                    gallery = [u[:1000] for u in sent[:40] if isinstance(u, str) and clean_print_link(u)] \
                        if isinstance(sent, list) else None
                    try:
                        profile = (clean_profiles([json.loads(request.form.get('profile') or 'null')]) or [None])[0]
                    except ValueError:
                        profile = None
                    try:
                        model_info = clean_model_info(json.loads(request.form.get('model_info') or 'null'))
                    except ValueError:
                        model_info = None
                    if link != entry.link or model_info:
                        entry.model_info = json.dumps(model_info) if model_info else None
                    if link != entry.link:
                        # inny model: stare zdjęcia i profil nie pasują; bez galerii dociągnie ją strona propozycji
                        entry.link = link
                        entry.gallery = json.dumps(gallery) if gallery else None
                        entry.print_profile = json.dumps(profile) if profile else None
                        entry.image_url = image_url or (gallery[0] if gallery else None)
                    else:
                        if gallery:
                            entry.gallery = json.dumps(gallery)
                        if profile:
                            entry.print_profile = json.dumps(profile)
                        entry.image_url = image_url or entry.image_url
                entry.title = form.title.data.strip()
                entry.description = (form.description.data or '').strip() or None
                entry.quality, entry.quantity = form.quality.data, form.quantity.data
                entry.material, entry.color, entry.color_hex = chosen
                db.session.commit()
                flash('Zmiany zapisane.', 'success')
                return redirect(url_for('print_detail', request_id=entry.id))
        return render_template('druk3d_nowa.html', form=form, max_mb=PRINT_MAX_MB, source=source,
                               filaments=filament_groups(), filament_selected=request.form.get('filament') or filament_choice(entry),
                               entry=entry, gallery=print_gallery(entry), transform=print_transform(entry),
                               file_ext=(entry.file_name or '').rsplit('.', 1)[-1].lower())

    @app.route('/druk3d/<int:request_id>')
    @login_required
    def print_detail(request_id):
        entry = PrintRequest.query.get_or_404(request_id)
        can_delete = can_edit = can_edit_print(entry)
        file_size = None
        if entry.file_path and os.path.exists(print_file_path(entry.file_path)):
            file_size = os.path.getsize(print_file_path(entry.file_path))
        return render_template('druk3d_szczegoly.html', entry=entry, can_delete=can_delete, can_edit=can_edit, file_size=file_size, print_statuses=PRINT_STATUSES,
                               gallery=print_gallery(entry), profile=print_profile(entry), model_info=print_model_info(entry),
                               photo_kinds=PRINT_PHOTO_KINDS, camera_ready=bool(printer_frame_url()),
                               cloud_ready=bool(os.getenv('BAMBU_TOKEN')),
                               transform=print_transform(entry), transform_text=describe_print_transform(print_transform(entry)),
                               gallery_possible=bool(entry.link and model_images_supported(entry.link)),
                               qualities=PRINT_QUALITIES, colors=PRINT_COLORS, delete_form=PrintDeleteForm(),
                               status_form=PrintStatusForm(status=entry.status, admin_note=entry.admin_note))

    @app.route('/druk3d/<int:request_id>/plik')
    @login_required
    def print_download(request_id):
        entry = PrintRequest.query.get_or_404(request_id)
        if not entry.file_path or not os.path.exists(print_file_path(entry.file_path)):
            abort(404)
        return send_file(print_file_path(entry.file_path), as_attachment=True, download_name=entry.file_name,
                         mimetype='application/octet-stream')

    def printer_frame_url():
        """Adres pojedynczej klatki z kamery drukarki (go2rtc na malince) - z PRINTER_STREAM_URL (.../api/ws?src=...)."""
        stream = os.getenv('PRINTER_STREAM_URL') or ''
        return stream.replace('/api/ws', '/api/frame.jpeg') if '/api/ws' in stream else None

    def download_image(url, timeout=20):
        import urllib.request as _ur
        with _ur.urlopen(_ur.Request(url, headers={'User-Agent': 'hlyw-druk3d/1.0'}), timeout=timeout) as resp:
            data = resp.read(PRINT_PHOTO_MAX_BYTES + 1)
        if len(data) > PRINT_PHOTO_MAX_BYTES:
            raise ValueError('za duży obrazek')
        return data

    def save_print_photo(entry, data, kind, source, caption=None):
        """Zapisuje zdjęcie (bajty) jako JPEG w static/images/druk3d i dodaje wpis; przy złym obrazku rzuca wyjątek."""
        folder = os.path.join(app.static_folder, 'images', 'druk3d')
        create_directory_if_not_exists(folder)
        name = uuid.uuid4().hex + '.jpg'
        save_jpeg_thumbnail(io.BytesIO(data), os.path.join(folder, name), size=PRINT_PHOTO_SIZE, quality=85)
        photo = PrintPhoto(request_id=entry.id, file_path='static/images/druk3d/' + name, kind=kind, source=source,
                           caption=' '.join((caption or '').split())[:200] or None, created_by=current_user.id)
        db.session.add(photo)
        return photo

    def remove_print_photo_file(photo):
        path = os.path.join(app.root_path, photo.file_path.replace('\\', '/'))
        if os.path.exists(path):
            os.remove(path)

    @app.template_global('print_photo_url')
    def print_photo_url(entry):
        """Najnowsze zdjęcie gotowego wydruku (na listę propozycji zamiast renderu); None, gdy nie ma."""
        photo = next((ph for ph in reversed(entry.photos) if ph.kind == 'wydruk'), None)
        return media_url(photo.file_path) if photo else None

    def bambu_task_title(task):
        return task.get('designTitleTranslated') or task.get('designTitle') or task.get('instanceTitleTranslated') \
            or task.get('title') or 'Wydruk'

    def cloud_tasks_for(entry):
        """Zakończone wydruki z chmury Bambu ze zdjęciem z kamery (snapShot), od najnowszego; pasujące do propozycji
        (numer modelu z linku MakerWorld = designId albo nazwa pliku = tytuł zadania) mają 'match'. None = chmura nie odpowiada."""
        data = _bambu_tasks_data()
        if data is None:
            return None
        model = re.search(r'makerworld\.com/(?:[a-z]{2}(?:-[a-z]{2})?/)?models/(\d+)', entry.link or '')
        model_id = int(model.group(1)) if model else None
        file_name = (entry.file_name or '').strip().lower()
        stem = file_name.rsplit('.', 1)[0]
        tasks = []
        for h in data.get('hits') or []:
            if h.get('status') != 2 or not h.get('snapShot'):        # 2 = wydruk zakończony (3 = przerwany, 4 = w trakcie)
                continue
            title = (h.get('title') or '').strip().lower()
            match = bool(model_id and h.get('designId') == model_id) or \
                bool(file_name and (title == file_name or (stem and title.rsplit('.', 1)[0] == stem)))
            tasks.append({'id': h.get('id'), 'title': bambu_task_title(h), 'end': h.get('endTime'), 'match': match,
                          'weight': h.get('weight'), 'minutes': round((h.get('costTime') or 0) / 60)})
        return tasks

    def cloud_task(task_id):
        data = _bambu_tasks_data()
        return next((h for h in (data or {}).get('hits', []) or [] if str(h.get('id')) == str(task_id)), None)

    def finish_photo(entry, choice):
        """Zdjęcie wybrane przy statusie „Wydrukowana”: 'kamera' = kamera drukarki teraz, 'task:<id>' = zdjęcie,
        które drukarka zrobiła po skończeniu tego wydruku (chmura Bambu), puste = bez zdjęcia. Zwraca (opis źródła, błąd)."""
        if choice == 'kamera':
            error = camera_photo(entry)
            return ('zdjęcie z kamery drukarki', None) if not error else (None, error)
        if choice.startswith('task:'):
            task = cloud_task(choice[5:])
            if not task or not task.get('snapShot'):
                return None, 'nie znalazłem tego wydruku w chmurze Bambu'
            try:
                save_print_photo(entry, download_image(task['snapShot']), 'wydruk', 'chmura', bambu_task_title(task))
            except Exception as e:
                app.logger.warning('Zdjęcie z chmury Bambu dla propozycji %s: %s', entry.id, e)
                return None, 'chmura Bambu nie oddała zdjęcia'
            return 'zdjęcie z chmury Bambu (wydruk „' + bambu_task_title(task) + '”)', None
        return None, None

    def camera_photo(entry, caption=None):
        """Zdjęcie z kamery drukarki dla propozycji; zwraca komunikat błędu albo None, gdy się udało."""
        url = printer_frame_url()
        if not url:
            return 'kamera drukarki nie jest skonfigurowana (PRINTER_STREAM_URL)'
        try:
            save_print_photo(entry, download_image(url), 'wydruk', 'kamera', caption)
        except Exception as e:
            app.logger.warning('Zdjęcie z kamery drukarki dla propozycji %s nie wyszło: %s', entry.id, e)
            return 'kamera drukarki nie odpowiada'
        return None

    @app.route('/druk3d/<int:request_id>/zdjecia/dodaj', methods=['POST'])
    @login_required
    def print_photo_add(request_id):
        """Nowe zdjęcie propozycji: admin z kamery / chmury Bambu / pliku, autor z pliku (co zrobił z modelem)."""
        entry = PrintRequest.query.get_or_404(request_id)
        is_admin = current_user.is_admin != "0"
        source = request.form.get('source')
        caption = request.form.get('caption')
        back = redirect(url_for('print_detail', request_id=entry.id) + '#zdjecia')
        if not is_admin and entry.user_id != current_user.id:
            flash('Zdjęcia dodaje autor propozycji albo admin.', 'danger')
            return back
        if source in ('kamera', 'chmura') and not is_admin:
            flash('Zdjęcie z drukarki dodaje admin.', 'danger')
            return back
        kind = request.form.get('kind') if is_admin and request.form.get('kind') in PRINT_PHOTO_KINDS else \
            ('wydruk' if is_admin else 'uzytkownik')
        if source == 'kamera':
            error = camera_photo(entry, caption)
            if error:
                flash('Nie udało się zrobić zdjęcia: ' + error + '.', 'danger')
                return back
        elif source == 'chmura':
            task = cloud_task((request.form.get('task_id') or '').strip())
            url = task and (task.get('snapShot') or task.get('cover'))
            if not url:
                flash('Nie znalazłem tego wydruku w chmurze Bambu.', 'danger')
                return back
            try:
                save_print_photo(entry, download_image(url), kind, 'chmura', caption or bambu_task_title(task))
            except Exception as e:
                app.logger.warning('Okładka z chmury Bambu dla propozycji %s: %s', entry.id, e)
                flash('Nie udało się pobrać obrazka z chmury Bambu.', 'danger')
                return back
        else:
            file = request.files.get('file')
            ext = file.filename.rsplit('.', 1)[-1].lower() if file and '.' in (file.filename or '') else ''
            if ext not in ALLOWED_IMAGE_EXTENSIONS:
                flash('Wybierz zdjęcie (' + ', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS)) + ').', 'danger')
                return back
            data = file.read(PRINT_PHOTO_MAX_BYTES + 1)
            if len(data) > PRINT_PHOTO_MAX_BYTES:
                flash('Zdjęcie jest za duże.', 'danger')
                return back
            try:
                save_print_photo(entry, data, kind, 'plik', caption)
            except Exception as e:
                app.logger.warning('Zdjęcie z pliku dla propozycji %s: %s', entry.id, e)
                flash('Nie udało się odczytać tego zdjęcia (HEIC z iPhone\'a wyślij jako JPG).', 'danger')
                return back
        db.session.commit()
        flash('Zdjęcie dodane.', 'success')
        return back

    @app.route('/druk3d/zdjecie/<int:photo_id>/usun', methods=['POST'])
    @login_required
    def print_photo_delete(photo_id):
        photo = PrintPhoto.query.get_or_404(photo_id)
        request_id = photo.request_id
        if current_user.is_admin == "0" and photo.created_by != current_user.id:
            flash('Usunąć zdjęcie może ten, kto je dodał, albo admin.', 'danger')
        else:
            remove_print_photo_file(photo)
            db.session.delete(photo)
            db.session.commit()
            flash('Zdjęcie usunięte.', 'success')
        return redirect(url_for('print_detail', request_id=request_id) + '#zdjecia')

    @app.route('/druk3d/chmura')
    @login_required
    def print_cloud_tasks():
        """Ostatnie wydruki z chmury Bambu do wyboru okładki (tylko admin)."""
        if current_user.is_admin == "0":
            abort(403)
        entry = PrintRequest.query.get_or_404(request.args.get('id', type=int))
        tasks = cloud_tasks_for(entry)
        if tasks is None:
            return jsonify(ok=False, error='token' if os.getenv('BAMBU_TOKEN') else 'not_configured', tasks=[])
        tasks.sort(key=lambda t: not t['match'])                  # pasujące do propozycji na początek
        return jsonify(ok=True, tasks=tasks[:16])

    @app.route('/druk3d/<int:request_id>/status', methods=['POST'])
    @login_required
    def print_set_status(request_id):
        entry = PrintRequest.query.get_or_404(request_id)
        form = PrintStatusForm()
        if current_user.is_admin == "0":
            flash('Tylko admin może zmieniać status propozycji.', 'danger')
        elif not form.validate_on_submit():
            flash('Nie udało się zapisać - odśwież stronę i spróbuj ponownie.', 'danger')
        else:
            if form.status.data != entry.status:
                entry.status = form.status.data
                entry.status_at = datetime.utcnow()
                entry.status_by = current_user.id
            entry.admin_note = (form.admin_note.data or '').strip() or None
            photo_source, photo_error = finish_photo(entry, request.form.get('finish_photo') or '') \
                if entry.status == 'wydrukowana' else (None, None)
            db.session.commit()
            flash(f'Zapisano. Status: {PRINT_STATUSES[entry.status][0]}.'
                  + (f' Dodano {photo_source}.' if photo_source else ''), 'success')
            if photo_error:
                flash('Zdjęcia nie dodałem: ' + photo_error + '. Możesz spróbować jeszcze raz niżej, w „Zdjęcia”.', 'warning')
        return redirect(url_for('print_detail', request_id=entry.id))

    @app.route('/druk3d/<int:request_id>/usun', methods=['POST'])
    @login_required
    def print_delete(request_id):
        entry = PrintRequest.query.get_or_404(request_id)
        if not PrintDeleteForm().validate_on_submit():
            flash('Nie udało się usunąć - odśwież stronę i spróbuj ponownie.', 'danger')
        elif current_user.is_admin == "0" and not (entry.user_id == current_user.id and entry.status == 'nowa'):
            flash('Możesz usunąć tylko własną propozycję, dopóki ma status „Nowa”.', 'danger')
        else:
            for name in (entry.file_path, entry.thumb_path):
                remove_print_file(name)
            for photo in list(entry.photos):
                remove_print_photo_file(photo)
                db.session.delete(photo)
            db.session.delete(entry)
            db.session.commit()
            flash('Propozycja usunięta.', 'success')
            return redirect(url_for('print_list'))
        return redirect(url_for('print_detail', request_id=entry.id))

    @app.route('/users')
    @login_required
    def users():
        sum_expression = (
                func.count(func.distinct(Message.id)) +
                func.count(func.distinct(Report.id)) +
                func.count(func.distinct(Images.id)) +
                func.count(func.distinct(Albums.id)) +
                func.count(func.distinct(Calendar.id)) +
                func.count(func.distinct(Comment.id)) +
                func.count(func.distinct(News.id))
        ).label('total_sum')  # Nadajemy nazwę sumie

        users_stats = db.session.query(
            User.id, User.username, User.photo,
            func.count(func.distinct(Message.id)).label('message_count'),
            func.count(func.distinct(Report.id)).label('report_count'),
            func.count(func.distinct(Images.id)).label('photo_count'),
            func.count(func.distinct(Albums.id)).label('album_count'),
            func.count(func.distinct(Calendar.id)).label('calendar_count'),
            func.count(func.distinct(Comment.id)).label('comment_count'),
            func.count(func.distinct(News.id)).label('news_count'),
            sum_expression  # Dodajemy sumę do wyników zapytania
        ).outerjoin(Message, Message.user_id == User.id) \
            .outerjoin(Report, Report.user_id == User.id) \
            .outerjoin(Images, Images.created_by == User.id) \
            .outerjoin(Albums, Albums.created_by == User.id) \
            .outerjoin(Calendar, Calendar.created_by == User.id) \
            .outerjoin(Comment, Comment.user_id == User.id) \
            .outerjoin(News, News.created_by == User.id) \
            .group_by(User.id) \
            .order_by(sum_expression.desc()).all()  # Sortowanie po sumie, malejąco



        return render_template('uzytkownicy.html', users_stats=users_stats)

    @app.route('/game_run/<game>', methods=['POST'])
    @login_required
    def game_run_start(game):
        """Gra woła to przy starcie partii i dostaje bilet, który odda razem z wynikiem."""
        if game not in GAME_SCORE_LIMITS:
            abort(404)
        now = datetime.utcnow()
        recent = GameRun.query.filter(GameRun.user_id == current_user.id,
                                      GameRun.started_at >= now - timedelta(minutes=1)).count()
        if recent >= GAME_RUN_STARTS_PER_MINUTE:
            return jsonify({'ok': False, 'error': 'Za dużo gier naraz - zwolnij trochę.'}), 429
        GameRun.query.filter(GameRun.started_at < now - GAME_RUN_MAX_AGE).delete()
        run = GameRun(id=uuid.uuid4().hex, user_id=current_user.id, game=game, started_at=now)
        db.session.add(run)
        db.session.commit()
        return jsonify({'ok': True, 'run': run.id})

    def check_game_run(game, score, data):
        """Sprawdza bilet z zapisu wyniku i od razu go zużywa. Zwraca opis błędu albo None."""
        run = GameRun.query.get(str(data.get('run') or ''))
        if not run or run.user_id != current_user.id or run.game != game:
            return 'Brak biletu gry - odśwież stronę i zagraj jeszcze raz.'
        if run.used:
            return 'Ten wynik został już zapisany.'
        run.used = True
        db.session.commit()
        elapsed = (datetime.utcnow() - run.started_at).total_seconds()
        base, per_second = GAME_SCORE_LIMITS[game]
        if elapsed > GAME_RUN_MAX_AGE.total_seconds() or score > base + per_second * elapsed:
            app.logger.warning('Odrzucony wynik %s: user=%s score=%s czas=%.0fs', game, current_user.id, score, elapsed)
            return 'Ten wynik wygląda na niemożliwy - nie został zapisany.'
        standings_cache['data'] = None   # wynik zaraz się zapisze - kasa i korony do przeliczenia
        return None

    @app.route('/snake', methods=['GET', 'POST'])
    @login_required
    def snake():
        best = db.session.query(func.max(Snake.points)).filter(Snake.created_by == str(current_user.id), Snake.created_at >= CURRENT_EDITION_START).scalar() or 0
        return render_template('snake.html', best=best)

    @app.route('/snake/save_score', methods=['POST'])
    @login_required
    def save_score():
        data = request.get_json(silent=True) or {}
        try:
            score = max(0, int(data.get('score', 0)))
        except (TypeError, ValueError):
            return jsonify({'ok': False}), 400

        error = check_game_run('snake', score, data)
        if error:
            return jsonify({'ok': False, 'error': error}), 400

        new_game = Snake(points=score, created_by=current_user.id)
        db.session.add(new_game)
        db.session.commit()

        best = db.session.query(func.max(Snake.points)).filter(Snake.created_by == str(current_user.id), Snake.created_at >= CURRENT_EDITION_START).scalar() or 0
        return jsonify({'ok': True, 'best': best})

    @app.route('/games', methods=['GET'])
    @login_required
    def games():
        snake_leader = Snake.query.filter(Snake.created_at >= CURRENT_EDITION_START).order_by(Snake.points.desc()).first()
        user = User.query.filter_by(id=snake_leader.created_by).first() if snake_leader else None
        tetris_leader = Tetris.query.filter(Tetris.created_at >= CURRENT_EDITION_START).order_by(Tetris.points.desc()).first()
        user2 = User.query.filter_by(id=tetris_leader.created_by).first() if tetris_leader else None
        dino_leader = Dino.query.filter(Dino.created_at >= CURRENT_EDITION_START).order_by(Dino.points.desc()).first()
        user3 = User.query.filter_by(id=dino_leader.created_by).first() if dino_leader else None
        ice_tower_leader = IceTower.query.order_by(IceTower.points.desc()).first()
        user4 = User.query.filter_by(id=ice_tower_leader.created_by).first() if ice_tower_leader else None
        kk_leader = KolkoKrzyzyk.query.order_by(KolkoKrzyzyk.points.desc()).first()
        user5 = User.query.filter_by(id=kk_leader.created_by).first() if kk_leader else None
        formula_leader = Formula.query.order_by(Formula.points.desc()).first()
        user6 = User.query.filter_by(id=formula_leader.created_by).first() if formula_leader else None
        # Pod Górkę ukryta - dostępna tylko z bezpośredniego adresu /gorka
        # gorka_leader = Gorka.query.order_by(Gorka.points.desc()).first()
        # user7 = User.query.filter_by(id=gorka_leader.created_by).first() if gorka_leader else None
        # Rekordziści poprzedniej edycji - wyniki zapisane do 8.10.2026 włącznie
        def previous_record(model):
            leader = model.query.filter(model.created_at < PREVIOUS_EDITION_END).order_by(model.points.desc()).first()
            leader_user = User.query.filter_by(id=leader.created_by).first() if leader else None
            return (leader, leader_user) if leader_user else None
        games=[]
        games.append(['Snake', 'static/images/snake.svg', snake_leader, user, 'snake', 'ranking_snake', previous_record(Snake)])
        games.append(['Tetris', 'static/images/tetris.svg', tetris_leader, user2, 'tetris', 'ranking_tetris', previous_record(Tetris)])
        games.append(['Dino', 'static/images/dino.svg', dino_leader, user3, 'dino', 'ranking_dino', previous_record(Dino)])
        games.append(['Ice Tower', 'static/images/ice_tower.svg', ice_tower_leader, user4, 'ice_tower', 'ranking_ice_tower'])
        games.append(['Kółko i krzyżyk', 'static/images/kolko_krzyzyk.svg', kk_leader, user5, 'kolko_krzyzyk', 'ranking_kolko_krzyzyk'])
        games.append(['Formuła', 'static/images/formula.svg', formula_leader, user6, 'formula', 'ranking_formula'])
        # games.append(['Pod Górkę', 'static/images/gorka.svg', gorka_leader, user7, 'gorka', 'ranking_gorka'])
        return render_template('games.html', games=games)

    @app.route('/tetris', methods=['GET', 'POST'])
    @login_required
    def tetris():
        best = db.session.query(func.max(Tetris.points)).filter(Tetris.created_by == str(current_user.id), Tetris.created_at >= CURRENT_EDITION_START).scalar() or 0
        return render_template('tetris.html', best=best)

    @app.route('/tetris/save_score', methods=['POST'])
    @login_required
    def save_score_tetris():
        data = request.get_json(silent=True) or {}
        try:
            score = max(0, int(data.get('score', 0)))
        except (TypeError, ValueError):
            return jsonify({'ok': False}), 400

        error = check_game_run('tetris', score, data)
        if error:
            return jsonify({'ok': False, 'error': error}), 400

        new_game = Tetris(points=score, created_by=current_user.id)
        db.session.add(new_game)
        db.session.commit()

        best = db.session.query(func.max(Tetris.points)).filter(Tetris.created_by == str(current_user.id), Tetris.created_at >= CURRENT_EDITION_START).scalar() or 0
        return jsonify({'ok': True, 'best': best})

    @app.route('/dino/save_score', methods=['POST'])
    @login_required
    def save_score_dino():
        data = request.get_json(silent=True) or {}
        try:
            score = max(0, int(data.get('score', 0)))
        except (TypeError, ValueError):
            return jsonify({'ok': False}), 400

        error = check_game_run('dino', score, data)
        if error:
            return jsonify({'ok': False, 'error': error}), 400

        new_game = Dino(points=score, created_by=current_user.id)
        db.session.add(new_game)
        db.session.commit()

        best = db.session.query(func.max(Dino.points)).filter(Dino.created_by == str(current_user.id), Dino.created_at >= CURRENT_EDITION_START).scalar() or 0
        return jsonify({'ok': True, 'best': best})

    def game_ranking(model, condition):
        """Ranking graczy (próby, suma punktów, rekord) i liczba gier dla gier spełniających condition."""
        ranking_data = db.session.query(
            User.id,
            User.username,
            User.photo,
            func.count(model.id).label('attempts'),  # Ilość prób
            func.sum(model.points).label('total_points'),  # Suma zdobytych punktów
            func.max(model.points).label('high_score')  # Najwyższy wynik (rekord)
        ).outerjoin(model, model.created_by == User.id)             .filter(condition)             .group_by(User.id)             .having(func.max(model.points) != None)             .order_by(func.max(model.points).desc())             .all()
        rozegranych_gier = model.query.filter(condition).count()
        return ranking_data, rozegranych_gier

    def render_edition_ranking(template, model):
        ranking_data, rozegranych_gier = game_ranking(model, model.created_at >= CURRENT_EDITION_START)
        old_ranking_data, old_rozegranych_gier = game_ranking(model, model.created_at < PREVIOUS_EDITION_END)
        return render_template(template, ranking_data=ranking_data, rozegranych_gier=rozegranych_gier,
                               old_ranking_data=old_ranking_data, old_rozegranych_gier=old_rozegranych_gier)

    @app.route('/ranking_snake', methods=['GET', 'POST'])
    @login_required
    def ranking_snake():
        return render_edition_ranking('ranking_snake.html', Snake)

    @app.route('/ranking_tetris', methods=['GET', 'POST'])
    @login_required
    def ranking_tetris():
        return render_edition_ranking('ranking_tetris.html', Tetris)

    @app.route('/ranking_dino', methods=['GET', 'POST'])
    @login_required
    def ranking_dino():
        return render_edition_ranking('ranking_dino.html', Dino)

    def game_catalog():
        """Gry z rankingiem: nazwa, model, ranking, ikona i warunek bieżącej / poprzedniej edycji."""
        def edition(model):
            return model.created_at >= CURRENT_EDITION_START, model.created_at < PREVIOUS_EDITION_END
        games = []
        for name, model, slug, has_editions in [
            ('Snake', Snake, 'snake', True),
            ('Tetris', Tetris, 'tetris', True),
            ('Dino', Dino, 'dino', True),
            ('Ice Tower', IceTower, 'ice_tower', False),
            ('Kółko i krzyżyk', KolkoKrzyzyk, 'kolko_krzyzyk', False),
            ('Formuła', Formula, 'formula', False),
            # ('Pod Górkę', Gorka, 'gorka', False),  # ukryta
        ]:
            current, previous = edition(model) if has_editions else (true(), None)
            games.append({'name': name, 'model': model, 'slug': slug, 'ranking': 'ranking_' + slug,
                          'icon': 'images/' + slug + '.svg', 'current': current, 'previous': previous})
        return games

    def player_place(model, condition, user_id):
        """Miejsce, rekord i liczba prób gracza w rankingu - None, gdy nie grał."""
        ranking_data, _ = game_ranking(model, condition)
        for place, row in enumerate(ranking_data, 1):
            if row.id == user_id:
                return {'place': place, 'high_score': row.high_score, 'attempts': row.attempts, 'players': len(ranking_data)}
        return None

    @app.route('/profil/<int:user_id>')
    @login_required
    def profil(user_id):
        user = User.query.get_or_404(user_id)
        stats = []
        for game in game_catalog():
            stats.append({'name': game['name'], 'ranking': game['ranking'], 'has_editions': game['previous'] is not None,
                          'current': player_place(game['model'], game['current'], user.id),
                          'previous': player_place(game['model'], game['previous'], user.id) if game['previous'] is not None else None})
        return render_template('profil.html', profile_user=user, stats=stats, profile_cash=user_cash(user.id),
                               profile_standing=standings().get(user.id, {'points': 0, 'games': 0, 'cash': 0}))

    def overall_ranking(rankings):
        """Ranking ogólny: za miejsca 1-10 w każdej grze 10, 9, ... 1 pkt."""
        table = {}
        for ranking_data in rankings:
            for place, row in enumerate(ranking_data[:10], 1):
                entry = table.setdefault(row.id, {'id': row.id, 'username': row.username, 'photo': row.photo,
                                                  'points': 0, 'gold': 0, 'podiums': 0})
                entry['points'] += 11 - place
                entry['gold'] += place == 1
                entry['podiums'] += place <= 3
        return sorted(table.values(), key=lambda e: (-e['points'], -e['gold']))

    @app.route('/hall_of_fame')
    @login_required
    def hall_of_fame():
        champions, previous_champions, rankings = [], [], []
        for game in game_catalog():
            ranking_data, games_played = game_ranking(game['model'], game['current'])
            rankings.append(ranking_data)
            champions.append({'game': game, 'podium': ranking_data[:3], 'games_played': games_played})
            if game['previous'] is not None:
                old_data, _ = game_ranking(game['model'], game['previous'])
                if old_data:
                    previous_champions.append({'game': game, 'leader': old_data[0]})
        # sekcja "Jak liczy się kasa?": wyliczenie dla zalogowanego i 5 najbogatszych
        all_standings = standings()
        top_cash = sorted((item for item in all_standings.items() if item[1]['cash']), key=lambda item: -item[1]['cash'])[:5]
        cash_users = {u.id: u for u in User.query.filter(User.id.in_([uid for uid, _ in top_cash])).all()} if top_cash else {}
        return render_template('hall_of_fame.html', champions=champions,
                               previous_champions=previous_champions, overall=overall_ranking(rankings),
                               edition_start=CURRENT_EDITION_START,
                               my_standing=all_standings.get(current_user.id, {'points': 0, 'games': 0, 'cash': 0}),
                               richest=[(cash_users[uid], entry) for uid, entry in top_cash if uid in cash_users])

    standings_cache = {'at': 0, 'data': None}

    def standings():
        """{user_id: {'place', 'points', 'games', 'cash'}} z rankingu ogólnego Hall of Fame (bieżąca edycja).
        Liczone najwyżej raz na minutę na workera - korona i kasa są w menu na każdej stronie."""
        if standings_cache['data'] is not None and time.time() - standings_cache['at'] < 60:
            return standings_cache['data']
        rankings, result = [], {}
        for game in game_catalog():
            ranking_data, _ = game_ranking(game['model'], game['current'])
            rankings.append(ranking_data)
            for row in ranking_data:
                entry = result.setdefault(row.id, {'place': None, 'points': 0, 'games': 0})
                entry['games'] += row.attempts
        for place, entry in enumerate(overall_ranking(rankings), 1):
            result[entry['id']].update(place=place, points=entry['points'])
        for entry in result.values():
            entry['cash'] = CASH_PER_HOF_POINT * entry['points'] + CASH_PER_GAME * entry['games']
        standings_cache.update(at=time.time(), data=result)
        return result

    def user_cash(user_id):
        return standings().get(user_id, {}).get('cash', 0)

    @app.template_global('crown')
    def crown(user_id):
        """Korona przy nicku dla TOP 1-3 rankingu ogólnego Hall of Fame (zgłoszenie #20)."""
        try:
            place = standings().get(int(user_id), {}).get('place')
        except (TypeError, ValueError):
            return ''
        if not place or place > 3:
            return ''
        return Markup(f'<span class="hl-crown hl-crown-{place}" title="{place}. miejsce w Hall of Fame">👑</span>')

    @app.template_filter('money')
    def money(value):
        """1234567 -> 1,234,567 (jak kasa w GTA)."""
        return f'{int(value or 0):,}'

    @app.context_processor
    def inject_loading_screen():
        """Ekran ładowania tylko przy pierwszej stronie w sesji przeglądarki (flaga w ciasteczku sesji)."""
        if not site_settings()['loading_on']:
            return {}
        if session.get('intro_seen') or request.method != 'GET' or request.blueprint or                 (request.endpoint or 'static') == 'static' or request.path.startswith('/api'):
            return {}
        session['intro_seen'] = True
        photo = Images.query.filter(db.or_(*[Images.file_path.ilike('%.' + ext) for ext in
                                             ('jpg', 'jpeg', 'png', 'webp')])).order_by(func.random()).first()
        return {'loading_screen': {'photo': photo.file_path if photo else 'static/images/hlyw_2.jpg',
                                   'tips': random.sample(LOADING_TIPS, 3),
                                   'duration_ms': max(1, site_settings()['loading_seconds']) * 1000}}

    @app.context_processor
    def inject_cash():
        if not current_user.is_authenticated:
            return {}
        return {'my_cash': user_cash(current_user.id),
                'cash_per_point': CASH_PER_HOF_POINT, 'cash_per_game': CASH_PER_GAME}

    wanted_cache = {'at': 0, 'data': None}

    def wanted_levels():
        """{user_id: (gwiazdki 0-5, punkty aktywności)} z ostatnich WANTED_DAYS dni, liczone raz na minutę."""
        if wanted_cache['data'] is not None and time.time() - wanted_cache['at'] < 60:
            return wanted_cache['data']
        since = datetime.utcnow() - timedelta(days=WANTED_DAYS)
        activity = {}

        def add(kind, rows):
            for user_id, count in rows:
                try:
                    user_id = int(user_id)
                except (TypeError, ValueError):
                    continue
                activity[user_id] = activity.get(user_id, 0) + WANTED_WEIGHTS[kind] * count

        def count_by(column, date_column):
            return db.session.query(column, func.count()).filter(date_column >= since).group_by(column).all()

        for game in game_catalog():
            add('gry', count_by(game['model'].created_by, game['model'].created_at))
        add('czat', count_by(Message.user_id, Message.timestamp))
        add('zdjęcia', count_by(Images.created_by, Images.created_at))
        add('newsy', count_by(News.created_by, News.created_at))
        add('komentarze', count_by(Comment.user_id, Comment.created_at))
        add('wydarzenia', count_by(Calendar.created_by, Calendar.created_at))
        result = {user_id: (sum(points >= t for t in WANTED_THRESHOLDS), points) for user_id, points in activity.items()}
        wanted_cache.update(at=time.time(), data=result)
        return result

    @app.template_global('wanted_stars')
    def wanted_stars(user_id):
        """Gwiazdki poszukiwania jak w GTA V: zapalone ★ + szare ★, razem 5."""
        level, points = wanted_levels().get(int(user_id), (0, 0))
        return Markup(f'<span class="hl-wanted" title="Poziom poszukiwania {level}/5 - aktywność z {WANTED_DAYS} dni: {points} pkt">'
                      f'{"★" * level}<span class="off">{"★" * (5 - level)}</span></span>')

    # ===================== Ostatnia aktywność =====================

    def recent_activity(since, limit, kinds=None, exclude_user_id=None):
        """Co się dzieje na stronie od `since` (UTC): lista słowników {kind, icon, user, text, url, at},
        od najnowszego. Gry jednej osoby w jedną grę są zebrane w jeden wpis (inaczej zalałyby listę).
        kinds - tylko wybrane rodzaje (np. dla powiadomień), exclude_user_id - bez własnych działań."""
        users, items = {}, []

        def who(user_id):
            try:
                user_id = int(user_id)
            except (TypeError, ValueError):
                return None
            if user_id not in users:
                users[user_id] = User.query.get(user_id)
            return users[user_id]

        def want(kind):
            return kinds is None or kind in kinds

        def add(kind, icon, user_id, text, url, at, system=False):
            user = None if system else who(user_id)
            if not system and (not user or user.id == exclude_user_id):
                return
            items.append({'kind': kind, 'icon': icon, 'user': user, 'text': text, 'url': url, 'at': at})

        if want('game'):
            for game in game_catalog():
                model = game['model']
                top = db.session.query(func.max(model.points)).filter(game['current']).scalar()
                rows = db.session.query(model.created_by, func.count(), func.max(model.points), func.max(model.created_at)) \
                    .filter(model.created_at > since).group_by(model.created_by).all()
                for user_id, count, best, at in rows:
                    games_text = plural(count, 'gra', 'gry', 'gier')
                    if best and top and best >= top:
                        text, icon = f'1. miejsce w grze {game["name"]} - {best} pkt!', '🏆'
                    else:
                        text, icon = f'{game["name"]}: {games_text}, najlepiej {best or 0} pkt', '🎮'
                    add('game', icon, user_id, text, url_for(game['ranking']), at)
        if want('news'):
            for n in News.query.filter(News.created_at > since).all():
                add('news', '📰', n.created_by, 'nowy news: ' + n.title, url_for('news'), n.created_at)
        if want('event'):
            for e in Calendar.query.filter(Calendar.created_at > since).all():
                add('event', '📅', e.created_by, f'nowe wydarzenie: {e.title} ({e.date.strftime("%d.%m")})',
                    url_for('event', day=e.date.day, month=e.date.month, year=e.date.year), e.created_at)
        if want('chat'):
            for m in Message.query.filter(Message.timestamp > since).order_by(Message.timestamp.desc()).limit(limit).all():
                text = m.content if len(m.content) <= 100 else m.content[:100] + '…'
                add('chat', '💬', m.user_id, f'na czacie: „{text}”', url_for('camera'), m.timestamp)
        if want('photos'):
            for album_id, user_id, count, at in db.session.query(Images.album_id, Images.created_by, func.count(),
                                                                 func.max(Images.created_at)) \
                    .filter(Images.created_at > since).group_by(Images.album_id, Images.created_by).all():
                album = Albums.query.get(album_id)
                add('photos', '📷', user_id,
                    f'+{plural(count, "zdjęcie", "zdjęcia", "zdjęć")} w albumie {album.name if album else ""}',
                    url_for('album', album_id=album_id) if album else url_for('albums'), at)
        if want('report'):
            for r in Report.query.filter(Report.created_at > since).all():
                add('report', '🛠️', r.user_id, 'nowe zgłoszenie: ' + r.title, url_for('view_report', report_id=r.id), r.created_at)
            for c in Comment.query.filter(Comment.created_at > since).all():
                report = Report.query.get(c.report_id)
                add('report', '💭', c.user_id, 'komentarz do zgłoszenia: ' + (report.title if report else ''),
                    url_for('view_report', report_id=c.report_id), c.created_at)
        if want('print'):
            for p in PrintRequest.query.filter(PrintRequest.created_at > since).all():
                add('print', '🖨️', p.user_id, 'propozycja do druku 3D: ' + p.title, url_for('print_detail', request_id=p.id), p.created_at)
            for p in PrintRequest.query.filter(PrintRequest.status_at > since).all():
                name, _, icon = PRINT_STATUSES[p.status]
                add('print', icon, p.status_by, f'druk 3D „{p.title}”: {name}', url_for('print_detail', request_id=p.id), p.status_at)
            for ph in PrintPhoto.query.filter(PrintPhoto.created_at > since).all():
                if ph.request:
                    text = ('zdjęcie gotowego wydruku: ' if ph.kind == 'wydruk' else 'wydruk w akcji: ') + ph.request.title
                    add('print', '📸' if ph.kind == 'wydruk' else '🏡', ph.created_by, text,
                        url_for('print_detail', request_id=ph.request_id) + '#zdjecia', ph.created_at)
        if want('tm'):
            for t in TmTime.query.filter(TmTime.created_at > since).all():
                ev = Calendar.query.get(t.track.event_id)
                if ev:
                    add('tm', '🏁', t.user_id, f'Trackmania, trasa {t.track.name}: {format_tm_time(t.time_ms)}',
                        url_for('event', day=ev.date.day, month=ev.date.month, year=ev.date.year) + '#trackmania', t.created_at)
        if want('user'):
            for u in User.query.filter(User.confirmed_on > since).all():
                add('user', '👋', u.id, 'nowa osoba na Hlywie - witamy!', url_for('profil', user_id=u.id), u.confirmed_on)
        if want('camera'):
            live_since = datetime.utcnow() - timedelta(seconds=30)
            for v in CameraVisit.query.filter(CameraVisit.last_seen > since).all():
                minutes = int((v.last_seen - v.started_at).total_seconds() // 60)
                if v.last_seen >= live_since:
                    text = '🔴 teraz na kamerze' + (f' (od {minutes} min)' if minutes else '')
                else:
                    text = f'oglądanie kamery: {minutes} min' if minutes else 'zajrzenie na kamerę'
                add('camera', '🎥', v.user_id, text, url_for('camera'), v.started_at)
        if want('album'):
            for a in Albums.query.filter(Albums.created_at > since).all():
                add('album', '📁', a.created_by, 'nowy album: ' + a.name, url_for('album', album_id=a.id), a.created_at)
        if want('like'):
            rows = db.session.query(ImageLike.user_id, Images.album_id, func.count(), func.max(ImageLike.created_at)) \
                .join(Images, Images.id == ImageLike.image_id) \
                .filter(ImageLike.created_at > since).group_by(ImageLike.user_id, Images.album_id).all()
            for user_id, album_id, count, at in rows:
                album = Albums.query.get(album_id)
                add('like', '❤️', user_id,
                    f'polubienie: {plural(count, "zdjęcie", "zdjęcia", "zdjęć")}' + (f' w albumie {album.name}' if album else ' w galerii'),
                    url_for('album', album_id=album_id) if album else url_for('albums'), at)
        if want('reaction'):
            rows = db.session.query(NewsReaction.user_id, NewsReaction.news_id,
                                    func.group_concat(NewsReaction.emoji, ''), func.max(NewsReaction.created_at)) \
                .filter(NewsReaction.created_at > since).group_by(NewsReaction.user_id, NewsReaction.news_id).all()
            for user_id, news_id, emojis, at in rows:
                n = News.query.get(news_id)
                if n:
                    add('reaction', emojis[:1] or '👍', user_id, f'reakcja {emojis} pod newsem: {n.title}', url_for('news'), at)
        if want('signup'):
            def signup(event_id, user_id, at, extra=''):
                ev = Calendar.query.get(event_id)
                if ev:
                    add('signup', '✋', user_id, f'zapis na: {ev.title}{extra}',
                        url_for('event', day=ev.date.day, month=ev.date.month, year=ev.date.year), at)
            for p in Participant.query.filter(Participant.created_at > since).all():
                signup(p.event_id, p.user_id, p.created_at)
            for p in FifaParticipant.query.filter(FifaParticipant.created_at > since).all():
                signup(p.event_id, p.user_id, p.created_at,
                       f' - gracz ({p.club})' if p.role == 'player' and p.club else (' - gracz' if p.role == 'player' else ' - kibic'))
        if want('match'):
            for m in TournamentMatch.query.filter(TournamentMatch.score_at > since).all():
                if m.home_score is None or not m.home_player or not m.away_player:
                    continue
                ev = Calendar.query.get(m.tournament.event_id) if m.tournament else None
                round_name = ('liga' if m.tournament and m.tournament.is_league else 'grupa') if m.round == 'grupa' else m.round
                add('match', '⚽', None,
                    f'FIFA ({round_name}): {m.home_player.username} {m.home_score}:{m.away_score} {m.away_player.username}',
                    url_for('event', day=ev.date.day, month=ev.date.month, year=ev.date.year) if ev else url_for('calendar'),
                    m.score_at, system=True)
        if want('quiz'):
            rows = db.session.query(QuizResponse.user_id, QuizItem.quiz_id, func.count(), func.max(QuizResponse.answered_at)) \
                .join(QuizItem, QuizItem.id == QuizResponse.item_id) \
                .filter(QuizResponse.answered_at > since).group_by(QuizResponse.user_id, QuizItem.quiz_id).all()
            for user_id, quiz_id, count, at in rows:
                q = Quiz.query.get(quiz_id)
                if q:
                    add('quiz', '🧠', user_id, f'quiz „{q.title}”: {plural(count, "odpowiedź", "odpowiedzi", "odpowiedzi")}',
                        url_for('quiz'), at)
        if want('upgrade'):
            # kilka ulepszeń dodanych jednego dnia = jeden wpis, żeby nie zasłoniły reszty
            by_day = {}
            for u in Upgrade.query.filter(Upgrade.date > since).order_by(Upgrade.date).all():
                by_day.setdefault(u.date.date(), []).append(u)
            for ups in by_day.values():
                text = ('Nowe ulepszenie: ' + ups[0].title if len(ups) == 1 else
                        f'Nowe ulepszenia ({len(ups)}): ' + ', '.join(u.title for u in ups))
                add('upgrade', '🚀', None, text, url_for('ostatnie_ulepszenia'), ups[-1].date, system=True)
        items.sort(key=lambda i: i['at'], reverse=True)
        return items[:limit]

    def activity_json(item):
        user = item['user']
        return {'kind': item['kind'], 'icon': item['icon'], 'text': item['text'], 'url': item['url'],
                'username': user.username if user else 'hlyw.pl', 'photo': user.photo if user else None,
                'at': item['at'].isoformat()}

    @app.route('/aktywnosc')
    @login_required
    def activity():
        """Pełna lista ostatnich aktywności (14 dni)."""
        return render_template('aktywnosc.html',
                               activity=recent_activity(datetime.utcnow() - timedelta(days=14), limit=100))

    @app.route('/aktywnosc/lista')
    @login_required
    def activity_list():
        """Sam kawałek HTML z listą - strona główna odświeża nim kartę „Co się dzieje” co minutę."""
        return render_template('_activity.html',
                               activity=recent_activity(datetime.utcnow() - timedelta(days=3), limit=8))

    @app.route('/api/powiadomienia')
    @login_required
    def api_notifications():
        """Powiadomienia jak SMS-y w GTA: co nowego dodali inni od `since` (UTC, ISO). Strona pyta co 45 s.
        Bez `since` zwraca tylko aktualny czas serwera - od niego liczy się następne zapytanie."""
        now = datetime.utcnow()
        try:
            since = datetime.fromisoformat(request.args['since'])
        except (KeyError, ValueError):
            return jsonify({'now': now.isoformat(), 'items': []})
        if not site_settings()['notify_on']:
            return jsonify({'now': now.isoformat(), 'items': []})
        since = max(since, now - timedelta(hours=1))   # po długiej przerwie nie zalewamy starociami
        items = recent_activity(since, limit=20, kinds=NOTIFY_KINDS, exclude_user_id=current_user.id)
        # tylko to, co zaczęło się od ostatniego pytania - np. trwające oglądanie kamery nie wraca co 45 s
        items = [i for i in items if i['at'] > since][:5]
        return jsonify({'now': now.isoformat(), 'items': [activity_json(i) for i in reversed(items)]})

    @app.route('/api/kasa')
    @login_required
    def api_cash():
        return jsonify({'cash': user_cash(current_user.id)})

    @app.route('/dino', methods=['GET', 'POST'])
    @login_required
    def dino():
        best = db.session.query(func.max(Dino.points)).filter(Dino.created_by == str(current_user.id), Dino.created_at >= CURRENT_EDITION_START).scalar() or 0
        return render_template('dino.html', best=best)

    # ===================== Quiz na żywo =====================

    def normalize_answer(text):
        """Do porównywania odpowiedzi otwartych: bez wielkości liter, polskich znaków i zbędnych spacji."""
        text = (text or '').strip().lower().replace('ł', 'l')
        text = ''.join(c for c in unicodedata.normalize('NFKD', text) if not unicodedata.combining(c))
        text = re.sub(r'[^\w\s,.-]', '', text)
        return re.sub(r'\s+', ' ', text).strip(' .')

    def check_quiz_answer(item, answer):
        if item.kind == 'abcd':
            return answer == item.correct_answer
        accepted = [normalize_answer(a) for a in item.correct_answer.split('|')]
        return normalize_answer(answer) in accepted

    def quiz_ranking(quiz):
        """[(user, punkty, poprawne)] od najlepszego; przy remisie wyżej ten, kto skończył odpowiadać wcześniej."""
        rows = db.session.query(QuizResponse.user_id,
                                func.sum(db.case((QuizResponse.is_correct == True, QuizItem.points), else_=0)),
                                func.sum(db.case((QuizResponse.is_correct == True, 1), else_=0)),
                                func.max(QuizResponse.answered_at)) \
            .join(QuizItem, QuizItem.id == QuizResponse.item_id) \
            .filter(QuizItem.quiz_id == quiz.id) \
            .group_by(QuizResponse.user_id).all()
        rows.sort(key=lambda r: (-(r[1] or 0), r[3]))
        users = {u.id: u for u in User.query.filter(User.id.in_([r[0] for r in rows])).all()} if rows else {}
        return [(users[r[0]], r[1] or 0, r[2] or 0) for r in rows if r[0] in users]

    def live_quiz():
        """Quiz, który właśnie trwa - ten widzą gracze na /quiz."""
        return Quiz.query.filter_by(state='trwa').order_by(Quiz.id.desc()).first()

    def quiz_admin_required():
        if current_user.is_admin == "0":
            flash('Quiz prowadzi tylko admin.', 'danger')
            return redirect(url_for('quiz'))
        return None

    @app.context_processor
    def inject_live_quiz():
        """Pozycja „Quiz LIVE” w menu, gdy quiz trwa."""
        return {'quiz_live': live_quiz() is not None}

    @app.route('/quiz')
    @login_required
    def quiz():
        return render_template('quiz.html')

    @app.route('/quiz/state')
    @login_required
    def quiz_state():
        """Stan quizu dla gracza - strona /quiz odpytuje to co 2 sekundy."""
        quiz = live_quiz()
        if not quiz:
            last = Quiz.query.filter_by(state='koniec').order_by(Quiz.id.desc()).first()
            if last:
                return jsonify({'state': 'koniec', 'title': last.title,
                                'ranking': [{'username': u.username, 'points': p, 'correct': c, 'me': u.id == current_user.id}
                                            for u, p, c in quiz_ranking(last)[:20]]})
            return jsonify({'state': 'brak'})

        data = {'state': 'trwa', 'title': quiz.title, 'total': len(quiz.items)}
        item = QuizItem.query.get(quiz.current_item_id) if quiz.current_item_id else None
        if not item:
            data['item'] = None
            return jsonify(data)

        mine = QuizResponse.query.filter_by(item_id=item.id, user_id=current_user.id).first()
        data.update({
            'item': {'id': item.id, 'number': quiz.items.index(item) + 1, 'text': item.text, 'kind': item.kind,
                     'options': item.options_dict, 'points': item.points},
            'revealed': quiz.revealed,
            'my_answer': mine.answer if mine else None,
            'answered': QuizResponse.query.filter_by(item_id=item.id).count(),
        })
        if quiz.revealed:
            data['correct'] = item.correct_label()
            data['my_correct'] = bool(mine and mine.is_correct)
            data['my_points'] = next((p for u, p, c in quiz_ranking(quiz) if u.id == current_user.id), 0)
        return jsonify(data)

    @app.route('/quiz/answer', methods=['POST'])
    @login_required
    def quiz_answer():
        data = request.get_json(silent=True) or {}
        quiz = live_quiz()
        item = QuizItem.query.get(quiz.current_item_id) if quiz and quiz.current_item_id else None
        if not item or item.id != data.get('item_id'):
            return jsonify({'ok': False, 'message': 'To pytanie jest już nieaktualne.'}), 409
        if quiz.revealed:
            return jsonify({'ok': False, 'message': 'Odpowiedź została już pokazana.'}), 409

        answer = str(data.get('answer', '')).strip()[:500]
        if not answer or (item.kind == 'abcd' and answer not in item.options_dict):
            return jsonify({'ok': False, 'message': 'Wybierz odpowiedź.'}), 400

        response = QuizResponse.query.filter_by(item_id=item.id, user_id=current_user.id).first() \
            or QuizResponse(item_id=item.id, user_id=current_user.id)
        response.answer = answer
        response.is_correct = check_quiz_answer(item, answer)
        response.answered_at = datetime.utcnow()
        db.session.add(response)
        db.session.commit()
        return jsonify({'ok': True})

    # ----- panel admina -----

    @app.route('/quiz/admin', methods=['GET', 'POST'])
    @login_required
    def quiz_admin():
        denied = quiz_admin_required()
        if denied:
            return denied
        if request.method == 'POST':
            title = request.form.get('title', '').strip()
            if title:
                new_quiz = Quiz(title=title[:150])
                db.session.add(new_quiz)
                db.session.commit()
                return redirect(url_for('quiz_edit', quiz_id=new_quiz.id))
            flash('Podaj nazwę quizu.', 'warning')
        return render_template('quiz_admin.html', quizzes=Quiz.query.order_by(Quiz.id.desc()).all())

    @app.route('/quiz/<int:quiz_id>/edit', methods=['GET', 'POST'])
    @login_required
    def quiz_edit(quiz_id):
        denied = quiz_admin_required()
        if denied:
            return denied
        quiz = Quiz.query.get_or_404(quiz_id)
        edit_item = QuizItem.query.get(request.args.get('item', type=int) or 0)
        if edit_item and edit_item.quiz_id != quiz.id:
            edit_item = None

        if request.method == 'POST':
            action = request.form.get('action')
            if action == 'rename':
                quiz.title = (request.form.get('title') or quiz.title).strip()[:150]
                db.session.commit()
                return redirect(url_for('quiz_edit', quiz_id=quiz.id))

            item = QuizItem.query.get(request.form.get('item_id', type=int) or 0)
            if item and item.quiz_id != quiz.id:
                abort(404)

            if action == 'delete' and item:
                if quiz.current_item_id == item.id:
                    quiz.current_item_id = None
                db.session.delete(item)
                db.session.commit()
                flash('Pytanie usunięte.', 'success')
                return redirect(url_for('quiz_edit', quiz_id=quiz.id))

            if action in ('up', 'down') and item:
                items = list(quiz.items)
                i = items.index(item)
                j = i - 1 if action == 'up' else i + 1
                if 0 <= j < len(items):
                    items[i], items[j] = items[j], items[i]
                for pos, it in enumerate(items):
                    it.position = pos
                db.session.commit()
                return redirect(url_for('quiz_edit', quiz_id=quiz.id))

            if action == 'save':
                text = request.form.get('text', '').strip()
                kind = 'otwarte' if request.form.get('kind') == 'otwarte' else 'abcd'
                points = max(1, min(10, request.form.get('points', 1, type=int) or 1))
                if kind == 'abcd':
                    options = {k: request.form.get(f'option_{k}', '').strip() for k in 'abcd'}
                    options = {k: v for k, v in options.items() if v}
                    correct = request.form.get('correct_choice', '')
                    error = None if len(options) >= 2 and correct in options else \
                        'Podaj co najmniej 2 odpowiedzi i zaznacz poprawną.'
                else:
                    options = None
                    correct = '|'.join(a.strip() for a in request.form.get('correct_text', '').split('|') if a.strip())
                    error = None if correct else 'Podaj poprawną odpowiedź.'
                if not text:
                    error = 'Wpisz treść pytania.'
                if error:
                    flash(error, 'warning')
                    return redirect(url_for('quiz_edit', quiz_id=quiz.id, item=item.id if item else None))

                if not item:
                    item = QuizItem(quiz_id=quiz.id, position=len(quiz.items))
                    db.session.add(item)
                item.text, item.kind, item.points, item.correct_answer = text, kind, points, correct[:500]
                item.options = json.dumps(options, ensure_ascii=False) if options else None
                # po zmianie poprawnej odpowiedzi przeliczamy już oddane odpowiedzi
                for r in item.responses:
                    r.is_correct = check_quiz_answer(item, r.answer)
                db.session.commit()
                flash('Pytanie zapisane.', 'success')
                return redirect(url_for('quiz_edit', quiz_id=quiz.id))

        return render_template('quiz_edit.html', quiz=quiz, edit_item=edit_item)

    @app.route('/quiz/<int:quiz_id>/delete', methods=['POST'])
    @login_required
    def quiz_delete(quiz_id):
        denied = quiz_admin_required()
        if denied:
            return denied
        db.session.delete(Quiz.query.get_or_404(quiz_id))
        db.session.commit()
        flash('Quiz usunięty.', 'success')
        return redirect(url_for('quiz_admin'))

    @app.route('/quiz/<int:quiz_id>/host')
    @login_required
    def quiz_host(quiz_id):
        denied = quiz_admin_required()
        if denied:
            return denied
        quiz = Quiz.query.get_or_404(quiz_id)
        item = QuizItem.query.get(quiz.current_item_id) if quiz.current_item_id else None
        responses = QuizResponse.query.filter_by(item_id=item.id).order_by(QuizResponse.answered_at).all() if item else []
        return render_template('quiz_host.html', quiz=quiz, item=item, responses=responses,
                               number=quiz.items.index(item) + 1 if item else 0, ranking=quiz_ranking(quiz))

    @app.route('/quiz/<int:quiz_id>/host/answered')
    @login_required
    def quiz_host_answered(quiz_id):
        """Kto już odpowiedział na bieżące pytanie - panel prowadzącego odświeża to na żywo."""
        if current_user.is_admin == "0":
            abort(403)
        quiz = Quiz.query.get_or_404(quiz_id)
        names = [r.user.username for r in QuizResponse.query.filter_by(item_id=quiz.current_item_id)
                 .order_by(QuizResponse.answered_at).all()] if quiz.current_item_id else []
        return jsonify({'count': len(names), 'names': names})

    @app.route('/quiz/<int:quiz_id>/control', methods=['POST'])
    @login_required
    def quiz_control(quiz_id):
        denied = quiz_admin_required()
        if denied:
            return denied
        quiz = Quiz.query.get_or_404(quiz_id)
        action = request.form.get('action')
        items = list(quiz.items)
        current = QuizItem.query.get(quiz.current_item_id) if quiz.current_item_id else None

        if action == 'start':
            if not items:
                flash('Najpierw dodaj pytania.', 'warning')
                return redirect(url_for('quiz_edit', quiz_id=quiz.id))
            Quiz.query.filter(Quiz.id != quiz.id, Quiz.state == 'trwa').update({'state': 'koniec'})
            for it in items:   # nowy start = czysta karta
                QuizResponse.query.filter_by(item_id=it.id).delete()
            quiz.state, quiz.current_item_id, quiz.revealed = 'trwa', items[0].id, False
        elif action == 'reveal' and current:
            quiz.revealed = True
        elif action == 'next' and current:
            i = items.index(current)
            if i + 1 < len(items):
                quiz.current_item_id, quiz.revealed = items[i + 1].id, False
            else:
                quiz.state, quiz.current_item_id, quiz.revealed = 'koniec', None, False
        elif action == 'finish':
            quiz.state, quiz.current_item_id, quiz.revealed = 'koniec', None, False
        elif action == 'toggle':
            response = QuizResponse.query.get_or_404(request.form.get('response_id', type=int))
            if response.item.quiz_id == quiz.id:
                response.is_correct = not response.is_correct
        db.session.commit()
        return redirect(url_for('quiz_host', quiz_id=quiz.id))

    @app.route("/api/videos", methods=["GET"])
    def get_videos():
        UPLOAD_FOLDER = os.path.join('app', 'static', 'videos')

        # Pobierz wszystkie pliki w folderze
        files = glob.glob(os.path.join(UPLOAD_FOLDER, "*"))

        # Posortuj pliki po nazwie (alfabetycznie)
        #files = sorted(files, key=lambda x: os.path.basename(x), reverse=True)
        files = sorted(files, key=lambda x: os.path.basename(x))

        # Tworzenie listy URL-i
        file_urls = [f"/static/videos/{os.path.basename(file)}" for file in files]

        return jsonify(file_urls)

    @app.after_request
    def set_csp(response):
        response.headers['Content-Security-Policy'] = "frame-ancestors 'self' https://player.twitch.tv"
        return response

    @app.route('/user_active', methods=['POST'])
    @login_required
    def user_active():
        """Rejestruje użytkownika jako aktywnego na stronie streamu"""
        now = datetime.utcnow()
        presence = Presence.query.get(current_user.id) or Presence(user_id=current_user.id)
        presence.last_seen = now
        db.session.add(presence)
        # historia oglądania: przerwa dłuższa niż CAMERA_VISIT_GAP = nowe wejście
        visit = CameraVisit.query.filter_by(user_id=current_user.id).order_by(CameraVisit.last_seen.desc()).first()
        if visit and visit.last_seen >= now - CAMERA_VISIT_GAP:
            visit.last_seen = now
        else:
            db.session.add(CameraVisit(user_id=current_user.id, started_at=now, last_seen=now))
        db.session.commit()
        return jsonify({"status": "ok"})

    def camera_viewers():
        """Użytkownicy, którzy byli na stronie kamery w ciągu ostatnich 30 sekund."""
        since = datetime.utcnow() - timedelta(seconds=30)
        return [p.user for p in Presence.query.filter(Presence.last_seen >= since).all()]

    @app.route('/get_active_users')
    @login_required
    def get_active_users():
        """Zwraca listę aktywnych użytkowników"""
        return jsonify({"users": [{"username": u.username, "photo": u.photo} for u in camera_viewers()]})

    @app.route('/send_test_mail', methods=['GET', 'POST'])
    @login_required
    def send_test_mail():
        if current_user.is_admin == "0":
            flash("Brak uprawnień do wysyłania maili", "danger")
            return redirect(url_for('index'))

        form = TestEmail()

        if form.validate_on_submit():
            msg = Message_(subject=form.subject.data, recipients=[form.email.data], html=form.content.data)
            mail.send(msg)
            flash('Email wysłano - zobacz spam', 'success')
            return render_template('test_email.html', form=form)
        else:
            form.email.data = 'kwasek18@gmail.com'
            form.content.data = 'test'
            form.subject.data = "Test subject"
        return render_template('test_email.html', form=form)

    @app.route("/start_tournament/<int:event_id>", methods=["POST"])
    @login_required
    def start_tournament(event_id):
        if current_user.is_admin == "0":
            flash("Brak uprawnień do rozpoczęcia turnieju", "danger")
            return redirect(request.referrer)

        event = Calendar.query.get_or_404(event_id)

        tournament = Tournament.query.filter_by(event_id=event.id).first()
        if tournament and tournament.started:
            flash("Turniej już został rozpoczęty.", "warning")
            return redirect(request.referrer)

        if not tournament:
            tournament = Tournament(event_id=event.id, started=True, finished=False)
            db.session.add(tournament)
            db.session.flush()
        else:
            tournament.started = True

        # gracze z eventu
        fifa_players = FifaParticipant.query.filter_by(event_id=event.id, role="player").all()
        mode = request.form.get("advance")
        if mode in ("liga", "liga2"):
            if len(fifa_players) < 3:
                db.session.rollback()
                flash("Za mało graczy: liga potrzebuje minimum 3.", "danger")
                return redirect(request.referrer)
            tournament.advance, tournament.legs = 0, 2 if mode == "liga2" else 1
            generate_league(tournament, fifa_players, tournament.legs)
        else:
            advance = 4 if mode == "4" else 2
            if len(fifa_players) < 2 * advance:
                db.session.rollback()
                flash(f"Za mało graczy: przy {advance} wychodzących z grupy potrzeba minimum {2 * advance}.", "danger")
                return redirect(request.referrer)
            tournament.advance = advance
            generate_groups_and_matches(tournament, fifa_players)
        db.session.commit()

        flash("Turniej rozpoczęty 🚀", "success")
        return redirect(url_for("event", day=event.date.day, month=event.date.month, year=event.date.year))

    @app.route("/update_match/<int:match_id>", methods=["POST"])
    @login_required
    def update_match(match_id):
        if current_user.is_admin == "0":
            flash("Brak uprawnień", "danger")
            return redirect(request.referrer)

        match = TournamentMatch.query.get_or_404(match_id)
        home = request.form.get("home_score", type=int)
        away = request.form.get("away_score", type=int)
        if (home is None) != (away is None) or (home is not None and (home < 0 or away < 0)):
            flash("Wpisz oba wyniki (liczby od 0) albo zostaw oba pola puste, żeby skasować wynik.", "warning")
            return redirect(request.referrer)
        if match.round != "grupa" and home is not None and home == away:
            flash("W fazie pucharowej musi być zwycięzca - wpisz wynik po dogrywce/karnych (np. 3:2).", "warning")
            return redirect(request.referrer)

        match.home_score, match.away_score = home, away
        match.score_at = datetime.utcnow() if home is not None else None
        message = sync_knockout(match.tournament)
        db.session.commit()
        flash("Wynik meczu zapisany ✅" if home is not None else "Wynik skasowany.", "success")
        if message:
            flash(message, "warning")
        return redirect(request.referrer)

    @app.route("/tournament/<int:event_id>/knockout", methods=["POST"])
    @login_required
    def tournament_knockout(event_id):
        """Admin: ilu graczy wychodzi z grupy (2/4) albo reset całej fazy pucharowej."""
        if current_user.is_admin == "0":
            flash("Brak uprawnień", "danger")
            return redirect(request.referrer)
        tournament = Tournament.query.filter_by(event_id=event_id).first_or_404()
        if tournament.is_league:
            flash("Liga nie ma fazy pucharowej.", "warning")
            return redirect(request.referrer)
        knockout = TournamentMatch.query.filter(TournamentMatch.tournament_id == tournament.id,
                                                TournamentMatch.round != "grupa").all()
        if request.form.get("action") == "reset":
            for match in knockout:
                db.session.delete(match)
            db.session.flush()
            flash("Faza pucharowa wyczyszczona - ułożyła się od nowa z tabel grup.", "success")
        else:
            advance = 4 if request.form.get("advance", type=int) == 4 else 2
            if any(has_score(m) for m in knockout):
                flash("Mecze pucharowe mają już wyniki - najpierw zresetuj fazę pucharową.", "warning")
                return redirect(request.referrer)
            if any(len(calculate_group_table(g)) < advance for g in tournament.groups):
                flash(f"W którejś grupie jest mniej niż {advance} graczy.", "warning")
                return redirect(request.referrer)
            tournament.advance = advance
            flash(f"Z każdej grupy wychodzi teraz {advance}.", "success")
        message = sync_knockout(tournament)
        db.session.commit()
        if message:
            flash(message, "warning")
        return redirect(request.referrer)

    @app.route("/finish_tournament/<int:event_id>", methods=["POST"])
    @login_required
    def finish_tournament(event_id):
        if current_user.is_admin == "0":
            flash("Brak uprawnień", "danger")
            return redirect(request.referrer)

        tournament = Tournament.query.filter_by(event_id=event_id).first()
        if not tournament:
            flash("Brak aktywnego turnieju", "warning")
            return redirect(request.referrer)

        tournament.finished = True
        db.session.commit()

        flash("Turniej zakończony 🏁", "success")
        return redirect(request.referrer)

    # ===================== Turniej Trackmania =====================

    def trackmania_data(event):
        """Trasy z wynikami, klasyfikacja generalna i to, kto może co edytować - dla event.html."""
        tracks = TmTrack.query.filter_by(event_id=event.id).order_by(TmTrack.id).all()
        standings_tm = {}
        for track in tracks:
            track.results = sorted(track.times, key=lambda t: (t.time_ms, t.created_at))
            for place, result in enumerate(track.results, 1):
                result.place = place
                result.points = TM_POINTS[place - 1] if place <= len(TM_POINTS) else 0
                row = standings_tm.setdefault(result.user_id, {'user': result.user, 'points': 0, 'wins': 0,
                                                               'tracks': 0, 'total_ms': 0})
                row['points'] += result.points
                row['wins'] += place == 1
                row['tracks'] += 1
                row['total_ms'] += result.time_ms
        # remis: więcej wygranych tras, potem więcej przejechanych, potem krótszy łączny czas
        general = sorted(standings_tm.values(), key=lambda r: (-r['points'], -r['wins'], -r['tracks'], r['total_ms']))
        participant_ids = {int(p.user_id) for p in Participant.query.filter_by(event_id=event.id).all()
                           if str(p.user_id).isdigit()}
        can_manage = current_user.is_admin != "0" or str(event.created_by) == str(current_user.id)
        return {'tracks': tracks, 'general': general, 'can_manage': can_manage,
                'can_drive': can_manage or current_user.id in participant_ids,
                'players': User.query.filter(User.id.in_(participant_ids)).order_by(User.username).all()
                           if can_manage else [],
                'points': TM_POINTS}

    def tm_event_or_404(event_id):
        event = Calendar.query.get_or_404(event_id)
        if 'trackmania' not in event.title.lower():
            abort(404)
        return event

    def redirect_to_event(event):
        return redirect(url_for('event', day=event.date.day, month=event.date.month, year=event.date.year) + '#trackmania')

    @app.route('/event/<int:event_id>/tm/track', methods=['POST'])
    @login_required
    def tm_add_track(event_id):
        event = tm_event_or_404(event_id)
        if not trackmania_data(event)['can_manage']:
            abort(403)
        name = (request.form.get('name') or '').strip()[:100]
        if name:
            db.session.add(TmTrack(event_id=event.id, name=name))
            db.session.commit()
            flash(f'Dodano trasę „{name}”.', 'success')
        return redirect_to_event(event)

    @app.route('/event/<int:event_id>/tm/track/<int:track_id>/delete', methods=['POST'])
    @login_required
    def tm_delete_track(event_id, track_id):
        event = tm_event_or_404(event_id)
        if not trackmania_data(event)['can_manage']:
            abort(403)
        track = TmTrack.query.filter_by(id=track_id, event_id=event.id).first_or_404()
        db.session.delete(track)
        db.session.commit()
        flash(f'Usunięto trasę „{track.name}” razem z jej czasami.', 'info')
        return redirect_to_event(event)

    @app.route('/event/<int:event_id>/tm/time', methods=['POST'])
    @login_required
    def tm_save_time(event_id):
        event = tm_event_or_404(event_id)
        rights = trackmania_data(event)
        track = TmTrack.query.filter_by(id=request.form.get('track_id', type=int), event_id=event.id).first_or_404()
        user_id = current_user.id
        if rights['can_manage'] and request.form.get('user_id', type=int):
            user_id = request.form.get('user_id', type=int)      # organizator wpisuje czas za kogoś
        elif not rights['can_drive']:
            flash('Najpierw zapisz się na wydarzenie.', 'warning')
            return redirect_to_event(event)
        time_ms = parse_tm_time(request.form.get('time'))
        if time_ms is None:
            flash('Zły format czasu - wpisz np. 1:02.345 albo 58.120.', 'danger')
            return redirect_to_event(event)
        entry = TmTime.query.filter_by(track_id=track.id, user_id=user_id).first()
        if entry:
            entry.time_ms, entry.created_at = time_ms, datetime.utcnow()
        else:
            db.session.add(TmTime(track_id=track.id, user_id=user_id, time_ms=time_ms))
        db.session.commit()
        flash(f'Zapisano czas {format_tm_time(time_ms)} na trasie „{track.name}”.', 'success')
        return redirect_to_event(event)

    @app.route('/event/<int:event_id>/tm/time/<int:time_id>/delete', methods=['POST'])
    @login_required
    def tm_delete_time(event_id, time_id):
        event = tm_event_or_404(event_id)
        entry = TmTime.query.get_or_404(time_id)
        if entry.track.event_id != event.id:
            abort(404)
        if entry.user_id != current_user.id and not trackmania_data(event)['can_manage']:
            abort(403)
        db.session.delete(entry)
        db.session.commit()
        flash('Usunięto czas.', 'info')
        return redirect_to_event(event)

    @app.route("/join_fifa_event/<int:event_id>", methods=["POST"])
    @login_required
    def join_fifa_event(event_id):
        role = request.form.get("role")
        club = request.form.get("club") if role == "player" else None

        if FifaParticipant.query.filter_by(event_id=event_id, user_id=current_user.id).first():
            flash("Już jesteś zapisany na to wydarzenie.", "warning")
            return redirect(request.referrer)

        fifa_participant = FifaParticipant(
            event_id=event_id,
            user_id=current_user.id,
            role=role,
            club=club
        )
        db.session.add(fifa_participant)
        db.session.commit()
        flash("Zapisano do turnieju FIFA ✅", "success")
        return redirect(request.referrer)

    @app.route('/ice_tower', methods=['GET', 'POST'])
    @login_required
    def ice_tower():
        best = db.session.query(func.max(IceTower.points)).filter(IceTower.created_by == str(current_user.id)).scalar() or 0
        return render_template('ice_tower.html', best=best)

    @app.route('/ice_tower/save_score', methods=['POST'])
    @login_required
    def save_score_ice_tower():
        data = request.get_json(silent=True) or {}
        try:
            score = max(0, int(data.get('score', 0)))
        except (TypeError, ValueError):
            return jsonify({'ok': False}), 400

        error = check_game_run('ice_tower', score, data)
        if error:
            return jsonify({'ok': False, 'error': error}), 400

        new_game = IceTower(points=score, created_by=current_user.id)
        db.session.add(new_game)
        db.session.commit()

        best = db.session.query(func.max(IceTower.points)).filter(IceTower.created_by == str(current_user.id)).scalar() or 0
        return jsonify({'ok': True, 'best': best})

    @app.route('/ranking_ice_tower', methods=['GET', 'POST'])
    @login_required
    def ranking_ice_tower():
        ranking_data, rozegranych_gier = game_ranking(IceTower, true())
        return render_template('ranking_ice_tower.html', ranking_data=ranking_data, rozegranych_gier=rozegranych_gier)

    @app.route('/kolko_krzyzyk', methods=['GET', 'POST'])
    @login_required
    def kolko_krzyzyk():
        best = db.session.query(func.max(KolkoKrzyzyk.points)).filter(KolkoKrzyzyk.created_by == str(current_user.id)).scalar() or 0
        return render_template('kolko_krzyzyk.html', best=best)

    @app.route('/kolko_krzyzyk/save_score', methods=['POST'])
    @login_required
    def save_score_kolko_krzyzyk():
        data = request.get_json(silent=True, force=True) or {}
        try:
            score = max(0, int(data.get('score', 0)))
        except (TypeError, ValueError):
            return jsonify({'ok': False}), 400

        error = check_game_run('kolko_krzyzyk', score, data)
        if error:
            return jsonify({'ok': False, 'error': error}), 400

        new_game = KolkoKrzyzyk(points=score, created_by=current_user.id)
        db.session.add(new_game)
        db.session.commit()

        best = db.session.query(func.max(KolkoKrzyzyk.points)).filter(KolkoKrzyzyk.created_by == str(current_user.id)).scalar() or 0
        return jsonify({'ok': True, 'best': best})

    @app.route('/ranking_kolko_krzyzyk', methods=['GET', 'POST'])
    @login_required
    def ranking_kolko_krzyzyk():
        ranking_data, rozegranych_gier = game_ranking(KolkoKrzyzyk, true())
        return render_template('ranking_kolko_krzyzyk.html', ranking_data=ranking_data, rozegranych_gier=rozegranych_gier)

    @app.route('/formula', methods=['GET', 'POST'])
    @login_required
    def formula():
        best = db.session.query(func.max(Formula.points)).filter(Formula.created_by == str(current_user.id)).scalar() or 0
        return render_template('formula.html', best=best)

    @app.route('/formula/save_score', methods=['POST'])
    @login_required
    def save_score_formula():
        data = request.get_json(silent=True, force=True) or {}
        try:
            score = max(0, int(data.get('score', 0)))
        except (TypeError, ValueError):
            return jsonify({'ok': False}), 400

        error = check_game_run('formula', score, data)
        if error:
            return jsonify({'ok': False, 'error': error}), 400

        new_game = Formula(points=score, created_by=current_user.id)
        db.session.add(new_game)
        db.session.commit()

        best = db.session.query(func.max(Formula.points)).filter(Formula.created_by == str(current_user.id)).scalar() or 0
        return jsonify({'ok': True, 'best': best})

    @app.route('/ranking_formula', methods=['GET', 'POST'])
    @login_required
    def ranking_formula():
        ranking_data, rozegranych_gier = game_ranking(Formula, true())
        return render_template('ranking_formula.html', ranking_data=ranking_data, rozegranych_gier=rozegranych_gier)

    @app.route('/gorka', methods=['GET', 'POST'])
    @login_required
    def gorka():
        best = db.session.query(func.max(Gorka.points)).filter(Gorka.created_by == str(current_user.id)).scalar() or 0
        return render_template('gorka.html', best=best)

    @app.route('/gorka/save_score', methods=['POST'])
    @login_required
    def save_score_gorka():
        data = request.get_json(silent=True, force=True) or {}
        try:
            score = max(0, int(data.get('score', 0)))
        except (TypeError, ValueError):
            return jsonify({'ok': False}), 400

        error = check_game_run('gorka', score, data)
        if error:
            return jsonify({'ok': False, 'error': error}), 400

        new_game = Gorka(points=score, created_by=current_user.id)
        db.session.add(new_game)
        db.session.commit()

        best = db.session.query(func.max(Gorka.points)).filter(Gorka.created_by == str(current_user.id)).scalar() or 0
        return jsonify({'ok': True, 'best': best})

    @app.route('/ranking_gorka', methods=['GET', 'POST'])
    @login_required
    def ranking_gorka():
        ranking_data, rozegranych_gier = game_ranking(Gorka, true())
        return render_template('ranking_gorka.html', ranking_data=ranking_data, rozegranych_gier=rozegranych_gier)

    return app
