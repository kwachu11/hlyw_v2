import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hlyw123hlyw123'
    LOGIN_MESSAGE = "Aby uzyskać dostęp do tej strony, musisz być zalogowany............."
    LOGIN_MESSAGE_CATEGORY = 'warning'
    DEBUG = True
    SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
    SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
    SPOTIPY_REDIRECT_URI = os.getenv('SPOTIPY_REDIRECT_URI')
