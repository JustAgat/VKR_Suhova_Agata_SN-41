// static/js/tracking.js
let sessionId = null;
let visitorId = localStorage.getItem('visitorId') || crypto.randomUUID();
localStorage.setItem('visitorId', visitorId);

async function send(data) {
    await fetch('/api/track', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, ...data }),
        keepalive: true   // важно для beforeunload
    });
}

// Запуск сессии
async function initSession() {
    const res = await fetch('/api/start_session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            visitor_id: visitorId,
            referrer: document.referrer,
            utm_source: new URLSearchParams(location.search).get('utm_source'),
            utm_medium: new URLSearchParams(location.search).get('utm_medium'),
            device_type: /Mobi|Android/i.test(navigator.userAgent) ? 'mobile' : 'desktop',
            browser: navigator.userAgent,
            screen: `${screen.width}x${screen.height}`,
            entry_section: 'hero'
        })
    });
    const json = await res.json();
    sessionId = json.session_id;
}

// Отслеживание секций (IntersectionObserver)
const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
        if (entry.isIntersecting && sessionId) {
            send({
                event_type: "section_view",
                payload: { section: entry.target.id }
            });
        }
    });
}, { threshold: 0.6 });

document.querySelectorAll('section[id]').forEach(sec => observer.observe(sec));

// Целевые действия
function trackClick(type, extra = {}) {
    if (sessionId) {
        send({ event_type: 'click', payload: { button: type, ...extra } });
    }
}

// Форма
document.getElementById('excursionForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = Object.fromEntries(new FormData(e.target));
    
    await send({
        event_type: "form_submit",
        payload: { ...formData, section: "form" }
    });
    
    // Можно отправить реальную заявку параллельно
    alert("Заявка отправлена! Спасибо ❤️");
});

// Клик по телефону и почте
document.querySelectorAll('a[href^="tel:"]').forEach(a => {
    a.addEventListener('click', () => trackClick('phone_click'));
});
document.querySelectorAll('a[href^="mailto:"]').forEach(a => {
    a.addEventListener('click', () => trackClick('email_click'));
});

// Завершение сессии
window.addEventListener('beforeunload', () => {
    if (sessionId) {
        // navigator.sendBeacon создан специально для отправки данных при закрытии страницы
        const formData = new FormData();
        formData.append('session_id', sessionId);
        navigator.sendBeacon('/api/end_session', formData);
    }
});

initSession();