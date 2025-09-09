from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, EmailField, FileField, DateField, TextAreaField, DateTimeLocalField
from wtforms.validators import DataRequired, EqualTo, Length

class LoginForm(FlaskForm):
    username = StringField('Nazwa użytkownika', validators=[DataRequired()])
    password = PasswordField('Hasło', validators=[DataRequired()])
    submit = SubmitField('Zaloguj')

class RegistrationForm(FlaskForm):
    username = StringField('Nazwa użytkownika', validators=[DataRequired()])
    email = EmailField('Email', validators=[DataRequired()])
    password = PasswordField('Hasło', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Potwierdź hasło', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Zarejestruj')

class AlbumForm(FlaskForm):
    title = StringField('Tytuł', validators=[DataRequired()])
    description = StringField('Opis')
    submit = SubmitField('Dodaj Album')

class ImageForm(FlaskForm):
    file = FileField('Wybierz Plik', validators=[DataRequired()])
    submit = SubmitField('Dodaj Zdjęcie')

class NewsForm(FlaskForm):
    title = StringField('Tytuł', validators=[DataRequired()])
    file = FileField('Wybierz Plik', validators=[DataRequired()])
    description = StringField('Opis', validators=[DataRequired()])
    submit = SubmitField('Dodaj Newsa')

class CalendarForm(FlaskForm):
    #date = DateTimeLocalField('Data i godzina', format='%Y-%m-%d %H:%M', validators=[DataRequired()])
    date = DateTimeLocalField('Data', validators=[DataRequired()])
    title = StringField('Tytuł', validators=[DataRequired()])
    description = StringField('Opis', validators=[DataRequired()])
    submit = SubmitField('Dodaj Wydarzenie')

class UserSettingsForm(FlaskForm):
    username = StringField('Nazwa użytkownika', validators=[DataRequired()])
    photo = FileField('Zmień zdjęcie profilowe')
    submit = SubmitField('Zapisz zmiany')

class ReportForm(FlaskForm):
    title = StringField('Tytuł', validators=[DataRequired()])
    description = TextAreaField('Opis', validators=[DataRequired()])
    submit = SubmitField('Zgłoś')

class CommentForm(FlaskForm):
    content = TextAreaField('Komentarz', validators=[DataRequired()])
    submit = SubmitField('Dodaj komentarz')

class TestEmail(FlaskForm):
    email = EmailField('Email', validators=[DataRequired()])
    subject = StringField('Temat', validators=[DataRequired()])
    content = TextAreaField('Treść', validators=[DataRequired()])
    submit = SubmitField('Wyślij testowego maila')

