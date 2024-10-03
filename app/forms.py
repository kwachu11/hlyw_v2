from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, EmailField, FileField, DateField
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
    date = DateField('Data', validators=[DataRequired()])
    title = StringField('Tytuł', validators=[DataRequired()])
    description = StringField('Opis', validators=[DataRequired()])
    submit = SubmitField('Dodaj Wydarzenie')

class UserSettingsForm(FlaskForm):
    username = StringField('Nazwa użytkownika', validators=[DataRequired()])
    photo = FileField('Zmień zdjęcie profilowe')
    submit = SubmitField('Zapisz zmiany')
