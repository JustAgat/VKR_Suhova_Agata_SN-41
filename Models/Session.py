from datetime import datetime 
from application import db
import uuid

class Session(db.Model):
    __tablename__ = 'sessions'
    id = db.Column(db.BigInteger, primary_key=True)
    session_id = db.Column(db.UUID, unique=True, nullable=False, default=uuid.uuid4)
    visitor_id = db.Column(db.UUID, db.ForeignKey('visitors.id'), nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime)
    duration_sec = db.Column(db.Integer)
    ip = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    referrer = db.Column(db.Text)
    utm_source = db.Column(db.String(50))
    utm_medium = db.Column(db.String(50))
    utm_campaign = db.Column(db.String(100))
    device_type = db.Column(db.String(20))
    browser = db.Column(db.Text)  # User-Agent может быть очень длинным
    screen = db.Column(db.String(30))
    pages_viewed = db.Column(db.Integer, default=0)
    is_bounce = db.Column(db.Boolean, default=True)
    entry_section = db.Column(db.String(50))
    exit_section = db.Column(db.String(50))
    
    # Связь с событиями: одна сессия может иметь много событий
    events = db.relationship('Event', backref='session', lazy='dynamic')
