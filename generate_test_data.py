"""
Генератор тестовых данных для системы аналитики.
Адаптирован из оригинального скрипта с процентными зонами кликов.

Использование:
    python generate_test_data.py <site_key>           — генерация данных
    python generate_test_data.py <site_key> --clean    — очистка + генерация
    python generate_test_data.py <site_key> --clean-only — только очистка

Пример:
    python generate_test_data.py a1b2c3d4e5f67890
    python generate_test_data.py a1b2c3d4e5f67890 --clean
"""

import sys
import uuid
import random
from datetime import datetime, timedelta

sys.path.insert(0, '.')

from application import app, db
from Models.Site import Site
from Models.Revision import Revision
from Models.Visitors import Visitor
from Models.Session import Session
from Models.Event import Event
from sqlalchemy.dialects.postgresql import JSONB
from psycopg2.extras import Json

# === КОНФИГУРАЦИЯ ===
NUM_VISITORS = 170
NUM_SESSIONS = 200
NUM_EVENTS = 300

# Фиксированный viewport 1440px — совпадает с RENDER_WIDTH в analytics.js
VIEWPORT_WIDTH = 1440
PAGE_HEIGHT = 5400  # приближённая высота страницы при 1440px с VH-fix

# === ЗОНЫ КЛИКОВ ПО ЭЛЕМЕНТАМ СТРАНИЦЫ ===
# Координаты в процентах: x от viewport_width, y от page_height
# (name, event_type, x_min%, x_max%, y_min%, y_max%, weight)
# ТОЛЬКО интерактивные элементы (кнопки, ссылки, поля форм).
CLICK_ZONES = [
    ('hero_cta', 'cta_click', 7, 28, 10, 11, 28),
    ('hero_secondary', 'cta_click', 7, 23, 11, 13, 12),
    ('form_name', 'click', 24, 47, 21, 22, 5),
    ('form_company', 'click', 53, 76, 21, 22, 3),
    ('form_email', 'click', 24, 47, 23, 24, 5),
    ('form_phone', 'click', 53, 76, 23, 24, 3),
    ('form_date', 'click', 24, 47, 25, 27, 4),
    ('form_time', 'click', 53, 76, 25, 27, 2),
    ('form_submit', 'cta_click', 24, 76, 27, 29, 20),
    ('tariff_base', 'tariff_click', 9, 27, 89, 90, 7),
    ('tariff_standard', 'tariff_click', 40, 59, 87, 88, 16),
    ('tariff_advanced', 'tariff_click', 72, 91, 88, 90, 7),
    ('footer_cta', 'cta_click', 33, 67, 95, 97, 13),
]

SECTIONS = ['hero', 'booking-form', 'about-us', 'challenges', 'our-solution', 'effectiveness', 'tariffs']
DEVICES = ['desktop', 'mobile']
SCREENS = ['1920x1080', '1366x768', '414x896', '375x667']
UTM_SOURCES = ['google', 'yandex', 'vk', 'direct', '']
UTM_MEDIUMS = ['organic', 'cpc', 'social', 'email', 'referral']
UTM_CAMPAIGNS = ['webinar', 'black_friday', 'spring_sale', 'new_features', '']
REFERRERS = ['https://google.com/', 'https://yandex.ru/', 'https://vk.com/', 'direct']


def clean_site_data(site_key):
    """Удалить все данные (events, sessions, visitors) для конкретного сайта"""
    with app.app_context():
        site = Site.query.filter_by(site_key=site_key).first()
        if not site:
            print(f"Сайт с ключом '{site_key}' не найден!")
            return False

        site_id = str(site.id)
        print(f"Очистка данных для сайта: {site.name} ({site.domain})")

        ev_count = Event.query.filter_by(site_id=site_id).delete()
        print(f"  Удалено событий: {ev_count}")

        sess_count = Session.query.filter_by(site_id=site_id).delete()
        print(f"  Удалено сессий: {sess_count}")

        vis_count = Visitor.query.filter_by(site_id=site_id).delete()
        print(f"  Удалено визиторов: {vis_count}")

        db.session.commit()
        print("✅ Очистка завершена!")
        return True


def pick_click_zone():
    """Выбрать зону клика по весу"""
    total_weight = sum(z[6] for z in CLICK_ZONES)
    r = random.uniform(0, total_weight)
    cumulative = 0
    for zone in CLICK_ZONES:
        cumulative += zone[6]
        if r <= cumulative:
            return zone
    return CLICK_ZONES[-1]


