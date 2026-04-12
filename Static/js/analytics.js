let currentPeriod = 7;
let currentView = 'overview';
let charts = {};

// === Переменные для heatmap.js ===
let heatmapInstance = null;
let currentHeatmapUrl = '/';
let currentHeatmapDays = 90;

function changeView(view) {
    currentView = view;
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    document.querySelector(`[data-view="${view}"]`).classList.add('active');
    
    document.querySelectorAll('[data-view-content]').forEach(el => {
        el.style.display = 'none';
        el.classList.add('hidden');
    });
    const target = document.querySelector(`[data-view-content="${view}"]`);
    target.style.display = 'block';
    target.classList.remove('hidden');
    
    if (view === 'overview') {
        loadData();
    } else if (view === 'sessions') {
        loadSessionsData();
    } else if (view === 'heatmap') {
        heatmapRefresh();
    } else if (view === 'comparison') {
        loadComparison();
    } else if (view === 'insights') {
        loadInsights();
    }
}

function changePeriod(days) {
    currentPeriod = days;
    document.getElementById('period-days').innerText = days;
    
    // Обновить подсвечивание кнопок периода
    document.querySelectorAll('.period-btn').forEach(btn => {
        btn.classList.remove('bg-red-600', 'text-white', 'hover:bg-red-700');
        btn.classList.add('bg-gray-300', 'text-gray-900', 'hover:bg-gray-400');
    });
    document.querySelectorAll('.period-btn-hm').forEach(btn => {
        btn.classList.remove('bg-red-600', 'text-white', 'hover:bg-red-700');
        btn.classList.add('bg-gray-300', 'text-gray-900', 'hover:bg-gray-400');
    });
    
    // Подсветить активную кнопку
    const activeBtnOverview = document.getElementById(`period-${days}`);
    const activeBtnHeatmap = document.getElementById(`period-${days}-hm`);
    
    if (activeBtnOverview) {
        activeBtnOverview.classList.remove('bg-gray-300', 'text-gray-900', 'hover:bg-gray-400');
        activeBtnOverview.classList.add('bg-red-600', 'text-white', 'hover:bg-red-700');
    }
    if (activeBtnHeatmap) {
        activeBtnHeatmap.classList.remove('bg-gray-300', 'text-gray-900', 'hover:bg-gray-400');
        activeBtnHeatmap.classList.add('bg-red-600', 'text-white', 'hover:bg-red-700');
    }
    
    // Обновить данные в зависимости от текущего view
    if (currentView === 'overview') {
        loadData();
    } else if (currentView === 'heatmap') {
        document.getElementById('period-days-hm').innerText = days;
        heatmapLoadWhenNeeded();
    }
}

async function loadData() {
    try {
        // Основные метрики
        const overview = await fetch(`/api/analytics/overview?${siteParams(`days=${currentPeriod}`)}`).then(r => r.json());
        document.getElementById('sessions-count').innerText = overview.sessions;
        document.getElementById('visitors-count').innerText = overview.visitors;
        document.getElementById('events-count').innerText = overview.events;
        document.getElementById('bounce-rate').innerText = overview.bounce_rate + '%';
        document.getElementById('avg-duration').innerText = overview.avg_duration;

        // Графики
        const timeline = await fetch(`/api/analytics/timeline?${siteParams(`days=${currentPeriod}`)}`).then(r => r.json());
        drawChart('timeline-chart', 'line', {
            labels: timeline.dates,
            datasets: [{
                label: 'Сессий',
                data: timeline.counts,
                borderColor: '#00d9ff',
                backgroundColor: 'rgba(0, 217, 255, 0.1)',
                tension: 0.3,
                fill: true
            }]
        });

        const devices = await fetch(`/api/analytics/devices?${siteParams(`days=${currentPeriod}`)}`).then(r => r.json());
        drawChart('devices-chart', 'doughnut', {
            labels: devices.devices,
            datasets: [{
                data: devices.counts,
                backgroundColor: ['#ff6b6b', '#4ecdc4', '#45b7d1']
            }]
        });

        const sections = await fetch(`/api/analytics/sections?${siteParams(`days=${currentPeriod}`)}`).then(r => r.json());
        drawChart('sections-chart', 'bar', {
            labels: sections.sections,
            datasets: [{
                label: 'Просмотры',
                data: sections.views,
                backgroundColor: '#00d9ff'
            }]
        });

        const utm = await fetch(`/api/analytics/utm?${siteParams(`days=${currentPeriod}`)}`).then(r => r.json());
        drawChart('utm-chart', 'pie', {
            labels: utm.sources,
            datasets: [{
                data: utm.counts,
                backgroundColor: ['#ff6b6b', '#4ecdc4', '#45b7d1', '#f7b731', '#5f27cd']
            }]
        });

        const events = await fetch(`/api/analytics/events?${siteParams(`days=${currentPeriod}`)}`).then(r => r.json());
        drawChart('events-chart', 'bar', {
            labels: events.events,
            datasets: [{
                label: 'События',
                data: events.counts,
                backgroundColor: '#00d9ff'
            }]
        }, true);

        // Последние сессии
        const sessions = await fetch(`/api/analytics/recent-sessions?${siteParams('limit=20')}`).then(r => r.json());
        const table = document.getElementById('sessions-table');
        table.innerHTML = sessions.map(s => `
            <tr class="border-b border-gray-700 hover:bg-gray-700/30 cursor-pointer" onclick="showSessionDetail('${s.session_id}')">
                <td class="py-2 px-2">${s.device_type}</td>
                <td class="py-2 px-2">${s.pages_viewed}</td>
                <td class="py-2 px-2">${s.duration || '-'}</td>
                <td class="py-2 px-2">${s.is_bounce ? 'Да' : 'Нет'}</td>
                <td class="py-2 px-2">${s.utm_source || '-'}</td>
                <td class="py-2 px-2 text-gray-400 text-xs">${new Date(s.started_at).toLocaleString('ru-RU')}</td>
            </tr>
        `).join('');

    } catch (error) {
        console.error('Error loading data:', error);
    }
}

