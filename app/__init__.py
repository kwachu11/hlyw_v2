
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
from markupsafe import Markup, escape
from flask_login import login_user, logout_user, login_required, current_user, LoginManager, UserMixin
from .forms import LoginForm, RegistrationForm
from itsdangerous import URLSafeTimedSerializer, URLSafeSerializer, BadSignature

from app.fifa_teams import FIFA_LEAGUES, FIFA_OTHER, FIFA_CLUB_MAX, club_league, resolve_club
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
import threading
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
# (klucz, typ, wartość domyślna, etykieta, grupa). Typy: bool, text, textarea, date (RRRR-MM-DD, puste = bez limitu), int,
# datetime (RRRR-MM-DDTGG:MM, czas polski = czas serwera).
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
    # licznik do wydarzenia (premiera, turniej...): przed datą odlicza, po niej pokazuje, ile minęło; też obrazek do maili
    ('gta6_on', 'bool', True, 'Pokazuj licznik', 'Licznik (premiera, turniej...)'),
    ('countdown_title', 'text', 'GTA VI', 'Nazwa - duży napis', 'Licznik (premiera, turniej...)'),
    ('countdown_at', 'datetime', '2026-11-19T00:00', 'Data i godzina (czas polski)', 'Licznik (premiera, turniej...)'),
    ('countdown_before', 'text', 'Do premiery zostało', 'Napis przed datą', 'Licznik (premiera, turniej...)'),
    ('countdown_after', 'text', 'GTA VI jest z nami już', 'Napis po dacie', 'Licznik (premiera, turniej...)'),
    ('countdown_note', 'text', 'Premiera 19.11.2026 o 00:00 · 🔴 dziś na kamerze stream z gry', 'Dopisek pod licznikiem',
     'Licznik (premiera, turniej...)'),
    ('countdown_link_text', 'text', 'oglądaj', 'Link w dopisku - napis (puste = bez linku)', 'Licznik (premiera, turniej...)'),
    ('countdown_link_url', 'text', '/camera', 'Link w dopisku - adres', 'Licznik (premiera, turniej...)'),
    ('countdown_home', 'bool', True, 'Na stronie głównej', 'Licznik (premiera, turniej...)'),
    ('countdown_camera', 'bool', True, 'Na stronie kamery', 'Licznik (premiera, turniej...)'),
    ('countdown_hide_days', 'int', 7, 'Schowaj po tylu dniach od daty', 'Licznik (premiera, turniej...)'),
    ('casino_on', 'bool', True, 'Kasyno otwarte (zamknięte widzi tylko admin)', 'Kasyno'),
    ('cash_per_hof_point', 'int', 100, 'Kasa $ za każdy punkt w Hall of Fame', 'Kasyno'),
    ('cash_per_game', 'int', 5, 'Kasa $ za każdą rozegraną grę', 'Kasyno'),
    ('casino_min_bet', 'int', 10, 'Najmniejsza stawka', 'Kasyno'),
    ('casino_max_bet', 'int', 1000000, 'Największa stawka (na jedno rozdanie / zakręcenie)', 'Kasyno'),
    ('poker_big_blind', 'int', 20, 'Poker: duża ciemna (mała = połowa; wpisowe 20-100 dużych ciemnych)', 'Kasyno'),
    ('casino_big_win', 'int', 1000, 'Wygrana od tylu $ trafia do „Co się dzieje” (0 = nigdy)', 'Kasyno'),
]

# Załączniki na czacie (jak na Messengerze): rodzaj -> rozszerzenia. Limit = client_max_body_size w nginx (50 MB).
CHAT_FILE_TYPES = {
    'image': {'jpg', 'jpeg', 'png', 'gif', 'webp', 'jfif', 'bmp'},
    'video': {'mp4', 'webm', 'mov', 'm4v'},
    'file': {'pdf', 'xls', 'xlsx', 'xlsm', 'csv', 'ods', 'doc', 'docx', 'odt', 'rtf', 'ppt', 'pptx', 'odp', 'txt',
             'zip', 'rar', '7z', 'stl', '3mf', 'obj', 'step', 'stp', 'mp3', 'wav', 'ogg', 'm4a', 'heic', 'apk', 'json', 'gpx'},
}
CHAT_FILE_MAX = 50 * 1024 * 1024 - 64 * 1024   # zapas na resztę formularza
CHAT_FILE_EXTENSIONS = {ext: kind for kind, exts in CHAT_FILE_TYPES.items() for ext in exts}
CHAT_REACTIONS = ['❤️', '😂', '😮', '😢', '😡', '👍']   # reakcje na wiadomości czatu (kolejność = w okienku wyboru)

# Rodzaje maili, które użytkownik może wyłączyć (ustawienia konta albo link z maila, bez logowania).
# Maile konta (potwierdzenie rejestracji, reset hasła) przychodzą zawsze.
MAIL_CATEGORIES = [
    ('mention', '💬 Oznaczenia na czacie', 'gdy ktoś oznaczy Cię na czacie przez @nick'),
    ('events', '📅 Wydarzenia i turnieje', 'zaproszenia na wydarzenia z kalendarza i turnieje FIFA'),
    ('news', '📰 Newsy i nowości', 'nowe newsy, albumy w galerii i ulepszenia strony'),
    ('other', '📣 Inne ogłoszenia', 'stream na kamerze, premiery, gry, druk 3D'),
]
MAIL_CATEGORY_KEYS = [key for key, _, _ in MAIL_CATEGORIES]
MAIL_CATEGORY_NAMES = {key: name for key, name, _ in MAIL_CATEGORIES}

# Oznaczenia @nick na czacie: mail do oznaczonego najwyżej raz na tyle czasu (wpis w MailLog o tym temacie).
CHAT_MENTION_COOLDOWN = timedelta(minutes=10)
CHAT_MENTION_LOG = 'czat-oznaczenie'

# Maile do użytkowników (/panel/maile). W temacie i treści: {nick}, {link_kamera}, {link_strona}.
MAIL_TEMPLATES = {
    'gta6_po': {
        'name': '🎮 GTA VI już jest - stream',
        'subject': 'GTA VI już jest - wbijaj na stream na hlyw.pl!',
        'body': '''<div style="background:#0d0d12;padding:24px;font-family:Arial,Helvetica,sans-serif;color:#eee">
<div style="max-width:560px;margin:0 auto;background:#17171f;border-radius:10px;overflow:hidden">
<div style="background:linear-gradient(90deg,#1fbf75,#0f8f9e,#ff2e88);padding:22px;text-align:center">
<div style="font-size:30px;font-weight:bold;color:#fff;letter-spacing:2px">GRAND THEFT AUTO VI</div>
<div style="color:#fff;font-size:15px;margin-top:4px">już jest! 🌴</div>
</div>
<div style="padding:22px;font-size:15px;line-height:1.6">
<p>Cześć <b>{nick}</b>!</p>
<p>Stało się - <b>GTA VI wyszło</b> 19.11.2026 o północy. Tyle czasu już gramy:</p>
<p style="text-align:center;margin:18px 0"><img src="{link_strona}gta6/licznik.gif" width="516" alt="Licznik od premiery GTA VI" style="max-width:100%;height:auto;border-radius:8px;display:block;margin:0 auto"></p>
<p>Na kamerze hlyw.pl leci <b>stream z gry</b> - wbijaj oglądać i pisz na czacie (możesz oznaczyć znajomych przez <b>@nick</b>).</p>
<p style="text-align:center;margin:26px 0">
<a href="{link_kamera}" style="background:#ff2e88;color:#fff;text-decoration:none;padding:12px 26px;border-radius:6px;font-weight:bold;display:inline-block">🔴 Oglądaj stream</a>
</p>
<p>Jeśli w nocy przyszedł już do Ciebie od nas mail o premierze - sorry za powtórkę, serwer się zadyszał. 😅</p>
<p>Do zobaczenia w Vice City!<br>Ekipa hlyw.pl</p>
</div>
<div style="padding:12px 22px;font-size:12px;color:#888;border-top:1px solid #2a2a35">Dostajesz tę wiadomość, bo masz konto na <a href="{link_strona}" style="color:#ff9d2e">hlyw.pl</a>. <a href="{link_ustawienia}" style="color:#ff9d2e">Zmień, jakie maile dostajesz</a>.</div>
</div></div>''',
    },
    'gta6': {
        'name': '🎮 GTA VI - zaproszenie na stream',
        'subject': 'GTA VI wychodzi o północy - oglądamy razem na hlyw.pl!',
        'body': '''<div style="background:#0d0d12;padding:24px;font-family:Arial,Helvetica,sans-serif;color:#eee">
<div style="max-width:560px;margin:0 auto;background:#17171f;border-radius:10px;overflow:hidden">
<div style="background:linear-gradient(90deg,#ff2e88,#ff9d2e);padding:22px;text-align:center">
<div style="font-size:30px;font-weight:bold;color:#fff;letter-spacing:2px">GRAND THEFT AUTO VI</div>
<div style="color:#fff;font-size:15px;margin-top:4px">premiera 19.11.2026 o 00:00</div>
</div>
<div style="padding:22px;font-size:15px;line-height:1.6">
<p>Cześć <b>{nick}</b>!</p>
<p>Czekaliśmy na to latami - <b>dziś o północy wychodzi GTA VI</b>. 🌴🚗</p>
<p style="text-align:center;margin:18px 0"><img src="{link_strona}gta6/licznik.gif" width="516" alt="Licznik premiery GTA VI" style="max-width:100%;height:auto;border-radius:8px;display:block;margin:0 auto"></p>
<p>Na kamerze hlyw.pl leci <b>stream z gry</b>, więc wbijaj oglądać razem z nami. Na stronie jest licznik, ile zostało do premiery, a potem - ile już gramy.</p>
<p style="text-align:center;margin:26px 0">
<a href="{link_kamera}" style="background:#ff2e88;color:#fff;text-decoration:none;padding:12px 26px;border-radius:6px;font-weight:bold;display:inline-block">🔴 Oglądaj stream</a>
</p>
<p>Do zobaczenia w Vice City!<br>Ekipa hlyw.pl</p>
</div>
<div style="padding:12px 22px;font-size:12px;color:#888;border-top:1px solid #2a2a35">Dostajesz tę wiadomość, bo masz konto na <a href="{link_strona}" style="color:#ff9d2e">hlyw.pl</a>. <a href="{link_ustawienia}" style="color:#ff9d2e">Zmień, jakie maile dostajesz</a>.</div>
</div></div>''',
    },
    'news': {
        'category': 'news',
        'name': '📰 Nowość na stronie',
        'subject': 'Coś nowego na hlyw.pl',
        'body': '''<div style="font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.6;color:#222">
<p>Cześć <b>{nick}</b>!</p>
<p>Na hlyw.pl pojawiło się coś nowego: ...</p>
<p><a href="{link_strona}">Wejdź na hlyw.pl</a></p>
<p>Ekipa hlyw.pl</p>
</div>''',
    },
    'pusty': {'name': '✏️ Pusty', 'subject': '', 'body': '<p>Cześć <b>{nick}</b>!</p>\n<p></p>'},
}
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
                                 '/formula', '/gorka', '/skok'), None),
    'camera': ('Kamera', 'camera', ('/camera',), None),
    'calendar': ('Kalendarz', 'calendar', ('/calendar', '/add_entry', '/event'), None),
    'hof': ('🏆 Hall of Fame', 'hall_of_fame', ('/hall_of_fame', '/profil'), None),
    'upgrades': ('Ostatnie Ulepszenia', 'ostatnie_ulepszenia', ('/ostatnie-ulepszenia',), 'upgrade'),
    'quiz': ('🧠 Quiz', 'quiz', ('/quiz',), 'quiz'),
    'activity': ('⚡ Ostatnia aktywność', 'activity', ('/aktywnosc',), None),
    'casino': ('🎰 Kasyno', 'casino', ('/kasyno',), None),
    'print': ('🖨️ Druk 3D', 'print_list', ('/druk3d',), 'print'),
    'reports': ('Zgłoszenia', 'view_report_list', ('/report',), None),
    'users': ('Użytkownicy', 'users', ('/users',), None),
}
MENU_DEFAULT_LAYOUT = [{'key': k} for k in ('home', 'albums', 'news', 'games', 'camera', 'calendar', 'hof', 'upgrades', 'quiz')] + \
    [{'group': 'Dodatki', 'items': [{'key': k} for k in ('casino', 'activity', 'print', 'reports', 'users')]}]
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
FILAMENT_ANY, FILAMENT_OTHER, FILAMENT_KEEP = 'obojetnie', 'inny', 'obecny'   # specjalne wartości wyboru w formularzu
FILAMENT_FROM_FILE = 'plik'      # „kolory jak w pliku 3MF”
FILAMENT_MAX = 8                 # najwięcej filamentów w jednej propozycji (wydruki wielokolorowe)   # każdy worker gunicorna trzyma ustawienia tyle sekund
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
    'skok': (0, 0),            # Turbo Skok sprawdza czas przejazdu osobno (SKOK_TRACKS), punkty liczy serwer
}
# Turbo Skok - wyścig platformowy na czas. Trasy (układ w templates/skok.html): klucz -> (nazwa, czas wzorcowy ms,
# najkrótszy możliwy czas ms). Punkty za przejazd = 1000 * wzorcowy / czas (szybciej = więcej), najwyżej 3000.
SKOK_TRACKS = {
    'rozgrzewka': ('Rozgrzewka', 12000, 3500),     # czasy wzorcowe z przejazdów bota (6,6-11 s zależnie od postaci)
    'lodowisko': ('Lodowisko', 18000, 5000),
    'wiezowce': ('Wieżowce', 16000, 4500),
    'tor_smierci': ('Tor śmierci', 24000, 7000),
}
SKOK_STAT_POINTS = 150           # punkty do rozdzielenia na prędkość / przyspieszenie / skok (każda 0-100)
SKOK_COLORS = ['#ffcc00', '#5ab0f2', '#ff4d6d', '#6fd26f', '#ff9d2e', '#b07cff', '#ffffff', '#ff7ad9']
SKOK_RACE_MAX = 4                # graczy w jednym wyścigu
SKOK_COUNTDOWN = 4               # s od startu do „START!”
SKOK_AUTOSTART = 20              # s od dołączenia drugiej osoby do samoczynnego startu
SKOK_AFTER_FIRST = 45            # s po pierwszym na mecie wyścig się kończy
SKOK_RACE_MAX_TIME = 300         # najdłużej trwa wyścig (s)
SKOK_RACER_TIMEOUT = 12          # bez synchronizacji tyle s = gracz wyszedł
SKOK_GHOST_STEP_MS = 50          # duch = pozycja co tyle ms
SKOK_GHOST_MAX = 6000            # najwyżej 5 minut przejazdu
# Kasyno (/kasyno): wirtualne żetony bez żadnej wartości. Losuje i liczy wszystko serwer.
CASINO_GAMES = {'blackjack': '🃏 Blackjack', 'ruletka': '🎡 Ruletka', 'bakarat': '🎴 Bakarat', 'poker': '♠ Poker'}
# Poker Texas Hold'em (No-Limit) - jeden wspólny stół. Wpisowe w dużych ciemnych, czas na ruch, przerwa po rozdaniu.
POKER_SEATS = 6
POKER_BUYIN_BB = (20, 100)
POKER_TURN_SECONDS = 25
POKER_START_SECONDS = 4          # od chwili, gdy są 2 gotowe osoby, do rozdania
POKER_PAUSE_SECONDS = 7          # po rozdaniu - pokazanie kart i wyników
POKER_TIMEOUTS_OUT = 2           # tyle przekroczeń czasu z rzędu = „nieobecny” (nie dostaje kart)
POKER_OUT_KICK_SECONDS = 180     # nieobecny tyle czasu - wstaje od stołu, żetony wracają do portfela
POKER_HANDS = ['Wysoka karta', 'Para', 'Dwie pary', 'Trójka', 'Strit', 'Kolor', 'Full', 'Kareta', 'Poker']
CASINO_BLACKJACK_DECKS = 6
CASINO_BLACKJACK_MAX_HANDS = 4       # po rozdzieleniach (split)
ROULETTE_WHEEL = [0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10, 5, 24, 16, 33, 1, 20, 14,
                  31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26]   # kolejność pól na kole europejskim
