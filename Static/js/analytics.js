let currentPeriod = 7;
let currentView = 'overview';
let charts = {};

function changeView(view) {
    currentView = view;
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    document.querySelector(`[data-view="${view}"]`).classList.add('active');
    
    document.querySelectorAll('[data-view-content]').forEach(el => el.style.display = 'none');
    document.querySelector(`[data-view-content="${view}"]`).style.display = 'block';
    
    if (view === 'overview') {
        loadData();
    } else if (view === 'sessions') {
        loadSessionsData();
    } else if (view === 'heatmap') {
        loadHeatmap();
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
        loadHeatmap();
    }
}

async function loadData() {
    try {
        // Основные метрики
        const overview = await fetch(`/api/analytics/overview?days=${currentPeriod}`).then(r => r.json());
        document.getElementById('sessions-count').innerText = overview.sessions;
        document.getElementById('visitors-count').innerText = overview.visitors;
        document.getElementById('events-count').innerText = overview.events;
        document.getElementById('bounce-rate').innerText = overview.bounce_rate + '%';
        document.getElementById('avg-duration').innerText = overview.avg_duration;

        // Графики
        const timeline = await fetch(`/api/analytics/timeline?days=${currentPeriod}`).then(r => r.json());
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

        const devices = await fetch(`/api/analytics/devices?days=${currentPeriod}`).then(r => r.json());
        drawChart('devices-chart', 'doughnut', {
            labels: devices.devices,
            datasets: [{
                data: devices.counts,
                backgroundColor: ['#ff6b6b', '#4ecdc4', '#45b7d1']
            }]
        });

        const sections = await fetch(`/api/analytics/sections?days=${currentPeriod}`).then(r => r.json());
        drawChart('sections-chart', 'bar', {
            labels: sections.sections,
            datasets: [{
                label: 'Просмотры',
                data: sections.views,
                backgroundColor: '#00d9ff'
            }]
        });

        const utm = await fetch(`/api/analytics/utm?days=${currentPeriod}`).then(r => r.json());
        drawChart('utm-chart', 'pie', {
            labels: utm.sources,
            datasets: [{
                data: utm.counts,
                backgroundColor: ['#ff6b6b', '#4ecdc4', '#45b7d1', '#f7b731', '#5f27cd']
            }]
        });

        const events = await fetch(`/api/analytics/events?days=${currentPeriod}`).then(r => r.json());
        drawChart('events-chart', 'bar', {
            labels: events.events,
            datasets: [{
                label: 'События',
                data: events.counts,
                backgroundColor: '#00d9ff'
            }]
        }, true);

        // Последние сессии
        const sessions = await fetch(`/api/analytics/recent-sessions?limit=20`).then(r => r.json());
        const table = document.getElementById('sessions-table');
        table.innerHTML = sessions.map(s => `
            <tr class="border-b border-gray-700 hover:bg-gray-700/30 cursor-pointer" onclick="showSessionDetail('${s.session_id}')">
                <td class="py-2 px-2">${s.device_type}</td>
                <td class="py-2 px-2">${s.pages_viewed}</td>
                <td class="py-2 px-2">${s.duration || '-'}</td>
                <td class="py-2 px-2">${s.is_bounce ? '✓' : '✗'}</td>
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
        
        let url = `/api/analytics/search-sessions?device_type=${deviceType}&utm_source=${utmSource}&is_bounce=${isBounce}`;
        if (minDuration) url += `&min_duration=${minDuration}`;
        
        const sessions = await fetch(url).then(r => r.json());
        
        const table = document.getElementById('filtered-sessions-table');
        table.innerHTML = sessions.map(s => `
            <tr class="border-b border-gray-700 hover:bg-gray-700/30 cursor-pointer" onclick="showSessionDetail('${s.session_id}')">
                <td class="py-2 px-2">${s.session_id.slice(0, 8)}...</td>
                <td class="py-2 px-2">${s.device_type}</td>
                <td class="py-2 px-2">${s.pages_viewed}</td>
                <td class="py-2 px-2">${s.duration || '-'}</td>
                <td class="py-2 px-2"><span class="inline-block px-2 py-1 rounded text-xs ${s.is_bounce ? 'bg-red-900' : 'bg-green-900'}">${s.is_bounce ? 'Bounce' : 'Conv'}</span></td>
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
                    <div><span class="text-gray-400">Bounce:</span> ${session.is_bounce ? 'Yes' : 'No'}</div>
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

// Загрузить данные при загрузке страницы
changeView('overview');

// Инициализировать подсвечивание кнопок периода
document.getElementById('period-7').classList.add('bg-red-600', 'text-white', 'hover:bg-red-700');
document.getElementById('period-7-hm').classList.add('bg-red-600', 'text-white', 'hover:bg-red-700');
