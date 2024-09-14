import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hlyw123hlyw123'
    DEBUG = True