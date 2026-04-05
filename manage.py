#!/usr/bin/env python
"""
Менеджер для работы с миграциями БД (Alembic)
"""

from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from application import app, db

migrate = Migrate(app, db)
manager = Manager(app)

# Добавление команд для миграций
manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    manager.run()
