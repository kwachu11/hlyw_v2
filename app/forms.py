from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, EmailField, FileField, DateField, TextAreaField, DateTimeLocalField, \
    SelectField, RadioField, IntegerField
from wtforms.validators import DataRequired, EqualTo, Length, NumberRange, Optional

# Druk 3D - opcje do wyboru w propozycji; listę filamentów i kolorów można dowolnie zmieniać
PRINT_EXTENSIONS = {'stl', '3mf', 'obj', 'step', 'stp'}
PRINT_MAX_MB = 50
PRINT_QUALITIES = {
    'obojetnie': 'Obojętnie',
    'szkic': 'Szkic - 0,28 mm (szybko)',
    'standard': 'Standard - 0,20 mm',
    'dokladna': 'Dokładna - 0,12 mm (wolno)',
}
PRINT_MATERIALS = ['Obojętnie', 'PLA', 'PETG', 'TPU (elastyczny)', 'ABS', 'ASA']
PRINT_COLORS = {   # nazwa -> kolor kółka w formularzu
    'Obojętnie': 'transparent', 'Czarny': '#111111', 'Biały': '#f5f5f5', 'Szary': '#8a8a8a', 'Czerwony': '#d32f2f',
    'Pomarańczowy': '#f57c00', 'Żółty': '#fbc02d', 'Zielony': '#388e3c', 'Niebieski': '#1976d2', 'Fioletowy': '#7b1fa2',
    'Różowy': '#ec407a', 'Inny (opisz w uwagach)': 'transparent',
}
PRINT_STATUSES = {   # wartość -> (nazwa, klasa plakietki, ikona w aktywności)
    'nowa': ('Nowa', 'badge-primary', '🖨️'),
    'zatwierdzona': ('Zatwierdzona', 'badge-info', '✅'),
    'w_druku': ('W druku', 'badge-warning', '🔥'),
    'wydrukowana': ('Wydrukowana', 'badge-success', '🎉'),
    'odrzucona': ('Odrzucona', 'badge-secondary', '❌'),
}

class LoginForm(FlaskForm):
    username = StringField('Nazwa użytkownika lub e-mail', validators=[DataRequired()])
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


class ForgotPasswordForm(FlaskForm):
    username = StringField('Nazwa użytkownika', validators=[DataRequired()])
    email = EmailField('Email', validators=[DataRequired()])
    submit = SubmitField('Dalej')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Nowe hasło', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Potwierdź nowe hasło', validators=[DataRequired(), EqualTo('password', message='Hasła nie są zgodne.')])
    submit = SubmitField('Ustaw nowe hasło')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Obecne hasło', validators=[DataRequired()])
    password = PasswordField('Nowe hasło', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Potwierdź nowe hasło', validators=[DataRequired(), EqualTo('password', message='Hasła nie są zgodne.')])
    submit = SubmitField('Zmień hasło')

class UpgradeForm(FlaskForm):
    title = StringField('Tytuł', validators=[DataRequired(), Length(max=150)])
    description = TextAreaField('Opis', validators=[DataRequired()])
    submit = SubmitField('Dodaj ulepszenie')

class PrintRequestForm(FlaskForm):
    title = StringField('Co wydrukować?', validators=[DataRequired(), Length(max=150)])
    file = FileField('Plik z modelem', render_kw={'accept': ','.join('.' + e for e in sorted(PRINT_EXTENSIONS)),
                                                  'data-hl-no-resize': '1'})
    link = StringField('albo link do modelu', validators=[Optional(), Length(max=500)],
                       render_kw={'placeholder': 'https://makerworld.com/... / printables.com/... / thingiverse.com/...'})
    image_url = StringField('Link do zdjęcia modelu', validators=[Optional(), Length(max=1000)],
                            render_kw={'placeholder': 'Prawy klik na zdjęciu → „Kopiuj adres obrazu”'})
    quality = SelectField('Jakość wydruku', choices=list(PRINT_QUALITIES.items()), default='obojetnie')
    material = SelectField('Filament', choices=[(m, m) for m in PRINT_MATERIALS], default='Obojętnie')
    color = RadioField('Kolor', choices=[(c, c) for c in PRINT_COLORS], default='Obojętnie')
    quantity = IntegerField('Liczba sztuk', validators=[DataRequired(), NumberRange(min=1, max=20)], default=1)
    description = TextAreaField('Uwagi', validators=[Optional(), Length(max=2000)],
                                render_kw={'rows': 3, 'placeholder': 'Rozmiar, do kiedy, na co to ma być...'})
    submit = SubmitField('Wyślij propozycję')

class PrintStatusForm(FlaskForm):
    status = SelectField('Status', choices=[(k, v[0]) for k, v in PRINT_STATUSES.items()])
    admin_note = TextAreaField('Odpowiedź dla autora', validators=[Optional(), Length(max=500)], render_kw={'rows': 2})
    submit = SubmitField('Zapisz')

class PrintDeleteForm(FlaskForm):
    submit = SubmitField('Usuń propozycję')
