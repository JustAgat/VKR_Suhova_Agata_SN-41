import uuid
from datetime import datetime
from application import db

class Visitor(db.Model):
    __tablename__ = 'visitors'
    id = db.Column(db.UUID, primary_key=True, default=uuid.uuid4)
    visitor_id = db.Column(db.UUID, unique=True, nullable=False)
    site_id = db.Column(db.UUID, db.ForeignKey('sites.id'), nullable=True)
    first_seen = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    visits = db.Column(db.Integer, default=1)
    
    # Связь с сессиями: один посетитель может иметь много сессий
    sessions = db.relationship('Session', backref='visitor', lazy='dynamic')
