
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
from sqlalchemy.exc import OperationalError
from flask import render_template, redirect, url_for, request
from flask_login import login_user, login_required, logout_user
from werkzeug.security import generate_password_hash, check_password_hash

from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, abort
from markupsafe import Markup
from flask_login import login_user, logout_user, login_required, current_user, LoginManager, UserMixin
from .forms import LoginForm, RegistrationForm
from itsdangerous import URLSafeTimedSerializer

from app.forms import AlbumForm, ImageForm, NewsForm, CalendarForm, UserSettingsForm, ReportForm, CommentForm, TestEmail, \
    ForgotPasswordForm, ResetPasswordForm, ChangePasswordForm, UpgradeForm

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
NOTIFY_KINDS = {'news', 'event', 'chat', 'photos', 'upgrade', 'tm', 'user'}
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
        __table_args__ = (db.UniqueConstraint('news_id', 'user_id', 'emoji'),)

    class Presence(db.Model):
        """Kiedy użytkownik ostatnio był na stronie kamery. W bazie, a nie w pamięci,
        bo każdy worker gunicorna ma własną pamięć i widziałby innych oglądających."""
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
        last_seen = db.Column(db.DateTime, nullable=False)
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

    class Tournament(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        event_id = db.Column(db.Integer, db.ForeignKey('calendar.id'))
        started = db.Column(db.Boolean, default=False)
        finished = db.Column(db.Boolean, default=False)
        advance = db.Column(db.Integer, nullable=False, default=2, server_default='2')  # ilu wychodzi z grupy: 2 albo 4

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

    @app.context_processor
    def inject_upgrade_badge():
        """Plakietka NOWE przy 'Ostatnie Ulepszenia' w menu, gdy jest świeży wpis."""
        latest = db.session.query(func.max(Upgrade.date)).scalar()
        return {'has_new_upgrade': bool(latest and latest >= datetime.utcnow() - timedelta(days=UPGRADE_NEW_DAYS)),
                'current_year': datetime.now().year,
                'report_statuses': REPORT_STATUSES}

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

    @app.route('/')
    def index():
        images=[]
        images.append("static\images\hlyw_1.png")
        images.append("static\images\hlyw_2.jpg")
        images.append("static\images\hlyw_3.jpg")
        images.append("static\images\hlyw_4.jpg")
        images.append("static\images\hlyw_5.jpg")
        images.append("static\images\hlyw_6.jpg")
        images.append("static\images\hlyw_7.jpg")
        images.append("static\images\hlyw_8.jpg")
        images.append("static\images\hlyw_9.jpg")
        images.append("static\images\hlyw_10.jpg")
        images.append("static\images\hlyw_11.jpg")
        images.append("static\images\hlyw_12.jpg")
        images.append("static\images\hlyw_13.jpg")
        images.append("static\images\hlyw_14.jpg")
        images.append("static\images\hlyw_15.jpg")
        images.append("static\images\hlyw_16.jpg")
        images.append("static\images\hlyw_17.jpg")
        images.append("static\images\hlyw_18.jpg")
        images.append("static\images\hlyw_19.jpg")
        images.append("static\images\hlyw_20.jpg")
        images.append("static\images\hlyw_21.jpg")
        images.append("static\images\hlyw_22.jpg")
        images.append("static\images\hlyw_23.jpg")


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
                login_user(user)
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
        return render_template('albums.html', album=all_album, images=images_no_album)

    @app.route('/albums/<int:album_id>')
    @login_required
    def album(album_id):
        album = Albums.query.get_or_404(album_id)
        images = Images.query.filter_by(album_id=album.id).order_by(Images.created_at).all()
        return render_template('album.html', album=album, images=images)

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

            image = Images(file_path=file_path, album_id=album_id)
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
                if p.user_id == current_user.id:
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
        return render_template('camera.html')

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
        if session.get('intro_seen') or request.method != 'GET' or request.blueprint or                 (request.endpoint or 'static') == 'static' or request.path.startswith('/api'):
            return {}
        session['intro_seen'] = True
        photo = Images.query.filter(db.or_(*[Images.file_path.ilike('%.' + ext) for ext in
                                             ('jpg', 'jpeg', 'png', 'webp')])).order_by(func.random()).first()
        return {'loading_screen': {'photo': photo.file_path if photo else 'static/images/hlyw_2.jpg',
                                   'tip': random.choice(LOADING_TIPS)}}

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
        if want('tm'):
            for t in TmTime.query.filter(TmTime.created_at > since).all():
                ev = Calendar.query.get(t.track.event_id)
                if ev:
                    add('tm', '🏁', t.user_id, f'Trackmania, trasa {t.track.name}: {format_tm_time(t.time_ms)}',
                        url_for('event', day=ev.date.day, month=ev.date.month, year=ev.date.year) + '#trackmania', t.created_at)
        if want('user'):
            for u in User.query.filter(User.confirmed_on > since).all():
                add('user', '👋', u.id, 'nowa osoba na Hlywie - witamy!', url_for('profil', user_id=u.id), u.confirmed_on)
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
        since = max(since, now - timedelta(hours=1))   # po długiej przerwie nie zalewamy starociami
        items = recent_activity(since, limit=5, kinds=NOTIFY_KINDS, exclude_user_id=current_user.id)
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
        presence = Presence.query.get(current_user.id) or Presence(user_id=current_user.id)
        presence.last_seen = datetime.utcnow()
        db.session.add(presence)
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
        advance = 4 if request.form.get("advance", type=int) == 4 else 2
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

    return app
