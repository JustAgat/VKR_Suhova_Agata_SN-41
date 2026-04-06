/**
 * Universal Tracking System
 * 
 * Использует data-атрибуты для конфигурации отслеживания событий.
 * Полностью универсален и не зависит от конкретной структуры сайта.
 * 
 * Пример использования:
 * <button data-track="click" data-track-event="button_click" data-track-name="cta">Клик</button>
 * <section data-track="section" data-track-name="hero">Контент</section>
 * <form data-track="form" data-track-event="form_submit">Форма</form>
 */

class UniversalTracking {
    constructor(config = {}) {
        this.config = {
            apiBaseUrl: config.apiBaseUrl || '',
            trackingUrl: config.trackingUrl || '/api/track',
            sessionStartUrl: config.sessionStartUrl || '/api/start_session',
            sessionEndUrl: config.sessionEndUrl || '/api/end_session',
            sectionThreshold: config.sectionThreshold || 0.6,
            ...config
        };

        this.sessionId = null;
        this.visitorId = this.getOrCreateVisitorId();
        this.initialized = false;

        this.init();
    }

    /**
     * Инициализация трекера
     */
    async init() {
        await this.startSession();
        this.setupObservers();
        this.setupEventListeners();
        this.setupBeforeUnload();
        this.initialized = true;
    }

    /**
     * Получить или создать ID визитора
     */
    getOrCreateVisitorId() {
        let visitorId = localStorage.getItem('visitorId');
        if (!visitorId) {
            visitorId = crypto.randomUUID();
            localStorage.setItem('visitorId', visitorId);
        }
        return visitorId;
    }

