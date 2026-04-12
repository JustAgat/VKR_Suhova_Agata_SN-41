from flask import request, jsonify
from application import app, db
from Models import Event, Visitor, Session
from Models.Revision import Revision
from Models.Visitors import Visitor as VisitorModel
from Models.Hypothesis import Hypothesis
from Controllers.hypothesis_evaluator import evaluate_hypothesis
from datetime import datetime, timedelta
from sqlalchemy import func, desc
from flask_restful import Resource
import json

def _site_filters_session(query):
    """Добавить фильтры site_id и revision_id к запросу Session"""
    site_id = request.args.get('site_id')
    revision_id = request.args.get('revision_id')
    if site_id:
        query = query.filter(Session.site_id == site_id)
    if revision_id:
        query = query.filter(Session.revision_id == revision_id)
    return query

def _site_filters_event(query):
    """Добавить фильтры site_id и revision_id к запросу Event"""
    site_id = request.args.get('site_id')
    revision_id = request.args.get('revision_id')
    if site_id:
        query = query.filter(Event.site_id == site_id)
    if revision_id:
        query = query.filter(Event.revision_id == revision_id)
    return query

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
        total_sessions = _site_filters_session(Session.query.filter(Session.started_at >= start_date)).count()
        total_visitors = _site_filters_session(db.session.query(func.count(func.distinct(Session.visitor_id))).filter(
            Session.started_at >= start_date
        )).scalar()
        total_events = _site_filters_event(Event.query.filter(Event.created_at >= start_date)).count()

        # Bounce rate
        total = total_sessions
        bounces = _site_filters_session(Session.query.filter(
            Session.started_at >= start_date,
            Session.is_bounce == True
        )).count()
        bounce_rate = round((bounces / total * 100), 2) if total > 0 else 0

        # Среднее время сессии
        avg_q = db.session.query(func.avg(Session.duration_sec)).filter(
            Session.started_at >= start_date,
            Session.duration_sec.isnot(None)
        )
        avg_q = _site_filters_session(avg_q)
        avg_duration = avg_q.scalar() or 0
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
        q = db.session.query(
            func.date(Session.started_at).label('date'),
            func.count(Session.session_id).label('count')
        ).filter(Session.started_at >= start_date)
        q = _site_filters_session(q)
        data = q.group_by(
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

        data = _site_filters_event(db.session.query(
            Event.payload['section'].astext.label('section'),
            func.count(Event.id).label('views')
        ).filter(
            Event.event_type == 'section_view',
            Event.created_at >= start_date
        )).group_by('section').order_by(desc('views')).limit(10).all()

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

        data = _site_filters_session(db.session.query(
            Session.device_type,
            func.count(Session.session_id).label('count')
        ).filter(Session.started_at >= start_date)).group_by(
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

        data = _site_filters_session(db.session.query(
            Session.utm_source,
            func.count(Session.session_id).label('count')
        ).filter(
            Session.started_at >= start_date,
            Session.utm_source.isnot(None)
        )).group_by(Session.utm_source).order_by(desc('count')).all()

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

        data = _site_filters_event(db.session.query(
            Event.event_type,
            func.count(Event.id).label('count')
        ).filter(Event.created_at >= start_date)).group_by(
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

        sessions = _site_filters_session(Session.query).order_by(
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

        query = _site_filters_session(Session.query)

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

    @staticmethod
    @app.route('/api/clicks', methods=['GET'])
    def get_clicks_heatmap():
        """
        Получить данные кликов для тепловой карты в формате heatmap.js
        Query параметры:
        - url: (обязательно) URL страницы (например: "/" или "/page")
        - days: количество дней истории (по умолчанию 7)
        Возвращает JSON с координатами в процентах (0-100)
        """
        page_url = request.args.get('url')
        days = request.args.get('days', 7, type=int)

        if not page_url:
            return jsonify({'error': 'URL parameter required', 'data': []}), 400

        # Дата начала периода
        start_date = datetime.utcnow() - timedelta(days=days)

        # Получаем ВСЕ клики для этой страницы за период с координатами
        clicks = _site_filters_event(Event.query.filter(
            Event.event_type.in_(['click_heatmap', 'click', 'cta_click', 'tariff_click', 'email_click', 'phone_click']),
            Event.page_url == page_url,
            Event.click_x != None,
            Event.click_y != None,
            Event.page_height != None,
            Event.viewport_width != None,
            Event.created_at >= start_date
        )).all()

        print(f"[DEBUG] Found {len(clicks)} clicks for {page_url} in last {days} days")

        if not clicks:
            return jsonify({
                'max': 100,
                'data': [],
                'total_clicks': 0,
                'unique_points': 0
            })

        # === Преобразуем абсолютные координаты в процентные (0-100) ===
        # Используем float с 1 знаком для точности (int терял до 55px)
        intensity_map = {}  # Для подсчёта интенсивности в каждой точке

        for click in clicks:
            # Нормализуем X: от 0 до viewport_width -> от 0% до 100%
            x_percent = round((click.click_x / (click.viewport_width or 1)) * 100, 1)
            # Нормализуем Y: от 0 до page_height -> от 0% до 100%
            y_percent = round((click.click_y / (click.page_height or 1)) * 100, 1)

            # Ограничиваем границы
            x_percent = max(0, min(100, x_percent))
            y_percent = max(0, min(100, y_percent))

            # Группируем клики по близким координатам (округление до 0.5%)
            gx = round(x_percent * 2) / 2
            gy = round(y_percent * 2) / 2
            key = f"{gx},{gy}"
            intensity_map[key] = intensity_map.get(key, 0) + 1

        # === Формируем данные для heatmap.js ===
        max_intensity = max(intensity_map.values()) if intensity_map else 1

        heatmap_data = []
        for coords, intensity in intensity_map.items():
            x, y = map(float, coords.split(','))

            # Нормализуем интенсивность к диапазону 0-100
            normalized_intensity = int((intensity / max_intensity) * 100)

            heatmap_data.append({
                'x': x,
                'y': y,
                'value': normalized_intensity
            })

        return jsonify({
            'max': 100,
            'data': heatmap_data,
            'total_clicks': len(clicks),
            'unique_points': len(intensity_map)
        })

    @staticmethod
    @app.route('/api/analytics/compare-revisions', methods=['GET'])
    def compare_revisions():
        """Сравнение метрик по всем ревизиям сайта"""
        site_id = request.args.get('site_id')
        days = request.args.get('days', 90, type=int)
        start_date = datetime.utcnow() - timedelta(days=days)

        if not site_id:
            return jsonify({'error': 'site_id required'}), 400

        revisions = Revision.query.filter_by(site_id=site_id).order_by(Revision.created_at).all()
        if not revisions:
            return jsonify({'revisions': []})

        result = []
        for rev in revisions:
            rid = str(rev.id)

            total_sessions = Session.query.filter(
                Session.site_id == site_id,
                Session.revision_id == rid,
                Session.started_at >= start_date
            ).count()

            total_visitors = db.session.query(func.count(func.distinct(Session.visitor_id))).filter(
                Session.site_id == site_id,
                Session.revision_id == rid,
                Session.started_at >= start_date
            ).scalar() or 0

            total_events = Event.query.filter(
                Event.site_id == site_id,
                Event.revision_id == rid,
                Event.created_at >= start_date
            ).count()

            bounces = Session.query.filter(
                Session.site_id == site_id,
                Session.revision_id == rid,
                Session.started_at >= start_date,
                Session.is_bounce == True
            ).count()
            bounce_rate = round((bounces / total_sessions * 100), 1) if total_sessions > 0 else 0

            avg_duration = db.session.query(func.avg(Session.duration_sec)).filter(
                Session.site_id == site_id,
                Session.revision_id == rid,
                Session.started_at >= start_date,
                Session.duration_sec.isnot(None)
            ).scalar() or 0

            avg_pages = db.session.query(func.avg(Session.pages_viewed)).filter(
                Session.site_id == site_id,
                Session.revision_id == rid,
                Session.started_at >= start_date
            ).scalar() or 0

            # CTA клики
            cta_clicks = Event.query.filter(
                Event.site_id == site_id,
                Event.revision_id == rid,
                Event.created_at >= start_date,
                Event.event_type.in_(['cta_click', 'tariff_click'])
            ).count()

            # Форма
            form_submits = Event.query.filter(
                Event.site_id == site_id,
                Event.revision_id == rid,
                Event.created_at >= start_date,
                Event.event_type == 'form_submit'
            ).count()

            result.append({
                'revision_id': rid,
                'name': rev.name,
                'is_active': rev.is_active,
                'created_at': rev.created_at.isoformat() if rev.created_at else None,
                'sessions': total_sessions,
                'visitors': total_visitors,
                'events': total_events,
                'bounce_rate': bounce_rate,
                'avg_duration': round(avg_duration),
                'avg_pages': round(float(avg_pages), 1),
                'cta_clicks': cta_clicks,
                'form_submits': form_submits,
            })

        return jsonify({'revisions': result})

    @staticmethod
    @app.route('/api/analytics/insights', methods=['GET'])
    def get_insights():
        """Оценка всех гипотез (базовых + пользовательских для сайта)"""
        site_id = request.args.get('site_id')
        revision_id = request.args.get('revision_id')
        days = request.args.get('days', 90, type=int)
        start_date = datetime.utcnow() - timedelta(days=days)

        if not site_id:
            return jsonify({'error': 'site_id required'}), 400

        # Базовые (site_id IS NULL) + пользовательские для сайта
        hypotheses = Hypothesis.query.filter(
            db.or_(Hypothesis.site_id == None, Hypothesis.site_id == site_id),
            Hypothesis.is_active == True
        ).order_by(Hypothesis.created_at).all()

        insights = []
        for hyp in hypotheses:
            result = evaluate_hypothesis(hyp, site_id, revision_id, days, start_date)
            if result:
                insights.append(result)

        return jsonify({'insights': insights})

    # ── CRUD для гипотез ──────────────────────────────────────

    @staticmethod
    @app.route('/api/hypotheses', methods=['GET'])
    def list_hypotheses():
        """Список гипотез для сайта (базовые + пользовательские)"""
        site_id = request.args.get('site_id')
        if not site_id:
            return jsonify({'error': 'site_id required'}), 400

        hypotheses = Hypothesis.query.filter(
            db.or_(Hypothesis.site_id == None, Hypothesis.site_id == site_id),
            Hypothesis.is_active == True
        ).order_by(Hypothesis.created_at).all()

        return jsonify({'hypotheses': [h.to_dict() for h in hypotheses]})

    @staticmethod
    @app.route('/api/hypotheses', methods=['POST'])
    def create_hypothesis():
        """Создать пользовательскую гипотезу"""
        body = request.get_json(force=True)
        site_id = body.get('site_id')
        if not site_id:
            return jsonify({'error': 'site_id required'}), 400

        hyp = Hypothesis(
            site_id=site_id,
            category=body.get('category', 'custom'),
            title=body.get('title', ''),
            hypothesis_text=body.get('hypothesis_text', ''),
            metric=body.get('metric', 'bounce_rate'),
            segment_a_field=body.get('segment_a_field'),
            segment_a_op=body.get('segment_a_op', '=='),
            segment_a_value=body.get('segment_a_value'),
            segment_b_field=body.get('segment_b_field'),
            segment_b_op=body.get('segment_b_op', '=='),
            segment_b_value=body.get('segment_b_value'),
            compare_mode=body.get('compare_mode', 'ratio'),
            threshold_confirmed=float(body.get('threshold_confirmed', 1.5)),
            threshold_partial=float(body.get('threshold_partial', 1.2)),
            advice_confirmed=body.get('advice_confirmed', ''),
            advice_not_confirmed=body.get('advice_not_confirmed', ''),
        )
        db.session.add(hyp)
        db.session.commit()
        return jsonify(hyp.to_dict()), 201

    @staticmethod
    @app.route('/api/hypotheses/<hyp_id>', methods=['DELETE'])
    def delete_hypothesis(hyp_id):
        """Удалить пользовательскую гипотезу (базовые нельзя)"""
        hyp = Hypothesis.query.get(hyp_id)
        if not hyp:
            return jsonify({'error': 'Not found'}), 404
        if hyp.site_id is None:
            return jsonify({'error': 'Нельзя удалить базовую гипотезу'}), 403
        db.session.delete(hyp)
        db.session.commit()
        return jsonify({'ok': True})
