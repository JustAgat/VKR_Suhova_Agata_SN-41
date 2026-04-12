from datetime import datetime
from application import db
from sqlalchemy.dialects.postgresql import JSONB
import uuid

class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.BigInteger, primary_key=True)
    session_id = db.Column(db.UUID, db.ForeignKey('sessions.session_id'))
    site_id = db.Column(db.UUID, db.ForeignKey('sites.id'), nullable=True)
    revision_id = db.Column(db.UUID, db.ForeignKey('revisions.id'), nullable=True)
    event_type = db.Column(db.String(50))
    payload = db.Column(JSONB)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # === Поля для тепловой карты кликов ===
    click_x = db.Column(db.Integer, nullable=True)  # Абсолютная X координата (pageX)
    click_y = db.Column(db.Integer, nullable=True)  # Абсолютная Y координата (pageY)
    viewport_width = db.Column(db.Integer, nullable=True)  # Ширина viewport
    viewport_height = db.Column(db.Integer, nullable=True)  # Высота viewport
    page_height = db.Column(db.Integer, nullable=True)  # Полная высота страницы
    page_url = db.Column(db.String(500), nullable=True)  # URL страницы при клике
