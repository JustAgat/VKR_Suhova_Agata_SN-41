import os
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')

# Строка подключения к PostgreSQL
DATABASE_URL = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

# Конфигурация SQLAlchemy
class Config:
    """Базовая конфигурация приложения"""
    
    # Основная конфигурация БД
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    
    # Отключение предупреждений об отслеживании изменений
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Настройки пула соединений
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,                    # Количество соединений в пуле
        'pool_recycle': 3600,               # Переиспользование соединения через 1 час
        'pool_pre_ping': True,              # Проверка соединения перед использованием
        'max_overflow': 20,                 # Максимум доп. соединений сверх pool_size
        'echo': False,                      # Вывод SQL запросов (измените на True для отладки)
        'connect_args': {
            'connect_timeout': 10,          # Тайм-аут подключения (сек)
            'application_name': 'flask_app',
        }
    }


class DevelopmentConfig(Config):
    """Конфигурация для разработки"""
    DEBUG = True
    SQLALCHEMY_ENGINE_OPTIONS = {
        **Config.SQLALCHEMY_ENGINE_OPTIONS,
        'echo': True,  # Вывод SQL запросов для отладки
    }


class ProductionConfig(Config):
    """Конфигурация для продакшена"""
    DEBUG = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        **Config.SQLALCHEMY_ENGINE_OPTIONS,
        'pool_size': 20,
        'max_overflow': 40,
        'echo': False,
    }


class TestingConfig(Config):
    """Конфигурация для тестирования"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


# Выбор конфигурации по умолчанию
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}