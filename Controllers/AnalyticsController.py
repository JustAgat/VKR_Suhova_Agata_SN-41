from flask import request, jsonify
from application import app, db
from Models import Event, Visitor, Session
from datetime import datetime, timedelta
from sqlalchemy import func, desc
from flask_restful import Resource
import json


class AnalyticsController(Resource):
    """
    API для аналитики и статистики
    """
    
    @staticmethod
    @app.route('/api/analytics/overview', methods=['GET'])
    def get_overview():
        """Основные метрики"""
        days = request.args.get('days', 7, type=int)
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Запросы
        total_sessions = Session.query.filter(Session.started_at >= start_date).count()
        total_visitors = db.session.query(func.count(func.distinct(Session.visitor_id))).filter(
            Session.started_at >= start_date
        ).scalar()
        
        total_events = Event.query.filter(Event.created_at >= start_date).count()
        
        # Bounce rate
        total = Session.query.filter(Session.started_at >= start_date).count()
        bounces = Session.query.filter(
            Session.started_at >= start_date,
            Session.is_bounce == True
        ).count()
        bounce_rate = round((bounces / total * 100), 2) if total > 0 else 0
        
        # Среднее время сессии
        avg_duration = db.session.query(func.avg(Session.duration_sec)).filter(
            Session.started_at >= start_date,
            Session.duration_sec.isnot(None)
        ).scalar() or 0
        avg_duration = round(avg_duration, 0)
        
        return jsonify({
            'sessions': total_sessions,
            'visitors': total_visitors,
            'events': total_events,
            'bounce_rate': bounce_rate,
            'avg_duration': int(avg_duration)
        })
    
    @staticmethod
    @app.route('/api/analytics/timeline', methods=['GET'])
    def get_timeline():
        """График по дням"""
        days = request.args.get('days', 7, type=int)
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Сессии по дням
        data = db.session.query(
            func.date(Session.started_at).label('date'),
            func.count(Session.session_id).label('count')
        ).filter(Session.started_at >= start_date).group_by(
            func.date(Session.started_at)
        ).order_by('date').all()
        
        dates = []
        counts = []
        for row in data:
            dates.append(row.date.strftime('%d.%m'))
            counts.append(row.count)
        
        return jsonify({'dates': dates, 'counts': counts})
    
    @staticmethod
    @app.route('/api/analytics/sections', methods=['GET'])
    def get_sections():
        """Популярные секции"""
        days = request.args.get('days', 7, type=int)
        start_date = datetime.utcnow() - timedelta(days=days)
        
        data = db.session.query(
            Event.payload['section'].astext.label('section'),
            func.count(Event.id).label('views')
        ).filter(
            Event.event_type == 'section_view',
            Event.created_at >= start_date
        ).group_by('section').order_by(desc('views')).limit(10).all()
        
        sections = []
        views = []
        for row in data:
            if row.section:
                sections.append(row.section)
                views.append(row.views)
        
        return jsonify({'sections': sections, 'views': views})
    
    @staticmethod
    @app.route('/api/analytics/devices', methods=['GET'])
    def get_devices():
        """Распределение по устройствам"""
        days = request.args.get('days', 7, type=int)
        start_date = datetime.utcnow() - timedelta(days=days)
        
        data = db.session.query(
            Session.device_type,
            func.count(Session.session_id).label('count')
        ).filter(Session.started_at >= start_date).group_by(
            Session.device_type
        ).all()
        
        devices = []
        counts = []
        for row in data:
            devices.append(row.device_type or 'unknown')
            counts.append(row.count)
        
        return jsonify({'devices': devices, 'counts': counts})
    
    @staticmethod
    @app.route('/api/analytics/utm', methods=['GET'])
    def get_utm():
        """Источники трафика"""
        days = request.args.get('days', 7, type=int)
        start_date = datetime.utcnow() - timedelta(days=days)
        
        data = db.session.query(
            Session.utm_source,
            func.count(Session.session_id).label('count')
        ).filter(
            Session.started_at >= start_date,
            Session.utm_source.isnot(None)
        ).group_by(Session.utm_source).order_by(desc('count')).all()
        
        sources = []
        counts = []
        for row in data:
            sources.append(row.utm_source)
            counts.append(row.count)
        
        return jsonify({'sources': sources, 'counts': counts})
    
    @staticmethod
    @app.route('/api/analytics/events', methods=['GET'])
    def get_events():
        """Типы событий"""
        days = request.args.get('days', 7, type=int)
        start_date = datetime.utcnow() - timedelta(days=days)
        
        data = db.session.query(
            Event.event_type,
            func.count(Event.id).label('count')
        ).filter(Event.created_at >= start_date).group_by(
            Event.event_type
        ).order_by(desc('count')).all()
        
        events = []
        counts = []
        for row in data:
            events.append(row.event_type)
            counts.append(row.count)
        
        return jsonify({'events': events, 'counts': counts})
    
    @staticmethod
    @app.route('/api/analytics/recent-sessions', methods=['GET'])
    def get_recent_sessions():
        """Последние сессии"""
        limit = request.args.get('limit', 20, type=int)
        
        sessions = Session.query.order_by(
            desc(Session.started_at)
        ).limit(limit).all()
        
        data = []
        for s in sessions:
            data.append({
                'session_id': str(s.session_id),
                'device_type': s.device_type,
                'pages_viewed': s.pages_viewed,
                'duration': s.duration_sec,
                'is_bounce': s.is_bounce,
                'utm_source': s.utm_source,
                'started_at': s.started_at.isoformat()
            })
        
        return jsonify(data)
    
    @staticmethod
    @app.route('/api/analytics/heatmap', methods=['GET'])
    def get_heatmap():
        """Тепловая карта по секциям (просмотры vs конверсия)"""
        days = request.args.get('days', 7, type=int)
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Все события просмотра секций
        section_views = db.session.query(
            Event.payload['section'].astext.label('section'),
            func.count(Event.id).label('views')
        ).filter(
            Event.event_type == 'section_view',
            Event.created_at >= start_date
        ).group_by('section').all()
        
        # Конверсии (клики/подписки с каждой секции)
        section_conversions = db.session.query(
            Session.entry_section,
            func.count(Session.session_id).label('conversions')
        ).filter(
            Session.started_at >= start_date,
            Session.is_bounce == False
        ).group_by(Session.entry_section).all()
        
        conversion_map = {row.entry_section: row.conversions for row in section_conversions}
        
        sections = []
        views = []
        conversions = []
        
        for row in section_views:
            section = row.section
            sections.append(section or 'unknown')
            views.append(row.views)
            conversions.append(conversion_map.get(section, 0))
        
        return jsonify({
            'sections': sections,
            'views': views,
            'conversions': conversions
        })
    
    @staticmethod
    @app.route('/api/analytics/search-sessions', methods=['GET'])
    def search_sessions():
        """Поиск и фильтрация сессий"""
        device_type = request.args.get('device_type')
        utm_source = request.args.get('utm_source')
        is_bounce = request.args.get('is_bounce')
        min_duration = request.args.get('min_duration', type=int)
        limit = request.args.get('limit', 100, type=int)
        
        query = Session.query
        
        if device_type and device_type != 'all':
            query = query.filter(Session.device_type == device_type)
        
        if utm_source and utm_source != 'all':
            query = query.filter(Session.utm_source == utm_source)
        
        if is_bounce and is_bounce != 'all':
            query = query.filter(Session.is_bounce == (is_bounce == 'true'))
        
        if min_duration:
            query = query.filter(Session.duration_sec >= min_duration)
        
        sessions = query.order_by(desc(Session.started_at)).limit(limit).all()
        
        data = []
        for s in sessions:
            data.append({
                'session_id': str(s.session_id),
                'device_type': s.device_type,
                'pages_viewed': s.pages_viewed,
                'duration': s.duration_sec,
                'is_bounce': s.is_bounce,
                'utm_source': s.utm_source,
                'started_at': s.started_at.isoformat()
            })
        
        return jsonify(data)
    
    @staticmethod
    @app.route('/api/analytics/session/<session_id>', methods=['GET'])
    def get_session_details(session_id):
        """Детали конкретной сессии"""
        session = Session.query.filter_by(session_id=session_id).first()
        
        if not session:
            return jsonify({'error': 'Not found'}), 404
        
        events = Event.query.filter_by(session_id=session_id).order_by(Event.created_at).all()
        
        events_data = []
        for e in events:
            events_data.append({
                'event_type': e.event_type,
                'payload': e.payload,
                'created_at': e.created_at.isoformat()
            })
        
        return jsonify({
            'session': {
                'session_id': str(session.session_id),
                'device_type': session.device_type,
                'browser': session.browser,
                'screen': session.screen,
                'referrer': session.referrer,
                'utm_source': session.utm_source,
                'utm_medium': session.utm_medium,
                'utm_campaign': session.utm_campaign,
                'pages_viewed': session.pages_viewed,
                'duration': session.duration_sec,
                'is_bounce': session.is_bounce,
                'entry_section': session.entry_section,
                'exit_section': session.exit_section,
                'started_at': session.started_at.isoformat(),
                'ended_at': session.ended_at.isoformat() if session.ended_at else None
            },
            'events': events_data
        })

