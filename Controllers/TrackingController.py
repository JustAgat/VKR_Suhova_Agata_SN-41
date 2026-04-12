from flask import request, jsonify
from application import app, db
from flask_restful import Resource
from Models import Event, Visitor, Session
from Models.Site import Site
from Models.Revision import Revision
import uuid
from datetime import datetime


def resolve_site_and_revision(site_key):
    """Resolve site_key to site_id and active revision_id"""
    if not site_key:
        return None, None
    site = Site.query.filter_by(site_key=site_key, is_active=True).first()
    if not site:
        return None, None
    revision = Revision.query.filter_by(site_id=site.id, is_active=True).first()
    return str(site.id), str(revision.id) if revision else None

class TrackingController(Resource):
    
    """
    Docstring for TrackingController
    """

    @staticmethod
    @app.route('/api/start_session', methods=['POST'])
    def start_session():
        data = request.json
        visitor_id = data.get("visitor_id")
        session_id = data.get("session_id") or str(uuid.uuid4())
        site_key = data.get("site_key")

        site_id, revision_id = resolve_site_and_revision(site_key)

        # Visitor
        visitor = Visitor.query.filter_by(visitor_id=visitor_id).first()
        if not visitor:
            visitor = Visitor(visitor_id=visitor_id, site_id=site_id)
            db.session.add(visitor)
            db.session.flush()  # Генерируем ID без полного коммита
        else:
            visitor.visits += 1
            visitor.last_seen = datetime.utcnow()

        # Session
        session = Session(
            session_id=session_id,
            visitor_id=visitor.id,
            site_id=site_id,
            revision_id=revision_id,
            ip=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
            referrer=data.get("referrer"),
            utm_source=data.get("utm_source"),
            utm_medium=data.get("utm_medium"),
            utm_campaign=data.get("utm_campaign"),
            device_type=data.get("device_type"),
            browser=data.get("browser"),
            screen=data.get("screen"),
            entry_section=data.get("entry_section", "hero")
        )
        db.session.add(session)
        db.session.commit()

        return jsonify({"session_id": session_id, "visitor_id": str(visitor.visitor_id)})
    
    # === Трекинг событий ===
    @staticmethod
    @app.route("/api/track", methods=["POST"])
    def track():
        data = request.json
        session_id = data.get("session_id")
        event_type = data.get("event_type")
        site_key = data.get("site_key")

        site_id, revision_id = resolve_site_and_revision(site_key)

        # Создаём объект события
        event = Event(
            session_id=session_id,
            site_id=site_id,
            revision_id=revision_id,
            event_type=event_type,
            payload=data.get("payload"),
            # === НОВОЕ: Сохраняем координаты кликов ===
            click_x=data.get("click_x"),
            click_y=data.get("click_y"),
            viewport_width=data.get("viewport_width"),
            viewport_height=data.get("viewport_height"),
            page_height=data.get("page_height"),
            page_url=data.get("page_url")
        )
        db.session.add(event)

        # Обновляем сессию
        session = Session.query.filter_by(session_id=session_id).first()
        if session:
            if event_type == "section_view":
                session.pages_viewed += 1
                session.is_bounce = False
                if not session.entry_section:
                    section = data.get("payload", {}).get("section")
                    if section:
                        session.entry_section = section
            elif event_type in ["form_submit", "phone_click", "email_click"]:
                session.is_bounce = False
            
            exit_section = data.get("payload", {}).get("section")
            if exit_section:
                session.exit_section = exit_section

        db.session.commit()
        return jsonify({"status": "ok"})


    # === Завершение сессии (beforeunload) ===
    @staticmethod
    @app.route("/api/end_session", methods=["POST"])
    def end_session():
        # navigator.sendBeacon отправляет FormData, поэтому получаем из request.form
        session_id = request.form.get('session_id') or (request.json.get('session_id') if request.json else None)
        
        if not session_id:
            return jsonify({"status": "error", "message": "No session_id"}), 400
        
        session = Session.query.filter_by(session_id=session_id).first()
        if session:
            session.ended_at = datetime.utcnow()
            
            # Проверяем что started_at существует и оба значения имеют одинаковый формат
            if session.started_at:
                # Убедиться что обе даты naive (без timezone info)
                if session.started_at.tzinfo is not None:
                    session.started_at = session.started_at.replace(tzinfo=None)
                session.duration_sec = int((session.ended_at - session.started_at).total_seconds())
            db.session.commit()

        return jsonify({"status": "ok"})




