from flask import Flask, jsonify
from flask_restful import Api, HTTPException
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from config import DevelopmentConfig
import logging

# Инициализация приложения
app = Flask(__name__, template_folder='Templates')
app.config.from_object(DevelopmentConfig)
db = SQLAlchemy(app)
api = Api(app)

# Инициализация миграций
migrate = Migrate(app, db)

# Импорт моделей после инициализации db для избежания циклических импортов
from Models import Event, Visitor, Session, User, Site, Revision
# Для русского языка
app.json.ensure_ascii = False

logger = logging.getLogger(__name__)