def generate(site_key):
    with app.app_context():
        # Найти сайт
        site = Site.query.filter_by(site_key=site_key).first()
        if not site:
            print(f"Сайт с ключом '{site_key}' не найден!")
            print("Доступные сайты:")
            for s in Site.query.all():
                print(f"  {s.name} ({s.domain}) — ключ: {s.site_key}")
            return

        # Найти активную ревизию
        revision = Revision.query.filter_by(site_id=site.id, is_active=True).first()

        site_id = str(site.id)
        revision_id = str(revision.id) if revision else None

        print(f"Сайт: {site.name} ({site.domain})")
        print(f"Site ID: {site_id}")
        print(f"Ревизия: {revision.name if revision else 'нет активной'}")
        print(f"Revision ID: {revision_id or 'N/A'}")

        # === 1. Visitors ===
        visitor_map = {}  # visitor_uuid → visitor db object
        print(f"Создаю {NUM_VISITORS} visitors...")

        for _ in range(NUM_VISITORS):
            visitor_uuid = uuid.uuid4()
            first_seen = datetime(2026, 1, 1) + timedelta(days=random.randint(0, 130))
            last_seen = first_seen + timedelta(days=random.randint(1, 45))
            visits = random.randint(1, 15)

            visitor = Visitor(
                visitor_id=visitor_uuid,
                site_id=site_id,
                first_seen=first_seen,
                last_seen=last_seen,
                visits=visits,
            )
            db.session.add(visitor)
            db.session.flush()
            visitor_map[str(visitor_uuid)] = visitor

        # === 2. Sessions ===
        session_uuids = []
        print(f"Создаю {NUM_SESSIONS} sessions...")
        visitor_keys = list(visitor_map.keys())

        for _ in range(NUM_SESSIONS):
            session_uuid = uuid.uuid4()
            visitor_uuid = random.choice(visitor_keys)
            visitor = visitor_map[visitor_uuid]

            days_offset = random.randint(0, 130)
            started_at = datetime(2026, 1, 1) + timedelta(
                days=days_offset,
                hours=random.randint(8, 22),
                minutes=random.randint(0, 59),
                seconds=random.randint(0, 59)
            )
            duration_sec = random.randint(30, 3000)
            ended_at = started_at + timedelta(seconds=duration_sec)

            sess = Session(
                session_id=session_uuid,
                visitor_id=visitor.id,
                site_id=site_id,
                revision_id=revision_id,
                started_at=started_at,
                ended_at=ended_at,
                duration_sec=duration_sec,
                ip=f'192.168.{random.randint(1,255)}.{random.randint(1,255)}',
                user_agent='Chrome/128',
                browser='Chrome',
                device_type=random.choice(DEVICES),
                screen=random.choice(SCREENS),
                referrer=random.choice(REFERRERS),
                utm_source=random.choice(UTM_SOURCES) or None,
                utm_medium=random.choice(UTM_MEDIUMS),
                utm_campaign=random.choice(UTM_CAMPAIGNS) or None,
                pages_viewed=random.randint(2, 15),
                is_bounce=random.random() < 0.25,
                entry_section=random.choice(SECTIONS),
                exit_section=random.choice(SECTIONS),
            )
            db.session.add(sess)
            session_uuids.append(session_uuid)

        db.session.flush()

        # === 3. Events ===
        event_types_non_click = ['section_view', 'form_submit']
        print(f"Создаю {NUM_EVENTS} events...")

        for _ in range(NUM_EVENTS):
            session_uuid = random.choice(session_uuids)
            viewport_width = VIEWPORT_WIDTH
            viewport_height = 900
            page_height = PAGE_HEIGHT

            # 60% — клики по элементам, 40% — просмотры секций и формы
            if random.random() < 0.6:
                # === Клик по элементу ===
                zone = pick_click_zone()
                zone_name, event_type, x_min, x_max, y_min, y_max, _ = zone

                # Гауссовое распространение к центру зоны
                x_center = (x_min + x_max) / 2
                y_center = (y_min + y_max) / 2
                x_spread = (x_max - x_min) / 6
                y_spread = (y_max - y_min) / 10

                x_pct = max(x_min, min(x_max, random.gauss(x_center, x_spread)))
                y_pct = max(y_min, min(y_max, random.gauss(y_center, y_spread)))

                # Жёсткий clamp — не выходим за границы зоны ни при каких условиях
                x_pct = max(x_min + 0.1, min(x_max - 0.1, x_pct))
                y_pct = max(y_min + 0.1, min(y_max - 0.1, y_pct))

                click_x = int(x_pct / 100 * viewport_width)
                click_y = int(y_pct / 100 * page_height)

                payload = {
                    "element": zone_name,
                    "target": zone_name.split('_')[0]
                }
                page_url = '/'
            else:
                # === Просмотр секции или отправка формы ===
                event_type = random.choice(event_types_non_click)

                if event_type == 'section_view':
                    payload = {
                        "section": random.choice(SECTIONS),
                        "time_spent": random.randint(10, 180)
                    }
                else:
                    payload = {"form": random.choice(['newsletter', 'contact', 'demo'])}

                click_x = random.randint(0, viewport_width)
                click_y = random.randint(0, page_height)
                page_url = random.choice(['/', '/about', '/pricing', '/blog'])

            # Дата события
            random_days_ago = random.randint(0, 130)
            event_date = datetime(2026, 4, 10) - timedelta(
                days=random_days_ago,
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )

            event = Event(
                session_id=session_uuid,
                site_id=site_id,
                revision_id=revision_id,
                event_type=event_type,
                payload=payload,
                created_at=event_date,
                click_x=click_x,
                click_y=click_y,
                viewport_width=viewport_width,
                viewport_height=viewport_height,
                page_height=page_height,
                page_url=page_url,
            )
            db.session.add(event)

        db.session.commit()
        print(f"\n✅ Готово!")
        print(f"  Визиторов: {NUM_VISITORS}")
        print(f"  Сессий: {NUM_SESSIONS}")
        print(f"  Событий: {NUM_EVENTS}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Использование: python generate_test_data.py <site_key> [--clean|--clean-only]")
        print("\nДоступные сайты:")
        with app.app_context():
            for s in Site.query.all():
                print(f"  {s.name} ({s.domain}) — ключ: {s.site_key}")
        sys.exit(1)

    site_key = sys.argv[1]
    flags = sys.argv[2:]

    if '--clean-only' in flags:
        clean_site_data(site_key)
    elif '--clean' in flags:
        clean_site_data(site_key)
        generate(site_key)
    else:
        generate(site_key)
