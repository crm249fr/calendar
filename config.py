import os

class Config:
    # Telegram
    TELEGRAM_TOKEN = "8765454976:AAGolrqZ8bcQJTj8FnCN1ltagpM0TBbNGDk"
    
    # Yandex AI
    YANDEX_API_KEY = "AQVN3pZhoIJM9PX_TV-U11qoIbKYsuNlhCCk0048"
    YANDEX_FOLDER_ID = "b1gn6ped0id50712c11g"
    
    # Database
    SQLALCHEMY_DATABASE_URI = 'sqlite:///smartnotes.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Flask
    SECRET_KEY = 'your-secret-key-here'
    DEBUG = True
    HOST = '127.0.0.1'
    PORT = 5000

# Месяцы на русском
MONTHS_RU = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
             'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