async function loadHeatmap() {
    try {
        const heatmap = await fetch(`/api/analytics/heatmap?days=${currentPeriod}`).then(r => r.json());
        
        // Найти максимум кликов для нормализации
        const maxClicks = Math.max(...heatmap.conversions, 1);
        
        // Позиции секций на странице (в процентах от общей высоты)
        const sectionPositions = {
            'hero': { top: 0, height: 25 },
            'booking_form': { top: 25, height: 20 },
            'about_us': { top: 45, height: 15 },
            'challenges': { top: 60, height: 15 },
            'our_solution': { top: 75, height: 10 },
            'effectiveness': { top: 85, height: 8 },
            'tariffs': { top: 93, height: 7 }
        };
        
        // Генерировать тепловой слой
        const heatmapPreview = document.getElementById('heatmap-preview');
        heatmapPreview.innerHTML = heatmap.sections.map((section, i) => {
            const clicks = heatmap.conversions[i];
            const intensity = clicks / maxClicks; // 0-1
            
            // Цвет на основе интенсивности
            const opacity = Math.max(0.15, intensity);
            const bgColor = `rgba(220, 38, 38, ${opacity})`;
            
            const pos = sectionPositions[section] || { top: i * 15, height: 15 };
            
            return `
                <div style="
                    position: absolute;
                    top: ${pos.top}%;
                    left: 0;
                    width: 100%;
                    height: ${pos.height}%;
                    background: ${bgColor};
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-weight: bold;
                    text-shadow: 0 2px 4px rgba(0,0,0,0.5);
                    border-bottom: 1px solid rgba(0,0,0,0.1);
                    transition: background 0.3s ease;
                " 
                class="heatmap-section"
                title="Секция: ${section}&#10;Клики: ${clicks}">
                    <div class="text-center">
                        <div class="text-lg font-bold capitalize">${section.replace('_', ' ')}</div>
                        <div class="text-sm">Клики: ${clicks}</div>
                    </div>
                </div>
            `;
        }).join('');
        
        // Заполнить таблицу
        const heatmapTable = document.getElementById('heatmap-table');
        heatmapTable.innerHTML = heatmap.sections.map((section, i) => {
            const views = heatmap.views[i];
            const clicks = heatmap.conversions[i];
            const ctr = views > 0 ? Math.round((clicks / views) * 100) : 0;
            const intensity = clicks / maxClicks;
            
            let intensityBar = getIntensityBar(intensity);
            
            return `
                <tr class="border-b border-gray-200 hover:bg-gray-50">
                    <td class="py-3 px-4 capitalize font-medium text-gray-900">${section.replace('_', ' ')}</td>
                    <td class="py-3 px-4 text-gray-700">${views}</td>
                    <td class="py-3 px-4 font-bold text-red-600">${clicks}</td>
                    <td class="py-3 px-4 font-semibold text-gray-900">${ctr}%</td>
                    <td class="py-3 px-4">
                        <div class="flex items-center gap-2">
                            <div style="width: 120px; height: 6px; background: #e5e7eb; border-radius: 3px; overflow: hidden;">
                                <div style="width: ${intensity * 100}%; height: 100%; background: linear-gradient(90deg, #fca5a5, #dc2626); transition: width 0.3s ease;"></div>
                            </div>
                            <span class="text-sm text-gray-600 w-12">${Math.round(intensity * 100)}%</span>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
        
    } catch (error) {
        console.error('Error loading heatmap:', error);
    }
}

function getIntensityBar(intensity) {
    if (intensity > 0.75) return '████████████████ Очень высокая';
    if (intensity > 0.5) return '████████████░░░░ Высокая';
    if (intensity > 0.25) return '████████░░░░░░░░ Средняя';
    return '████░░░░░░░░░░░░ Низкая';
}

async function loadSessionsData() {
    try {
        const deviceType = document.getElementById('filter-device')?.value || 'all';
        const utmSource = document.getElementById('filter-utm')?.value || 'all';
        const isBounce = document.getElementById('filter-bounce')?.value || 'all';
        const minDuration = document.getElementById('filter-duration')?.value || undefined;
        
        let url = `/api/analytics/search-sessions?${siteParams(`device_type=${deviceType}&utm_source=${utmSource}&is_bounce=${isBounce}`)}`;
        if (minDuration) url += `&min_duration=${minDuration}`;
        
        const sessions = await fetch(url).then(r => r.json());
        
        const table = document.getElementById('filtered-sessions-table');
        table.innerHTML = sessions.map(s => `
            <tr class="border-b border-gray-700 hover:bg-gray-700/30 cursor-pointer" onclick="showSessionDetail('${s.session_id}')">
                <td class="py-2 px-2">${s.session_id.slice(0, 8)}...</td>
                <td class="py-2 px-2">${s.device_type}</td>
                <td class="py-2 px-2">${s.pages_viewed}</td>
                <td class="py-2 px-2">${s.duration || '-'}</td>
                <td class="py-2 px-2"><span class="inline-block px-2 py-1 rounded text-xs ${s.is_bounce ? 'bg-red-900' : 'bg-green-900'}">${s.is_bounce ? 'Отказ' : 'Целевой'}</span></td>
                <td class="py-2 px-2">${s.utm_source || '-'}</td>
                <td class="py-2 px-2 text-gray-400 text-xs">${new Date(s.started_at).toLocaleString('ru-RU')}</td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading sessions:', error);
    }
}

async function showSessionDetail(sessionId) {
    try {
        const response = await fetch(`/api/analytics/session/${sessionId}`).then(r => r.json());
        const session = response.session;
        const events = response.events;
        
        const modal = document.getElementById('session-modal');
        const content = document.getElementById('modal-content');
        
        content.innerHTML = `
            <div class="mb-4">
                <h3 class="text-xl font-bold mb-2">Сессия ${session.session_id.slice(0, 8)}...</h3>
                <div class="grid grid-cols-2 gap-4 text-sm">
                    <div><span class="text-gray-400">Устройство:</span> ${session.device_type}</div>
                    <div><span class="text-gray-400">Браузер:</span> ${session.browser?.split(' ')[0] || '-'}</div>
                    <div><span class="text-gray-400">Экран:</span> ${session.screen}</div>
                    <div><span class="text-gray-400">Длительность:</span> ${session.duration}s</div>
                    <div><span class="text-gray-400">Страниц:</span> ${session.pages_viewed}</div>
                    <div><span class="text-gray-400">Отказ:</span> ${session.is_bounce ? 'Да' : 'Нет'}</div>
                    <div class="col-span-2"><span class="text-gray-400">UTM Source:</span> ${session.utm_source || '-'}</div>
                    <div class="col-span-2"><span class="text-gray-400">Referrer:</span> ${session.referrer?.slice(0, 50) || '-'}...</div>
                </div>
            </div>
            
            <div>
                <h4 class="font-bold mb-2">События (${events.length})</h4>
                <div class="space-y-2 max-h-96 overflow-y-auto">
                    ${events.map(e => `
                        <div class="bg-gray-800 p-2 rounded text-xs">
                            <span class="text-blue-400">${e.event_type}</span> - ${new Date(e.created_at).toLocaleTimeString('ru-RU')}
                            ${e.payload ? '<br>' + JSON.stringify(e.payload).slice(0, 100) : ''}
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
        
        modal.style.display = 'flex';
    } catch (error) {
        console.error('Error loading session:', error);
    }
}

function closeModal() {
    document.getElementById('session-modal').style.display = 'none';
}

function drawChart(canvasId, type, data, indexAxis = false, isBubble = false) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    
    if (charts[canvasId]) {
        charts[canvasId].destroy();
    }

    const config = {
        type: type,
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#94a3b8' } }
            },
            scales: isBubble ? {
                x: {
                    ticks: { color: '#94a3b8' },
                    grid: { color: '#334155' }
                },
                y: {
                    ticks: { color: '#94a3b8' },
                    grid: { color: '#334155' }
                }
            } : {
                y: {
                    ticks: { color: '#94a3b8' },
                    grid: { color: '#334155' }
                },
                x: {
                    ticks: { color: '#94a3b8' },
                    grid: { color: '#334155' }
                }
            }
        }
    };

    if (indexAxis) {
        config.options.indexAxis = 'y';
    }

    charts[canvasId] = new Chart(ctx, config);
}