    /**
     * Запустить сессию
     */
    async startSession() {
        try {
            const sessionData = {
                visitor_id: this.visitorId,
                referrer: document.referrer,
                utm_source: new URLSearchParams(location.search).get('utm_source'),
                utm_medium: new URLSearchParams(location.search).get('utm_medium'),
                url: location.href,
                title: document.title,
                device_type: /Mobi|Android/i.test(navigator.userAgent) ? 'mobile' : 'desktop',
                browser: navigator.userAgent,
                screen: `${screen.width}x${screen.height}`,
                timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                ...this.config.sessionData // Позволить дополнительные данные сессии
            };

            const response = await fetch(this.config.sessionStartUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(sessionData)
            });

            const data = await response.json();
            this.sessionId = data.session_id;
            console.log('[Tracking] Session started:', this.sessionId);
        } catch (error) {
            console.error('[Tracking] Session start failed:', error);
        }
    }

    /**
     * Отправить событие
     */
    async track(eventType, payload = {}) {
        if (!this.sessionId) return;

        try {
            await fetch(this.config.trackingUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    event_type: eventType,
                    payload,
                    timestamp: new Date().toISOString()
                }),
                keepalive: true
            });
        } catch (error) {
            console.error('[Tracking] Track failed:', error);
        }
    }

    /**
     * Настроить IntersectionObserver для секций
     */
    setupObservers() {
        // Отслеживание видимости секций
        const sectionObserver = new IntersectionObserver(
            entries => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const trackName = this.getTrackAttribute(entry.target, 'name');
                        const event = this.getTrackAttribute(entry.target, 'event') || 'section_view';
                        
                        if (trackName) {
                            this.track(event, { section: trackName });
                        }
                    }
                });
            },
            { threshold: this.config.sectionThreshold }
        );

        // Наблюдаем все элементы с data-track="section"
        document.querySelectorAll('[data-track="section"]').forEach(el => {
            sectionObserver.observe(el);
        });
    }

    /**
     * Настроить обработчики событий
     */
    setupEventListeners() {
        // Клики по элементам
        document.addEventListener('click', (e) => {
            const trackEl = e.target.closest('[data-track="click"]');
            if (trackEl) {
                const eventType = this.getTrackAttribute(trackEl, 'event') || 'click';
                const trackName = this.getTrackAttribute(trackEl, 'name');
                const extra = this.getTrackDataAttributes(trackEl);
                
                this.track(eventType, { button: trackName, ...extra });
            }
        });

        // Отправка форм
        document.addEventListener('submit', async (e) => {
            const trackEl = e.target.closest('[data-track="form"]');
            if (trackEl) {
                e.preventDefault();
                
                const formData = Object.fromEntries(new FormData(e.target));
                const eventType = this.getTrackAttribute(trackEl, 'event') || 'form_submit';
                const trackName = this.getTrackAttribute(trackEl, 'name') || 'form';
                const extra = this.getTrackDataAttributes(trackEl);
                
                await this.track(eventType, {
                    ...formData,
                    form_name: trackName,
                    ...extra
                });

                // Опционально: показать callback (можно переопределить через config)
                if (this.config.onFormSubmit) {
                    this.config.onFormSubmit(e.target, formData);
                } else {
                    alert('Спасибо! Ваша заявка отправлена.');
                }

                // Очистить форму
                e.target.reset();
            }
        });

        // Клики по ссылкам (tel, mailto)
        document.addEventListener('click', (e) => {
            const link = e.target.closest('a');
            if (link) {
                const href = link.getAttribute('href') || '';
                let eventType = null;
                let extra = {};

                if (href.startsWith('tel:')) {
                    eventType = 'phone_click';
                    extra = { phone: href.replace('tel:', '') };
                } else if (href.startsWith('mailto:')) {
                    eventType = 'email_click';
                    extra = { email: href.replace('mailto:', '') };
                }

                // Проверить data-track атрибут
                if (link.hasAttribute('data-track')) {
                    eventType = this.getTrackAttribute(link, 'event') || eventType;
                }

                if (eventType) {
                    const trackName = this.getTrackAttribute(link, 'name');
                    this.track(eventType, { link: trackName || href, ...extra });
                }
            }
        });
    }

    /**
     * Завершение сессии при закрытии страницы
     */
    setupBeforeUnload() {
        window.addEventListener('beforeunload', () => {
            if (this.sessionId) {
                const formData = new FormData();
                formData.append('session_id', this.sessionId);
                navigator.sendBeacon(this.config.sessionEndUrl, formData);
            }
        });
    }

    /**
     * Получить значение data-track-* атрибута
     */
    getTrackAttribute(el, key) {
        return el.getAttribute(`data-track-${key}`);
    }

    /**
     * Получить все data- атрибуты элемента (кроме data-track-*)
     */
    getTrackDataAttributes(el) {
        const data = {};
        Array.from(el.attributes).forEach(attr => {
            if (attr.name.startsWith('data-') && !attr.name.startsWith('data-track-')) {
                const key = attr.name.replace('data-', '');
                data[key] = attr.value;
            }
        });
        return data;
    }

    /**
     * Манульный трекинг из кода
     */
    trackEvent(eventType, payload = {}) {
        this.track(eventType, payload);
    }

    /**
     * Получить текущий sessionId
     */
    getSessionId() {
        return this.sessionId;
    }
}

// Экспорт для использования
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UniversalTracking;
}

// Auto-init: если найден скрипт с data-auto-init, запустить автоматически
document.addEventListener('DOMContentLoaded', () => {
    const script = document.currentScript || 
                   document.querySelector('script[data-auto-init]');
    
    if (script && script.hasAttribute('data-auto-init')) {
        // Считать конфиг из data-атрибутов скрипта
        const config = {};
        Array.from(script.attributes).forEach(attr => {
            if (attr.name.startsWith('data-track-')) {
                const key = attr.name
                    .replace('data-track-', '')
                    .replace(/-([a-z])/g, (g) => g[1].toUpperCase()); // camelCase
                config[key] = attr.value === 'true' ? true : 
                             attr.value === 'false' ? false : 
                             attr.value;
            }
        });
        
        window.tracker = new UniversalTracking(config);
    }
});
