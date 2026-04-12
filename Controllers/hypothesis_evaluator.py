"""
Универсальный движок оценки гипотез.
Вычисляет метрику для двух сегментов и сравнивает.
"""
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from application import db
from Models import Event, Session
from Models.Visitors import Visitor as VisitorModel
from sqlalchemy import func


def evaluate_hypothesis(hyp, site_id, revision_id, days, start_date):
    """
    Оценивает одну гипотезу (объект Hypothesis) и возвращает dict с результатом.
    """
    all_sessions = _get_sessions(site_id, revision_id, start_date)
    all_events = _get_events(site_id, revision_id, start_date)

    if not all_sessions:
        return None

    # Предвычисленные данные для сложных сегментов
    ctx = _build_context(all_sessions, all_events, site_id, start_date)

    # Разделить сессии на сегмент A и сегмент B
    seg_a = _filter_segment(all_sessions, ctx, hyp.segment_a_field, hyp.segment_a_op, hyp.segment_a_value)

    if hyp.segment_b_field:
        seg_b = _filter_segment(all_sessions, ctx, hyp.segment_b_field, hyp.segment_b_op, hyp.segment_b_value)
    else:
        # B = все кроме A
        a_ids = {str(s.session_id) for s in seg_a}
        seg_b = [s for s in all_sessions if str(s.session_id) not in a_ids]

    # Вычислить метрику для обоих сегментов
    val_a = _compute_metric(hyp.metric, seg_a, ctx)
    val_b = _compute_metric(hyp.metric, seg_b, ctx)

    # Определить статус
    status, ratio_or_diff = _compare(hyp.compare_mode, val_a, val_b,
                                      hyp.threshold_confirmed, hyp.threshold_partial)

    # Сформировать текст результата
    result_text = _format_result(hyp.metric, val_a, val_b, ratio_or_diff, len(seg_a), len(seg_b))
    advice = hyp.advice_confirmed if status in ('confirmed', 'partial') else hyp.advice_not_confirmed

    return {
        'id': str(hyp.id),
        'category': hyp.category,
        'title': hyp.title,
        'hypothesis': hyp.hypothesis_text,
        'result': result_text,
        'advice': advice or '',
        'status': status,
        'is_base': hyp.site_id is None,
        'values': {
            'seg_a': round(val_a, 1),
            'seg_b': round(val_b, 1),
            'ratio': round(ratio_or_diff, 2),
            'n_a': len(seg_a),
            'n_b': len(seg_b),
        }
    }


# ── Внутренние функции ───────────────────────────────────────

def _get_sessions(site_id, revision_id, start_date):
    q = Session.query.filter(Session.site_id == site_id, Session.started_at >= start_date)
    if revision_id:
        q = q.filter(Session.revision_id == revision_id)
    return q.all()


def _get_events(site_id, revision_id, start_date):
    q = Event.query.filter(Event.site_id == site_id, Event.created_at >= start_date)
    if revision_id:
        q = q.filter(Event.revision_id == revision_id)
    return q.all()


def _build_context(sessions, events, site_id, start_date):
    """Предвычисление данных для сложных сегментов."""
    ctx = {}

    # sections_viewed на сессию
    session_sections = defaultdict(set)
    section_events = [e for e in events if e.event_type == 'section_view']
    for e in section_events:
        sec = (e.payload or {}).get('section')
        if sec:
            session_sections[str(e.session_id)].add(sec)
    ctx['session_sections'] = session_sections
    ctx['section_events'] = section_events

    # Время в секциях на сессию
    section_time = defaultdict(lambda: defaultdict(int))
    for e in section_events:
        sec = (e.payload or {}).get('section')
        t = (e.payload or {}).get('time_spent', 0)
        if sec and t:
            section_time[str(e.session_id)][sec] = max(section_time[str(e.session_id)][sec], int(t))
    ctx['section_time'] = section_time

    # Клики на сессию
    click_events = [e for e in events if e.event_type in ('click', 'cta_click', 'tariff_click')]
    clicks_per_session = Counter()
    for e in click_events:
        clicks_per_session[str(e.session_id)] += 1
    ctx['clicks_per_session'] = clicks_per_session
    ctx['click_events'] = click_events

    # CTA-позиции
    cta_events = [e for e in events if e.event_type in ('cta_click', 'tariff_click')
                  and e.click_y is not None and e.page_height and e.page_height > 0]
    ctx['cta_events'] = cta_events

    # Returning visitors
    visitor_ids = list(set(s.visitor_id for s in sessions))
    returning_ids = set()
    if visitor_ids:
        returning = VisitorModel.query.filter(
            VisitorModel.id.in_(visitor_ids), VisitorModel.visits > 1
        ).all()
        returning_ids = {v.id for v in returning}
    ctx['returning_visitor_ids'] = returning_ids

    return ctx


def _filter_segment(sessions, ctx, field, op, value):
    """Фильтрует сессии по условию сегмента."""
    if not field or not value:
        return sessions

    op = op or '=='
    result = []

    for s in sessions:
        sid = str(s.session_id)

        if field == 'device_type':
            actual = s.device_type or ''
        elif field == 'utm_source':
            actual = s.utm_source or ''
        elif field == 'utm_medium':
            actual = s.utm_medium or ''
        elif field == 'utm_campaign':
            actual = s.utm_campaign or ''
        elif field == 'is_bounce':
            actual = str(s.is_bounce).lower()
        elif field == 'visitor_type':
            actual = 'returning' if s.visitor_id in ctx['returning_visitor_ids'] else 'new'
        elif field == 'sections_viewed':
            actual = len(ctx['session_sections'].get(sid, set()))
            if _compare_val(actual, op, value):
                result.append(s)
            continue
        elif field.startswith('time_in_section:'):
            section_name = field.split(':', 1)[1]
            actual = ctx['section_time'].get(sid, {}).get(section_name, 0)
            if _compare_val(actual, op, value):
                result.append(s)
            continue
        elif field == 'rage_clicks':
            actual = ctx['clicks_per_session'].get(sid, 0)
            if _compare_val(actual, op, value):
                result.append(s)
            continue
        elif field == 'cta_position':
            # value = 'top30' или 'bottom30'
            # Этот сегмент фильтрует по событиям, не по сессиям напрямую
            # Обрабатывается отдельно
            return _filter_by_cta_position(sessions, ctx, value)
        else:
            continue

        # Для строковых полей
        if op == '==':
            if str(actual).lower() == str(value).lower():
                result.append(s)
        elif op == '!=':
            if str(actual).lower() != str(value).lower():
                result.append(s)

    return result