// ============================================
// === HEATMAP.JS ФУНКЦИИ ===
// ============================================

/**
 * Изменение выбранной страницы в select
 */
function heatmapOnUrlChange() {
    const select = document.getElementById('heatmap-url-select');
    if (select) {
        currentHeatmapUrl = select.value;
        // Обновляем src iframe
        const iframe = document.getElementById('heatmap-iframe');
        if (iframe) iframe.src = currentHeatmapUrl;
        heatmapRefresh();
    }
}

/**
 * Обновить тепловую карту (при нажатии кнопки или смене параметров)
 */
async function heatmapRefresh() {
    const daysSelect = document.getElementById('heatmap-days-select');
    if (daysSelect) {
        currentHeatmapDays = parseInt(daysSelect.value) || 90;
    }
    
    const urlSelect = document.getElementById('heatmap-url-select');
    if (urlSelect) {
        currentHeatmapUrl = urlSelect.value;
    }

    // Полный сброс heatmap при смене параметров
    if (heatmapInstance) {
        const inner = document.getElementById('heatmap-inner');
        if (inner) inner.querySelectorAll('.heatmap-canvas').forEach(c => c.remove());
        heatmapInstance = null;
    }

    await heatmapLoadData(currentHeatmapUrl, currentHeatmapDays);
}

