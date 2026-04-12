"""
Скрипт для создания базовых гипотез в БД.
Запускать один раз после миграции: python seed_hypotheses.py
"""
from application import app, db
from Models.Hypothesis import Hypothesis


BASE_HYPOTHESES = [
    {
        'category': 'engagement',
        'title': 'Глубина просмотра и конверсия',
        'hypothesis_text': 'Пользователи, взаимодействующие с 4+ секциями, конвертируются значительно лучше.',
        'metric': 'conversion',
        'segment_a_field': 'sections_viewed',
        'segment_a_op': '>=',
        'segment_a_value': '4',
        'segment_b_field': 'sections_viewed',
        'segment_b_op': '<=',
        'segment_b_value': '2',
        'compare_mode': 'ratio',
        'threshold_confirmed': 2.0,
        'threshold_partial': 1.3,
        'advice_confirmed': 'Стимулируйте прокрутку: добавьте якорные ссылки, анимации при скролле или \u00abчитать далее\u00bb.',
        'advice_not_confirmed': 'Разница незначительна \u2014 контент равномерно вовлекает.',
    },
    {
        'category': 'engagement',
        'title': 'Секция \u00abО нас\u00bb и время на странице',
        'hypothesis_text': 'Пользователи, проводящие больше 40 сек в \u00abО нас\u00bb, чаще оставляют заявку.',
        'metric': 'conversion',
        'segment_a_field': 'time_in_section:about-us',
        'segment_a_op': '>',
        'segment_a_value': '40',
        'segment_b_field': None,
        'segment_b_op': '==',
        'segment_b_value': None,
        'compare_mode': 'ratio',
        'threshold_confirmed': 1.5,
        'threshold_partial': 1.1,
        'advice_confirmed': 'Расширьте секцию \u00abО нас\u00bb: добавьте кейсы, видеоотзывы, сертификаты.',
        'advice_not_confirmed': 'Секция \u00abО нас\u00bb не влияет значимо \u2014 возможно стоит сократить.',
    },
    {
        'category': 'ux',
        'title': 'Мобильные пользователи и множественные клики',
        'hypothesis_text': 'На мобильных устройствах наблюдается повышенное число rage-кликов из-за мелких элементов.',
        'metric': 'rage_click_pct',
        'segment_a_field': 'device_type',
        'segment_a_op': '==',
        'segment_a_value': 'mobile',
        'segment_b_field': 'device_type',
        'segment_b_op': '==',
        'segment_b_value': 'desktop',
        'compare_mode': 'abs',
        'threshold_confirmed': 15.0,
        'threshold_partial': 5.0,
        'advice_confirmed': 'Увеличьте кнопки и интерактивные зоны на мобильной версии (мин. 44\u00d744px).',
        'advice_not_confirmed': 'Мобильный UX в допустимых пределах.',
    },
    {
        'category': 'traffic',
        'title': 'Google трафик vs органический',
        'hypothesis_text': 'Трафик из Google имеет выше показатель отказов и меньше вовлечённость.',
        'metric': 'bounce_rate',
        'segment_a_field': 'utm_source',
        'segment_a_op': '==',
        'segment_a_value': 'google',
        'segment_b_field': 'utm_medium',
        'segment_b_op': '==',
        'segment_b_value': 'organic',
        'compare_mode': 'ratio',
        'threshold_confirmed': 1.3,
        'threshold_partial': 1.0,
        'advice_confirmed': 'Проверьте релевантность рекламных объявлений целевым страницам.',
        'advice_not_confirmed': 'Рекламный трафик показывает хорошее качество.',
    },
    {
        'category': 'traffic',
        'title': 'Реферальный трафик',
        'hypothesis_text': 'Пользователи по реферальным ссылкам проводят больше времени и лучше конвертятся.',
        'metric': 'conversion',
        'segment_a_field': 'utm_medium',
        'segment_a_op': '==',
        'segment_a_value': 'referral',
        'segment_b_field': None,
        'segment_b_op': '==',
        'segment_b_value': None,
        'compare_mode': 'ratio',
        'threshold_confirmed': 1.3,
        'threshold_partial': 1.0,
        'advice_confirmed': 'Масштабируйте реферальные программы \u2014 это самый качественный трафик.',
        'advice_not_confirmed': 'Реферальный трафик не выделяется \u2014 проверьте источники.',
    },
    {
        'category': 'traffic',
        'title': 'Кампания \u00abspring_sale\u00bb',
        'hypothesis_text': 'Кампания привлекает пользователей с низким engagement.',
        'metric': 'bounce_rate',
        'segment_a_field': 'utm_campaign',
        'segment_a_op': '==',
        'segment_a_value': 'spring_sale',
        'segment_b_field': None,
        'segment_b_op': '==',
        'segment_b_value': None,
        'compare_mode': 'ratio',
        'threshold_confirmed': 1.3,
        'threshold_partial': 1.0,
        'advice_confirmed': 'Пересмотрите креативы и таргетинг кампании \u2014 высокий процент отказов.',
        'advice_not_confirmed': 'Кампания показывает нормальные результаты.',
    },
    {
        'category': 'retention',
        'title': 'Возвращающиеся посетители',
        'hypothesis_text': 'Возвращающиеся посетители имеют выше длительность сессии и ниже отказы.',
        'metric': 'avg_duration',
        'segment_a_field': 'visitor_type',
        'segment_a_op': '==',
        'segment_a_value': 'returning',
        'segment_b_field': 'visitor_type',
        'segment_b_op': '==',
        'segment_b_value': 'new',
        'compare_mode': 'ratio',
        'threshold_confirmed': 1.3,
        'threshold_partial': 1.0,
        'advice_confirmed': 'Инвестируйте в ретаргетинг и email-рассылки \u2014 возвращающиеся пользователи ценнее.',
        'advice_not_confirmed': 'Разница между новыми и возвращающимися незначительна.',
    },
    {
        'category': 'conversion',
        'title': 'Расположение CTA на странице',
        'hypothesis_text': 'CTA в верхней части страницы получают больше кликов, чем нижние.',
        'metric': 'cta_clicks',
        'segment_a_field': 'cta_position',
        'segment_a_op': '==',
        'segment_a_value': 'top30',
        'segment_b_field': 'cta_position',
        'segment_b_op': '==',
        'segment_b_value': 'bottom30',
        'compare_mode': 'ratio',
        'threshold_confirmed': 2.0,
        'threshold_partial': 1.0,
        'advice_confirmed': 'Добавьте плавающую CTA-кнопку или дублицируйте форму выше по странице.',
        'advice_not_confirmed': 'Нижние CTA работают \u2014 пользователи дочитывают до конца.',
    },
]


def seed():
    with app.app_context():
        existing = Hypothesis.query.filter(Hypothesis.site_id == None).count()
        if existing > 0:
            print(f'Базовые гипотезы уже существуют ({existing} шт.). Пропуск.')
            return

        for h in BASE_HYPOTHESES:
            hyp = Hypothesis(site_id=None, **h)
            db.session.add(hyp)

        db.session.commit()
        print(f'Создано {len(BASE_HYPOTHESES)} базовых гипотез.')


if __name__ == '__main__':
    seed()
