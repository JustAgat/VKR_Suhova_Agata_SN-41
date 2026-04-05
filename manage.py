#!/usr/bin/env python
"""
Менеджер для работы с миграциями БД (Alembic)
"""

from flask.cli import FlaskGroup
from flask_migrate import Migrate
from application import app, db

migrate = Migrate(app, db)
cli = FlaskGroup(create_app=lambda: app)

if __name__ == '__main__':
    cli()