/**
 * Ожидание полной загрузки iframe
 */
function waitForIframe(iframe) {
    return new Promise((resolve) => {
        if (!iframe) { resolve(); return; }
        try {
            const doc = iframe.contentDocument || iframe.contentWindow.document;
            if (doc.readyState === 'complete') { resolve(); return; }
        } catch(e) { /* cross-origin — пропускаем */ }
        iframe.addEventListener('load', resolve, { once: true });
    });
}

/**
 * Загрузить данные кликов с сервера
 */
async function heatmapLoadData(pageUrl, days) {
    const loading = document.getElementById('heatmap-loading');
    if (loading) loading.style.display = 'flex';

    try {
        const iframe = document.getElementById('heatmap-iframe');

        // Загружаем данные API и ждём iframe параллельно
        const [response] = await Promise.all([
            fetch(`/api/clicks?${siteParams(`url=${encodeURIComponent(pageUrl)}&days=${days}`)}`),
            waitForIframe(iframe)
        ]);
        
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        const heatmapData = await response.json();

        // Обновляем счётчики
        document.getElementById('heatmap-total-clicks').innerText = 
            (heatmapData.total_clicks || 0).toLocaleString('ru-RU');
        document.getElementById('heatmap-unique-points').innerText = 
            (heatmapData.unique_points || 0).toLocaleString('ru-RU');
        document.getElementById('heatmap-period-days').innerText = days;

        // Инициализируем heatmap
        heatmapInitialize(heatmapData.data || []);

    } catch (error) {
        console.error('[Heatmap] Load error:', error);
        const container = document.getElementById('heatmap-container');
        const existingError = container?.querySelector('.heatmap-error');
        if (existingError) existingError.remove();
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'heatmap-error absolute inset-0 flex items-center justify-center bg-red-50/80';
        errorDiv.style.zIndex = '25';
        errorDiv.innerHTML = `<div class="text-center">
            <p class="text-red-700 font-bold">Ошибка загрузки данных</p>
            <p class="text-red-600 text-sm mt-2">${error.message}</p>
        </div>`;
        container?.appendChild(errorDiv);

    } finally {
        if (loading) loading.style.display = 'none';
    }
}

