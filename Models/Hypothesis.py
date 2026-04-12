import uuid
from datetime import datetime
from application import db


class Hypothesis(db.Model):
    __tablename__ = 'hypotheses'

    id = db.Column(db.UUID, primary_key=True, default=uuid.uuid4)
    site_id = db.Column(db.UUID, db.ForeignKey('sites.id'), nullable=True)  # NULL = базовая
    category = db.Column(db.String(50), nullable=False)  # engagement, ux, traffic, retention, conversion
    title = db.Column(db.String(200), nullable=False)
    hypothesis_text = db.Column(db.Text, nullable=False)

    # Что измеряем
    metric = db.Column(db.String(50), nullable=False)  # bounce_rate, avg_duration, conversion, cta_clicks, ...

    # Сегмент A (основная группа)
    segment_a_field = db.Column(db.String(50), nullable=True)   # device_type, utm_source, sections_viewed, ...
    segment_a_op = db.Column(db.String(10), default='==')       # ==, >=, <=, >, <
    segment_a_value = db.Column(db.String(100), nullable=True)  # mobile, google, 4, ...

    # Сегмент B (группа сравнения, NULL = все остальные)
    segment_b_field = db.Column(db.String(50), nullable=True)
    segment_b_op = db.Column(db.String(10), default='==')
    segment_b_value = db.Column(db.String(100), nullable=True)

    # Пороги для определения статуса (ratio = A / B)
    compare_mode = db.Column(db.String(10), default='ratio')  # ratio, diff, abs
    threshold_confirmed = db.Column(db.Float, default=1.5)
    threshold_partial = db.Column(db.Float, default=1.2)

    # Тексты советов
    advice_confirmed = db.Column(db.Text, nullable=True)
    advice_not_confirmed = db.Column(db.Text, nullable=True)

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': str(self.id),
            'site_id': str(self.site_id) if self.site_id else None,
            'category': self.category,
            'title': self.title,
            'hypothesis_text': self.hypothesis_text,
            'metric': self.metric,
            'segment_a_field': self.segment_a_field,
            'segment_a_op': self.segment_a_op,
            'segment_a_value': self.segment_a_value,
            'segment_b_field': self.segment_b_field,
            'segment_b_op': self.segment_b_op,
            'segment_b_value': self.segment_b_value,
            'compare_mode': self.compare_mode,
            'threshold_confirmed': self.threshold_confirmed,
            'threshold_partial': self.threshold_partial,
            'advice_confirmed': self.advice_confirmed,
            'advice_not_confirmed': self.advice_not_confirmed,
            'is_active': self.is_active,
            'is_base': self.site_id is None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