def _filter_by_cta_position(sessions, ctx, position):
    """Фильтрует: возвращает сессии где CTA клик в указанной позиции."""
    session_ids = set()
    for e in ctx['cta_events']:
        pct = e.click_y / e.page_height * 100
        if position == 'top30' and pct < 30:
            session_ids.add(str(e.session_id))
        elif position == 'bottom30' and pct > 70:
            session_ids.add(str(e.session_id))

    return [s for s in sessions if str(s.session_id) in session_ids]


def _compare_val(actual, op, value):
    """Сравнивает числовое значение."""
    try:
        v = float(value)
    except (ValueError, TypeError):
        return False
    try:
        a = float(actual)
    except (ValueError, TypeError):
        return False

    if op == '>=':
        return a >= v
    elif op == '<=':
        return a <= v
    elif op == '>':
        return a > v
    elif op == '<':
        return a < v
    elif op == '==':
        return abs(a - v) < 0.01
    elif op == '!=':
        return abs(a - v) >= 0.01
    return False


def _compute_metric(metric, sessions, ctx):
    """Вычисляет метрику для набора сессий."""
    n = len(sessions)
    if n == 0:
        return 0.0

    if metric == 'bounce_rate':
        bounces = sum(1 for s in sessions if s.is_bounce)
        return bounces / n * 100
    elif metric == 'conversion':
        conv = sum(1 for s in sessions if not s.is_bounce)
        return conv / n * 100
    elif metric == 'avg_duration':
        total = sum(s.duration_sec or 0 for s in sessions)
        return total / n
    elif metric == 'avg_pages':
        total = sum(s.pages_viewed or 0 for s in sessions)
        return total / n
    elif metric == 'sessions':
        return float(n)
    elif metric == 'cta_clicks':
        sids = {str(s.session_id) for s in sessions}
        return float(sum(1 for e in ctx.get('click_events', [])
                         if e.event_type in ('cta_click', 'tariff_click')
                         and str(e.session_id) in sids))
    elif metric == 'events':
        return float(sum(ctx['clicks_per_session'].get(str(s.session_id), 0) for s in sessions))
    elif metric == 'rage_click_pct':
        sids = {str(s.session_id) for s in sessions}
        rage = sum(1 for sid, cnt in ctx['clicks_per_session'].items() if sid in sids and cnt > 5)
        return rage / n * 100
    elif metric == 'avg_clicks':
        sids = {str(s.session_id) for s in sessions}
        total = sum(ctx['clicks_per_session'].get(sid, 0) for sid in sids)
        return total / n
    return 0.0


def _compare(mode, val_a, val_b, thresh_confirmed, thresh_partial):
    """Сравнивает A и B, возвращает (status, ratio_or_diff)."""
    if mode == 'ratio':
        ratio = val_a / max(val_b, 0.1)
        if ratio >= thresh_confirmed:
            return 'confirmed', ratio
        elif ratio >= thresh_partial:
            return 'partial', ratio
        return 'not_confirmed', ratio
    elif mode == 'ratio_inverse':
        # A < B — хорошо (например bounce меньше)
        ratio = val_b / max(val_a, 0.1)
        if ratio >= thresh_confirmed:
            return 'confirmed', ratio
        elif ratio >= thresh_partial:
            return 'partial', ratio
        return 'not_confirmed', ratio
    elif mode == 'diff':
        diff = val_a - val_b
        if diff >= thresh_confirmed:
            return 'confirmed', diff
        elif diff >= thresh_partial:
            return 'partial', diff
        return 'not_confirmed', diff
    elif mode == 'abs':
        if val_a >= thresh_confirmed:
            return 'confirmed', val_a
        elif val_a >= thresh_partial:
            return 'partial', val_a
        return 'not_confirmed', val_a
    return 'not_confirmed', 0


METRIC_LABELS = {
    'sessions': 'Сессии',
    'bounce_rate': 'Показатель отказов (%)',
    'conversion': 'Конверсия (%)',
    'avg_duration': 'Ср. длит. (сек)',
    'avg_pages': 'Ср. страниц',
    'cta_clicks': 'CTA-клики',
    'events': 'События',
    'rage_click_pct': 'Rage-клики (%)',
    'avg_clicks': 'Ср. кликов/сессия',
    'visitors': 'Посетители',
}


def _format_result(metric, val_a, val_b, ratio, n_a, n_b):
    """Формирует текст результата."""
    label = METRIC_LABELS.get(metric, metric)
    unit = ''
    if metric in ('bounce_rate', 'conversion', 'rage_click_pct'):
        unit = '%'
    elif metric == 'avg_duration':
        unit = 'с'

    return (f'Сегмент A: {val_a:.1f}{unit} (n={n_a}). '
            f'Сегмент B: {val_b:.1f}{unit} (n={n_b}). '
            f'Соотношение: \u00d7{ratio:.2f}.')