/**
 * Инициализировать и отрисовать heatmap.js на полную высоту страницы
 */
function heatmapInitialize(dataArray) {
    const RENDER_WIDTH = 1440; // Фиксированная ширина рендера (как в Яндекс.Метрике)
    const inner = document.getElementById('heatmap-inner');
    const iframe = document.getElementById('heatmap-iframe');
    const nodata = document.getElementById('heatmap-nodata');

    if (!inner || !iframe) {
        console.error('[Heatmap] Missing DOM elements');
        return;
    }

    // Скрываем "нет данных"
    if (nodata) nodata.style.display = 'none';

    // === Если нет данных ===
    if (!dataArray || dataArray.length === 0) {
        if (nodata) nodata.style.display = 'flex';
        return;
    }

    // === Проверяем h337 ===
    if (typeof h337 === 'undefined') {
        console.error('[Heatmap] h337 is not defined! Retrying in 1s...');
        setTimeout(() => heatmapInitialize(dataArray), 1000);
        return;
    }

    // === Фиксируем ширину iframe для стабильного рендера ===
    iframe.style.width = RENDER_WIDTH + 'px';
    iframe.style.transformOrigin = 'top left';

    // === Получаем полную высоту страницы из iframe ===
    let pageHeight;
    try {
        const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;

        // Инжектируем CSS, который заменяет viewport-зависимые высоты на фиксированные
        let fixStyle = iframeDoc.getElementById('heatmap-fix-vh');
        if (!fixStyle) {
            fixStyle = iframeDoc.createElement('style');
            fixStyle.id = 'heatmap-fix-vh';
            fixStyle.textContent = `
                .min-h-screen { min-height: 800px !important; }
                .h-screen { height: auto !important; }
            `;
            iframeDoc.head.appendChild(fixStyle);
        }

        // Пересчитать layout после установки фиксированной ширины и CSS
        void iframeDoc.body.offsetHeight;

        pageHeight = Math.max(
            iframeDoc.documentElement.scrollHeight,
            iframeDoc.body.scrollHeight,
            700
        );

        // === DEBUG: замерить позиции элементов при RENDER_WIDTH ===
        const sectionIds = ['hero', 'booking-form', 'about-us', 'challenges', 'our-solution', 'effectiveness', 'tariffs'];
        console.log(`[Heatmap] === POSITIONS at RENDER_WIDTH=${RENDER_WIDTH} (pageHeight=${pageHeight}) ===`);
        sectionIds.forEach(id => {
            const el = iframeDoc.getElementById(id);
            if (el) {
                const top = el.offsetTop;
                const h = el.offsetHeight;
                console.log(`[Heatmap]  #${id}: top=${top}px (${(top/pageHeight*100).toFixed(1)}%), h=${h}px, bottom=${top+h}px (${((top+h)/pageHeight*100).toFixed(1)}%)`);
            }
        });
        const trackEls = iframeDoc.querySelectorAll('[data-track-name], input[name], button[type="submit"]');
        console.log('[Heatmap] === INTERACTIVE ELEMENTS ===');
        trackEls.forEach(el => {
            const rect = el.getBoundingClientRect();
            const absTop = rect.top + (iframe.contentWindow.scrollY || 0);
            const absLeft = rect.left;
            const name = el.dataset?.trackName || el.name || el.type || 'unknown';
            console.log(`[Heatmap]  "${name}": x=${(absLeft/RENDER_WIDTH*100).toFixed(1)}%-${((absLeft+rect.width)/RENDER_WIDTH*100).toFixed(1)}%, y=${(absTop/pageHeight*100).toFixed(1)}%-${((absTop+rect.height)/pageHeight*100).toFixed(1)}%`);
        });
    } catch (e) {
        console.warn('[Heatmap] Cannot read iframe height, using fallback');
        pageHeight = 5400;
    }

    // === Масштабирование: iframe рендерится при RENDER_WIDTH, масштабируем в контейнер ===
    const containerWidth = inner.offsetWidth;
    const scale = containerWidth / RENDER_WIDTH;
    const scaledHeight = Math.round(pageHeight * scale);

    iframe.style.height = pageHeight + 'px';
    iframe.style.transform = `scale(${scale})`;
    inner.style.height = scaledHeight + 'px';

    console.log(`[Heatmap] Render: ${RENDER_WIDTH}x${pageHeight} → scale ${scale.toFixed(3)} → ${containerWidth}x${scaledHeight}`);

    // === Очищаем предыдущий heatmap ===
    if (heatmapInstance) {
        inner.querySelectorAll('.heatmap-canvas').forEach(c => c.remove());
        heatmapInstance = null;
    }

    try {
        heatmapInstance = h337.create({
            container: inner,
            radius: Math.round(25 * scale),
            blur: 0.85,
            maxOpacity: 0.7,
            minOpacity: 0,
            gradient: {
                '.0': '#0000FF',
                '.17': '#00FFFF',
                '.33': '#00FF00',
                '.5': '#FFFF00',
                '.67': '#FF8800',
                '.84': '#FF4400',
                '1.0': '#FF0000'
            }
        });

        // Ставим canvas поверх iframe
        const heatCanvas = inner.querySelector('.heatmap-canvas');
        if (heatCanvas) {
            heatCanvas.style.zIndex = '5';
            heatCanvas.style.pointerEvents = 'none';
        }

        // === Преобразуем процентные координаты → пиксели масштабированного контейнера ===
        const pixelData = dataArray.map(p => ({
            x: Math.round((p.x / 100) * containerWidth),
            y: Math.round((p.y / 100) * scaledHeight),
            value: p.value
        }));

        heatmapInstance.setData({ max: 100, data: pixelData });

        console.log('[Heatmap] Rendered successfully!', {
            points: pixelData.length,
            pageSize: { width: containerWidth, height: scaledHeight }
        });
    } catch (error) {
        console.error('[Heatmap] Render error:', error);
    }
}

