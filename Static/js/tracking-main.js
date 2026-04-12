/**
 * Universal Tracking System с поддержкой тепловой карты кликов
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
            siteKey: config.siteKey || null,
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
        this.setupClickHeatmapTracking();
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
                site_key: this.config.siteKey,
                referrer: document.referrer,
                utm_source: new URLSearchParams(location.search).get('utm_source'),
                utm_medium: new URLSearchParams(location.search).get('utm_medium'),
                url: location.href,
                title: document.title,
                device_type: /Mobi|Android/i.test(navigator.userAgent) ? 'mobile' : 'desktop',
                browser: navigator.userAgent,
                screen: `${screen.width}x${screen.height}`,
                timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                ...this.config.sessionData
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
     * Отправить событие на сервер
     */
    async track(eventType, payload = {}) {
        if (!this.sessionId) return;

        try {
            await fetch(this.config.trackingUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    site_key: this.config.siteKey,
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
     * === Сбор всех кликов для тепловой карты ===
     * Отправляет координаты каждого клика на /api/track с полной информацией
     */
    setupClickHeatmapTracking() {
        document.addEventListener('click', (e) => {
            // Пропускаем клики внутри панели аналитики (чтобы не мусорить данные)
            if (e.target.closest('#analytics-panel')) return;            
            // ⚠️ ВАЖНО: Пропускаем клики из iframe-ов (например, с preview страницы)
            // Проверяем, находимся ли мы в iframe
            if (window.self !== window.top) {
                console.log('[Tracking] Ignoring click from iframe');
                return;
            }

            // Находим ближайший идентифицируемый элемент
            const trackEl = e.target.closest('[id], [data-track], [data-track-name]') || e.target;

            // Собираем информацию о клике
            const clickData = {
                session_id: this.sessionId,
                site_key: this.config.siteKey,
                event_type: 'click_heatmap',
                payload: {
                    element_tag: e.target.tagName.toLowerCase(),
                    element_id: trackEl.id || null,
                    element_text: (e.target.innerText || '').substring(0, 50).trim(),
                    element_class: (e.target.className || '').toString().substring(0, 100),
                    track_name: trackEl.getAttribute('data-track-name') || null
                },
                // === КООРДИНАТЫ КЛИКА ===
                click_x: Math.round(e.pageX),  // Абсолютная X координата на странице
                click_y: Math.round(e.pageY),  // Абсолютная Y координата на странице
                viewport_width: window.innerWidth,
                viewport_height: window.innerHeight,
                page_height: document.documentElement.scrollHeight,
                page_url: window.location.pathname  // Только pathname для точного совпадения
            };

            // Отправляем на сервер асинхронно (не блокируем событие)
            fetch(this.config.trackingUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(clickData),
                keepalive: true
            }).catch(err => console.error('[Heatmap] Click tracking error:', err));
        }, true);  // ← true = capture phase, чтобы не пропускать клики
    }

    /**
     * Настроить IntersectionObserver для секций
     */
    setupObservers() {
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

        document.querySelectorAll('[data-track="section"]').forEach(el => {
            sectionObserver.observe(el);
        });
    }

    /**
     * Настроить обработчики событий
     */
    setupEventListeners() {
        // Клики по элементам с data-track="click"
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
        document.addEventListener('submit', (e) => {
            const formEl = e.target.closest('[data-track="form"]');
            if (formEl) {
                const eventType = this.getTrackAttribute(formEl, 'event') || 'form_submit';
                const trackName = this.getTrackAttribute(formEl, 'name') || formEl.id;
                
                this.track(eventType, { form: trackName });
            }
        });
    }

    /**
     * Настроить отправку данных перед закрытием вкладки
     */
    setupBeforeUnload() {
        window.addEventListener('beforeunload', () => {
            if (this.sessionId) {
                navigator.sendBeacon(this.config.sessionEndUrl, 
                    new FormData(Object.entries({ session_id: this.sessionId }).reduce((form, [k, v]) => {
                        form.append(k, v);
                        return form;
                    }, new FormData()))
                );
            }
        });
    }

    /**
     * Получить значение атрибута data-track-*
     */
    getTrackAttribute(element, key) {
        return element.getAttribute(`data-track-${key}`);
    }

    /**
     * Получить все атрибуты data-track-*
     */
    getTrackDataAttributes(element) {
        const result = {};
        Array.from(element.attributes).forEach(attr => {
            if (attr.name.startsWith('data-track-')) {
                const key = attr.name.replace('data-track-', '');
                if (key !== 'event' && key !== 'name') {
                    result[key] = attr.value;
                }
            }
        });
        return result;
    }
}

// ===== ГЛОБАЛЬНАЯ ИНИЦИАЛИЗАЦИЯ =====
// НЕ инициализируем трекинг на аналитике и других страницах
// Трекинг активируется ТОЛЬКО если на странице есть атрибут data-auto-init
const trackingScriptTag = document.currentScript;
const isAnalyticsPage = document.querySelector('[data-view-content]') !== null;  // ← Проверка на analytics
const isNotInIframe = window.self === window.top;

if (!isAnalyticsPage && isNotInIframe && trackingScriptTag && trackingScriptTag.hasAttribute('data-auto-init')) {
    window.tracking = new UniversalTracking({
        siteKey: trackingScriptTag.getAttribute('data-site-key') || null,
        trackingUrl: '/api/track',
        sessionStartUrl: '/api/start_session'
    });
    console.log('[Tracking] Initialized on page');
} else {
    const reasons = [];
    if (isAnalyticsPage) reasons.push('analytics page detected');
    if (!isNotInIframe) reasons.push('inside iframe');
    if (!trackingScriptTag?.hasAttribute('data-auto-init')) reasons.push('no data-auto-init');
    console.log('[Tracking] Skipped -', reasons.join(' + '));
    // Создаём пустой объект для совместимости
    window.tracking = {
        sessionId: null,
        visitorId: null,
        initialized: false
    };
}