ROULETTE_RED = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
CASINO_LIVE_ROWS = 20                    # „na żywo”: tyle ostatnich zakładów wszystkich graczy
CASINO_LIVE_SEEN = timedelta(seconds=45) # kto tyle czasu temu odświeżał kasyno, jest „przy stołach”
CASINO_LIVE_OWN_DELAY = timedelta(seconds=6)   # własny zakład pojawia się po animacji (koło kręci się ~5 s)
ROULETTE_MAX_BETS = 160
# Wspólna ruletka: runda co ROULETTE_ROUND s (numer rundy = sekundy od 1970 // 30). Zakłady do ROULETTE_CLOSE s rundy,
# wynik losowany dopiero od ROULETTE_SETTLE s (sekunda zapasu na zakład, który właśnie się zapisuje), potem koło się kręci.
ROULETTE_ROUND, ROULETTE_CLOSE, ROULETTE_SETTLE = 30, 24, 25
# split = zakład na dwa sąsiednie pola stołu (17:1): obok siebie w rzędzie, jedno pod drugim, 0 z 1/2/3
ROULETTE_SPLITS = {(0, 1), (0, 2), (0, 3)} | {(n, n + 1) for n in range(1, 37) if n % 3} | {(n, n + 3) for n in range(1, 34)}
# zakłady na kilka numerów: rodzaj -> (dozwolone zestawy, ile razy stawka wraca razem ze stawką)
ROULETTE_GROUPS = {
    'split': (ROULETTE_SPLITS, 18),                                                          # 2 numery, 17:1
    'street': ({(n, n + 1, n + 2) for n in range(1, 35, 3)}, 12),                            # rząd 3 numerów, 11:1
    'corner': ({(n, n + 1, n + 3, n + 4) for n in range(1, 33) if n % 3}, 9),                # 4 w rogu, 8:1
    'sixline': ({tuple(range(n, n + 6)) for n in range(1, 32, 3)}, 6),                       # dwa rzędy, 5:1
}
# Kasa w stylu GTA (pasek w menu): za punkt w rankingu ogólnym Hall of Fame i za każdą rozegraną grę -
# stawki ustawia admin w /panel (SITE_SETTINGS cash_per_hof_point / cash_per_game, grupa „Kasyno”).
# "Gwiazdki poszukiwania" (1-5) za aktywność z ostatnich 7 dni: punkty za akcję i progi gwiazdek
WANTED_DAYS = 7
WANTED_WEIGHTS = {'gry': 1, 'czat': 2, 'zdjęcia': 1, 'newsy': 5, 'komentarze': 2, 'wydarzenia': 5}
WANTED_THRESHOLDS = [1, 15, 40, 100, 200]
# Ekran ładowania jak w GTA V (raz na sesję przeglądarki): losowe zdjęcie z galerii + wskazówka
LOADING_TIPS = [
    'Pobij rekord w dowolnej grze, a dostaniesz „misja zaliczona” i kasę na koncie.',
    'TOP 3 rankingu ogólnego Hall of Fame nosi koronę przy nicku.',
    'Za punkty w Hall of Fame i za każdą rozegraną grę wpada kasa $ - wydasz ją w kasynie.',
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
    # Wyścigi Turbo Skoku na żywo zapisują pozycje graczy kilka razy na sekundę - osobny plik bazy obok głównej
    # (np. instance/baza_wyscigi.db), żeby te zapisy nie blokowały reszty strony.
    main_uri = app.config['SQLALCHEMY_DATABASE_URI']
    race_uri = re.sub(r'(\.db)?$', '_wyscigi.db', main_uri, count=1) if main_uri.startswith('sqlite:///') \
        else 'sqlite:///' + os.path.join(base_dir, 'instance', 'wyscigi.db')
    app.config['SQLALCHEMY_BINDS'] = {'wyscigi': {'url': race_uri, 'connect_args': {'timeout': 10}}}
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
        mail_prefs = db.Column(db.Text)      # JSON: lista wyłączonych rodzajów maili (MAIL_CATEGORIES); puste = wszystkie

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
        # załącznik (instance/czat): zdjęcie, film albo dowolny obsługiwany plik - CHAT_FILE_TYPES
        file_path = db.Column(db.String(200))
        file_name = db.Column(db.String(200))
        file_kind = db.Column(db.String(10))      # image / video / file
        file_size = db.Column(db.Integer)
        reply_to_id = db.Column(db.Integer)      # odpowiedź na wiadomość (cytat nad tekstem)

    class ChatReaction(db.Model):
        """Reakcja na wiadomość czatu - jedna na osobę i wiadomość (jak na Messengerze)."""
        __tablename__ = 'chat_reaction'
        id = db.Column(db.Integer, primary_key=True)
        message_id = db.Column(db.Integer, db.ForeignKey('message.id'), nullable=False, index=True)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        emoji = db.Column(db.String(16), nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        __table_args__ = (db.UniqueConstraint('message_id', 'user_id'),)

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
        filaments = db.Column(db.Text)              # JSON [{material, name, hex, file}] - wszystkie wybrane kolory
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

    class PrintPhotoLike(db.Model):
        """Polubienie zdjęcia wydruku (❤), jak w galerii."""
        __tablename__ = 'print_photo_like'
        id = db.Column(db.Integer, primary_key=True)
        photo_id = db.Column(db.Integer, db.ForeignKey('print_photo.id'), nullable=False, index=True)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        __table_args__ = (db.UniqueConstraint('photo_id', 'user_id'),)

    class MailLog(db.Model):
        """Dziennik maili z /panel/maile: kto dostał (albo nie) wiadomość o danym temacie."""
        __tablename__ = 'mail_log'
        id = db.Column(db.Integer, primary_key=True)
        subject = db.Column(db.String(200), nullable=False, index=True)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        ok = db.Column(db.Boolean, default=True)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)

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

    class Skok(db.Model):
        """Przejazd Turbo Skoku. points/created_at/created_by jak w innych grach (Hall of Fame, kasa za grę),
        do tego trasa, czas i duch (pozycje co SKOK_GHOST_STEP_MS) - duch tylko przy rekordzie gracza na trasie."""
        id = db.Column(db.Integer, primary_key=True)
        points = db.Column(db.Integer)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        created_by = db.Column(db.String(500))
        track = db.Column(db.String(20), nullable=False, index=True)
        time_ms = db.Column(db.Integer, nullable=False)
        ghost = db.Column(db.Text)

    class SkokProfile(db.Model):
        """Postać w Turbo Skoku: statystyki (suma najwyżej SKOK_STAT_POINTS) i kolor."""
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
        speed = db.Column(db.Integer, nullable=False, default=50)
        accel = db.Column(db.Integer, nullable=False, default=50)
        jump = db.Column(db.Integer, nullable=False, default=50)
        color = db.Column(db.String(7), nullable=False, default='#ffcc00')

    class SkokRace(db.Model):
        """Wyścig na żywo (osobna baza 'wyscigi'). Czasy jako sekundy od 1970 (time.time())."""
        __bind_key__ = 'wyscigi'
        id = db.Column(db.Integer, primary_key=True)
        course = db.Column(db.String(20), nullable=False)
        status = db.Column(db.String(10), nullable=False, default='lobby')   # lobby / count / run / done
        host_id = db.Column(db.Integer, nullable=False)
        created_at = db.Column(db.Float, nullable=False)
        auto_at = db.Column(db.Float)          # samoczynny start (gdy są 2+ osoby)
        start_at = db.Column(db.Float)         # chwila „START!”
        end_at = db.Column(db.Float)
        recorded = db.Column(db.Boolean, nullable=False, default=False)

    class SkokRacer(db.Model):
        __bind_key__ = 'wyscigi'
        race_id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(150), nullable=False)
        photo = db.Column(db.String(200))
        color = db.Column(db.String(7), nullable=False)
        stats = db.Column(db.String(100), nullable=False)
        state = db.Column(db.Text)             # pozycja, prędkość, przedmiot... (JSON z gry)
        seen = db.Column(db.Float, nullable=False)
        finish_ms = db.Column(db.Integer)

    class SkokEvent(db.Model):
        """Zdarzenia wyścigu dla innych graczy: mina, wybuch miny, laser."""
        __bind_key__ = 'wyscigi'
        id = db.Column(db.Integer, primary_key=True)
        race_id = db.Column(db.Integer, nullable=False, index=True)
        user_id = db.Column(db.Integer, nullable=False)
        kind = db.Column(db.String(10), nullable=False)
        data = db.Column(db.String(300))
        at = db.Column(db.Float, nullable=False)

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

    class CasinoWallet(db.Model):
        """Portfel kasyna. balance = wynik w kasynie od 21.11.2026 (wygrane - stawki, może być na minusie);
        kasa do gry = kasa z gier (user_cash, jak w menu) + balance. Do tego trwające rozdanie blackjacka (JSON)."""
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
        balance = db.Column(db.Integer, nullable=False, default=0)
        daily_date = db.Column(db.Date, nullable=True)
        streak = db.Column(db.Integer, nullable=False, default=0)
        blackjack = db.Column(db.Text, nullable=True)
        seen_at = db.Column(db.DateTime, nullable=True)        # ostatnio na /kasyno - lista „przy stołach”
        seen_game = db.Column(db.String(20), nullable=True)    # przy którym stole (zakładka)
        user = db.relationship('User')

    class CasinoBet(db.Model):
        """Jedna rozegrana runda (albo odebrane dzienne: game='dzienne', bet=0) - historia, ranking, aktywność."""
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
        game = db.Column(db.String(20), nullable=False)
        bet = db.Column(db.Integer, nullable=False, default=0)
        payout = db.Column(db.Integer, nullable=False, default=0)
        details = db.Column(db.String(300))
        created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
        user = db.relationship('User')

    class PokerTable(db.Model):
        """Wspólny stół pokera: cały stan w JSON (miejsca, rozdanie, talia). version = blokada optymistyczna -
        zapis tylko, gdy nikt w międzyczasie nie zmienił stołu (kilka workerów gunicorna)."""
        id = db.Column(db.Integer, primary_key=True, autoincrement=False)
        state = db.Column(db.Text, nullable=False)
        version = db.Column(db.Integer, nullable=False, default=0)

    class RouletteRound(db.Model):
        """Wynik rundy wspólnej ruletki; id = numer rundy. Wiersz powstaje raz (klucz główny) - razem z wypłatami."""
        id = db.Column(db.Integer, primary_key=True, autoincrement=False)
        number = db.Column(db.Integer, nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)

    class RouletteBet(db.Model):
        """Zakład we wspólnej ruletce (stawka zdjęta z portfela od razu, wypłata przy rozliczeniu rundy)."""
        id = db.Column(db.Integer, primary_key=True)
        round_id = db.Column(db.Integer, nullable=False, index=True)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        kind = db.Column(db.String(10), nullable=False)
        value = db.Column(db.String(30), nullable=False, default='')   # '17', '17-20', '2' (tuzin), '' (kolor)
        amount = db.Column(db.Integer, nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        user = db.relationship('User')

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

        # baza wyścigów: tryb WAL (czytanie nie czeka na zapisy pozycji graczy); ustawienie zostaje w pliku bazy
        try:
            with db.engines['wyscigi'].connect() as conn:
                conn.exec_driver_sql('PRAGMA journal_mode=WAL')
        except Exception as e:      # np. inny worker właśnie to robi - spróbuje następny start
            app.logger.warning('Baza wyścigów - WAL: %s', e)

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
            ('print_request', 'filaments', "TEXT"),
            ('message', 'file_path', "VARCHAR(200)"),
            ('message', 'file_name', "VARCHAR(200)"),
            ('message', 'file_kind', "VARCHAR(10)"),
            ('message', 'file_size', "INTEGER"),
            ('message', 'reply_to_id', "INTEGER"),
            ('user', 'mail_prefs', "TEXT"),
            ('casino_wallet', 'seen_at', "DATETIME"),
            ('casino_wallet', 'seen_game', "VARCHAR(20)"),
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

        # 21.11.2026: kasyno przechodzi z darmowych dziennych żetonów na kasę $ z gier - raz zerujemy portfele
        # (na prośbę usera bez zwrotu): saldo, rozdania blackjacka, nierozliczone zakłady ruletki, stół pokera.
        # Flaga w site_setting (klucz główny) - robi to tylko jeden worker i tylko raz.
        if not db.session.get(SiteSetting, 'casino_cash_reset'):
            try:
                db.session.add(SiteSetting(key='casino_cash_reset', value='1'))
                CasinoWallet.query.update({CasinoWallet.balance: 0, CasinoWallet.blackjack: None}, synchronize_session=False)
                settled = db.session.query(RouletteRound.id)
                RouletteBet.query.filter(~RouletteBet.round_id.in_(settled)).delete(synchronize_session=False)
                PokerTable.query.delete(synchronize_session=False)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()

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


    @app.url_defaults
    def static_version(endpoint, values):
        """Wersja pliku w adresie: url_for('static', ...) -> /static/css/gta.css?v=<czas zmiany pliku>.
        Cloudflare każe przeglądarce trzymać pliki statyczne 4 h, więc bez tego po wdrożeniu nowy HTML
        dostawał stary CSS/JS. Zmieniony plik = nowy adres = od razu świeża wersja."""
        # tylko CSS i JS - czcionka z preload musi mieć ten sam adres co w CSS (url('fonts/...') bez wersji)
        if endpoint == 'static' and str(values.get('filename', '')).endswith(('.css', '.js')) and 'v' not in values:
            try:
                values['v'] = int(os.stat(os.path.join(app.static_folder, values['filename'])).st_mtime)
            except (OSError, ValueError):
                pass

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

    def countdown_info():
        """Licznik z panelu (grupa „Licznik”): teksty i moment w ms od 1970 - data z panelu to czas serwera (polski)."""
        s = site_settings()
        try:
            at = datetime.fromisoformat(s['countdown_at'])
        except (TypeError, ValueError):
            return None
        return {'title': s['countdown_title'], 'at': at, 'ms': int(at.timestamp() * 1000),
                'before': s['countdown_before'], 'after': s['countdown_after'], 'note': s['countdown_note'],
                'link_text': s['countdown_link_text'], 'link_url': s['countdown_link_url'],
                'hide_days': max(1, s['countdown_hide_days'])}

    app.jinja_env.globals['countdown_info'] = countdown_info

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
                    if kind == 'datetime':
                        try:
                            value = datetime.fromisoformat(value).strftime('%Y-%m-%dT%H:%M')
                        except ValueError:
                            flash(f'„{label}”: zła data lub godzina - zostawiam poprzednią wartość.', 'warning')
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
            taken_clubs = {}          # klub (małymi literami) -> kto go ma - w formularzu zajęte są wyszarzone
            my_fifa = None
            for fp in fifa_participants:
                user = User.query.get(fp.user_id)
                participants_names.append({
                    "username": user.username,
                    "role": fp.role,
                    "club": fp.club,
                    "league": club_league(fp.club) if fp.club else None,
                })
                if fp.role == "player" and fp.club:
                    taken_clubs[fp.club.strip().lower()] = user.username
                if fp.user_id == current_user.id:
                    czy_zapisany = True
                    my_fifa = fp

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
            fifa_leagues=FIFA_LEAGUES if fifa_mode else [], fifa_other=FIFA_OTHER,
            taken_clubs=taken_clubs if fifa_mode else {}, my_fifa=my_fifa if fifa_mode else None,
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

    def bambu_cache_path(task_id, kind):
        """Plik z obrazkiem zadania z chmury Bambu na dysku (instance/bambu_cache) - okładka i zdjęcie po wydruku
        już się nie zmieniają, więc każdy pobieramy z Bambu tylko raz."""
        return os.path.join(app.instance_path, 'bambu_cache', f'{int(task_id)}_{kind}')

    def send_bambu_image(path):
        with open(path, 'rb') as f:
            head = f.read(3)
        resp = send_file(path, mimetype='image/jpeg' if head == b'\xff\xd8\xff' else 'image/png', max_age=7 * 24 * 3600)
        return resp

    @app.route('/api/drukarka/okladka')
    @login_required
    def drukarka_okladka():
        # obrazek wydruku z chmury Bambu - okładka (render z slicera) albo zdjęcie po wydruku (?rodzaj=zdjecie),
        # po id albo nazwie zadania; token zostaje po stronie serwera, a pobrane obrazki - na dysku
        import urllib.request as _ur
        kind = 'zdjecie' if request.args.get('rodzaj') == 'zdjecie' else 'okladka'
        field = 'snapShot' if kind == 'zdjecie' else 'cover'
        tid = (request.args.get('id') or '').strip()
        if tid.isdigit() and os.path.exists(bambu_cache_path(tid, kind)):
            return send_bambu_image(bambu_cache_path(tid, kind))     # bez pytania chmury o listę zadań
        data = _bambu_tasks_data()
        if data is None:
            abort(404)
        hits = data.get('hits', []) or []
        name = (request.args.get('name') or '').strip().lower()
        task = None
        for h in hits:
            if tid and str(h.get('id')) == tid:
                task = h; break
            if not tid and name and (h.get('title') or '').strip().lower() == name:
                task = h; break
        if task is None and not tid and not name and hits:
            task = hits[0]                        # fallback: najnowsze
        url = task and task.get(field)
        if not url:
            abort(404)
        path = bambu_cache_path(task['id'], kind)
        if not os.path.exists(path):
            try:
                img = _ur.urlopen(_ur.Request(url, headers={'User-Agent': 'hlyw-camera/1.0'}), timeout=10).read(5 * 1024 * 1024)
            except Exception:
                abort(502)
            create_directory_if_not_exists(os.path.dirname(path))
            tmp = path + '.' + uuid.uuid4().hex + '.tmp'      # kilka workerów naraz - zapis przez plik tymczasowy
            with open(tmp, 'wb') as f:
                f.write(img)
            os.replace(tmp, path)
        return send_bambu_image(path)

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
            new_message = Message(content=message_content[:500], user_id=user_id, reply_to_id=chat_reply_target(data.get('reply_to')))
            db.session.add(new_message)
            db.session.commit()
            mentioned = notify_chat_mentions(message_content)
            return jsonify({"status": "success", "message": message_content, "mentioned": mentioned})
        return jsonify({"status": "error"}), 400

    def chat_file_caption(name):
        """Treść wiadomości z samym plikiem - widać ją na stronie głównej, w „Co się dzieje” i w powiadomieniach."""
        return ('📎 ' + (name or 'plik'))[:500]

    @app.route('/czat/plik', methods=['POST'])
    @login_required
    def chat_upload():
        """Wiadomość na czacie z załącznikiem (zdjęcie, film, Excel, PDF, ...) i opcjonalnym tekstem."""
        upload = request.files.get('file')
        text = (request.form.get('message') or '').strip()[:500]
        if not upload or not upload.filename:
            return jsonify({"status": "error", "error": "Nie wybrano pliku."}), 400
        original = os.path.basename(upload.filename.replace('\\', '/')).strip()[:150] or 'plik'
        ext = original.rsplit('.', 1)[-1].lower() if '.' in original else ''
        kind = CHAT_FILE_EXTENSIONS.get(ext)
        if not kind:
            return jsonify({"status": "error", "error": f'Tego typu pliku (.{ext or "?"}) nie obsługujemy.'}), 400
        upload.stream.seek(0, os.SEEK_END)
        size = upload.stream.tell()
        upload.stream.seek(0)
        if size > CHAT_FILE_MAX:
            return jsonify({"status": "error", "error": "Plik jest za duży - maksymalnie 50 MB."}), 400
        if not size:
            return jsonify({"status": "error", "error": "Plik jest pusty."}), 400
        folder = os.path.join(app.instance_path, 'czat')
        create_directory_if_not_exists(folder)
        stored = uuid.uuid4().hex + '.' + ext        # nazwy od użytkownika nie używamy na dysku
        upload.save(os.path.join(folder, stored))
        message = Message(content=text or chat_file_caption(original), user_id=current_user.id,
                          file_path=stored, file_name=original, file_kind=kind, file_size=size,
                          reply_to_id=chat_reply_target(request.form.get('reply_to')))
        db.session.add(message)
        db.session.commit()
        mentioned = notify_chat_mentions(text) if text else []
        return jsonify({"status": "success", "mentioned": mentioned})

    def chat_file_disk_path(message):
        if not message.file_path or '/' in message.file_path or '\\' in message.file_path:
            abort(404)
        path = os.path.join(app.instance_path, 'czat', message.file_path)
        if not os.path.exists(path):
            abort(404)
        return path

    @app.route('/czat/plik/<int:message_id>')
    @login_required
    def chat_file(message_id):
        """Załącznik z czatu: zdjęcia i filmy w przeglądarce (z przewijaniem filmu), resztę pobiera się pod oryginalną nazwą."""
        message = Message.query.get_or_404(message_id)
        path = chat_file_disk_path(message)
        inline = message.file_kind in ('image', 'video')
        response = send_file(path, as_attachment=not inline, download_name=message.file_name or message.file_path,
                             conditional=True, max_age=7 * 24 * 3600)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    @app.route('/czat/plik/<int:message_id>/miniatura')
    @login_required
    def chat_file_thumbnail(message_id):
        message = Message.query.get_or_404(message_id)
        if message.file_kind != 'image':
            abort(404)
        path = chat_file_disk_path(message)
        thumb = thumbnail_path(f'c{message.id}')
        if not os.path.exists(thumb):
            create_directory_if_not_exists(os.path.dirname(thumb))
            try:
                save_jpeg_thumbnail(path, thumb)
            except Exception as e:
                app.logger.warning('Nie udało się utworzyć miniatury załącznika %s: %s', message.id, e)
                return redirect(url_for('chat_file', message_id=message.id))
        return send_file(thumb, mimetype='image/jpeg', max_age=30 * 24 * 3600)

    def chat_mentions(content):
        """Użytkownicy oznaczeni w wiadomości przez @nick (nicki mogą mieć spacje - najpierw najdłuższe)."""
        text, found = content, []
        for user in sorted(User.query.filter(User.id != current_user.id).all(), key=lambda u: -len(u.username)):
            pattern = re.compile('@' + re.escape(user.username) + r'(?!\w)', re.IGNORECASE)
            if pattern.search(text):
                found.append(user)
                text = pattern.sub(' ', text)       # krótszy nick nie złapie się wewnątrz dłuższego
        return found

    def notify_chat_mentions(content):
        """Mail „ktoś oznaczył Cię na czacie” - w tle, każdemu najwyżej raz na CHAT_MENTION_COOLDOWN."""
        users = chat_mentions(content)
        if not users:
            return []
        since = datetime.utcnow() - CHAT_MENTION_COOLDOWN
        recent = {row.user_id for row in MailLog.query.filter(MailLog.subject == CHAT_MENTION_LOG, MailLog.ok.is_(True),
                                                              MailLog.created_at >= since)}
        root = request.url_root
        if 'hlyw.pl' in root:
            root = 'https://hlyw.pl/'
        jobs = []
        for user in users:
            address = (user.email or '').strip()
            if not user.confirmed or not address or user.id in recent or not wants_mail(user, 'mention'):
                continue
            prefs = mail_prefs_url(user, root, 'mention')
            html = render_template('mail_oznaczenie.html', nick=user.username, author=current_user.username,
                                   content=content, camera_url=root + 'camera', site_url=root, prefs_url=prefs)
            jobs.append((user.id, address, f'{current_user.username} oznacza Cię na czacie hlyw.pl', html, prefs))
        if jobs:
            threading.Thread(target=send_mail_jobs, args=(jobs, CHAT_MENTION_LOG), daemon=True).start()
        return [u.username for u in users]

    @app.route('/czat/uzytkownicy')
    @login_required
    def chat_users():
        """Nicki do podpowiedzi @oznaczeń na czacie."""
        return jsonify({"users": sorted((u.username for u in User.query.filter(User.confirmed.is_(True))), key=str.lower)})

    @app.route('/get_messages')
    @login_required
    def get_messages():
        # Pobierz wszystkie wiadomości z bazy danych
        messages = Message.query.order_by(Message.timestamp.desc()).limit(30).all()
        messages_data = []
        ids = [m.id for m in messages]
        reactions = chat_reaction_summary(ids)
        # cytowane wiadomości (mogą być starsze niż ostatnie 30)
        quoted = {m.id: m for m in Message.query.filter(Message.id.in_({m.reply_to_id for m in messages if m.reply_to_id}))}

        for msg in messages:
            reply = None
            original = quoted.get(msg.reply_to_id)
            if original:
                reply = {"id": original.id, "username": original.user.username,
                         "text": chat_snippet(original)}
            user = msg.user  # Dostęp do użytkownika powiązanego z wiadomością
            place = standings().get(user.id, {}).get('place')
            attachment = None
            if msg.file_path:
                attachment = {"name": msg.file_name, "kind": msg.file_kind, "size": msg.file_size,
                              "url": url_for('chat_file', message_id=msg.id),
                              "thumb": url_for('chat_file_thumbnail', message_id=msg.id) if msg.file_kind == 'image' else None,
                              # sam podpis „📎 nazwa” (wiadomość bez tekstu) nie jest pokazywany drugi raz
                              "auto_text": msg.content == chat_file_caption(msg.file_name)}
            messages_data.append({
                "id": msg.id,
                "file": attachment,
                "reply": reply,
                "reactions": reactions.get(msg.id, []),
                "content": msg.content,
                "timestamp": msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                "time": when_label(msg.timestamp),
                "username": user.username,  # Dodajemy nazwę użytkownika
                "crown": place if place and place <= 3 else None,  # korona TOP 1-3 Hall of Fame
                "photo": user.photo  # Dodajemy zdjęcie użytkownika
            })

        return jsonify({"messages": messages_data, "reaction_choices": CHAT_REACTIONS})

    def chat_snippet(message, length=90):
        """Krótki fragment wiadomości do cytatu w odpowiedzi."""
        text = (message.content or '').replace('\n', ' ').strip()
        return text if len(text) <= length else text[:length - 1].rstrip() + '…'

    def chat_reply_target(value):
        """Id wiadomości, na którą ktoś odpowiada - tylko jeśli taka istnieje."""
        try:
            message_id = int(value)
        except (TypeError, ValueError):
            return None
        return message_id if db.session.get(Message, message_id) else None

    def chat_reaction_summary(message_ids):
        """{id wiadomości: [{emoji, count, mine, users}]} w kolejności CHAT_REACTIONS."""
        if not message_ids:
            return {}
        rows = (db.session.query(ChatReaction, User.username).join(User, User.id == ChatReaction.user_id)
                .filter(ChatReaction.message_id.in_(message_ids)).order_by(ChatReaction.created_at).all())
        grouped = {}
        for reaction, username in rows:
            item = grouped.setdefault(reaction.message_id, {}).setdefault(
                reaction.emoji, {"emoji": reaction.emoji, "count": 0, "mine": False, "users": []})
            item["count"] += 1
            item["users"].append(username)
            item["mine"] = item["mine"] or reaction.user_id == current_user.id
        order = {e: i for i, e in enumerate(CHAT_REACTIONS)}
        return {mid: sorted(items.values(), key=lambda r: order.get(r["emoji"], 99)) for mid, items in grouped.items()}

    @app.route('/czat/reakcja', methods=['POST'])
    @login_required
    def chat_react():
        """Reakcja na wiadomość: ta sama drugi raz = cofnięcie, inna = zamiana (jedna na osobę)."""
        data = request.get_json(silent=True) or {}
        emoji = data.get('emoji')
        message = db.session.get(Message, data.get('message_id') if isinstance(data.get('message_id'), int) else -1)
        if not message or emoji not in CHAT_REACTIONS:
            return jsonify({"status": "error"}), 400
        existing = ChatReaction.query.filter_by(message_id=message.id, user_id=current_user.id).first()
        if existing and existing.emoji == emoji:
            db.session.delete(existing)
        elif existing:
            existing.emoji = emoji
            existing.created_at = datetime.utcnow()
        else:
            db.session.add(ChatReaction(message_id=message.id, user_id=current_user.id, emoji=emoji))
        try:
            db.session.commit()
        except IntegrityError:          # podwójne kliknięcie - druga próba dodania tej samej reakcji
            db.session.rollback()
        return jsonify({"status": "success", "reactions": chat_reaction_summary([message.id]).get(message.id, [])})

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
    app.jinja_env.globals['chat_file_extensions'] = sorted(CHAT_FILE_EXTENSIONS)   # załączniki na czacie (camera.html)
    app.jinja_env.globals['chat_file_max'] = CHAT_FILE_MAX
    app.jinja_env.globals['chat_reactions'] = CHAT_REACTIONS
    app.jinja_env.globals['mail_categories'] = MAIL_CATEGORIES                 # ustawienia maili (user_settings.html)
    app.jinja_env.globals['mail_disabled_for'] = lambda user: mail_disabled(user)

    @app.template_global('print_thumb_url')
    def print_thumb_url(entry):
        """Adres miniatury z pliku; ?v= zmienia się razem z miniaturą (np. po edycji), więc nie wisi stara z pamięci."""
        if not entry.thumb_path:
            return None
        return url_for('print_thumbnail', request_id=entry.id, v=hashlib.md5(entry.thumb_path.encode()).hexdigest()[:8])

    def decode_paint_state(token):
        """Kolorowanie trójkąta w 3MF z Bambu/Orca (paint_color): '4' = filament 1, '8' = 2, '0C' = 3, '1C' = 4...
        Dłuższe ciągi to podzielone trójkąty - pomijamy, ich kolory i tak są w prostych."""
        token = token.upper()
        if len(token) == 1 and token in '48':
            return int(token, 16) >> 2
        if len(token) == 2 and token[1] == 'C' and token[0] in '0123456789ABCDEF':
            return 3 + int(token[0], 16)
        return None

    def read_3mf_info(path):
        """Ustawienia z pliku 3MF zapisanego w Bambu Studio / Orca: warstwa, ścianki, wypełnienie, podpory, dysza,
        drukarka, UŻYTE filamenty (z przypisania obiektów i kolorowania), a jeśli plik był pocięty - czas i gramy.
        Wynik w kształcie profilu z MakerWorld (source='3mf'); None, gdy plik nie ma ustawień."""
        try:
            with zipfile.ZipFile(path) as z:
                names = z.namelist()
                if 'Metadata/project_settings.config' not in names:
                    return None
                ps = json.loads(z.read('Metadata/project_settings.config'))
                colors = [str(c) for c in ps.get('filament_colour') or []]
                types = [str(t) for t in ps.get('filament_type') or []]
                used = set()
                if 'Metadata/model_settings.config' in names:
                    text = z.read('Metadata/model_settings.config').decode('utf-8', 'ignore')
                    used.update(int(v) for v in re.findall(r'key="extruder" value="(\d+)"', text))
                for name in names:
                    info = z.getinfo(name)
                    if name.startswith('3D/') and name.endswith('.model') and info.file_size <= 400 * 1024 * 1024:
                        with z.open(name) as f:
                            for chunk in iter(lambda: f.read(8 * 1024 * 1024), b''):
                                for token in set(re.findall(rb'paint_color="([0-9A-Fa-f]{1,2})"', chunk)):
                                    state = decode_paint_state(token.decode())
                                    if state:
                                        used.add(state)
                slice_xml = z.read('Metadata/slice_info.config').decode('utf-8', 'ignore') \
                    if 'Metadata/slice_info.config' in names else ''
        except Exception as e:
            app.logger.warning('Nie udało się odczytać ustawień z 3MF %s: %s', path, e)
            return None
        used = sorted(i for i in used or {1} if 1 <= i <= len(colors)) or ([1] if colors else [])
        seconds = grams = 0
        plates, used_g = [], {}
        for plate in re.findall(r'<plate>(.*?)</plate>', slice_xml, re.S):     # tylko w pociętym pliku
            meta = dict(re.findall(r'<metadata key="(\w+)" value="([^"]*)"', plate))
            s, g = to_number(meta.get('prediction'), int), to_number(meta.get('weight'))
            seconds, grams = seconds + s, grams + g
            plates.append({'seconds': s, 'grams': g, 'image': ''})
            for fid, fg in re.findall(r'<filament id="(\d+)"[^>]*used_g="([\d.]+)"', plate):
                used_g[int(fid)] = used_g.get(int(fid), 0) + to_number(fg)
        nozzle = (ps.get('nozzle_diameter') or [None])[0] if isinstance(ps.get('nozzle_diameter'), list) else ps.get('nozzle_diameter')
        return {
            'source': '3mf', 'title': ' '.join(str(ps.get('print_settings_id') or 'Plik 3MF').split())[:150],
            'seconds': seconds, 'grams': round(grams, 1), 'plates': plates if len(plates) > 1 else [],
            'filaments': [{'type': types[i - 1] if i <= len(types) else '', 'color': colors[i - 1],
                           'grams': round(used_g.get(i, 0), 1)} for i in used],
            'ams': len(used) > 1, 'printer': str(ps.get('printer_model') or '').replace('Bambu Lab ', '')[:30],
            'nozzle': nozzle,
            'settings': {k: str(v) for k, v in (('layerHeight', ps.get('layer_height')), ('wallLoops', ps.get('wall_loops')),
                                                 ('sparseInfillDensity', ps.get('sparse_infill_density')),
                                                 ('enableSupport', ps.get('enable_support'))) if v not in (None, '')},
        }

    def print_file_profile(stored):
        """Profil z wgranego pliku 3MF (po czyszczeniu jak profile z MakerWorld) albo None."""
        if not stored or not stored.lower().endswith('.3mf'):
            return None
        info = read_3mf_info(print_file_path(stored))
        return (clean_profiles([info]) or [None])[0] if info else None

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
            from_file = p.get('source') == '3mf'
            if not (0 <= seconds if from_file else 0 < seconds) or seconds >= 30 * 24 * 3600 or not 0 <= grams < 100000:
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
            profiles.append({'source': '3mf' if from_file else 'makerworld',
                             'title': ' '.join(str(p.get('title') or '').split())[:150], 'seconds': seconds,
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
            elif not request.form.getlist('filament'):
                flash('Wybierz filament z listy.', 'danger')
            else:
                stored = None
                if upload:
                    stored = uuid.uuid4().hex + '.' + ext
                    create_directory_if_not_exists(os.path.dirname(print_file_path(stored)))
                    upload.save(print_file_path(stored))
                file_profile = print_file_profile(stored)          # 3MF: ustawienia, kolory, czas z pliku
                chosen = apply_filament(request.form.getlist('filament'), file_profile=file_profile)
                if not chosen:
                    if stored:
                        remove_print_file(stored)
                    flash('Wybierz filament z listy.', 'danger')
                    return render_template('druk3d_nowa.html', form=form, max_mb=PRINT_MAX_MB, source=source, entry=None,
                                           filaments=filament_groups(), filament_selected=request.form.getlist('filament'),
                                           file_colors=None)
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
                profile = file_profile
                if link:
                    try:
                        profile = (clean_profiles([json.loads(request.form.get('profile') or 'null')]) or [None])[0]
                    except ValueError:
                        profile = None
                material, color, color_hex, filament_items = chosen
                model_info = None
                if link:
                    try:
                        model_info = clean_model_info(json.loads(request.form.get('model_info') or 'null'))
                    except ValueError:
                        model_info = None
                entry = PrintRequest(thumb_path=thumb, gallery=json.dumps(gallery) if gallery else None, color_hex=color_hex,
                                     filaments=json.dumps(filament_items, ensure_ascii=False) if filament_items else None,
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
                               filaments=filament_groups(), filament_selected=request.form.getlist('filament') or [FILAMENT_ANY],
                               file_colors=None)

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

    @app.template_global('print_filaments')
    def request_filaments(entry):
        """Wszystkie kolory propozycji [{material, name, hex, file}] - starsze propozycje mają jeden (material/color)."""
        try:
            items = json.loads(entry.filaments) if entry.filaments else None
        except ValueError:
            items = None
        if isinstance(items, list) and items:
            return items
        return [{'material': entry.material, 'name': entry.color, 'hex': print_color_hex(entry), 'file': False}]

    def filament_choice(entry):
        """Które opcje formularza odpowiadają propozycji (przy edycji) - lista wartości."""
        items = request_filaments(entry)
        if entry.material == 'Obojętnie' and entry.color == 'Obojętnie':
            return [FILAMENT_ANY]
        if any(i.get('file') for i in items):
            return [FILAMENT_FROM_FILE]
        chosen = []
        for i in items:
            if i.get('material') == 'Inny':
                chosen.append(FILAMENT_OTHER)
                continue
            f = Filament.query.filter_by(material=i.get('material'), name=i.get('name')).first()
            if not f or f.status == 'ukryty':
                return [FILAMENT_KEEP]          # coś spoza dzisiejszej listy - zostaje „Bez zmian”
            chosen.append(str(f.id))
        return chosen or [FILAMENT_KEEP]

    def apply_filament(values, entry=None, file_profile=None):
        """Wybór z formularza (jedna albo kilka wartości) -> (materiał, kolor, hex, lista kolorów); None, gdy zły.
        file_profile - profil z pliku 3MF, z którego bierzemy kolory przy „Kolory jak w pliku”."""
        values = [v for v in (values if isinstance(values, list) else [values]) if v]
        if not values:
            return None
        if FILAMENT_ANY in values:
            return 'Obojętnie', 'Obojętnie', None, []
        if FILAMENT_KEEP in values and entry is not None:
            return entry.material, entry.color, entry.color_hex, request_filaments(entry)
        items = []
        if FILAMENT_FROM_FILE in values:
            if not file_profile or not file_profile.get('filaments'):
                return None
            for f in file_profile['filaments'][:FILAMENT_MAX]:
                hex_ = clean_hex(f.get('color'))
                items.append({'material': f.get('type') or 'PLA', 'name': color_name_from_hex(hex_) if hex_ else 'Kolor z pliku',
                              'hex': hex_, 'file': True})
        else:
            for v in values:
                if v == FILAMENT_OTHER:
                    continue
                f = db.session.get(Filament, int(v)) if v.isdigit() else None
                if not f or f.status == 'ukryty':
                    return None
                if not any(i['material'] == f.material and i['name'] == f.name for i in items):
                    items.append({'material': f.material, 'name': f.name, 'hex': f.hex, 'file': False})
            if FILAMENT_OTHER in values:
                items.append({'material': 'Inny', 'name': 'Inny (opisz w uwagach)', 'hex': None, 'file': False})
        if not items or len(items) > FILAMENT_MAX:
            return None
        materials = list(dict.fromkeys(i['material'] for i in items))
        return (' + '.join(materials)[:100], ' + '.join(i['name'] for i in items)[:200],
                next((i['hex'] for i in items if i['hex']), None), items)

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
            chosen = None if not request.form.getlist('filament') else True    # właściwy wybór niżej, po ewentualnym nowym pliku
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
                        entry.print_profile = None                       # profil z poprzedniego pliku nie pasuje
                    file_profile = print_file_profile(entry.file_path)
                    if file_profile:
                        entry.print_profile = json.dumps(file_profile)
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
                chosen = apply_filament(request.form.getlist('filament'), entry,
                                        file_profile=print_file_profile(entry.file_path) if source == 'plik' else None)
                if not chosen:
                    db.session.rollback()
                    flash('Wybierz filament z listy.', 'danger')
                    return redirect(url_for('print_edit', request_id=entry.id))
                entry.quality, entry.quantity = form.quality.data, form.quantity.data
                entry.material, entry.color, entry.color_hex, filament_items = chosen
                entry.filaments = json.dumps(filament_items, ensure_ascii=False) if filament_items else None
                db.session.commit()
                flash('Zmiany zapisane.', 'success')
                return redirect(url_for('print_detail', request_id=entry.id))
        return render_template('druk3d_nowa.html', form=form, max_mb=PRINT_MAX_MB, source=source,
                               filaments=filament_groups(), filament_selected=request.form.getlist('filament') or filament_choice(entry),
                               file_colors=[f['color'] for f in (print_file_profile(entry.file_path) or {}).get('filaments', [])],
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
                               photo_likes=print_photo_likes([ph.id for ph in entry.photos]),
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
        for path in (os.path.join(app.root_path, photo.file_path.replace('\\', '/')), thumbnail_path('p' + str(photo.id))):
            try:
                if os.path.exists(path):
                    os.remove(path)
            except OSError as e:          # np. plik akurat otwarty - zdjęcie i tak znika z bazy
                app.logger.warning('Nie udało się usunąć pliku %s: %s', path, e)

    @app.template_global('print_photo_url')
    def print_photo_url(entry):
        """Miniatura najnowszego zdjęcia gotowego wydruku (na listę propozycji zamiast renderu); None, gdy nie ma."""
        photo = next((ph for ph in reversed(entry.photos) if ph.kind == 'wydruk'), None)
        return url_for('print_photo_thumbnail', photo_id=photo.id) if photo else None

    @app.route('/miniatura/druk/<int:photo_id>')
    @login_required
    def print_photo_thumbnail(photo_id):
        """Miniatura zdjęcia wydruku (480 px) do siatki i listy - pełne zdjęcie dopiero w przeglądarce zdjęć."""
        photo = PrintPhoto.query.get_or_404(photo_id)
        return send_thumbnail('p' + str(photo.id), photo.file_path)

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

    def print_photo_likes(photo_ids):
        """{photo_id: {'count', 'mine', 'who'}} - jak image_likes w galerii."""
        result = {i: {'count': 0, 'mine': False, 'who': []} for i in photo_ids}
        if photo_ids:
            rows = db.session.query(PrintPhotoLike.photo_id, PrintPhotoLike.user_id, User.username) \
                .join(User, User.id == PrintPhotoLike.user_id).filter(PrintPhotoLike.photo_id.in_(photo_ids)) \
                .order_by(PrintPhotoLike.created_at).all()
            for photo_id, user_id, username in rows:
                r = result[photo_id]
                r['count'] += 1
                r['mine'] = r['mine'] or user_id == current_user.id
                r['who'].append(username)
        for r in result.values():
            r['who'] = ', '.join(r['who'])
        return result

    @app.route('/druk3d/zdjecie/<int:photo_id>/like', methods=['POST'])
    @login_required
    def like_print_photo(photo_id):
        """Przełącza ❤ pod zdjęciem wydruku."""
        PrintPhoto.query.get_or_404(photo_id)
        existing = PrintPhotoLike.query.filter_by(photo_id=photo_id, user_id=current_user.id).first()
        if existing:
            db.session.delete(existing)
        else:
            db.session.add(PrintPhotoLike(photo_id=photo_id, user_id=current_user.id))
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
        return jsonify({'status': 'success', **print_photo_likes([photo_id])[photo_id]})

    @app.route('/druk3d/zdjecie/<int:photo_id>/usun', methods=['POST'])
    @login_required
    def print_photo_delete(photo_id):
        photo = PrintPhoto.query.get_or_404(photo_id)
        request_id = photo.request_id
        if current_user.is_admin == "0" and photo.created_by != current_user.id:
            flash('Usunąć zdjęcie może ten, kto je dodał, albo admin.', 'danger')
        else:
            remove_print_photo_file(photo)
            PrintPhotoLike.query.filter_by(photo_id=photo.id).delete()
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
                PrintPhotoLike.query.filter_by(photo_id=photo.id).delete()
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
        skok_leader = Skok.query.order_by(Skok.points.desc()).first()
        user8 = User.query.filter_by(id=skok_leader.created_by).first() if skok_leader else None
        games.append(['Turbo Skok', 'static/images/skok.svg', skok_leader, user8, 'skok', 'ranking_skok'])
        # games.append(['Pod Górkę', 'static/images/gorka.svg', gorka_leader, user7, 'gorka', 'ranking_gorka'])
        casino_leader = None
        if site_settings()['casino_on']:
            top = CasinoWallet.query.filter(CasinoWallet.balance > 0).order_by(CasinoWallet.balance.desc()).first()
            casino_leader = top if top and top.user else None
        return render_template('games.html', games=games, casino_on=site_settings()['casino_on'], casino_leader=casino_leader)

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
            ('Turbo Skok', Skok, 'skok', False),
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
        return render_template('profil.html', profile_user=user, stats=stats, profile_cash=user_money(user.id),
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
        per_point, per_game = max(0, site_settings()['cash_per_hof_point']), max(0, site_settings()['cash_per_game'])
        for entry in result.values():
            entry['cash'] = per_point * entry['points'] + per_game * entry['games']
        standings_cache.update(at=time.time(), data=result)
        return result

    def user_cash(user_id):
        """Kasa zarobiona w grach: za punkty Hall of Fame i za rozegrane gry."""
        return standings().get(user_id, {}).get('cash', 0)

    def user_money(user_id):
        """Kasa na pasku w menu = zarobiona w grach + wynik w kasynie (wygrane i przegrane)."""
        wallet = db.session.get(CasinoWallet, user_id)
        return user_cash(user_id) + (wallet.balance if wallet else 0)

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
        return {'my_cash': user_money(current_user.id),
                'cash_per_point': site_settings()['cash_per_hof_point'], 'cash_per_game': site_settings()['cash_per_game']}

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

    # ===================== Kasyno (blackjack, ruletka, bakarat) =====================
    # Żetony są wirtualne. Karty i liczby losuje serwer (SystemRandom), przeglądarka tylko pokazuje wynik.
    # Saldo zmienia się jednym UPDATE ... WHERE (np. balance >= stawka), więc podwójne kliknięcie
    # albo dwie karty przeglądarki nie zrobią salda na minusie ani dwóch wypłat.

    casino_rng = random.SystemRandom()
    CARD_RANKS, CARD_SUITS = 'A23456789TJQK', 'SHDC'

    def casino_guard():
        """None = można grać; inaczej gotowa odpowiedź (kasyno zamknięte w panelu - admin wchodzi zawsze)."""
        if site_settings()['casino_on'] or current_user.is_admin != "0":
            return None
        if request.method == 'GET':
            flash('Kasyno jest teraz zamknięte.', 'info')
            return redirect(url_for('index'))
        return jsonify({'ok': False, 'error': 'Kasyno jest teraz zamknięte.'}), 403

    def casino_limits():
        s = site_settings()
        low = max(1, s['casino_min_bet'])
        return low, max(low, s['casino_max_bet'])

    def casino_wallet(user_id):
        wallet = db.session.get(CasinoWallet, user_id)
        if wallet is None:
            try:
                db.session.add(CasinoWallet(user_id=user_id, balance=0, streak=0))
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
            wallet = db.session.get(CasinoWallet, user_id)
        return wallet

    def casino_update(user_id, values, *conditions):
        """Atomowa zmiana portfela; True, gdy warunki pasowały (False = za mało żetonów / ktoś był szybszy)."""
        return CasinoWallet.query.filter(CasinoWallet.user_id == user_id, *conditions) \
            .update(values, synchronize_session=False) == 1

    def casino_record(user_id, game, bet, payout, text):
        db.session.add(CasinoBet(user_id=user_id, game=game, bet=bet, payout=payout, details=text[:300]))

    def casino_error(message, status=400, **extra):
        return jsonify({'ok': False, 'error': message, **extra}), status

    def casino_money(user_id, wallet=None):
        """Kasa do gry w kasynie = kasa z gier (Hall of Fame + rozegrane gry, jak w menu) + wynik w kasynie."""
        wallet = wallet or casino_wallet(user_id)
        return user_cash(user_id) + wallet.balance

    def casino_can_pay(user_id, amount):
        """Warunek do UPDATE: po zdjęciu `amount` kasa do gry nie spadnie poniżej zera."""
        return CasinoWallet.balance >= amount - user_cash(user_id)

    def casino_state(user_id):
        wallet = casino_wallet(user_id)
        hand = json.loads(wallet.blackjack) if wallet.blackjack else None
        return {'balance': casino_money(user_id, wallet), 'blackjack': bj_view(hand) if hand else None}

    def casino_history(user_id, limit=12):
        rows = CasinoBet.query.filter_by(user_id=user_id).order_by(CasinoBet.id.desc()).limit(limit).all()
        return [casino_bet_json(b) for b in rows]

    def casino_bet_json(b):
        return {'game': CASINO_GAMES.get(b.game, '🎁 Dzienne żetony'), 'bet': b.bet, 'payout': b.payout,
                'net': b.payout - b.bet, 'text': b.details or '', 'when': when_label(b.created_at)}

    def card_points(card):
        """Blackjack: A = 11 (albo 1), figury = 10."""
        return 11 if card[0] == 'A' else 10 if card[0] in 'TJQK' else int(card[0])

    def new_shoe(decks):
        shoe = [r + s for r in CARD_RANKS for s in CARD_SUITS] * decks
        casino_rng.shuffle(shoe)
        return shoe

    def bj_value(cards):
        """(suma, czy miękka - as liczony za 11)."""
        total, aces = 0, 0
        for card in cards:
            total += card_points(card)
            aces += card[0] == 'A'
        while total > 21 and aces:
            total, aces = total - 10, aces - 1
        return total, aces > 0

    def bj_natural(hand):
        return len(hand['cards']) == 2 and not hand.get('split') and bj_value(hand['cards'])[0] == 21

    def bj_actions(state):
        if state.get('over'):
            return {}
        hand = state['hands'][state['active']]
        two = len(hand['cards']) == 2
        return {'hit': True, 'stand': True, 'double': two and not hand.get('doubled'),
                'split': two and card_points(hand['cards'][0]) == card_points(hand['cards'][1])
                and len(state['hands']) < CASINO_BLACKJACK_MAX_HANDS}

    def bj_progress(state):
        """Przechodzi do następnej ręki gracza; gdy wszystkie skończone - krupier dobiera i rozliczenie."""
        hands, dealer, shoe = state['hands'], state['dealer'], state['shoe']
        for hand in hands:
            if bj_value(hand['cards'])[0] >= 21:
                hand['done'] = True
        while state['active'] < len(hands) and hands[state['active']]['done']:
            state['active'] += 1
        if state['active'] < len(hands):
            return state
        state['active'] = len(hands) - 1
        dealer_bj = len(dealer) == 2 and bj_value(dealer)[0] == 21
        if not dealer_bj and any(bj_value(h['cards'])[0] <= 21 and not bj_natural(h) for h in hands):
            while bj_value(dealer)[0] < 17:          # krupier stoi na każdej 17
                dealer.append(shoe.pop())
        dealer_total = bj_value(dealer)[0]
        for hand in hands:
            value, bet, natural = bj_value(hand['cards'])[0], hand['bet'], bj_natural(hand)
            if value > 21:
                hand['result'], hand['payout'] = 'bust', 0
            elif natural and dealer_bj:
                hand['result'], hand['payout'] = 'push', bet
            elif natural:
                hand['result'], hand['payout'] = 'blackjack', bet + bet * 3 // 2
            elif dealer_bj or (dealer_total <= 21 and value < dealer_total):
                hand['result'], hand['payout'] = 'lose', 0
            elif dealer_total > 21 or value > dealer_total:
                hand['result'], hand['payout'] = 'win', bet * 2
            else:
                hand['result'], hand['payout'] = 'push', bet
        state['over'] = True
        return state

    def bj_view(state):
        """Rozdanie do przeglądarki - bez buta z kartami i z zakrytą drugą kartą krupiera w trakcie."""
        over = bool(state.get('over'))
        dealer = state['dealer'] if over else state['dealer'][:1] + ['??']
        return {'over': over, 'dealer': dealer, 'dealer_value': bj_value(state['dealer'] if over else state['dealer'][:1])[0],
                'active': state['active'], 'actions': bj_actions(state),
                'hands': [{'cards': h['cards'], 'bet': h['bet'], 'value': bj_value(h['cards'])[0],
                           'soft': bj_value(h['cards'])[1], 'result': h.get('result'), 'payout': h.get('payout')}
                          for h in state['hands']],
                'payout': sum(h.get('payout') or 0 for h in state['hands']) if over else None}

    def bj_summary(state):
        names = {'bust': 'fura', 'push': 'remis', 'blackjack': 'BLACKJACK', 'lose': 'przegrana', 'win': 'wygrana'}
        hands = ', '.join(f'{bj_value(h["cards"])[0]} ({names[h["result"]]})' for h in state['hands'])
        return f'Ty {hands} · krupier {bj_value(state["dealer"])[0]}'

    @app.route('/kasyno')
    @login_required
    def casino():
        blocked = casino_guard()
        if blocked:
            return blocked
        low, high = casino_limits()
        return render_template('kasyno.html', state=casino_state(current_user.id), history=casino_history(current_user.id),
                               min_bet=low, max_bet=high, wheel=ROULETTE_WHEEL, red=sorted(ROULETTE_RED),
                               top=casino_top_wins(current_user.id),
                               roulette=roulette_state(current_user.id),
                               roulette_times=[ROULETTE_ROUND, ROULETTE_CLOSE, ROULETTE_SETTLE])

    @app.route('/kasyno/blackjack', methods=['POST'])
    @login_required
    def casino_blackjack():
        blocked = casino_guard()
        if blocked:
            return blocked
        data = request.get_json(silent=True) or {}
        action = data.get('action')
        wallet = casino_wallet(current_user.id)
        raw = wallet.blackjack
        state = json.loads(raw) if raw else None
        extra = 0                                     # ile żetonów jeszcze zdjąć (stawka, podwojenie, split)
        if action == 'deal':
            if state:
                return casino_error('Najpierw dokończ rozdanie.', blackjack=bj_view(state))
            low, high = casino_limits()
            try:
                bet = int(data.get('bet'))
            except (TypeError, ValueError):
                return casino_error('Podaj stawkę.')
            if not low <= bet <= high:
                return casino_error(f'Stawka od {money(low)} do {money(high)} $.')
            shoe = new_shoe(CASINO_BLACKJACK_DECKS)
            player, dealer = [shoe.pop()], [shoe.pop()]
            player.append(shoe.pop())
            dealer.append(shoe.pop())
            state = {'shoe': shoe, 'dealer': dealer, 'active': 0,
                     'hands': [{'cards': player, 'bet': bet, 'done': False}]}
            extra = bet
            # krupier zagląda pod kartę: blackjack u niego albo u gracza kończy rozdanie od razu
            if bj_value(dealer)[0] == 21 or bj_natural(state['hands'][0]):
                state['hands'][0]['done'] = True
            state = bj_progress(state)
            condition = CasinoWallet.blackjack.is_(None)
        elif action in ('hit', 'stand', 'double', 'split'):
            if not state:
                return casino_error('Nie ma trwającego rozdania.')
            if not bj_actions(state).get(action):
                return casino_error('Tego teraz nie można zrobić.', blackjack=bj_view(state))
            hand = state['hands'][state['active']]
            shoe = state['shoe']
            if action == 'hit':
                hand['cards'].append(shoe.pop())
            elif action == 'stand':
                hand['done'] = True
            elif action == 'double':
                extra = hand['bet']
                hand.update(bet=hand['bet'] * 2, doubled=True, done=True)
                hand['cards'].append(shoe.pop())
            else:
                extra = hand['bet']
                first, second = hand['cards']
                aces = first[0] == 'A'
                new = [{'cards': [first, shoe.pop()], 'bet': hand['bet'], 'done': aces, 'split': True},
                       {'cards': [second, shoe.pop()], 'bet': hand['bet'], 'done': aces, 'split': True}]
                state['hands'][state['active']:state['active'] + 1] = new   # rozdzielone asy dostają po jednej karcie
            state = bj_progress(state)
            condition = CasinoWallet.blackjack == raw
        else:
            return casino_error('Nieznany ruch.')

        payout = sum(h.get('payout') or 0 for h in state['hands']) if state.get('over') else 0
        if not casino_update(current_user.id,
                             {CasinoWallet.balance: CasinoWallet.balance - extra + payout,
                              CasinoWallet.blackjack: None if state.get('over') else json.dumps(state)},
                             condition, casino_can_pay(current_user.id, extra)):
            db.session.rollback()
            message = 'Za mało kasy - zarób ją w grach.' if casino_money(current_user.id) < extra \
                else 'Rozdanie zmieniło się w innym oknie - odświeżam.'
            return casino_error(message, **casino_state(current_user.id))
        if state.get('over'):
            casino_record(current_user.id, 'blackjack', sum(h['bet'] for h in state['hands']), payout, bj_summary(state))
        db.session.commit()
        result = {'ok': True, **casino_state(current_user.id), 'blackjack': bj_view(state)}
        if state.get('over'):
            result['history'] = casino_history(current_user.id)
        return jsonify(result)

    def roulette_multiplier(kind, value, number):
        """Ile razy stawka wraca (razem ze stawką) przy wyniku number; 0 = zakład przegrany."""
        if kind == 'n':
            return 36 if number == value else 0
        if kind in ROULETTE_GROUPS:
            return ROULETTE_GROUPS[kind][1] if number in value else 0
        if number == 0:
            return 0
        won = {'red': number in ROULETTE_RED, 'black': number not in ROULETTE_RED,
               'odd': number % 2 == 1, 'even': number % 2 == 0, 'low': number <= 18, 'high': number >= 19,
               'dozen': (number - 1) // 12 + 1 == value, 'column': (number - 1) % 3 + 1 == value}[kind]
        return (3 if kind in ('dozen', 'column') else 2) if won else 0

    def roulette_value(kind, raw):
        """Zakład z przeglądarki / bazy -> (wartość do wypłaty, tekst do zapisu); ValueError, gdy zakład jest zły."""
        if kind in ROULETTE_GROUPS:      # numery po myślniku, np. split '17-20', róg '17-18-20-21'
            value = tuple(sorted(int(x) for x in str(raw).split('-')))
            if value not in ROULETTE_GROUPS[kind][0]:
                raise ValueError
            return value, '-'.join(map(str, value))
        if kind in ('n', 'dozen', 'column'):
            value = int(raw)
            if not (0 <= value <= 36 if kind == 'n' else 1 <= value <= 3):
                raise ValueError
            return value, str(value)
        if kind in ('red', 'black', 'odd', 'even', 'low', 'high'):
            return None, ''
        raise ValueError

    def roulette_color(number):
        return 'zielone' if number == 0 else 'czerwone' if number in ROULETTE_RED else 'czarne'

    def roulette_resolve(rnd):
        """Losuje wynik rundy i wypłaca wszystkim - w jednej transakcji z wierszem rundy, więc tylko raz
        (drugi worker dostaje IntegrityError na kluczu głównym i nic nie robi)."""
        number = casino_rng.randrange(37)
        try:
            db.session.add(RouletteRound(id=rnd, number=number))
            db.session.flush()
        except IntegrityError:
            db.session.rollback()
            return
        per_user = {}
        for b in RouletteBet.query.filter_by(round_id=rnd).all():
            stake, payout = per_user.get(b.user_id, (0, 0))
            try:
                won = b.amount * roulette_multiplier(b.kind, roulette_value(b.kind, b.value)[0], number)
            except ValueError:
                won = b.amount      # nie powinno się zdarzyć - stawka wraca
            per_user[b.user_id] = (stake + b.amount, payout + won)
        for user_id, (stake, payout) in per_user.items():
            if payout:
                casino_update(user_id, {CasinoWallet.balance: CasinoWallet.balance + payout})
            casino_record(user_id, 'ruletka', stake, payout, f'wypadło {number} ({roulette_color(number)})')
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()

    def roulette_settle():
        """Rozlicza rundy po zamknięciu zakładów - leniwie, przy pytaniu kogokolwiek z kasyna.
        Bieżąca runda dostaje wynik nawet bez zakładów (koło kręci się dla oglądających)."""
        now = time.time()
        rnd = int(now // ROULETTE_ROUND)
        due = rnd if now >= rnd * ROULETTE_ROUND + ROULETTE_SETTLE else rnd - 1
        waiting = {r for (r,) in db.session.query(RouletteBet.round_id)
                   .outerjoin(RouletteRound, RouletteRound.id == RouletteBet.round_id)
                   .filter(RouletteRound.id.is_(None), RouletteBet.round_id <= due).distinct()}
        if not db.session.get(RouletteRound, due):
            waiting.add(due)
        for r in sorted(waiting):
            roulette_resolve(r)

    def roulette_bet_json(b, user_id):
        return {'user': b.user.username, 'photo': avatar_url(b.user.photo), 'me': b.user_id == user_id,
                'user_id': b.user_id, 't': b.kind, 'v': b.value, 'a': b.amount}

    def roulette_state(user_id):
        """Stół dla przeglądarki: zegar rundy, zakłady wszystkich w bieżącej rundzie, wynik ostatniej i kto ile wygrał."""
        roulette_settle()
        now = time.time()
        rnd = int(now // ROULETTE_ROUND)
        start = rnd * ROULETTE_ROUND
        bets = RouletteBet.query.filter_by(round_id=rnd).order_by(RouletteBet.id).all()
        last = RouletteRound.query.filter(RouletteRound.id <= rnd).order_by(RouletteRound.id.desc()).first()
        last_json = None
        if last:
            results = {}
            last_bets = RouletteBet.query.filter_by(round_id=last.id).all()
            for b in last_bets:
                r = results.setdefault(b.user_id, {'user': b.user.username, 'photo': avatar_url(b.user.photo),
                                                   'me': b.user_id == user_id, 'stake': 0, 'payout': 0, 'straight': False})
                won = b.amount * roulette_multiplier(b.kind, roulette_value(b.kind, b.value)[0], last.number)
                r['stake'] += b.amount
                r['payout'] += won
                r['straight'] = r['straight'] or (b.kind == 'n' and won > 0)
            rows = sorted(results.values(), key=lambda r: -(r['payout'] - r['stake']))
            last_json = {'round': last.id, 'number': last.number, 'color': roulette_color(last.number), 'results': rows,
                         'bets': [roulette_bet_json(b, user_id) for b in last_bets]}
        return {'round': rnd, 'now_ms': int(now * 1000), 'open': now < start + ROULETTE_CLOSE,
                'bets': [roulette_bet_json(b, user_id) for b in bets], 'last': last_json,
                'recent': [r.number for r in RouletteRound.query.order_by(RouletteRound.id.desc()).limit(12)]}

    @app.route('/kasyno/ruletka/stan')
    @login_required
    def casino_roulette_state():
        blocked = casino_guard()
        if blocked:
            return blocked
        result = {'ok': True, 'roulette': roulette_state(current_user.id), 'balance': casino_money(current_user.id)}
        if request.args.get('historia'):
            result['history'] = casino_history(current_user.id)
        return jsonify(result)

    @app.route('/kasyno/ruletka', methods=['POST'])
    @login_required
    def casino_roulette():
        """Zakład do bieżącej rundy wspólnej ruletki (można dokładać kilka razy, póki zakłady są otwarte)."""
        blocked = casino_guard()
        if blocked:
            return blocked
        now = time.time()
        rnd = int(now // ROULETTE_ROUND)
        if now >= rnd * ROULETTE_ROUND + ROULETTE_CLOSE:
            return casino_error('Zakłady zamknięte - poczekaj na następną rundę.', roulette=roulette_state(current_user.id))
        raw_bets = (request.get_json(silent=True) or {}).get('bets')
        if not isinstance(raw_bets, list) or not 0 < len(raw_bets) <= ROULETTE_MAX_BETS:
            return casino_error('Postaw coś na stole.')
        bets = {}
        for b in raw_bets:
            try:
                kind, amount = str(b.get('t')), int(b.get('a'))
                _, value = roulette_value(kind, b.get('v'))
            except (AttributeError, TypeError, ValueError):
                return casino_error('Zły zakład.')
            if amount < 1:
                return casino_error('Zły zakład.')
            bets[(kind, value)] = bets.get((kind, value), 0) + amount
        total = sum(bets.values())
        already = db.session.query(func.coalesce(func.sum(RouletteBet.amount), 0)) \
            .filter_by(round_id=rnd, user_id=current_user.id).scalar()
        low, high = casino_limits()
        if already + total < low or already + total > high:
            return casino_error(f'Na jedną rundę od {money(low)} do {money(high)} $'
                                + (f' (masz już {money(already)})' if already else '') + '.')
        casino_wallet(current_user.id)
        if not casino_update(current_user.id, {CasinoWallet.balance: CasinoWallet.balance - total},
                             casino_can_pay(current_user.id, total)):
            db.session.rollback()
            return casino_error('Za mało kasy - zarób ją w grach.')
        db.session.add_all(RouletteBet(round_id=rnd, user_id=current_user.id, kind=kind, value=value, amount=amount)
                           for (kind, value), amount in bets.items())
        db.session.commit()
        return jsonify({'ok': True, 'roulette': roulette_state(current_user.id), **casino_state(current_user.id)})

    def baccarat_points(card):
        return 1 if card[0] == 'A' else 0 if card[0] in 'TJQK' else int(card[0])

    def baccarat_value(cards):
        return sum(baccarat_points(c) for c in cards) % 10

    def baccarat_deal():
        """Punto banco: zasady dobierania trzeciej karty jak w kasynie."""
        shoe = new_shoe(8)
        player, banker = [shoe.pop()], [shoe.pop()]
        player.append(shoe.pop())
        banker.append(shoe.pop())
        if baccarat_value(player) >= 8 or baccarat_value(banker) >= 8:   # „naturalna” 8 albo 9
            return player, banker
        third = None
        if baccarat_value(player) <= 5:
            player.append(shoe.pop())
            third = baccarat_points(player[-1])
        b = baccarat_value(banker)
        if third is None:
            draw = b <= 5
        else:
            draw = b <= 2 or (b == 3 and third != 8) or (b == 4 and 2 <= third <= 7) \
                or (b == 5 and 4 <= third <= 7) or (b == 6 and 6 <= third <= 7)
        if draw:
            banker.append(shoe.pop())
        return player, banker

    @app.route('/kasyno/bakarat', methods=['POST'])
    @login_required
    def casino_baccarat():
        blocked = casino_guard()
        if blocked:
            return blocked
        raw = (request.get_json(silent=True) or {}).get('bets') or {}
        try:
            bets = {k: int(raw.get(k) or 0) for k in ('player', 'banker', 'tie')}
        except (AttributeError, TypeError, ValueError):
            return casino_error('Zły zakład.')
        total = sum(bets.values())
        low, high = casino_limits()
        if min(bets.values()) < 0 or not low <= total <= high:
            return casino_error(f'Na jedno rozdanie od {money(low)} do {money(high)} $.')
        casino_wallet(current_user.id)
        if not casino_update(current_user.id, {CasinoWallet.balance: CasinoWallet.balance - total},
                             casino_can_pay(current_user.id, total)):
            db.session.rollback()
            return casino_error('Za mało kasy - zarób ją w grach.')
        player, banker = baccarat_deal()
        pv, bv = baccarat_value(player), baccarat_value(banker)
        winner = 'player' if pv > bv else 'banker' if bv > pv else 'tie'
        if winner == 'tie':      # przy remisie zakłady na gracza i bankiera wracają
            payout = bets['tie'] * 9 + bets['player'] + bets['banker']
        elif winner == 'player':
            payout = bets['player'] * 2
        else:                    # bankier płaci 0,95 do 1 (5% prowizji)
            payout = bets['banker'] + bets['banker'] * 95 // 100
        if payout:
            casino_update(current_user.id, {CasinoWallet.balance: CasinoWallet.balance + payout})
        names = {'player': 'Gracz', 'banker': 'Bankier', 'tie': 'Remis'}
        casino_record(current_user.id, 'bakarat', total, payout, f'{names[winner]} · Gracz {pv} : {bv} Bankier')
        db.session.commit()
        return jsonify({'ok': True, 'player': player, 'banker': banker, 'player_value': pv, 'banker_value': bv,
                        'winner': winner, 'payout': payout, 'net': payout - total,
                        **casino_state(current_user.id), 'history': casino_history(current_user.id)})

    # ===================== Poker Texas Hold'em (wspólny stół) =====================
    # Cały stan stołu to jeden JSON w PokerTable. Każda zmiana: wczytaj -> policz -> zapisz z warunkiem version
    # (inaczej ponów). Zegary (czas na ruch, kolejne rozdanie) liczy się leniwie przy każdym pytaniu o stół.
    # Żetony przy stole są zdjęte z portfela przy siadaniu i wracają przy wstawaniu.

    POKER_RANK_VALUES = {r: i for i, r in enumerate('23456789TJQKA', 2)}

    def poker_score5(cards):
        """Siła 5 kart jako krotka do porównań: (kategoria 0-8, karty rozstrzygające...)."""
        vals = sorted((POKER_RANK_VALUES[c[0]] for c in cards), reverse=True)
        counts = {}
        for v in vals:
            counts[v] = counts.get(v, 0) + 1
        groups = sorted(counts.items(), key=lambda kv: (-kv[1], -kv[0]))
        flush = len({c[1] for c in cards}) == 1
        straight = None
        if len(counts) == 5:
            if vals[0] - vals[4] == 4:
                straight = vals[0]
            elif vals == [14, 5, 4, 3, 2]:      # strit od asa: A-2-3-4-5
                straight = 5
        if straight and flush:
            return (8, straight)
        if groups[0][1] == 4:
            return (7, groups[0][0], groups[1][0])
        if groups[0][1] == 3 and groups[1][1] == 2:
            return (6, groups[0][0], groups[1][0])
        if flush:
            return (5, *vals)
        if straight:
            return (4, straight)
        if groups[0][1] == 3:
            return (3, groups[0][0], *[v for v, _ in groups[1:]])
        if groups[0][1] == 2 and groups[1][1] == 2:
            return (2, groups[0][0], groups[1][0], groups[2][0])
        if groups[0][1] == 2:
            return (1, groups[0][0], *[v for v, _ in groups[1:]])
        return (0, *vals)

    def poker_best(cards):
        """Najlepsze 5 z 7 kart: (siła, te 5 kart)."""
        return max(((poker_score5(c), list(c)) for c in combinations(cards, 5)), key=lambda x: x[0])

    def poker_hand_name(score):
        if score[0] == 8 and score[1] == 14:
            return 'Poker królewski'
        return POKER_HANDS[score[0]]

    def poker_blinds():
        bb = max(2, site_settings()['poker_big_blind'])
        return bb // 2, bb

    def poker_new_state():
        return {'seats': [None] * POKER_SEATS, 'button': -1, 'hand': None, 'hand_no': 0, 'next_at': None, 'log': []}

    def poker_row():
        row = db.session.get(PokerTable, 1)
        if row is None:
            try:
                db.session.add(PokerTable(id=1, state=json.dumps(poker_new_state()), version=0))
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
            row = db.session.get(PokerTable, 1)
        return row

    def poker_log(state, text):
        state['log'] = (state['log'] + [text])[-12:]

    def poker_next(state, start, cond):
        """Następne miejsce po `start` (zgodnie z ruchem wskazówek) spełniające cond(seat); None, gdy brak."""
        for i in range(1, POKER_SEATS + 1):
            s = (start + i) % POKER_SEATS
            if cond(s):
                return s
        return None

    def poker_ready(state):
        """Miejsca, które dostaną karty: ktoś siedzi, jest obecny i ma żetony."""
        return [i for i, s in enumerate(state['seats']) if s and not s['out'] and s['stack'] > 0]

    def poker_pay(state, seat, amount):
        """Gracz dokłada do puli (najwyżej tyle, ile ma)."""
        h, s = state['hand'], state['seats'][seat]
        p = h['p'][str(seat)]
        pay = min(amount, s['stack'])
        s['stack'] -= pay
        p['bet'] += pay
        p['contrib'] += pay
        if s['stack'] == 0:
            p['allin'] = True
        return pay

    def poker_start_hand(state, now):
        sb_amount, bb_amount = poker_blinds()
        ready = poker_ready(state)
        state['button'] = poker_next(state, state['button'], lambda s: s in ready)
        state['hand_no'] += 1
        deck = new_shoe(1)
        h = {'no': state['hand_no'], 'deck': deck, 'board': [], 'phase': 'preflop', 'current': 0, 'min_raise': bb_amount,
             'bb': bb_amount, 'turn': None, 'deadline': None, 'results': None,
             'p': {str(s): {'uid': state['seats'][s]['uid'], 'name': state['seats'][s]['name'], 'cards': [deck.pop(), deck.pop()],
                            'bet': 0, 'contrib': 0, 'folded': False, 'allin': False, 'acted': False, 'last': ''} for s in ready}}
        state['hand'] = h
        state['next_at'] = None
        if len(ready) == 2:          # heads-up: rozdający daje małą ciemną i zaczyna przed flopem
            sb, bb = state['button'], poker_next(state, state['button'], lambda s: s in ready)
        else:
            sb = poker_next(state, state['button'], lambda s: s in ready)
            bb = poker_next(state, sb, lambda s: s in ready)
        poker_pay(state, sb, sb_amount)
        h['p'][str(sb)]['last'] = f'mała ciemna {sb_amount}'
        poker_pay(state, bb, bb_amount)
        h['p'][str(bb)]['last'] = f'duża ciemna {bb_amount}'
        h['current'] = max(h['p'][str(sb)]['bet'], h['p'][str(bb)]['bet'])
        poker_log(state, f'Rozdanie #{h["no"]} - ciemne {sb_amount}/{bb_amount}')
        h['turn'] = bb                # pierwszy ruch: następny po dużej ciemnej
        poker_after_action(state, now, from_seat=bb, fresh=True)

    def poker_can_act(h):
        return [int(s) for s, p in h['p'].items() if not p['folded'] and not p['allin']]

    def poker_after_action(state, now, from_seat, fresh=False):
        """Po ruchu: następny gracz, kolejna ulica albo koniec rozdania."""
        h = state['hand']
        alive = [int(s) for s, p in h['p'].items() if not p['folded']]
        if len(alive) == 1:
            return poker_finish(state, now, showdown=False)
        can_act = poker_can_act(h)
        waiting = [s for s in can_act if not h['p'][str(s)]['acted'] or h['p'][str(s)]['bet'] < h['current']]
        if len(can_act) == 1 and h['p'][str(can_act[0])]['bet'] >= h['current']:
            waiting = []              # został jeden, który może grać, i nie musi nic dopłacać
        if waiting:
            h['turn'] = poker_next(state, from_seat, lambda s: s in waiting)
            h['deadline'] = now + POKER_TURN_SECONDS
            return
        # koniec licytacji na tej ulicy
        for p in h['p'].values():
            p['bet'], p['acted'] = 0, False
        h['current'], h['min_raise'] = 0, h['bb']
        while True:
            if h['phase'] == 'river':
                return poker_finish(state, now, showdown=True)
            h['phase'], count = {'preflop': ('flop', 3), 'flop': ('turn', 1), 'turn': ('river', 1)}[h['phase']]
            h['deck'].pop()           # karta spalona
            h['board'] += [h['deck'].pop() for _ in range(count)]
            if len(poker_can_act(h)) >= 2:
                break                 # inaczej (wszyscy all-in) dokładamy karty do końca bez licytacji
        for p in h['p'].values():
            if not p['folded'] and not p['allin']:
                p['last'] = ''
        h['turn'] = poker_next(state, state['button'], lambda s: s in poker_can_act(h))
        h['deadline'] = now + POKER_TURN_SECONDS

    def poker_finish(state, now, showdown):
        """Rozliczenie: pule główna i boczne (wg wkładów), podział przy remisie, zapis rund do historii kasyna."""
        h = state['hand']
        contrib = {int(s): p['contrib'] for s, p in h['p'].items()}
        alive = [int(s) for s, p in h['p'].items() if not p['folded']]
        won = {s: 0 for s in contrib}
        scores = {}
        if showdown:
            for s in alive:
                scores[s] = poker_best(h['p'][str(s)]['cards'] + h['board'])
            levels = sorted({c for c in contrib.values() if c > 0})
            prev = 0
            for level in levels:
                amount = sum(min(c, level) - min(c, prev) for c in contrib.values())
                eligible = [s for s in alive if contrib[s] >= level] or alive
                prev = level
                if not amount:
                    continue
                best = max(scores[s][0] for s in eligible)
                winners = [s for s in eligible if scores[s][0] == best]
                # nieparzysty żeton - pierwszemu zwycięzcy na lewo od rozdającego
                winners.sort(key=lambda s: (s - state['button'] - 1) % POKER_SEATS)
                share, rest = divmod(amount, len(winners))
                for i, s in enumerate(winners):
                    won[s] += share + (1 if i < rest else 0)
        else:
            won[alive[0]] = sum(contrib.values())
        results = []
        for s, p in h['p'].items():
            s = int(s)
            seat = state['seats'][s]
            if won[s]:
                if seat and seat['uid'] == p['uid']:
                    seat['stack'] += won[s]
                else:                 # wstał w trakcie rozdania - wygrana prosto do portfela
                    h.setdefault('refunds', []).append([p['uid'], won[s]])
            name = poker_hand_name(scores[s][0]) if s in scores else None
            if s in alive or won[s]:
                results.append({'seat': s, 'name': p['name'], 'won': won[s], 'hand': name,
                                'best': scores[s][1] if s in scores else [], 'cards': p['cards'] if showdown and s in alive else None})
            if p['contrib']:
                street = {'preflop': 'przed flopem', 'flop': 'na flopie', 'turn': 'na turnie', 'river': 'na riverze'}
                if p['folded']:
                    text = 'pas ' + street.get(h.get('fold_phase', {}).get(str(s), ''), '')
                elif name:
                    text = f'{name}' + (' - wygrana' if won[s] else '')
                else:
                    text = 'wszyscy spasowali - pula' if won[s] else ''
                h.setdefault('records', []).append([p['uid'], p['contrib'], won[s], f'rozdanie #{h["no"]}: {text}'])
        results.sort(key=lambda r: -r['won'])
        h['results'] = results
        winners_text = ', '.join(f'{r["name"]} +{r["won"]}' + (f' ({r["hand"]})' if r['hand'] else '') for r in results if r['won'])
        poker_log(state, f'#{h["no"]}: {winners_text}')
        h['phase'], h['turn'], h['deadline'] = 'done', None, None
        state['next_at'] = now + POKER_PAUSE_SECONDS

    def poker_act(state, seat, action, amount, now, auto=False):
        """Ruch gracza; zwraca tekst błędu albo None. Nic nie zmienia, gdy ruch jest niedozwolony."""
        h = state['hand']
        if not h or h['phase'] == 'done' or h['turn'] != seat:
            return 'Teraz nie Twój ruch.'
        p, s = h['p'][str(seat)], state['seats'][seat]
        to_call = h['current'] - p['bet']
        if action == 'allin':
            action, amount = ('raise', p['bet'] + s['stack']) if p['bet'] + s['stack'] > h['current'] else ('call', 0)
        if action == 'check' and to_call > 0:
            return 'Nie możesz czekać - trzeba sprawdzić albo spasować.'
        if action == 'call' and to_call <= 0:
            action = 'check'
        if action == 'raise':
            try:
                amount = int(amount)
            except (TypeError, ValueError):
                return 'Podaj kwotę podbicia.'
            all_in = amount == p['bet'] + s['stack']
            if amount <= h['current'] or amount > p['bet'] + s['stack']:
                return 'Zła kwota podbicia.'
            if amount - h['current'] < h['min_raise'] and not all_in:
                return f'Podbij przynajmniej do {h["current"] + h["min_raise"]}.'
        if action not in ('fold', 'check', 'call', 'raise'):
            return 'Nieznany ruch.'
        if action == 'fold':
            p['folded'], p['last'] = True, 'pas'
            h.setdefault('fold_phase', {})[str(seat)] = h['phase']
        elif action == 'check':
            p['last'] = 'czeka'
        elif action == 'call':
            pay = poker_pay(state, seat, to_call)
            p['last'] = f'sprawdza {pay}' + (' (all-in)' if p['allin'] else '')
        else:
            raise_by, opening = amount - h['current'], h['current'] == 0
            poker_pay(state, seat, amount - p['bet'])
            if raise_by >= h['min_raise']:
                h['min_raise'] = raise_by
            h['current'] = amount
            for other in h['p'].values():
                if other is not p:
                    other['acted'] = False
            p['last'] = ('all-in ' if p['allin'] else 'stawia ' if opening else 'podbija do ') + str(amount)
        p['acted'] = True
        if not auto:
            s['timeouts'] = 0
        poker_log(state, f'{p["name"]}: {p["last"]}' + (' (czas minął)' if auto else ''))
        poker_after_action(state, now, from_seat=seat)
        return None

    def poker_stand(state, seat, now, ops):
        """Wstanie od stołu: w trakcie rozdania pas, reszta żetonów wraca do portfela."""
        s = state['seats'][seat]
        h = state['hand']
        if h and h['phase'] != 'done' and str(seat) in h['p'] and not h['p'][str(seat)]['folded']:
            p = h['p'][str(seat)]
            if h['turn'] == seat:
                poker_act(state, seat, 'fold', 0, now)
            else:
                p['folded'], p['last'] = True, 'wstał od stołu'
                h.setdefault('fold_phase', {})[str(seat)] = h['phase']
                if len([q for q in h['p'].values() if not q['folded']]) == 1:
                    poker_finish(state, now, showdown=False)
        if s['stack']:
            ops.append((s['uid'], s['stack']))
        poker_log(state, f'{s["name"]} wstaje od stołu ({s["stack"]} $ wraca)')
        state['seats'][seat] = None

    def poker_tick(state, now, ops):
        """Zegary stołu; True, gdy coś się zmieniło."""
        changed = False
        h = state['hand']
        if h and h['phase'] != 'done' and h['turn'] is not None:
            seat = state['seats'][h['turn']]
            if seat is None or seat['out'] or now >= h['deadline']:
                turn = h['turn']
                if seat and not seat['out']:
                    seat['timeouts'] += 1
                    if seat['timeouts'] >= POKER_TIMEOUTS_OUT:
                        seat['out'], seat['out_since'] = True, now
                p = h['p'][str(turn)]
                poker_act(state, turn, 'check' if p['bet'] >= h['current'] else 'fold', 0, now, auto=True)
                changed = True
        h = state['hand']
        if h and h['phase'] == 'done' and state['next_at'] and now >= state['next_at']:
            state['hand'] = None
            state['next_at'] = None
            changed = True
        if not state['hand']:
            for i, s in enumerate(state['seats']):
                if s and (s['stack'] == 0 or (s['out'] and now - (s.get('out_since') or now) > POKER_OUT_KICK_SECONDS)):
                    poker_stand(state, i, now, ops)
                    changed = True
            if len(poker_ready(state)) >= 2:
                if state['next_at'] is None:
                    state['next_at'] = now + POKER_START_SECONDS
                    changed = True
                elif now >= state['next_at']:
                    poker_start_hand(state, now)
                    changed = True
            elif state['next_at'] is not None:
                state['next_at'] = None
                changed = True
        return changed

    def poker_mutate(fn=None):
        """Wczytuje stół, odpala zegary i (opcjonalnie) fn(state, now, ops) -> błąd albo None, zapisuje z blokadą.
        ops = [(user_id, zmiana portfela)], rekordy historii zbiera rozliczenie. Zwraca (stan, błąd)."""
        for _ in range(6):
            db.session.rollback()
            row = poker_row()
            version, state = row.version, json.loads(row.state)
            now, ops = time.time(), []
            changed = poker_tick(state, now, ops)
            error = fn(state, now, ops) if fn else None
            if error and not changed:
                return state, error
            if not changed and not fn:
                return state, None
            # wygrane graczy, którzy wstali w trakcie rozdania, i historia kasyna - raz, przy rozliczeniu
            h = state['hand']
            if h and h.get('records') and not h.get('recorded'):
                for uid, delta in h.pop('refunds', []):
                    ops.append((uid, delta))
                records = h['records']
                h['recorded'] = True
            else:
                records = []
            if PokerTable.query.filter_by(id=1, version=version) \
                    .update({PokerTable.state: json.dumps(state), PokerTable.version: version + 1}, synchronize_session=False) != 1:
                db.session.rollback()
                continue
            for uid, delta in ops:
                if delta < 0:
                    if not casino_update(uid, {CasinoWallet.balance: CasinoWallet.balance + delta}, casino_can_pay(uid, -delta)):
                        db.session.rollback()
                        return state, 'Za mało kasy - zarób ją w grach.'
                elif delta:
                    casino_update(uid, {CasinoWallet.balance: CasinoWallet.balance + delta})
            for uid, bet, payout, text in records:
                casino_record(uid, 'poker', bet, payout, text)
            db.session.commit()
            return state, error
        return state, 'Stół jest teraz oblegany - spróbuj jeszcze raz.'

    def poker_view(state, user_id):
        """Stół dla przeglądarki: cudze karty tylko po pokazaniu przy końcu rozdania, bez talii."""
        h = state['hand']
        my_seat = next((i for i, s in enumerate(state['seats']) if s and s['uid'] == user_id), None)
        shown = {r['seat']: r for r in (h['results'] or [])} if h else {}
        seats = []
        for i, s in enumerate(state['seats']):
            p = h['p'].get(str(i)) if h else None
            if not s and not p:
                seats.append(None)
                continue
            cards = None
            if p and (not s or s['uid'] == p['uid']):
                if i == my_seat or (i in shown and shown[i]['cards']):
                    cards = p['cards']
                elif not p['folded']:
                    cards = ['??', '??']
            seats.append({'name': s['name'] if s else p['name'], 'photo': s['photo'] if s else None, 'stack': s['stack'] if s else 0,
                          'empty': not s, 'out': bool(s and s['out']), 'me': i == my_seat, 'cards': cards,
                          'bet': p['bet'] if p else 0, 'folded': bool(p and p['folded']), 'allin': bool(p and p['allin']),
                          'last': p['last'] if p else ('nieobecny' if s and s['out'] else ''),
                          'won': shown[i]['won'] if i in shown else 0, 'hand_name': shown[i]['hand'] if i in shown else None,
                          'best': shown[i]['best'] if i in shown else []})
        actions = None
        if h and h['phase'] != 'done' and h['turn'] == my_seat and my_seat is not None:
            p, s = h['p'][str(my_seat)], state['seats'][my_seat]
            to_call = h['current'] - p['bet']
            max_to = p['bet'] + s['stack']
            actions = {'check': to_call <= 0, 'call': min(to_call, s['stack']) if to_call > 0 else 0,
                       'min_raise': min(h['current'] + h['min_raise'], max_to), 'max_raise': max_to,
                       'can_raise': max_to > h['current'], 'pot': sum(q['contrib'] for q in h['p'].values()), 'current': h['current'],
                       'my_bet': p['bet']}
        my_hand = None
        if h and my_seat is not None and str(my_seat) in h['p'] and len(h['board']) >= 3 and not h['p'][str(my_seat)]['folded']:
            my_hand = poker_hand_name(poker_best(h['p'][str(my_seat)]['cards'] + h['board'])[0])
        sb, bb = poker_blinds()
        return {'seats': seats, 'board': h['board'] if h else [], 'pot': sum(q['contrib'] for q in h['p'].values()) if h else 0,
                'phase': h['phase'] if h else None, 'turn': h['turn'] if h else None, 'hand_no': h['no'] if h else state['hand_no'],
                'deadline_ms': int(h['deadline'] * 1000) if h and h['deadline'] else None,
                'next_ms': int(state['next_at'] * 1000) if state['next_at'] else None, 'now_ms': int(time.time() * 1000),
                'button': state['button'], 'me': my_seat, 'actions': actions, 'my_hand': my_hand,
                'me_out': bool(my_seat is not None and state['seats'][my_seat]['out']),
                'log': state['log'][-8:], 'blinds': [sb, bb], 'buyin': [bb * POKER_BUYIN_BB[0], bb * POKER_BUYIN_BB[1]],
                'turn_seconds': POKER_TURN_SECONDS}

    @app.route('/kasyno/poker/stan')
    @login_required
    def poker_state_route():
        blocked = casino_guard()
        if blocked:
            return blocked
        state, _ = poker_mutate()
        return jsonify({'ok': True, 'poker': poker_view(state, current_user.id), 'balance': casino_money(current_user.id)})

    @app.route('/kasyno/poker', methods=['POST'])
    @login_required
    def poker_action_route():
        blocked = casino_guard()
        if blocked:
            return blocked
        data = request.get_json(silent=True) or {}
        action = data.get('action')
        uid = current_user.id
        casino_wallet(uid)

        def change(state, now, ops):
            my_seat = next((i for i, s in enumerate(state['seats']) if s and s['uid'] == uid), None)
            if action == 'sit':
                if my_seat is not None:
                    return 'Już siedzisz przy stole.'
                try:
                    seat, buyin = int(data.get('seat')), int(data.get('buyin'))
                except (TypeError, ValueError):
                    return 'Wybierz miejsce i wpisowe.'
                _, bb = poker_blinds()
                low, high = bb * POKER_BUYIN_BB[0], bb * POKER_BUYIN_BB[1]
                h = state['hand']
                if not 0 <= seat < POKER_SEATS or state['seats'][seat] or (h and h['phase'] != 'done' and str(seat) in h['p']):
                    return 'To miejsce jest zajęte.'
                if not low <= buyin <= high:
                    return f'Wpisowe od {money(low)} do {money(high)} $.'
                if casino_money(uid) < buyin:
                    return 'Za mało kasy - zarób ją w grach.'
                state['seats'][seat] = {'uid': uid, 'name': current_user.username, 'photo': avatar_url(current_user.photo),
                                        'stack': buyin, 'out': False, 'out_since': None, 'timeouts': 0}
                ops.append((uid, -buyin))
                poker_log(state, f'{current_user.username} siada do stołu z {buyin} żetonami')
                return None
            if my_seat is None:
                return 'Nie siedzisz przy stole.'
            if action == 'stand':
                poker_stand(state, my_seat, now, ops)
                return None
            if action == 'back':
                state['seats'][my_seat].update(out=False, out_since=None, timeouts=0)
                return None
            if action == 'away':
                state['seats'][my_seat].update(out=True, out_since=now)
                return None
            return poker_act(state, my_seat, action, data.get('amount'), now)

        state, error = poker_mutate(change)
        result = {'ok': not error, 'poker': poker_view(state, uid), 'balance': casino_money(uid)}
        if error:
            result['error'] = error
        return jsonify(result), (400 if error else 200)

    def casino_revealed(viewer_id, now):
        """Warunek: wynik już można pokazać. Własne rundy i całą wspólną ruletkę dopiero po animacji
        (koło kręci się kilka sekund po rozliczeniu), resztę od razu."""
        return db.or_(db.and_(CasinoBet.user_id != viewer_id, CasinoBet.game != 'ruletka'),
                      CasinoBet.created_at <= now - CASINO_LIVE_OWN_DELAY)

    def casino_top_wins(viewer_id=None):
        """Największa wygrana (na plusie ponad stawkę) dzisiaj - od polskiej północy - i od początku kasyna.
        Własna świeża wygrana widza dochodzi po animacji, jak w „na żywo”."""
        now = datetime.utcnow()
        midnight_utc = datetime.combine(date.today(), datetime.min.time()) - (datetime.now() - now)
        query = CasinoBet.query.filter(CasinoBet.game.in_(list(CASINO_GAMES)), CasinoBet.payout > CasinoBet.bet)
        if viewer_id:
            query = query.filter(casino_revealed(viewer_id, now))

        def best(q):
            b = q.order_by((CasinoBet.payout - CasinoBet.bet).desc(), CasinoBet.id).first()
            if not b or not b.user:
                return None
            return {'id': b.id, 'user': b.user.username, 'photo': avatar_url(b.user.photo), 'user_id': b.user_id,
                    'game': CASINO_GAMES[b.game], 'bet': b.bet, 'net': b.payout - b.bet, 'text': b.details or '',
                    'when': when_label(b.created_at)}
        return {'day': best(query.filter(CasinoBet.created_at >= midnight_utc)), 'all': best(query)}

    @app.route('/kasyno/na-zywo')
    @login_required
    def casino_live():
        """Zakłady wszystkich graczy i kto jest teraz przy stołach - /kasyno pyta co 3 s."""
        blocked = casino_guard()
        if blocked:
            return blocked
        now = datetime.utcnow()
        game = request.args.get('gra')
        game = game if game in CASINO_GAMES else None
        wallet = casino_wallet(current_user.id)
        # obecność zapisujemy najwyżej co 15 s (albo przy zmianie stołu), żeby nie pisać do bazy przy każdym pytaniu
        if not wallet.seen_at or now - wallet.seen_at > timedelta(seconds=15) or wallet.seen_game != game:
            casino_update(current_user.id, {CasinoWallet.seen_at: now, CasinoWallet.seen_game: game})
            db.session.commit()
        roulette_settle()   # rundy ruletki rozliczają się też wtedy, gdy nikt nie patrzy na jej zakładkę
        rows = CasinoBet.query.filter(CasinoBet.game.in_(list(CASINO_GAMES)), casino_revealed(current_user.id, now)) \
            .order_by(CasinoBet.id.desc()).limit(CASINO_LIVE_ROWS).all()
        big_win = site_settings()['casino_big_win']
        feed = [{'id': b.id, 'user': b.user.username, 'photo': avatar_url(b.user.photo), 'me': b.user_id == current_user.id,
                 'game': CASINO_GAMES[b.game], 'bet': b.bet, 'net': b.payout - b.bet, 'text': b.details or '',
                 'big': big_win > 0 and b.payout - b.bet >= big_win, 'ago': int((now - b.created_at).total_seconds())}
                for b in rows if b.user]
        players = []
        for w in CasinoWallet.query.filter(CasinoWallet.seen_at >= now - CASINO_LIVE_SEEN).all():
            if not w.user:
                continue
            hand = None
            if w.blackjack:
                try:
                    hand = sum(h['bet'] for h in json.loads(w.blackjack)['hands'])
                except (ValueError, KeyError, TypeError):
                    hand = None
            players.append({'user': w.user.username, 'photo': avatar_url(w.user.photo), 'me': w.user_id == current_user.id,
                            'game': CASINO_GAMES.get(w.seen_game, '🎰 Kasyno'), 'balance': casino_money(w.user_id, w), 'hand': hand})
        players.sort(key=lambda p: (not p['me'], p['user'].lower()))
        return jsonify({'ok': True, 'feed': feed, 'players': players, 'top': casino_top_wins(current_user.id)})

    def casino_ranking(sort='saldo'):
        """[{user, balance, rounds, net, best}] - saldo z portfela, reszta z rozegranych rund (bez dziennych)."""
        stats = {uid: (rounds, net or 0, best or 0) for uid, rounds, net, best in db.session.query(
            CasinoBet.user_id, func.count(), func.sum(CasinoBet.payout - CasinoBet.bet), func.max(CasinoBet.payout - CasinoBet.bet))
            .filter(CasinoBet.game.in_(list(CASINO_GAMES))).group_by(CasinoBet.user_id).all()}
        rows = []
        for wallet in CasinoWallet.query.all():
            if not wallet.user or (wallet.balance == 0 and wallet.user_id not in stats):
                continue
            rounds, net, best = stats.get(wallet.user_id, (0, 0, 0))
            rows.append({'user': wallet.user, 'balance': casino_money(wallet.user_id, wallet), 'rounds': rounds, 'net': net,
                         'best': max(best, 0)})
        key = {'netto': 'net', 'wygrana': 'best', 'gry': 'rounds'}.get(sort, 'balance')
        rows.sort(key=lambda r: (-r[key], -r['balance'], r['user'].username.lower()))
        return rows

    @app.route('/kasyno/ranking')
    @login_required
    def casino_ranking_page():
        blocked = casino_guard()
        if blocked:
            return blocked
        sort = request.args.get('sort', 'saldo')
        if sort not in ('saldo', 'netto', 'wygrana', 'gry'):
            sort = 'saldo'
        rounds = CasinoBet.query.filter(CasinoBet.game.in_(list(CASINO_GAMES))).count()
        return render_template('kasyno_ranking.html', ranking=casino_ranking(sort), sort=sort, rounds=rounds,
                               top=casino_top_wins(current_user.id))

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
            chat_rows = Message.query.filter(Message.timestamp > since).order_by(Message.timestamp.desc()).limit(limit).all()
            replied = {m.id: m for m in Message.query.filter(Message.id.in_({m.reply_to_id for m in chat_rows if m.reply_to_id}))}
            file_words = {'image': ('🖼️', 'zdjęcie'), 'video': ('🎬', 'film'), 'file': ('📎', 'plik')}
            for m in chat_rows:
                text = m.content if len(m.content) <= 100 else m.content[:100] + '…'
                icon, what = '💬', 'na czacie'
                if m.file_path:
                    icon, word = file_words.get(m.file_kind, file_words['file'])
                    what = f'{word} na czacie'
                    text = m.file_name if m.content == chat_file_caption(m.file_name) else f'{m.file_name} - {text}'
                original = replied.get(m.reply_to_id)
                if original and original.user:
                    what = f'odpowiedź dla {original.user.username}' + (f' ({word})' if m.file_path else '')
                    icon = '↩️' if not m.file_path else icon
                add('chat', icon, m.user_id, f'{what}: „{text}”', url_for('camera'), m.timestamp)
        if want('reaction'):
            # reakcje na czacie - osobno dla każdej wiadomości (jedna reakcja na osobę)
            for reaction in ChatReaction.query.filter(ChatReaction.created_at > since).all():
                m = db.session.get(Message, reaction.message_id)
                if m and m.user:
                    add('reaction', reaction.emoji, reaction.user_id,
                        f'reakcja {reaction.emoji} na wiadomość {m.user.username}: „{chat_snippet(m, 60)}”',
                        url_for('camera'), reaction.created_at)
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
        if want('like'):
            rows = db.session.query(PrintPhotoLike.user_id, PrintPhoto.request_id, func.count(), func.max(PrintPhotoLike.created_at)) \
                .join(PrintPhoto, PrintPhoto.id == PrintPhotoLike.photo_id) \
                .filter(PrintPhotoLike.created_at > since).group_by(PrintPhotoLike.user_id, PrintPhoto.request_id).all()
            for user_id, request_id, count, at in rows:
                pr = db.session.get(PrintRequest, request_id)
                if pr:
                    add('like', '❤️', user_id, f'polubienie zdjęcia wydruku: {pr.title}',
                        url_for('print_detail', request_id=pr.id) + '#zdjecia', at)
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
        big_win = site_settings()['casino_big_win']
        if want('casino') and big_win > 0:
            for b in CasinoBet.query.filter(CasinoBet.created_at > since, CasinoBet.game.in_(list(CASINO_GAMES)),
                                            CasinoBet.payout - CasinoBet.bet >= big_win).all():
                add('casino', '🎰', b.user_id, f'kasyno - {CASINO_GAMES[b.game][2:]}: wygrana {money(b.payout - b.bet)} $'
                    + (f' ({b.details})' if b.details else ''), url_for('casino_ranking_page'), b.created_at)
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
        return jsonify({'cash': user_money(current_user.id)})

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

    def gta6_font(size, logo=False):
        from PIL import ImageFont
        fonts = [os.path.join(app.static_folder, 'css', 'fonts', 'pricedown.otf')] if logo else []
        fonts += ['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 'C:/Windows/Fonts/arialbd.ttf',
                  os.path.join(app.static_folder, 'css', 'fonts', 'pricedown.otf')]
        for path in fonts:
            try:
                return ImageFont.truetype(path, size)
            except (OSError, IOError):
                continue
        return ImageFont.load_default()

    @app.route('/gta6/licznik.gif')
    def gta6_counter_gif():
        """Licznik do maili (bez JS): animacja na 60 s liczona od chwili otwarcia maila - publiczna, bez cache."""
        from PIL import Image, ImageDraw
        cd = countdown_info()
        if not cd:
            abort(404)
        width, height = 560, 150
        time_font, label_font = gta6_font(40), gta6_font(17)
        logo_size = 54                       # długa nazwa - mniejsza czcionka, żeby zmieściła się przed licznikiem
        while logo_size > 18 and ImageDraw.Draw(Image.new('RGB', (1, 1))).textlength(cd['title'], font=gta6_font(logo_size, logo=True)) > 190:
            logo_size -= 4
        logo_font = gta6_font(logo_size, logo=True)
        before, after_text = cd['before'].upper(), cd['after'].upper()
        when = cd['at'].strftime('%d.%m.%Y, %H:%M')
        frames = []
        base = int(time.time() - cd['ms'] / 1000)
        for step in range(60):
            diff = base + step
            after = diff >= 0
            s = abs(diff)
            d, h, m, sec = s // 86400, s % 86400 // 3600, s % 3600 // 60, s % 60
            text = (f'{d} d ' if d else '') + f'{h:02d}:{m:02d}:{sec:02d}'
            img = Image.new('RGB', (width, height), (23, 23, 31))
            draw = ImageDraw.Draw(img)
            left, right = ((31, 191, 117), (255, 46, 136)) if after else ((255, 46, 136), (255, 157, 46))
            for x in range(width):           # poziomy gradient jak na stronie
                t = x / (width - 1)
                draw.line([(x, 0), (x, height)], fill=tuple(int(left[i] + (right[i] - left[i]) * t) for i in range(3)))
            draw.text((24, height // 2), cd['title'], font=logo_font, fill=(255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0), anchor='lm')
            draw.text((230, 34), after_text if after else before, font=label_font, fill=(255, 255, 255))
            draw.text((230, 60), text, font=time_font, fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
            draw.text((230, 112), when, font=label_font, fill=(255, 255, 255))
            frames.append(img.convert('P', palette=Image.ADAPTIVE, colors=64))
        out = io.BytesIO()
        frames[0].save(out, format='GIF', save_all=True, append_images=frames[1:], duration=1000, optimize=True)
        response = send_file(io.BytesIO(out.getvalue()), mimetype='image/gif')
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Expires'] = '0'
        return response

    @app.route('/panel/maile', methods=['GET', 'POST'])
    @login_required
    def mail_sender():
        """Admin wysyła maila (z szablonu) do wybranych użytkowników - każdy dostaje osobną wiadomość."""
        if current_user.is_admin == "0":
            abort(403)
        users = sorted((u for u in User.query.all() if (u.email or '').strip()), key=lambda u: u.username.lower())
        root = request.url_root
        if 'hlyw.pl' in root:
            root = 'https://hlyw.pl/'
        links = {'{link_kamera}': root + 'camera', '{link_strona}': root}

        def fill(text, user, html=True, prefs_url=''):
            text = text.replace('{nick}', str(escape(user.username)) if html else user.username)
            for key, value in links.items():
                text = text.replace(key, value)
            if html:
                # każdy mail ma osobisty link do ustawień maili (działa bez logowania)
                if '{link_ustawienia}' not in text:
                    text += '{link_ustawienia_stopka}'
                text = text.replace('{link_ustawienia_stopka}', mail_footer(prefs_url)).replace('{link_ustawienia}', prefs_url)
            # Gmail trzyma obrazek pod danym adresem w swoim proxy dla wszystkich odbiorców - każdy mail dostaje
            # własny adres licznika, żeby pokazywał czas z chwili otwarcia, a nie z pierwszego pobrania
            return re.sub(r'gta6/licznik\.gif(?:\?m=\w+)?', lambda m: 'gta6/licznik.gif?m=' + os.urandom(6).hex(), text)

        form = {'template': request.form.get('template', 'gta6_po'), 'subject': request.form.get('subject', ''),
                'body': request.form.get('body', ''), 'to': request.form.getlist('to'),
                'mode': 'html' if request.form.get('mode') == 'html' else 'prosty', 'text': request.form.get('text', ''),
                'simple_template': request.form.get('simple_template', ''),
                'button_text': request.form.get('button_text', ''), 'button_url': request.form.get('button_url', ''),
                'counter': bool(request.form.get('counter')),
                'category': request.form.get('category') if request.form.get('category') in MAIL_CATEGORY_KEYS else 'other'}
        if request.method == 'POST':
            if form['mode'] == 'prosty':
                form['body'] = simple_mail_html(form, root) if form['text'].strip() else ''
            subject, body = form['subject'].strip(), form['body'].strip()
            if request.form.get('action') == 'test':
                chosen = [current_user]
            else:
                wanted = {int(x) for x in form['to'] if x.isdigit()}
                chosen = [u for u in users if u.id in wanted]
            is_test = request.form.get('action') == 'test'
            skipped = 0
            # kto wyłączył ten rodzaj maili (ustawienia konta / link z maila) - nie dostaje go; test do siebie zawsze idzie
            unwanted = [] if is_test else [u for u in chosen if not wants_mail(u, form['category'])]
            chosen = [u for u in chosen if u not in unwanted]
            if subject and chosen and not is_test and request.form.get('skip_sent'):
                done = {row.user_id for row in MailLog.query.filter_by(subject=subject[:200], ok=True)}
                skipped = sum(1 for u in chosen if u.id in done)
                chosen = [u for u in chosen if u.id not in done]
            if not subject or not body:
                flash('Uzupełnij temat i treść maila.', 'danger')
            elif not chosen:
                flash('Wszyscy zaznaczeni już dostali mail z tym tematem.' if skipped else
                      'Nikt z zaznaczonych nie chce maili tego rodzaju.' if unwanted else 'Zaznacz przynajmniej jednego odbiorcę.',
                      'warning' if skipped or unwanted else 'danger')
            else:
                # jeden e-mail może mieć kilka kont - wysyłamy raz
                jobs, seen = [], set()
                for user in chosen:
                    address = user.email.strip()
                    if address.lower() not in seen:
                        seen.add(address.lower())
                        prefs = mail_prefs_url(user, root)
                        jobs.append((user.id, address, fill(subject, user, html=False), fill(body, user, prefs_url=prefs),
                                     mail_prefs_url(user, root, form['category'])))
                log_subject = None if is_test else subject[:200]
                if is_test:
                    send_mail_jobs(jobs, log_subject)          # jeden mail - od razu, z wynikiem
                    ok = send_mail_jobs.last_ok
                    flash('Wysłano test na Twój adres - sprawdź skrzynkę (i spam).' if ok else 'Test nie wyszedł - zobacz log serwera.',
                          'success' if ok else 'danger')
                else:
                    # dhosting potrzebuje ~1-2 s na mail, a gunicorn ubija zapytanie po 30 s - wysyłka idzie w tle
                    threading.Thread(target=send_mail_jobs, args=(jobs, log_subject), daemon=True).start()
                    flash(f'Wysyłka ruszyła w tle: {len(jobs)} maili' + (f' (pominięto {skipped}, którzy już dostali)' if skipped else '')
                          + (f' · bez {len(unwanted)} os., które nie chcą maili „{MAIL_CATEGORY_NAMES[form["category"]]}”' if unwanted else '')
                          + '. Postęp widać niżej - odśwież stronę.', 'success')
                    return redirect(url_for('mail_sender', temat=subject[:200]))
        else:
            tpl = MAIL_TEMPLATES['gta6_po']
            form.update(subject=request.args.get('temat') or '', body=tpl['body'], text='Cześć {nick}!\n\n',
                        button_text='Wejdź na hlyw.pl', button_url='/', to=[str(u.id) for u in users if u.confirmed])
        progress = None
        if form['subject'].strip():
            rows = MailLog.query.filter_by(subject=form['subject'].strip()[:200]).all()
            names = {u.id: u.username for u in users}
            progress = {'ok': sorted(names.get(r.user_id, '?') for r in rows if r.ok),
                        'failed': sorted(names.get(r.user_id, '?') for r in rows if not r.ok)}
        return render_template('panel_maile.html', users=users, form=form, templates=MAIL_TEMPLATES,
                               simple_templates=simple_mail_templates(), categories=MAIL_CATEGORIES,
                               disabled_by={u.id: sorted(mail_disabled(u)) for u in users},
                               preview_nick=current_user.username, links=links, progress=progress)

    def simple_mail_templates():
        """Szablony prostego maila: ogólne + gotowe maile o rzeczach ze strony (wydarzenia, newsy, albumy).
        Każdy: {id, name, subject, text, button_text, button_url, counter}, pogrupowane do <optgroup>."""
        def tpl(tid, name, subject, text, button_text='', button_url='', counter=False, category='other'):
            return {'id': tid, 'name': name, 'subject': subject, 'text': text, 'button_text': button_text,
                    'button_url': button_url, 'counter': counter, 'category': category}
        hello = 'Cześć {nick}!\n\n'
        cd = countdown_info()
        general = [
            tpl('pusty', '✏️ Pusty', '', hello, 'Wejdź na hlyw.pl', '/'),
            tpl('stream', '🔴 Stream na kamerze', 'Leci stream na hlyw.pl - wbijaj!',
                hello + 'Właśnie leci stream na kamerze hlyw.pl. Wbijaj oglądać i pisz na czacie - '
                        'możesz oznaczyć znajomych przez @nick, wrzucić zdjęcie albo film.\n\nDo zobaczenia na czacie!',
                '🔴 Oglądaj stream', '/camera'),
            tpl('nowosc', '🚀 Nowość na stronie', 'Coś nowego na hlyw.pl',
                hello + 'Na hlyw.pl pojawiło się coś nowego: ...\n\nWejdź, sprawdź i daj znać na czacie, co o tym myślisz!',
                'Zobacz ulepszenia', '/ostatnie-ulepszenia', category='news'),
            tpl('gry', '🎮 Gry i rankingi', 'Ktoś czai się na Twój rekord na hlyw.pl',
                hello + 'W rankingach gier na hlyw.pl sporo się dzieje - sprawdź, czy dalej jesteś na szczycie, '
                        'i zgarnij punkty do Hall of Fame.\n\nPowodzenia!', 'Zagraj', '/games'),
            tpl('druk', '🖨️ Druk 3D', 'Masz pomysł, co wydrukować?',
                hello + 'Na drukarce HLYW można drukować Wasze pomysły. Wklej link do modelu z MakerWorld albo wrzuć plik '
                        'STL / 3MF - czas druku i zużycie filamentu policzą się same, a my damy znać, kiedy będzie gotowe.',
                'Zaproponuj wydruk', '/druk3d/nowa'),
            tpl('wroc', '👋 Dawno Cię nie było', 'Tęsknimy na hlyw.pl!',
                hello + 'Dawno Cię nie było na hlyw.pl, a sporo się zmieniło: czat z oznaczeniami i zdjęciami, nowe gry, '
                        'druk 3D i turnieje FIFA.\n\nWpadnij zobaczyć!', 'Wróć na hlyw.pl', '/'),
        ]
        if cd:
            general.insert(1, tpl('licznik', f'⏳ Licznik: {cd["title"]}', f'{cd["title"]} - {cd["at"]:%d.%m.%Y, %H:%M}',
                                  hello + f'{cd["title"]}: {cd["at"]:%d.%m.%Y} o {cd["at"]:%H:%M}. Licznik niżej pokazuje, '
                                          'ile zostało (albo ile już minęło).\n\nBądźcie z nami!',
                                  cd['link_text'].capitalize() if cd['link_text'] else '', cd['link_url'] if cd['link_text'] else '',
                                  counter=True))
        days = ['poniedziałek', 'wtorek', 'środa', 'czwartek', 'piątek', 'sobota', 'niedziela']
        events = []
        for e in Calendar.query.filter(Calendar.date >= datetime.now() - timedelta(days=1)).order_by(Calendar.date).limit(15):
            when = f'{days[e.date.weekday()]}, {e.date:%d.%m.%Y}' + (f' o {e.date:%H:%M}' if (e.date.hour, e.date.minute) != (0, 0) else '')
            fifa = 'fifa' in e.title.lower()
            text = hello + f'{when}: {e.title}.' + (f'\n\n{e.description.strip()}' if (e.description or '').strip() else '')
            text += ('\n\nZapisz się jako gracz (wybierz klub) albo kibic - im nas więcej, tym lepiej!' if fifa
                     else '\n\nZapisz się w kalendarzu, żebyśmy wiedzieli, ile osób będzie.')
            events.append(tpl(f'event{e.id}', f'📅 {e.date:%d.%m} - {e.title}', f'{e.title} - {e.date:%d.%m} ({days[e.date.weekday()]})',
                              text, 'Zobacz i zapisz się', url_for('event', day=e.date.day, month=e.date.month, year=e.date.year),
                              category='events'))
        news = []
        for n in News.query.order_by(News.created_at.desc()).limit(10):
            body = (n.description or '').strip()
            body = body if len(body) <= 700 else body[:700].rstrip() + '…'
            news.append(tpl(f'news{n.id}', f'📰 {n.title}', f'Breaking News: {n.title}',
                            hello + f'Na hlyw.pl nowy news: {n.title}\n\n{body}', 'Czytaj na hlyw.pl', '/news', category='news'))
        albums = []
        for a in Albums.query.order_by(Albums.created_at.desc()).limit(10):
            count = Images.query.filter_by(album_id=a.id).count()
            desc = f' - {a.description.strip()}' if (a.description or '').strip() else ''
            albums.append(tpl(f'album{a.id}', f'📷 {a.name}', f'Nowe zdjęcia: {a.name}',
                              hello + f'W galerii jest album „{a.name}”{desc} - {plural(count, "zdjęcie", "zdjęcia", "zdjęć")}. '
                                      'Zobacz, polub najlepsze i dorzuć swoje!', 'Zobacz zdjęcia', url_for('album', album_id=a.id),
                              category='news'))
        groups = [('Ogólne', general), ('Wydarzenia z kalendarza', events), ('Newsy', news), ('Albumy w galerii', albums)]
        return [{'group': g, 'items': items} for g, items in groups if items]

    def simple_mail_html(form, root):
        """Prosty mail: zwykły tekst (akapity, linki klikalne) w szacie hlyw.pl + opcjonalny przycisk i licznik.
        {nick} i pozostałe wstawki zostają - podmienia je fill() dla każdego odbiorcy."""
        def paragraph(block):
            html = str(escape(block.strip()))
            html = re.sub(r'(https?://[^\s<]+[^\s<.,;:!?)\]])',
                          r'<a href="\1" style="color:#ff9d2e">\1</a>', html)
            return html.replace('\n', '<br>')
        paragraphs = [paragraph(b) for b in re.split(r'\n\s*\n', form['text'].replace('\r\n', '\n')) if b.strip()]
        url = form['button_url'].strip()
        if url.startswith('/'):
            url = root.rstrip('/') + url
        elif url and not re.match(r'https?://', url):
            url = ''
        return render_template('mail_prosty.html', paragraphs=paragraphs, button_text=form['button_text'].strip(),
                               button_url=url, counter=form['counter'], site_url=root)

    @app.route('/panel/maile/podglad', methods=['POST'])
    @login_required
    def mail_preview():
        """Podgląd prostego maila (ten sam HTML, który pójdzie do odbiorców) - z nickiem admina."""
        if current_user.is_admin == "0":
            abort(403)
        root = request.url_root
        if 'hlyw.pl' in root:
            root = 'https://hlyw.pl/'
        form = {k: request.form.get(k, '') for k in ('text', 'button_text', 'button_url')}
        form['counter'] = bool(request.form.get('counter'))
        html = simple_mail_html(form, root).replace('{nick}', str(escape(current_user.username)))
        return html.replace('{link_kamera}', root + 'camera').replace('{link_strona}', root).replace('{link_ustawienia}', '#')

    # ---------- które maile użytkownik chce dostawać ----------
    def mail_disabled(user):
        """Zbiór wyłączonych rodzajów maili (MAIL_CATEGORIES)."""
        try:
            return {k for k in json.loads(user.mail_prefs or '[]') if k in MAIL_CATEGORY_KEYS}
        except (TypeError, ValueError):
            return set()

    def wants_mail(user, category):
        return category not in mail_disabled(user)

    def mail_prefs_serializer():
        return URLSafeSerializer(app.config['SECRET_KEY'], salt='maile-ustawienia')

    def mail_prefs_url(user, root, category=None):
        """Osobisty link do ustawień maili - działa bez logowania (podpisany id użytkownika)."""
        url = root.rstrip('/') + '/maile/ustawienia/' + mail_prefs_serializer().dumps(user.id)
        return url + (f'?rodzaj={category}' if category else '')

    def save_mail_prefs(user, enabled):
        user.mail_prefs = json.dumps([k for k in MAIL_CATEGORY_KEYS if k not in enabled]) if set(enabled) != set(MAIL_CATEGORY_KEYS) else None
        db.session.commit()

    def mail_footer(prefs_url):
        """Stopka z linkiem do ustawień - dokładana do maili HTML, które jej nie mają."""
        return ('<div style="font-family:Arial,Helvetica,sans-serif;font-size:12px;color:#888;text-align:center;padding:12px">'
                f'Nie chcesz takich maili? <a href="{prefs_url}" style="color:#ff9d2e">Zmień, jakie maile dostajesz</a> '
                '- bez logowania.</div>')

    @app.route('/maile/ustawienia/<token>', methods=['GET', 'POST'])
    def mail_prefs_public(token):
        """Ustawienia maili z linku w mailu (bez logowania). Obsługuje też „Anuluj subskrypcję” w Gmailu
        (List-Unsubscribe-Post: POST z List-Unsubscribe=One-Click wyłącza rodzaj z ?rodzaj=, a bez niego wszystkie)."""
        try:
            user = db.session.get(User, int(mail_prefs_serializer().loads(token)))
        except (BadSignature, TypeError, ValueError):
            user = None
        if not user:
            abort(404)
        category = request.args.get('rodzaj') if request.args.get('rodzaj') in MAIL_CATEGORY_KEYS else None
        if request.method == 'POST' and request.form.get('List-Unsubscribe') == 'One-Click':
            enabled = set(MAIL_CATEGORY_KEYS) - mail_disabled(user) - ({category} if category else set(MAIL_CATEGORY_KEYS))
            save_mail_prefs(user, enabled)
            return '', 204
        if request.method == 'POST':
            save_mail_prefs(user, set(request.form.getlist('rodzaj')))
            flash('Zapisano - od teraz dostajesz tylko zaznaczone maile.', 'success')
            return redirect(url_for('mail_prefs_public', token=token))
        return render_template('maile_ustawienia.html', user=user, disabled=mail_disabled(user), categories=MAIL_CATEGORIES,
                               highlight=category, action=url_for('mail_prefs_public', token=token))

    @app.route('/user_settings/maile', methods=['POST'])
    @login_required
    def mail_prefs_save():
        save_mail_prefs(current_user, set(request.form.getlist('rodzaj')))
        flash('Zapisano ustawienia maili.', 'success')
        return redirect(url_for('user_settings') + '#maile')

    def send_mail_jobs(jobs, log_subject):
        """Wysyła przygotowane maile [(user_id, adres, temat, html[, link do ustawień])] jednym połączeniem SMTP
        i zapisuje wynik w MailLog. Link do ustawień idzie też w nagłówku List-Unsubscribe (przycisk w Gmailu)."""
        send_mail_jobs.last_ok = 0
        with app.app_context():
            try:
                with mail.connect() as conn:
                    for user_id, address, subject, html, *rest in jobs:
                        headers = {}
                        if rest and rest[0]:
                            headers = {'List-Unsubscribe': f'<{rest[0]}>', 'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click'}
                        try:
                            conn.send(Message_(subject=subject, recipients=[address], html=html, extra_headers=headers or None))
                            ok = True
                            send_mail_jobs.last_ok += 1
                        except Exception:
                            app.logger.exception('Mail do użytkownika %s nie wyszedł', user_id)
                            ok = False
                        if log_subject:
                            db.session.add(MailLog(subject=log_subject, user_id=user_id, ok=ok))
                            db.session.commit()
                        time.sleep(0.3)
            except Exception:
                app.logger.exception('Brak połączenia z serwerem poczty')
                db.session.rollback()

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

    def pick_fifa_club(event_id, user_id):
        """Klub z formularza (liga + klub albo „Inna drużyna”) -> (nazwa, błąd). Klub może mieć tylko jeden gracz."""
        club = resolve_club(request.form.get("league"), request.form.get("club"), request.form.get("club_custom"))
        if not club:
            return None, "Wybierz ligę i klub."
        taken = FifaParticipant.query.filter(FifaParticipant.event_id == event_id, FifaParticipant.role == "player",
                                             FifaParticipant.user_id != user_id,
                                             func.lower(func.trim(FifaParticipant.club)) == club.strip().lower()).first()
        if taken:
            owner = User.query.get(taken.user_id)
            return None, f"{club} - ten klub ma już {owner.username if owner else 'inny gracz'}. Wybierz inny."
        return club, None

    def fifa_started(event_id):
        tournament = Tournament.query.filter_by(event_id=event_id).first()
        return bool(tournament and tournament.started)

    @app.route("/fifa/<int:event_id>/klub", methods=["POST"])
    @login_required
    def change_fifa_club(event_id):
        """Gracz zmienia klub - tylko dopóki turniej się nie zaczął."""
        entry = FifaParticipant.query.filter_by(event_id=event_id, user_id=current_user.id, role="player").first_or_404()
        if fifa_started(event_id):
            flash("Turniej już trwa - klubu nie można zmienić.", "warning")
            return redirect(request.referrer or url_for("calendar"))
        club, error = pick_fifa_club(event_id, current_user.id)
        if error:
            flash(error, "danger")
        else:
            entry.club = club
            db.session.commit()
            flash(f"Grasz teraz jako {club} ⚽", "success")
        return redirect(request.referrer or url_for("calendar"))

    @app.route("/join_fifa_event/<int:event_id>", methods=["POST"])
    @login_required
    def join_fifa_event(event_id):
        role = request.form.get("role")
        if role not in ("player", "observer"):
            flash("Wybierz, czy grasz, czy oglądasz.", "warning")
            return redirect(request.referrer)
        club = None
        if role == "player":
            club, error = pick_fifa_club(event_id, current_user.id)
            if error:
                flash(error, "danger")
                return redirect(request.referrer)

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

    # ===================== Turbo Skok (wyścig platformowy na czas) =====================

    def skok_best_times(track, limit=10):
        """Najlepszy czas każdego gracza na trasie: [(user, czas ms)] od najszybszego."""
        rows = db.session.query(Skok.created_by, func.min(Skok.time_ms)).filter(Skok.track == track) \
            .group_by(Skok.created_by).all()
        ids = [int(r[0]) for r in rows if r[0] and str(r[0]).isdigit()]
        users = {str(u.id): u for u in User.query.filter(User.id.in_(ids))} if ids else {}
        rows = sorted((r for r in rows if str(r[0]) in users), key=lambda r: r[1])
        return [(users[str(r[0])], r[1]) for r in rows][:limit] if limit else [(users[str(r[0])], r[1]) for r in rows]

    def skok_points(track, time_ms):
        return min(3000, round(1000 * SKOK_TRACKS[track][1] / max(1, time_ms)))

    @app.route('/skok')
    @login_required
    def skok():
        me = str(current_user.id)
        tracks = []
        for key, (name, par, _) in SKOK_TRACKS.items():
            best = db.session.query(func.min(Skok.time_ms)).filter(Skok.track == key, Skok.created_by == me).scalar()
            top = skok_best_times(key, 1)
            tracks.append({'key': key, 'name': name, 'par': par, 'best': best,
                           'record': {'user': top[0][0].username, 'time': top[0][1]} if top else None})
        return render_template('skok.html', tracks=tracks, profile=skok_profile(current_user.id), colors=SKOK_COLORS,
                               stat_points=SKOK_STAT_POINTS, race_max=SKOK_RACE_MAX)

    @app.route('/skok/duchy/<track>')
    @login_required
    def skok_ghosts(track):
        """Duchy na trasę: rekordzisty i mój najlepszy przejazd (gdy to nie ten sam)."""
        if track not in SKOK_TRACKS:
            abort(404)
        ghosts, seen = [], set()
        top = skok_best_times(track, 3)
        wanted = [u.id for u, _ in top[:1]] + [current_user.id]
        for uid in wanted:
            if uid in seen:
                continue
            seen.add(uid)
            run = Skok.query.filter(Skok.track == track, Skok.created_by == str(uid), Skok.ghost.isnot(None)) \
                .order_by(Skok.time_ms).first()
            if run:
                user = db.session.get(User, uid)
                ghosts.append({'name': user.username if user else '?', 'me': uid == current_user.id, 'time': run.time_ms,
                               'path': json.loads(run.ghost)})
        return jsonify({'ok': True, 'ghosts': ghosts})

    @app.route('/skok/save_score', methods=['POST'])
    @login_required
    def save_score_skok():
        data = request.get_json(silent=True) or {}
        track = data.get('track')
        try:
            time_ms = int(data.get('time'))
        except (TypeError, ValueError):
            return jsonify({'ok': False}), 400
        if track not in SKOK_TRACKS:
            return jsonify({'ok': False}), 400
        ghost = data.get('ghost')
        run = GameRun.query.get(str(data.get('run') or ''))
        started = run.started_at if run else None
        error = check_game_run('skok', 0, data)
        if error:
            return jsonify({'ok': False, 'error': error}), 400
        name, par, min_ms = SKOK_TRACKS[track]
        elapsed_ms = (datetime.utcnow() - started).total_seconds() * 1000
        # czas z gry musi zgadzać się z czasem rzeczywistym od biletu (bilet bierze się na „START!”)
        steps = time_ms / SKOK_GHOST_STEP_MS
        ghost_ok = isinstance(ghost, list) and steps * 0.7 - 5 <= len(ghost) <= min(SKOK_GHOST_MAX, steps * 1.3 + 5) \
            and all(isinstance(p, list) and len(p) == 2 and all(isinstance(v, int) for v in p) for p in ghost)
        if time_ms < min_ms or not elapsed_ms - 5000 <= time_ms <= elapsed_ms + 3000 or not ghost_ok:
            app.logger.warning('Odrzucony przejazd skok: user=%s trasa=%s czas=%s realnie=%.0f duch=%s',
                               current_user.id, track, time_ms, elapsed_ms, len(ghost) if isinstance(ghost, list) else None)
            return jsonify({'ok': False, 'error': 'Ten czas wygląda na niemożliwy - nie został zapisany.'}), 400
        me = str(current_user.id)
        previous = db.session.query(func.min(Skok.time_ms)).filter(Skok.track == track, Skok.created_by == me).scalar()
        new_best = previous is None or time_ms < previous
        if new_best:      # trzymamy tylko ducha z najlepszego przejazdu gracza na trasie
            Skok.query.filter(Skok.track == track, Skok.created_by == me, Skok.ghost.isnot(None)) \
                .update({Skok.ghost: None}, synchronize_session=False)
        db.session.add(Skok(points=skok_points(track, time_ms), created_by=me, track=track, time_ms=time_ms,
                            ghost=json.dumps(ghost, separators=(',', ':')) if new_best else None))
        db.session.commit()
        times = skok_best_times(track, 0)
        place = next((i for i, (u, _) in enumerate(times, 1) if u.id == current_user.id), None)
        return jsonify({'ok': True, 'best': time_ms if new_best else previous, 'new_best': new_best,
                        'points': skok_points(track, time_ms), 'place': place, 'players': len(times),
                        'record': {'user': times[0][0].username, 'time': times[0][1]} if times else None})

    @app.route('/ranking_skok')
    @login_required
    def ranking_skok():
        ranking_data, rozegranych_gier = game_ranking(Skok, true())
        tracks = [{'key': key, 'name': name, 'times': skok_best_times(key, 10)} for key, (name, _, _) in SKOK_TRACKS.items()]
        return render_template('ranking_skok.html', ranking_data=ranking_data, rozegranych_gier=rozegranych_gier,
                               tracks=tracks)

    # ----- postać i wyścigi na żywo -----

    def skok_profile(user_id):
        prof = db.session.get(SkokProfile, user_id)
        if prof is None:
            return {'speed': 50, 'accel': 50, 'jump': 50, 'color': SKOK_COLORS[user_id % len(SKOK_COLORS)]}
        return {'speed': prof.speed, 'accel': prof.accel, 'jump': prof.jump, 'color': prof.color}

    @app.route('/skok/profil', methods=['POST'])
    @login_required
    def skok_profile_save():
        data = request.get_json(silent=True) or {}
        try:
            stats = {k: int(data.get(k)) for k in ('speed', 'accel', 'jump')}
        except (TypeError, ValueError):
            return jsonify({'ok': False, 'error': 'Złe statystyki.'}), 400
        color = data.get('color')
        if any(not 0 <= v <= 100 for v in stats.values()) or sum(stats.values()) > SKOK_STAT_POINTS or color not in SKOK_COLORS:
            return jsonify({'ok': False, 'error': f'Każda statystyka 0-100, razem najwyżej {SKOK_STAT_POINTS}.'}), 400
        prof = db.session.get(SkokProfile, current_user.id) or SkokProfile(user_id=current_user.id)
        prof.speed, prof.accel, prof.jump, prof.color = stats['speed'], stats['accel'], stats['jump'], color
        db.session.add(prof)
        db.session.commit()
        return jsonify({'ok': True, 'profile': skok_profile(current_user.id)})

    def skok_race_tick(race, now):
        """Zegar wyścigu (leniwie, przy każdym pytaniu): odpadanie nieobecnych, start, koniec, zapis wyników."""
        racers = SkokRacer.query.filter_by(race_id=race.id).all()
        if race.status == 'lobby':
            for r in racers:
                if r.seen < now - SKOK_RACER_TIMEOUT:
                    db.session.delete(r)
            racers = [r for r in racers if r.seen >= now - SKOK_RACER_TIMEOUT]
            if not racers:
                db.session.delete(race)
                return None
            if race.host_id not in [r.user_id for r in racers]:
                race.host_id = racers[0].user_id      # gospodarz wyszedł - przejmuje następny
            if len(racers) >= 2 and race.auto_at is None:
                race.auto_at = now + SKOK_AUTOSTART
            elif len(racers) < 2:
                race.auto_at = None
            if race.auto_at and now >= race.auto_at:
                race.status, race.start_at = 'count', now + SKOK_COUNTDOWN
        if race.status == 'count' and now >= race.start_at:
            race.status = 'run'
        if race.status == 'run':
            active = [r for r in racers if r.seen >= now - SKOK_RACER_TIMEOUT or r.finish_ms]
            finished = [r for r in racers if r.finish_ms]
            first_at = race.start_at + min(r.finish_ms for r in finished) / 1000 if finished else None
            if (active and all(r.finish_ms for r in active)) or not active \
                    or (first_at and now > first_at + SKOK_AFTER_FIRST) or now > race.start_at + SKOK_RACE_MAX_TIME:
                race.status, race.end_at = 'done', now
        if race.status == 'done' and not race.recorded:
            race.recorded = True
            # ukończony wyścig = przejazd w Turbo Skoku (Hall of Fame, kasa za grę, najlepsze czasy)
            for r in racers:
                if r.finish_ms:
                    db.session.add(Skok(points=skok_points(race.course, r.finish_ms), created_by=str(r.user_id),
                                        track=race.course, time_ms=r.finish_ms))
            standings_cache['data'] = None
        return race

    def skok_race_view(race, now, user_id, since=0):
        racers = SkokRacer.query.filter_by(race_id=race.id).all()
        order = sorted([r for r in racers if r.finish_ms], key=lambda r: r.finish_ms)
        places = {r.user_id: i for i, r in enumerate(order, 1)}
        events = SkokEvent.query.filter(SkokEvent.race_id == race.id, SkokEvent.id > since).order_by(SkokEvent.id).all() \
            if since >= 0 else []
        return {'id': race.id, 'course': race.course, 'status': race.status, 'host': race.host_id == user_id,
                'now': now, 'auto_at': race.auto_at, 'start_at': race.start_at,
                'racers': [{'uid': r.user_id, 'name': r.name, 'photo': r.photo, 'color': r.color, 'me': r.user_id == user_id,
                            'stats': json.loads(r.stats), 'state': json.loads(r.state) if r.state else None,
                            'finish_ms': r.finish_ms, 'place': places.get(r.user_id),
                            'away': r.seen < now - SKOK_RACER_TIMEOUT and not r.finish_ms} for r in racers],
                'events': [{'id': e.id, 'uid': e.user_id, 'kind': e.kind, 'data': json.loads(e.data or '{}')}
                           for e in events if e.user_id != user_id],
                'last_event': events[-1].id if events else since}

    def skok_join(race, now):
        prof = skok_profile(current_user.id)
        SkokRacer.query.filter(SkokRacer.user_id == current_user.id, SkokRacer.race_id != race.id).delete()
        db.session.merge(SkokRacer(race_id=race.id, user_id=current_user.id, name=current_user.username,
                                   photo=avatar_url(current_user.photo), color=prof['color'],
                                   stats=json.dumps({k: prof[k] for k in ('speed', 'accel', 'jump')}), seen=now))

    @app.route('/skok/wyscigi')
    @login_required
    def skok_races():
        """Lobby: otwarte i trwające wyścigi."""
        now = time.time()
        old = [r.id for r in SkokRace.query.filter(SkokRace.created_at < now - 3600).all()]
        if old:     # sprzątanie po starych wyścigach (pozycje i zdarzenia też)
            SkokEvent.query.filter(SkokEvent.race_id.in_(old)).delete(synchronize_session=False)
            SkokRacer.query.filter(SkokRacer.race_id.in_(old)).delete(synchronize_session=False)
            SkokRace.query.filter(SkokRace.id.in_(old)).delete(synchronize_session=False)
        rows = []
        for race in SkokRace.query.order_by(SkokRace.id.desc()).all():
            race = skok_race_tick(race, now)
            if not race or (race.status == 'done' and now - (race.end_at or now) > 60):
                continue
            racers = SkokRacer.query.filter_by(race_id=race.id).all()
            rows.append({'id': race.id, 'course': race.course, 'course_name': SKOK_TRACKS.get(race.course, ('?',))[0],
                         'status': race.status, 'players': [{'name': r.name, 'photo': r.photo, 'color': r.color} for r in racers],
                         'mine': any(r.user_id == current_user.id for r in racers)})
        db.session.commit()
        return jsonify({'ok': True, 'races': rows, 'max': SKOK_RACE_MAX})

    @app.route('/skok/wyscigi', methods=['POST'])
    @login_required
    def skok_race_create():
        course = (request.get_json(silent=True) or {}).get('course')
        if course not in SKOK_TRACKS:
            return jsonify({'ok': False, 'error': 'Wybierz trasę.'}), 400
        now = time.time()
        race = SkokRace(course=course, status='lobby', host_id=current_user.id, created_at=now)
        db.session.add(race)
        db.session.flush()
        skok_join(race, now)
        db.session.commit()
        return jsonify({'ok': True, 'race': skok_race_view(race, now, current_user.id)})

    @app.route('/skok/wyscig/<int:race_id>/dolacz', methods=['POST'])
    @login_required
    def skok_race_join(race_id):
        now = time.time()
        race = db.session.get(SkokRace, race_id)
        race = skok_race_tick(race, now) if race else None
        if not race or race.status != 'lobby':
            db.session.commit()
            return jsonify({'ok': False, 'error': 'Ten wyścig już wystartował albo się skończył.'}), 400
        count = SkokRacer.query.filter(SkokRacer.race_id == race.id, SkokRacer.user_id != current_user.id).count()
        if count >= SKOK_RACE_MAX:
            return jsonify({'ok': False, 'error': f'Wyścig pełny ({SKOK_RACE_MAX} osoby).'}), 400
        skok_join(race, now)
        skok_race_tick(race, now)
        db.session.commit()
        return jsonify({'ok': True, 'race': skok_race_view(race, now, current_user.id)})

    @app.route('/skok/wyscig/<int:race_id>/opusc', methods=['POST'])
    @login_required
    def skok_race_leave(race_id):
        racer = db.session.get(SkokRacer, (race_id, current_user.id))
        race = db.session.get(SkokRace, race_id)
        if racer and race and race.status in ('lobby', 'count'):
            db.session.delete(racer)
        elif racer:
            racer.seen = 0          # w trakcie wyścigu: zostaje na liście jako nieukończony
        db.session.commit()
        return jsonify({'ok': True})

    @app.route('/skok/wyscig/<int:race_id>/start', methods=['POST'])
    @login_required
    def skok_race_start(race_id):
        now = time.time()
        race = db.session.get(SkokRace, race_id)
        race = skok_race_tick(race, now) if race else None
        if not race or race.status != 'lobby' or race.host_id != current_user.id:
            db.session.commit()
            return jsonify({'ok': False, 'error': 'Start może dać tylko gospodarz, przed wyścigiem.'}), 400
        if SkokRacer.query.filter_by(race_id=race.id).count() < 2:
            return jsonify({'ok': False, 'error': 'Potrzeba co najmniej 2 osób - sam zagraj w czasówkę.'}), 400
        race.status, race.start_at = 'count', now + SKOK_COUNTDOWN
        db.session.commit()
        return jsonify({'ok': True, 'race': skok_race_view(race, now, current_user.id)})

    @app.route('/skok/wyscig/<int:race_id>/sync', methods=['POST'])
    @login_required
    def skok_race_sync(race_id):
        """Gra wysyła swój stan (co ~120 ms) i dostaje stan innych graczy oraz nowe zdarzenia."""
        data = request.get_json(silent=True) or {}
        now = time.time()
        race = db.session.get(SkokRace, race_id)
        racer = db.session.get(SkokRacer, (race_id, current_user.id)) if race else None
        if racer:
            racer.seen = now        # przed zegarem wyścigu - inaczej gracz wyglądałby na nieobecnego
            db.session.flush()
        race = skok_race_tick(race, now) if race else None
        if not race or not racer:
            db.session.commit()
            return jsonify({'ok': False, 'error': 'Nie ma Cię w tym wyścigu.'}), 404
        state = data.get('state')
        if isinstance(state, dict) and race.status == 'run':
            racer.state = json.dumps(state, separators=(',', ':'))[:600]
        for ev in (data.get('events') or [])[:10]:
            if isinstance(ev, dict) and ev.get('kind') in ('mine', 'boom', 'laser') and race.status == 'run':
                db.session.add(SkokEvent(race_id=race.id, user_id=current_user.id, kind=ev['kind'],
                                         data=json.dumps(ev.get('data') or {}, separators=(',', ':'))[:300], at=now))
        if data.get('finish_ms') is not None and race.status == 'run' and not racer.finish_ms:
            try:
                ms = int(data['finish_ms'])
            except (TypeError, ValueError):
                ms = -1
            elapsed = (now - race.start_at) * 1000
            # czas z gry musi zgadzać się z zegarem serwera od „START!”
            if ms >= SKOK_TRACKS[race.course][2] and abs(ms - elapsed) < 3000:
                racer.finish_ms = ms
            else:
                app.logger.warning('Odrzucona meta wyścigu: user=%s czas=%s serwer=%.0f', current_user.id, ms, elapsed)
        db.session.flush()
        skok_race_tick(race, now)
        try:
            since = int(data.get('since') or 0)
        except (TypeError, ValueError):
            since = 0
        view = skok_race_view(race, now, current_user.id, since)
        db.session.commit()
        return jsonify({'ok': True, 'race': view})

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