/**
 * Загрузить тепловую карту при открытии вкладки
 */
function heatmapLoadWhenNeeded() {
    heatmapRefresh();
}

// Загрузить данные при загрузке страницы
changeView('overview');

// ============================================
// === СРАВНЕНИЕ РЕВИЗИЙ ===
// ============================================
async function loadComparison() {
    const container = document.getElementById('comparison-content');
    container.innerHTML = '<div class="card"><div class="text-center py-8 text-gray-500">Загрузка...</div></div>';

    try {
        const data = await fetch(`/api/analytics/compare-revisions?${siteParams('days=90')}`).then(r => r.json());
        const revs = data.revisions;

        if (!revs || revs.length === 0) {
            container.innerHTML = '<div class="card"><p class="text-gray-500 text-center py-8">Нет ревизий для сравнения.</p></div>';
            return;
        }

        // Метрики для отображения
        const metrics = [
            { key: 'sessions', label: 'Сессии' },
            { key: 'visitors', label: 'Визиторы' },
            { key: 'events', label: 'События' },
            { key: 'bounce_rate', label: 'Отказы %', suffix: '%', lower_better: true },
            { key: 'avg_duration', label: 'Ср. длительность (с)' },
            { key: 'avg_pages', label: 'Ср. страниц' },
            { key: 'cta_clicks', label: 'CTA клики' },
            { key: 'form_submits', label: 'Отправки форм' },
        ];

        // Таблица сравнения
        let html = `<div class="card mb-6 overflow-x-auto">
            <h3 class="text-xl font-bold mb-4">Сравнительная таблица</h3>
            <table class="w-full text-sm">
                <thead>
                    <tr class="border-b-2 border-gray-300">
                        <th class="text-left py-3 px-4 font-semibold">Метрика</th>
                        ${revs.map(r => `<th class="text-center py-3 px-4 font-semibold">${r.name}${r.is_active ? ' <span class="text-xs text-green-600">●</span>' : ''}</th>`).join('')}
                    </tr>
                </thead>
                <tbody>`;

        metrics.forEach(m => {
            const vals = revs.map(r => r[m.key] || 0);
            const best = m.lower_better ? Math.min(...vals) : Math.max(...vals);

            html += `<tr class="border-b border-gray-200 hover:bg-gray-50">
                <td class="py-3 px-4 font-medium">${m.label}</td>`;

            revs.forEach(r => {
                const val = r[m.key] || 0;
                const isBest = val === best && vals.filter(v => v === best).length === 1;
                const cls = isBest ? 'font-bold text-green-700' : '';
                html += `<td class="text-center py-3 px-4 ${cls}">${val}${m.suffix || ''}</td>`;
            });

            html += `</tr>`;
        });

        html += `</tbody></table></div>`;

        // Графики сравнения
        html += `<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div class="card"><h3 class="text-lg font-bold mb-3">Сессии по ревизиям</h3><div class="chart-container"><canvas id="comp-sessions-chart"></canvas></div></div>
            <div class="card"><h3 class="text-lg font-bold mb-3">Отказы по ревизиям</h3><div class="chart-container"><canvas id="comp-bounce-chart"></canvas></div></div>
            <div class="card"><h3 class="text-lg font-bold mb-3">CTA клики</h3><div class="chart-container"><canvas id="comp-cta-chart"></canvas></div></div>
            <div class="card"><h3 class="text-lg font-bold mb-3">Ср. длительность (с)</h3><div class="chart-container"><canvas id="comp-duration-chart"></canvas></div></div>
        </div>`;

        container.innerHTML = html;

        // Отрисовка графиков
        const labels = revs.map(r => r.name);
        const colors = ['#e30613', '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899'];

        drawChart('comp-sessions-chart', 'bar', { labels, datasets: [{ label: 'Сессии', data: revs.map(r => r.sessions), backgroundColor: colors.slice(0, revs.length) }] });
        drawChart('comp-bounce-chart', 'bar', { labels, datasets: [{ label: 'Отказы %', data: revs.map(r => r.bounce_rate), backgroundColor: colors.slice(0, revs.length) }] });
        drawChart('comp-cta-chart', 'bar', { labels, datasets: [{ label: 'CTA клики', data: revs.map(r => r.cta_clicks), backgroundColor: colors.slice(0, revs.length) }] });
        drawChart('comp-duration-chart', 'bar', { labels, datasets: [{ label: 'Длительность', data: revs.map(r => r.avg_duration), backgroundColor: colors.slice(0, revs.length) }] });

    } catch (err) {
        console.error('Comparison error:', err);
        container.innerHTML = '<div class="card"><p class="text-red-500 text-center py-8">Ошибка загрузки данных</p></div>';
    }
}

