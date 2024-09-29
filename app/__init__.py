
from dotenv import load_dotenv
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import json
from datetime import datetime, timedelta
from flask_login import LoginManager, UserMixin
from flask_sqlalchemy import SQLAlchemy
from flask import render_template, redirect, url_for, request
from flask_login import login_user, login_required, logout_user
from werkzeug.security import generate_password_hash, check_password_hash

from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from .forms import LoginForm, RegistrationForm

from app.forms import AlbumForm, ImageForm, NewsForm, CalendarForm

import locale

from datetime import datetime, timedelta
import calendar as callendar
from datetime import date
# Wczytaj zmienne środowiskowe z pliku .env
load_dotenv()




def create_app():
    app = Flask(__name__)
    db = SQLAlchemy()
    login_manager = LoginManager()
    app.secret_key = os.getenv('SECRET_KEY')  # Ustawienie secret key do sesji
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
    db.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = 'login'  # Widok do przekierowania w przypadku nieautoryzowanego dostępu
    login_manager.login_message = 'Musisz się zalogować, aby uzyskać dostęp do tej strony.'

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
    class User(db.Model, UserMixin):
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(150), unique=True, nullable=False)
        email = db.Column(db.String(150), nullable=False)
        password = db.Column(db.String(150), nullable=False)

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



    # Tworzenie tabel w bazie danych przy starcie aplikacji
    with app.app_context():
        db.create_all()


    login_manager = LoginManager(app)
    login_manager.login_view = 'login'  # Widok do przekierowania w przypadku nieautoryzowanego dostępu



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
            else:
                new_user = User(username=form.username.data, email=form.email.data, password=form.password.data)  # Hasło powinno być hashowane
                db.session.add(new_user)
                db.session.commit()
                login_user(new_user)
                return redirect(url_for('index'))
        return render_template('register.html', form=form)

    @app.route('/albums', methods=['GET'])
    def albums():
        all_album = Albums.query.all()
        images_no_album=Images.query.filter_by(album_id=0).all()
        return render_template('albums.html', album=all_album, images=images_no_album)

    @app.route('/add_album', methods=['GET', 'POST'])
    def add_album():
        form = AlbumForm()
        if form.validate_on_submit():
            albums = Albums(name=form.title.data, description=form.description.data, created_by=current_user.id)
            db.session.add(albums)
            db.session.commit()
            return redirect(url_for('albums'))
        return render_template('add_album.html', form=form)

    @app.route('/add_images', methods=['GET', 'POST'])
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
    def news():
        all_news = News.query.order_by(News.created_at.desc()).all()
        return render_template('breaking_news.html', news=all_news)

    @app.route('/add_new', methods=['GET', 'POST'])
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
    def calendar():
        locale.setlocale(locale.LC_TIME, 'pl_PL')
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
    def camera():
        return render_template('camera.html')

    return app

