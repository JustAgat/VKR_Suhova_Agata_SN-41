from datetime import datetime
from application import db
from sqlalchemy.dialects.postgresql import JSONB
import uuid

class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.BigInteger, primary_key=True)
    session_id = db.Column(db.UUID, db.ForeignKey('sessions.session_id'))
    event_type = db.Column(db.String(50))
    payload = db.Column(JSONB)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    