// ============================================
// === МОДАЛЬНОЕ ОКНО ГИПОТЕЗ ===
// ============================================
function openHypothesisModal() {
    document.getElementById('hypothesis-modal').style.display = 'flex';
}

function closeHypothesisModal() {
    document.getElementById('hypothesis-modal').style.display = 'none';
    document.getElementById('hyp-error').classList.add('hidden');
}

async function submitHypothesis() {
    const errDiv = document.getElementById('hyp-error');
    errDiv.classList.add('hidden');

    const title = document.getElementById('hyp-title').value.trim();
    const hypothesis_text = document.getElementById('hyp-text').value.trim();
    if (!title || !hypothesis_text) {
        errDiv.textContent = 'Заполните название и формулировку гипотезы';
        errDiv.classList.remove('hidden');
        return;
    }

    const body = {
        title,
        hypothesis_text,
        category: document.getElementById('hyp-category').value,
        metric: document.getElementById('hyp-metric').value,
        segment_a_field: document.getElementById('hyp-seg-a-field').value,
        segment_a_op: document.getElementById('hyp-seg-a-op').value,
        segment_a_value: document.getElementById('hyp-seg-a-value').value,
        segment_b_field: document.getElementById('hyp-seg-b-field').value || null,
        segment_b_op: document.getElementById('hyp-seg-b-op').value || null,
        segment_b_value: document.getElementById('hyp-seg-b-value').value || null,
        compare_mode: document.getElementById('hyp-compare-mode').value,
        threshold_confirmed: parseFloat(document.getElementById('hyp-thresh-conf').value) || 1.5,
        threshold_partial: parseFloat(document.getElementById('hyp-thresh-part').value) || 1.2,
        advice_confirmed: document.getElementById('hyp-advice-yes').value.trim() || null,
        advice_not_confirmed: document.getElementById('hyp-advice-no').value.trim() || null,
    };

    try {
        const resp = await fetch(`/api/hypotheses?${siteParams()}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(body),
        });
        const data = await resp.json();
        if (!resp.ok) {
            errDiv.textContent = data.error || 'Ошибка создания';
            errDiv.classList.remove('hidden');
            return;
        }
        closeHypothesisModal();
        loadInsights();
    } catch (err) {
        console.error('Create hypothesis error:', err);
        errDiv.textContent = 'Ошибка сети';
        errDiv.classList.remove('hidden');
    }
}

async function deleteHypothesis(id) {
    if (!confirm('Удалить эту гипотезу?')) return;
    try {
        await fetch(`/api/hypotheses/${id}`, { method: 'DELETE' });
        loadInsights();
    } catch (err) {
        console.error('Delete hypothesis error:', err);
    }
}

// ============================================
// === ГИПОТЕЗЫ И РЕКОМЕНДАЦИИ ===
// ============================================
async function loadInsights() {
    const container = document.getElementById('insights-content');
    container.innerHTML = '<div class="card"><div class="text-center py-8 text-gray-500">Анализ данных...</div></div>';

    try {
        const data = await fetch(`/api/analytics/insights?${siteParams('days=90')}`).then(r => r.json());
        const insights = data.insights;

        if (!insights || insights.length === 0) {
            container.innerHTML = '<div class="card"><p class="text-gray-500 text-center py-8">Недостаточно данных для анализа.</p></div>';
            return;
        }

        const statusColors = {
            confirmed: { bg: 'bg-green-50', border: 'border-green-300', badge: 'bg-green-100 text-green-800', label: 'Подтверждена' },
            partial: { bg: 'bg-yellow-50', border: 'border-yellow-300', badge: 'bg-yellow-100 text-yellow-800', label: 'Частично' },
            not_confirmed: { bg: 'bg-gray-50', border: 'border-gray-300', badge: 'bg-gray-100 text-gray-600', label: 'Не подтверждена' }
        };

        const categoryLabels = {
            engagement: 'Вовлечённость',
            ux: 'UX / Интерфейс',
            traffic: 'Трафик и маркетинг',
            retention: 'Возвращаемость',
            conversion: 'Конверсия'
        };

        const grouped = {};
        insights.forEach(i => {
            if (!grouped[i.category]) grouped[i.category] = [];
            grouped[i.category].push(i);
        });

        let html = '';
        for (const [cat, items] of Object.entries(grouped)) {
            html += `<div class="mb-8">
                <h2 class="text-2xl font-bold mb-4">${categoryLabels[cat] || cat}</h2>
                <div class="space-y-4">`;

            items.forEach(ins => {
                const st = statusColors[ins.status] || statusColors.not_confirmed;
                const deleteBtn = ins.is_base === false
                    ? `<button onclick="deleteHypothesis('${ins.id}')" class="ml-2 text-gray-400 hover:text-red-500 transition-colors" title="Удалить гипотезу"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg></button>`
                    : '';
                const customTag = ins.is_base === false
                    ? '<span class="ml-2 px-2 py-0.5 rounded text-[10px] font-medium bg-blue-100 text-blue-700">Пользовательская</span>'
                    : '';
                html += `
                <div class="card ${st.bg} border ${st.border}">
                    <div class="flex items-start justify-between mb-3">
                        <h3 class="text-lg font-bold text-gray-900">${ins.title}${customTag}</h3>
                        <div class="flex items-center shrink-0">
                            <span class="px-3 py-1 rounded-full text-xs font-semibold ${st.badge}">${st.label}</span>
                            ${deleteBtn}
                        </div>
                    </div>
                    <div class="mb-2">
                        <p class="text-sm text-gray-600"><strong>Гипотеза:</strong> ${ins.hypothesis}</p>
                    </div>
                    <div class="mb-2">
                        <p class="text-sm text-gray-800"><strong>Результат:</strong> ${ins.result}</p>
                    </div>
                    <div class="mt-3 p-3 rounded-lg" style="background:rgba(0,0,0,0.03);">
                        <p class="text-sm font-medium" style="color:#e30613;"><svg class="inline w-4 h-4 mr-1 -mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/></svg>${ins.advice}</p>
                    </div>
                </div>`;
            });

            html += `</div></div>`;
        }

        container.innerHTML = html;

    } catch (err) {
        console.error('Insights error:', err);
        container.innerHTML = '<div class="card"><p class="text-red-500 text-center py-8">Ошибка загрузки данных</p></div>';
    }
}

// Инициализировать подсвечивание кнопок периода
const period7Btn = document.getElementById('period-7');
const period7HmBtn = document.getElementById('period-7-hm');
if (period7Btn) period7Btn.classList.add('bg-red-600', 'text-white', 'hover:bg-red-700');
if (period7HmBtn) period7HmBtn.classList.add('bg-red-600', 'text-white', 'hover:bg-red-700');
