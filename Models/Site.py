from datetime import datetime
from application import db
import uuid
import secrets


class Site(db.Model):
    __tablename__ = 'sites'

    id = db.Column(db.UUID, primary_key=True, default=uuid.uuid4)
    user_id = db.Column(db.UUID, db.ForeignKey('users.id'), nullable=False)
    site_key = db.Column(db.String(32), unique=True, nullable=False, index=True)
    domain = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # Связи
    revisions = db.relationship('Revision', backref='site', lazy='dynamic', order_by='Revision.created_at.desc()')
    sessions = db.relationship('Session', backref='site', lazy='dynamic')

    @staticmethod
    def generate_site_key():
        """Генерирует уникальный публичный ключ сайта (16 символов hex)"""
        return secrets.token_hex(8)
