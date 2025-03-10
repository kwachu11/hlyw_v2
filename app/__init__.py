
from dotenv import load_dotenv
import os
import glob
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import json
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from flask import render_template, redirect, url_for, request
from flask_login import login_user, login_required, logout_user
from werkzeug.security import generate_password_hash, check_password_hash

from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user, LoginManager, UserMixin
from .forms import LoginForm, RegistrationForm
from itsdangerous import URLSafeTimedSerializer

from app.forms import AlbumForm, ImageForm, NewsForm, CalendarForm, UserSettingsForm, ReportForm, CommentForm

import locale

from datetime import datetime, timedelta
import calendar as callendar
from datetime import date

from flask_mail import Mail, Message as Message_
import base64
from ftplib import FTP
from flask import session
import time

# Wczytaj zmienne środowiskowe z pliku .env





def create_app():
    load_dotenv()
    app = Flask(__name__)
    db = SQLAlchemy()

    app.secret_key = os.getenv('SECRET_KEY')  # Ustawienie secret key do sesji
    app.config['SECURITY_PASSWORD_SALT']="abcd1234abcdef"
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
    db.init_app(app)

    # Tworzymy instancję LoginManager
    login_manager = LoginManager(app)
    login_manager.login_view = 'login'  # Widok logowania, jeśli użytkownik nie jest zalogowany
    login_manager.login_message = os.getenv('LOGIN_MESSAGE')  # Niestandardowy komunikat
    login_manager.login_message_category = os.getenv('LOGIN_MESSAGE_CATEGORY') # Opcjonalna kategoria (np. warning)

    # Inicjalizujemy login_manager z aplikacją
    login_manager.init_app(app)

    #maile
    app.config['MAIL_SERVER'] = 'smtp.d243.mikr.dev'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'support@hlyw.pl'  # Twój adres email
    app.config['MAIL_PASSWORD'] = 'SupportEmail+_11'  # Hasło do konta
    app.config['MAIL_DEFAULT_SENDER'] = 'support@hlyw.pl'

    mail = Mail(app)
    active_users = {}

    def convert_to_unix_path(path):
        return path.replace('\\', '/')

    def create_directory_if_not_exists(path):
        """Utwórz katalog, jeśli nie istnieje."""
        if not os.path.exists(path):
            os.makedirs(path)

    def get_event_days(year, month):
        events = Calendar.query.filter(
            db.extract('year', Calendar.date) == year,
            db.extract('month', Calendar.date) == month
        ).all()

        event_days = [event.date.day for event in events]
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

    def manage_files(folder_path, max_files):
        """
        Funkcja usuwa najstarsze pliki w folderze, zostawiając tylko max_files najnowszych.
        """
        # Pobierz listę plików w folderze, posortowaną według daty modyfikacji (od najstarszych do najnowszych)
        files = sorted(
            [os.path.join(folder_path, f) for f in os.listdir(folder_path) if
             os.path.isfile(os.path.join(folder_path, f))],
            key=os.path.getmtime
        )

        # Usuń pliki, jeśli jest ich więcej niż max_files
        while len(files) > max_files:
            oldest_file = files.pop(0)  # Pobierz najstarszy plik
            os.remove(oldest_file)  # Usuń plik
            print(f"Usunięto plik: {oldest_file}")  # Logowanie usunięcia pliku (opcjonalne)

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
        date = db.Column(db.Date, nullable=False)
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

    class QuizParticipant(db.Model):  # Poprawiona nazwa na liczbie pojedynczej
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(500), nullable=False)  # Dodano ograniczenie NOT NULL
        score = db.Column(db.Integer, default=0)  # Wynik domyślnie 0

        # Powiązanie z odpowiedziami (relacja odwrotna)
        answers = db.relationship('QuizAnswer', backref='participant', lazy=True)

    class QuizQuestion(db.Model):  # Poprawiona nazwa na liczbie pojedynczej
        id = db.Column(db.Integer, primary_key=True)
        question_text = db.Column(db.Text, nullable=False)  # Użyto Text zamiast String dla dłuższych pytań
        is_active = db.Column(db.Boolean, default=False)
        type = db.Column(db.Integer, nullable=False, default="0")
        correct_answer=db.Column(db.String(500), nullable=False)
        options=db.Column(db.String(500), nullable=True)

        # Powiązanie z odpowiedziami (relacja odwrotna)
        answers = db.relationship('QuizAnswer', backref='question', lazy=True)

    class QuizAnswer(db.Model):  # Poprawiona nazwa na liczbie pojedynczej
        id = db.Column(db.Integer, primary_key=True)
        answer = db.Column(db.Text, nullable=False)  # Użyto Text zamiast String dla dłuższych odpowiedzi

        # Powiązanie z uczestnikiem
        participant_id = db.Column(db.Integer, db.ForeignKey('quiz_participant.id'), nullable=False)

        # Powiązanie z pytaniem
        question_id = db.Column(db.Integer, db.ForeignKey('quiz_question.id'), nullable=False)

    # Tworzenie tabel w bazie danych przy starcie aplikacji
    with app.app_context():
        db.create_all()


    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.route('/')
    def index():
        images=[]
        images.append("static\images\hlyw_1.jpg")
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


        return render_template('index.html', images=images)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            if not user.confirmed:
                flash('Twoje konto nie zostało potwierdzone. Sprawdź swoją skrzynkę pocztową.', 'warning')
                return redirect(url_for('login'))
            if user and user.password == form.password.data:  # Hasło powinno być hashowane
                login_user(user)
                return redirect(url_for('index'))
            else:
                flash('Niepoprawna nazwa użytkownika lub hasło', 'danger')
        return render_template('login.html', form=form)

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

            if form.password.data != form.confirm_password.data:
                flash('Hasła nie są zgodne.', 'danger')
                return redirect(url_for('register'))

            else:
                new_user = User(username=form.username.data, email=form.email.data, password=form.password.data)  # Hasło powinno być hashowane
                db.session.add(new_user)
                db.session.commit()
                send_confirmation_email(new_user.email)
                flash('Zarejestrowano pomyślnie! Sprawdź swoją skrzynkę pocztową w celu potwierdzenia konta.',
                      'success')
                return redirect(url_for('login'))
        return render_template('register.html', form=form)

    @app.route('/albums', methods=['GET'])
    @login_required
    def albums():
        all_album = Albums.query.all()
        images_no_album=Images.query.filter_by(album_id=0).all()
        return render_template('albums.html', album=all_album, images=images_no_album)

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
            file = form.file.data
            album_id = request.args.get('album_id')

            if album_id == None:
                album_id='0'

            file_path = os.path.join('app', 'static', 'images', album_id, file.filename)
            print(file_path)

            # Utwórz katalog, jeśli nie istnieje
            create_directory_if_not_exists(os.path.dirname(file_path))

            file.save(file_path)
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
        return render_template('breaking_news.html', news=all_news)

    @app.route('/add_new', methods=['GET', 'POST'])
    @login_required
    def add_new():
        form = NewsForm()
        if form.validate_on_submit():
            title = form.title.data
            description = form.description.data
            file = form.file.data

            file_path = os.path.join('app', 'static', 'images', 'newsy', file.filename)
            print(file_path)

            # Utwórz katalog, jeśli nie istnieje
            create_directory_if_not_exists(os.path.dirname(file_path))

            file.save(file_path)
            file_path = file_path[4:]  # do bazy bez app

            news = News(title=title, description=description, file_path=file_path, created_by=current_user.id)
            db.session.add(news)
            db.session.commit()
            return redirect(url_for('news'))
        return render_template('add_new.html', form=form)

    @app.route('/calendar', methods=['GET'])
    @login_required
    def calendar():
        locale.setlocale(locale.LC_TIME, 'pl_PL.UTF-8')
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
        print(event_days)

        return render_template('calendar.html',
                               calendar=cal,
                               year=year,
                               month=month,
                               month_name=callendar.month_name[month],
                               previous_month=previous_month,
                               previous_year=previous_year,
                               next_month=next_month,
                               next_year=next_year,
                               event_days=event_days)

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
        add_user=request.args.get('add_user', type=int)



        query_date = date(year, month, day)

        event = Calendar.query.filter_by(date=query_date).first()
        owner= User.query.filter_by(id=event.created_by).first()

        if add_user!=None:
            new_Participant = Participant(user_id=add_user, event_id=event.id)
            db.session.add(new_Participant)
            db.session.commit()
            flash('Zapisałeś się na wydarzenie !', 'success')

        participants=Participant.query.filter_by(event_id=event.id).all()



        czy_zapisany=False
        participants_names=[]
        for i in participants:
            name = User.query.filter_by(id=i.user_id).first()
            participants_names.append(name)
            if current_user.id == int(i.user_id):
                czy_zapisany=True


        return render_template('event.html', day=day, month=month, year=year,
                               event=event, owner=owner, participants=participants, czy_zapisany=czy_zapisany,
                               current_user=current_user, participants_names=participants_names)



    @app.route('/camera')
    @login_required
    def camera():
        return render_template('camera.html')

    @app.route('/user_settings', methods=['GET', 'POST'])
    @login_required
    def user_settings():
        form = UserSettingsForm()

        if form.validate_on_submit():
            # Zaktualizuj nazwę użytkownika i email
            current_user.username = form.username.data

            # Zaktualizuj zdjęcie, jeśli użytkownik je dodał
            if form.photo.data:
                file = form.photo.data
                file_path = os.path.join('app', 'static', 'images','profile_pics', file.filename)
                #print(file_path)

                # Utwórz katalog, jeśli nie istnieje
                create_directory_if_not_exists(os.path.dirname(file_path))

                file.save(file_path)
                file_path = file_path[31:]  # do bazy bez sciezki
                current_user.photo = file_path

            # Zapisz zmiany w bazie danych
            db.session.commit()
            return redirect(url_for('user_settings'))  # Przekieruj po zapisaniu zmian

        # Ustaw pola formularza na obecne dane użytkownika
        form.username.data = current_user.username

        return render_template('user_settings.html', form=form)

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
        messages = Message.query.order_by(Message.timestamp.desc()).limit(10).all()
        messages_data = []

        for msg in messages:
            user = msg.user  # Dostęp do użytkownika powiązanego z wiadomością
            messages_data.append({
                "content": msg.content,
                "timestamp": msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                "username": user.username,  # Dodajemy nazwę użytkownika
                "photo": user.photo  # Dodajemy zdjęcie użytkownika
            })

        return jsonify({"messages": messages_data})

    @app.route('/ostatnie-ulepszenia')
    def ostatnie_ulepszenia():
        # Pobierz ostatnie ulepszenia z bazy danych
        upgrades = Upgrade.query.order_by(Upgrade.date.desc()).all()
        return render_template('ostatnie_ulepszenia.html', upgrades=upgrades)

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
        return render_template('view_report_list.html', reports=reports)

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

    @app.route('/snake', methods=['GET', 'POST'])
    @login_required
    def snake():
        return render_template('snake.html')

    @app.route('/snake/save_score', methods=['POST'])
    def save_score():
        data = request.get_json()
        score = data.get('score')

        # Dodaj wiadomość flash
        flash(f'Wynik: {score}.', 'success')  # Użyj 'success' jako kategorii

        new_game = Snake(points=int(score), created_by=current_user.id)
        db.session.add(new_game)
        db.session.commit()

        # Przekieruj do strony, gdzie chcesz wyświetlić wiadomość
        return jsonify({'redirect_url': url_for('snake')})

    @app.route('/games', methods=['GET'])
    @login_required
    def games():
        snake_leader = Snake.query.order_by(Snake.points.desc()).first()
        user=User.query.filter_by(id=snake_leader.created_by).first()
        tetris_leader = Tetris.query.order_by(Tetris.points.desc()).first()
        user2 = User.query.filter_by(id=tetris_leader.created_by).first()
        dino_leader = Dino.query.order_by(Dino.points.desc()).first()
        user3 = User.query.filter_by(id=dino_leader.created_by).first()
        games=[]
        games.append(['Snake', 'static/images/snake.png', snake_leader, user, 'snake', 'ranking_snake'])
        games.append(['Tetris', 'static/images/tetris.png', tetris_leader, user2, 'tetris', 'ranking_tetris'])
        games.append(['Dino', 'static/images/dino.png', dino_leader, user3, 'dino', 'ranking_dino'])
        print(games)
        return render_template('games.html', games=games)

    @app.route('/tetris', methods=['GET', 'POST'])
    @login_required
    def tetris():
        return render_template('tetris.html')

    @app.route('/tetris/save_score', methods=['POST'])
    def save_score_tetris():
        data = request.get_json()
        score = data.get('score')

        # Dodaj wiadomość flash
        flash(f'Wynik: {score}.', 'success')  # Użyj 'success' jako kategorii

        new_game = Tetris(points=int(score), created_by=current_user.id)
        db.session.add(new_game)
        db.session.commit()

        # Przekieruj do strony, gdzie chcesz wyświetlić wiadomość
        return jsonify({'redirect_url': url_for('tetris')})

    @app.route('/dino/save_score', methods=['POST'])
    def save_score_dino():
        data = request.get_json()
        score = data.get('score')

        # Dodaj wiadomość flash
        flash(f'Wynik: {score}.', 'success')  # Użyj 'success' jako kategorii

        new_game = Dino(points=int(score), created_by=current_user.id)
        db.session.add(new_game)
        db.session.commit()

        # Przekieruj do strony, gdzie chcesz wyświetlić wiadomość
        return jsonify({'redirect_url': url_for('dino')})

    @app.route('/ranking_snake', methods=['GET', 'POST'])
    @login_required
    def ranking_snake():
        ranking_data = db.session.query(
            User.id,
            User.username,
            User.photo,
            func.count(Snake.id).label('attempts'),  # Ilość prób
            func.sum(Snake.points).label('total_points'),  # Suma zdobytych punktów
            func.max(Snake.points).label('high_score')  # Najwyższy wynik (rekord)
        ).outerjoin(Snake, Snake.created_by == User.id) \
            .group_by(User.id) \
            .having(func.max(Snake.points) != None) \
            .order_by(func.max(Snake.points).desc()) \
            .all()

        rozegranych_gier = Snake.query.count()

        return render_template('ranking_snake.html', ranking_data=ranking_data, rozegranych_gier=rozegranych_gier)

    @app.route('/ranking_tetris', methods=['GET', 'POST'])
    @login_required
    def ranking_tetris():
        ranking_data = db.session.query(
            User.id,
            User.username,
            User.photo,
            func.count(Tetris.id).label('attempts'),  # Ilość prób
            func.sum(Tetris.points).label('total_points'),  # Suma zdobytych punktów
            func.max(Tetris.points).label('high_score')  # Najwyższy wynik (rekord)
        ).outerjoin(Tetris, Tetris.created_by == User.id) \
            .group_by(User.id) \
            .having(func.max(Tetris.points) != None) \
            .order_by(func.max(Tetris.points).desc()) \
            .all()

        rozegranych_gier = Tetris.query.count()

        return render_template('ranking_tetris.html', ranking_data=ranking_data, rozegranych_gier=rozegranych_gier)


    @app.route('/ranking_dino', methods=['GET', 'POST'])
    @login_required
    def ranking_dino():
        ranking_data = db.session.query(
            User.id,
            User.username,
            User.photo,
            func.count(Dino.id).label('attempts'),  # Ilość prób
            func.sum(Dino.points).label('total_points'),  # Suma zdobytych punktów
            func.max(Dino.points).label('high_score')  # Najwyższy wynik (rekord)
        ).outerjoin(Dino, Dino.created_by == User.id) \
            .group_by(User.id) \
            .having(func.max(Dino.points) != None) \
            .order_by(func.max(Dino.points).desc()) \
            .all()

        rozegranych_gier = Dino.query.count()

        return render_template('ranking_dino.html', ranking_data=ranking_data, rozegranych_gier=rozegranych_gier)

    @app.route('/dino', methods=['GET', 'POST'])
    @login_required
    def dino():
        return render_template('dino.html')

    @app.route('/quiz', methods=['GET', 'POST'])
    @login_required
    def quiz():
        options = []
        pobrane = ""
        pytanie = QuizQuestion.query.filter_by(is_active="1").first()
        if pytanie == None:
            pytanie="Czekaj na pytanie..."




        odpowiedz = QuizAnswer.query.filter_by(question_id=pytanie.id, participant_id=current_user.id).first()



        return render_template('quiz.html', pytanie=pytanie, options=options, odpowiedz=odpowiedz.answer)

    @app.route('/dodaj_pytania', methods=['GET', 'POST'])
    @login_required
    def dodaj_pytania():

        db.session.query(QuizQuestion).delete()
        db.session.commit()


        question1 = QuizQuestion(id=1, question_text="W którym roku powstał Hlyw?", correct_answer="2021")
        question2 = QuizQuestion(id=2, type="1", question_text="Podaj liczbę powierzchni użytkowej Hlywa w m²",
                                 correct_answer="b",
                                 options=json.dumps({"a": "15,91 m²", "b": "16,88 m²", "c": "14,92 m²", "d": "17,08 m²"}))
        question3 = QuizQuestion(id=3, type="1", question_text="Jaką pierwszą rzecz Prezes Hlywu wydrukował na drukarce 3D?",
                                 correct_answer="c",
                                 options=json.dumps({"a": "Papież", "b": "Napis HLYW", "c": "Sześcian", "d": "BMW"}))
        question4 = QuizQuestion(id=4, type="1", question_text="Ile Czucz miał lat?",
                                 correct_answer="a",
                                 options=json.dumps({"a": "16", "b": "17", "c": "18", "d": "19"}))
        question5 = QuizQuestion(id=5, question_text="Ile najwięcej osób było jednocześnie w Hlywie?", correct_answer="23")


        db.session.add_all([question1, question2, question3, question4, question5])
        db.session.commit()

        return "Pytania zostały dodane"

    @app.route('/current_question/', defaults={'answer': None}, methods=['GET', 'POST'])
    @app.route('/current_question/<string:answer>', methods=['GET', 'POST'])
    def current_question(answer):
        question = QuizQuestion.query.filter_by(is_active=True).first()
        odpowiedz=QuizAnswer.query.filter_by(question_id=question.id, participant_id=current_user.id).first()
        if odpowiedz:
            odpowiedz.answer=answer
        else:
            odpowiedz=QuizAnswer(answer=answer, question_id=question.id, participant_id=current_user.id)

        if odpowiedz:
            db.session.add(odpowiedz)
            db.session.commit()


        if question:
            return jsonify({
                'question_id': question.id,
                'question_text': question.question_text,
                'odpowiedz':answer
            })
        return jsonify({'question_id': None, 'question_text': "Czekaj na pytanie..."})

    @app.route('/set_active_question/<int:question_id>', methods=['POST'])
    def set_active_question(question_id):
        # Wyłącz wszystkie pytania
        QuizQuestion.query.update({'is_active': False})
        db.session.commit()

        # Włącz wybrane pytanie
        question = QuizQuestion.query.get(question_id)
        if question:
            question.is_active = True
            db.session.commit()
            return jsonify({'status': 'success', 'message': f'Pytanie {question_id} ustawione jako aktywne'})
        return jsonify({'status': 'error', 'message': 'Nie znaleziono pytania'})

    @app.route('/api/upload', methods=['POST'])
    def upload_file():
        if 'file' not in request.files:
            return "Brak pliku", 400

        file = request.files['file']
        if file.filename == '':
            return "Brak nazwy pliku", 400

        # Folder docelowy
        UPLOAD_FOLDER = os.path.join('app', 'static', 'videos')
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Upewnij się, że folder istnieje

        # Zapisanie pliku
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)

        # Ograniczenie liczby plików do 5
        manage_files(UPLOAD_FOLDER, max_files=5)

        return "Plik zapisany", 200

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
        user_id = current_user.id
        active_users[user_id] = {
            "username": current_user.username,
            "photo": current_user.photo,
            "last_seen": datetime.utcnow()
        }
        return jsonify({"status": "ok"})

    @app.route('/get_active_users')
    @login_required
    def get_active_users():
        """Zwraca listę aktywnych użytkowników"""
        now = datetime.utcnow()
        time.sleep(1)
        # Usuwamy użytkowników, którzy nie odświeżali statusu przez 10 sekund
        active_users_filtered = {
            uid: data for uid, data in active_users.items()
            if now - data["last_seen"] < timedelta(seconds=30)
        }
        return jsonify({"users": list(active_users_filtered.values())})


    return app

