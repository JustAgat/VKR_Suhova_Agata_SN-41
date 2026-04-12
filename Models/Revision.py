from datetime import datetime
from application import db
import uuid


class Revision(db.Model):
    __tablename__ = 'revisions'

    id = db.Column(db.UUID, primary_key=True, default=uuid.uuid4)
    site_id = db.Column(db.UUID, db.ForeignKey('sites.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)  # "v1.0 — Первоначальный дизайн"
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime, nullable=True)  # NULL = текущая активная
    is_active = db.Column(db.Boolean, default=True)

    # Связь с сессиями
    sessions = db.relationship('Session', backref='revision', lazy='dynamic')
