/* Premium Dashboard JavaScript */
(function () {
  // Escape HTML helper
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  }

  // Risk badge HTML generator
  function riskBadgeHTML(level) {
    const gradients = {
      'CRITICAL': 'from-red-700 to-red-900',
      'HIGH': 'from-rose-500 to-red-600',
      'MEDIUM': 'from-amber-400 to-orange-500',
      'LOW': 'from-emerald-400 to-teal-500'
    };
    
    return `
      <span class="inline-flex items-center gap-1.5 px-2.5 py-1 bg-gradient-to-r ${gradients[level] || gradients.LOW} text-white text-[10px] font-bold rounded-full uppercase tracking-wide shadow-sm">
        <span class="w-1.5 h-1.5 bg-white rounded-full ${level === 'HIGH' || level === 'CRITICAL' ? 'animate-pulse' : ''}"></span>
        ${level}
      </span>
    `;
  }

  // Severity badge
  function severityBadge(sev) {
    const colors = sev >= 4 ? ['bg-rose-100', 'text-rose-700', 'border-rose-200'] :
                   sev === 3 ? ['bg-amber-100', 'text-amber-700', 'border-amber-200'] :
                   ['bg-surface-100', 'text-surface-600', 'border-surface-200'];
    return `
      <span class="inline-flex items-center px-2 py-1 ${colors[0]} ${colors[1]} text-xs font-bold rounded-lg border ${colors[2]}">
        ${sev >= 4 ? '<svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>' : ''}
        SEV ${sev}
      </span>
    `;
  }

  // Alert badge
  function alertBadge(sev) {
    const configs = {
      'CRITICAL': ['from-rose-600 to-red-700', 'animate-ping'],
      'HIGH': ['from-orange-500 to-red-500', ''],
      'MEDIUM': ['from-amber-400 to-orange-500', ''],
      'LOW': ['bg-surface-200 text-surface-600', '']
    };
    const config = configs[sev] || configs['LOW'];
    const isLow = sev === 'LOW';
    
    return isLow ? 
      `<span class="inline-flex items-center gap-1 px-2 py-1 ${config[0]} text-[10px] font-bold rounded-full uppercase tracking-wide">${sev}</span>` :
      `<span class="inline-flex items-center gap-1 px-2 py-1 bg-gradient-to-r ${config[0]} text-white text-[10px] font-bold rounded-full uppercase tracking-wide shadow-sm">
        ${config[1] ? '<span class="w-1.5 h-1.5 bg-white rounded-full animate-ping"></span>' : ''}
        ${sev}
      </span>`;
  }

  // Animate number counter
  function animateNumber(element, target, suffix = '', duration = 800) {
    const start = 0;
    const startTime = performance.now();
    
    function update(currentTime) {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const easeOut = 1 - Math.pow(1 - progress, 3);
      const current = Math.floor(start + (target - start) * easeOut);
      
      element.textContent = current + suffix;
      
      if (progress < 1) {
        requestAnimationFrame(update);
      } else {
        element.textContent = target + suffix;
      }
    }
    
    requestAnimationFrame(update);
  }

  const ICONS = {
    chart: '<svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z"/></svg>',
    bell: '<svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0"/></svg>',
    check: '<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>',
    warning: '<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"/></svg>',
    alert: '<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m2.25.75V9.75a2.25 2.25 0 00-4.5 0v3.75M3.75 9.75h16.5M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V9.75"/></svg>',
    route: '<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 6.75V15m6-6v8.25m.503 3.498l4.875-2.437c.381-.19.622-.58.622-1.006V4.82c0-.836-.88-1.38-1.628-1.006l-3.869 1.934c-.317.159-.69.159-1.006 0L9.503 3.252a1.125 1.125 0 00-1.006 0L3.622 5.689C3.24 5.88 3 6.27 3 6.695V19.18c0 .836.88 1.38 1.628 1.006l3.869-1.934c.317-.159.69-.159 1.006 0l4.994 2.497c.317.158.69.158 1.006 0z"/></svg>',
    pin: '<svg class="w-3 h-3 inline" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z"/></svg>',
    doc: '<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"/></svg>',
  };

  function riskLevelIcon(level) {
    if (level === 'CRITICAL' || level === 'HIGH') return ICONS.alert;
    if (level === 'MEDIUM') return ICONS.warning;
    return ICONS.check;
  }

  function riskLevelIconColor(level) {
    if (level === 'CRITICAL') return 'bg-red-50 text-red-600';
    if (level === 'HIGH') return 'bg-rose-50 text-rose-600';
    if (level === 'MEDIUM') return 'bg-amber-50 text-amber-600';
    return 'bg-emerald-50 text-emerald-600';
  }

  // Render Risk Areas with progress bars
  function renderRiskAreas(areas) {
    const container = document.getElementById('risk-areas-container');
    if (!areas.length) {
      container.innerHTML = `
        <div class="text-center py-8">
          <div class="w-12 h-12 mx-auto mb-3 rounded-xl bg-surface-100 text-surface-400 flex items-center justify-center">${ICONS.chart}</div>
          <p class="text-surface-400 text-sm">No risk areas monitored yet</p>
        </div>
      `;
      return;
    }

    // Sort by risk score descending
    const sorted = [...areas].sort((a, b) => b.risk_score - a.risk_score);
    
    container.innerHTML = sorted.slice(0, 6).map((area, index) => {
      const width = Math.min(100, Math.max(5, area.risk_score));
      const colors = area.risk_level === 'CRITICAL' ?
        ['from-red-600 to-red-800', 'bg-red-50'] :
        area.risk_level === 'HIGH' ? 
        ['from-rose-400 to-rose-600', 'bg-rose-50'] :
        area.risk_level === 'MEDIUM' ? 
        ['from-amber-400 to-orange-500', 'bg-amber-50'] :
        ['from-emerald-400 to-teal-500', 'bg-emerald-50'];
      
      const iconClass = riskLevelIconColor(area.risk_level);
      const icon = riskLevelIcon(area.risk_level);
      const scoreColor = area.risk_level === 'CRITICAL' ? 'text-red-700' : area.risk_level === 'HIGH' ? 'text-rose-600' : area.risk_level === 'MEDIUM' ? 'text-amber-600' : 'text-emerald-600';
      
      return `
        <div class="group" style="animation: fadeIn 0.3s ease ${index * 0.05}s both;">
          <div class="flex items-center justify-between mb-2">
            <div class="flex items-center gap-3">
              <div class="w-8 h-8 rounded-lg ${iconClass} flex items-center justify-center">
                ${icon}
              </div>
              <div>
                <p class="text-sm font-semibold text-surface-800">${esc(area.area_name)}</p>
                <p class="text-[10px] text-surface-400">${area.event_count || 0} events tracked</p>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-lg font-display font-bold ${scoreColor}">${area.risk_score}</span>
              ${riskBadgeHTML(area.risk_level)}
            </div>
          </div>
          <div class="h-2 bg-surface-100 rounded-full overflow-hidden">
            <div class="h-full bg-gradient-to-r ${colors[0]} rounded-full transition-all duration-1000 ease-out relative overflow-hidden" style="width: 0%" data-width="${width}%">
              <div class="absolute inset-0 bg-white/30 animate-pulse"></div>
            </div>
          </div>
        </div>
      `;
    }).join('');

    // Animate progress bars after render
    setTimeout(() => {
      container.querySelectorAll('[data-width]').forEach(bar => {
        bar.style.width = bar.dataset.width;
      });
    }, 100);
  }

  // Render Alerts
  function renderAlerts(alerts) {
    const container = document.getElementById('alerts-feed');
    if (!alerts.length) {
      container.innerHTML = `
        <div class="text-center py-6">
          <div class="w-10 h-10 mx-auto mb-2 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">${ICONS.check}</div>
          <p class="text-surface-400 text-xs">No active alerts</p>
        </div>
      `;
      return;
    }

    container.innerHTML = alerts.slice(0, 5).map((alert, index) => `
      <div class="glass-card p-4 rounded-xl border-l-4 ${alert.severity === 'CRITICAL' ? 'border-l-rose-500' : alert.severity === 'HIGH' ? 'border-l-orange-500' : 'border-l-amber-400'} hover:shadow-md transition-all" style="animation: slideIn 0.3s ease ${index * 0.05}s both;">
        <div class="flex items-start justify-between gap-3">
          <div class="flex-1 min-w-0">
            <p class="text-sm text-surface-700 font-medium leading-snug line-clamp-2">${esc(alert.message)}</p>
            <div class="flex items-center gap-2 mt-2">
              ${alertBadge(alert.severity)}
              <span class="text-[10px] text-surface-400">Target: ${esc(alert.target_role)}</span>
            </div>
          </div>
          <span class="text-[10px] text-surface-400 whitespace-nowrap">${new Date(alert.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
        </div>
      </div>
    `).join('');

    document.dispatchEvent(new CustomEvent('sr:alerts-updated', { detail: alerts }));
  }

  // Render Events
  function renderEvents(events) {
    const container = document.getElementById('events-feed');
    if (!events.length) {
      container.innerHTML = `<p class="text-surface-400 text-sm text-center py-4">No recent events</p>`;
      return;
    }

    container.innerHTML = events.slice(0, 5).map((event, index) => `
      <div class="flex items-center gap-4 p-3 rounded-xl hover:bg-surface-50 transition-colors group cursor-pointer" style="animation: fadeIn 0.3s ease ${index * 0.05}s both;">
        <div class="w-10 h-10 rounded-lg ${event.severity >= 4 ? 'bg-rose-50 text-rose-600' : event.severity === 3 ? 'bg-amber-50 text-amber-600' : 'bg-surface-100 text-surface-500'} flex items-center justify-center flex-shrink-0">
          ${event.severity >= 4 ? ICONS.alert : event.severity === 3 ? ICONS.warning : ICONS.doc}
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-sm font-semibold text-surface-800 truncate group-hover:text-primary-600 transition-colors">${esc(event.title)}</p>
          <p class="text-[10px] text-surface-400 flex items-center gap-2">
            <span class="inline-flex items-center gap-1">${ICONS.pin} ${esc(event.location)}</span>
            <span>•</span>
            <span>${esc(event.source)}</span>
          </p>
        </div>
        <div class="flex-shrink-0">
          ${severityBadge(event.severity)}
        </div>
      </div>
    `).join('');
  }

  // Render Routes
  function renderRoutes(routes) {
    const container = document.getElementById('routes-feed');
    if (!routes.length) {
      container.innerHTML = `
        <div class="text-center py-6">
          <div class="w-10 h-10 mx-auto mb-2 rounded-lg bg-surface-100 text-surface-400 flex items-center justify-center">${ICONS.route}</div>
          <p class="text-surface-400 text-xs">No routes generated yet</p>
          <button onclick="location.href='/routes'" class="mt-3 px-4 py-2 bg-primary-100 text-primary-700 text-xs font-semibold rounded-lg hover:bg-primary-200 transition-colors">
            Generate Route
          </button>
        </div>
      `;
      return;
    }

    container.innerHTML = routes.slice(0, 4).map((route, index) => {
      const colors = route.risk_score >= 70 ? 
        ['bg-gradient-to-r from-rose-400 to-red-500', 'bg-rose-50 text-rose-700'] :
        route.risk_score >= 40 ? 
        ['bg-gradient-to-r from-amber-400 to-orange-500', 'bg-amber-50 text-amber-700'] :
        ['bg-gradient-to-r from-emerald-400 to-teal-500', 'bg-emerald-50 text-emerald-700'];
      
      return `
        <div class="glass-card p-4 rounded-xl flex items-center justify-between hover:shadow-md transition-all cursor-pointer group" style="animation: slideIn 0.3s ease ${index * 0.05}s both;" onclick="location.href='/routes'">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-lg ${colors[1]} flex items-center justify-center">
              ${ICONS.route}
            </div>
            <div>
              <p class="text-sm font-semibold text-surface-800">
                <span class="text-surface-500">${esc(route.start_location)}</span>
                <span class="mx-1 text-surface-300">→</span>
                <span>${esc(route.end_location)}</span>
              </p>
              <p class="text-[10px] text-surface-400">Risk Score: ${route.risk_score}/100</p>
            </div>
          </div>
          <div class="flex items-center gap-3">
            <div class="h-2 w-16 bg-surface-200 rounded-full overflow-hidden">
              <div class="h-full ${colors[0]} rounded-full" style="width: ${Math.min(100, route.risk_score)}%"></div>
            </div>
            <span class="text-xs font-bold ${colors[1].split(' ')[1]}">${route.risk_score}</span>
            <svg class="w-4 h-4 text-surface-400 group-hover:text-primary-500 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
            </svg>
          </div>
        </div>
      `;
    }).join('');
  }

  // Update KPI cards with animation
  function updateKPIs(kpis) {
    const setKPI = (id, value, suffix = '') => {
      const el = document.getElementById(id);
      if (el && !isNaN(value)) {
        animateNumber(el, value, suffix);
        
        // Update progress bar for risk
        if (id === 'kpi-avg-risk') {
          const bar = document.getElementById(id + '-bar');
          if (bar) {
            setTimeout(() => {
              bar.style.width = Math.min(100, value) + '%';
            }, 100);
          }
        }
      }
    };
    
    setKPI('kpi-avg-risk', Math.round(kpis.average_risk));
    setKPI('kpi-high-risk', kpis.high_risk_areas);
    setKPI('kpi-alerts', kpis.active_alerts);
    setKPI('kpi-events', kpis.total_events);

    // Update mini cards
    const safeRoutes = document.getElementById('safe-routes-count');
    const institutions = document.getElementById('institutions-count');
    if (safeRoutes) safeRoutes.textContent = kpis.total_routes || 0;
    if (institutions) institutions.textContent = kpis.monitored_areas || 0;
  }

  // Load dashboard data
  async function load() {
    try {
      const data = await SR.get('/api/dashboard/summary');
      
      // Update KPIs
      updateKPIs(data.kpis);
      
      // Update last update time
      const lastUpdate = document.getElementById('last-update');
      if (lastUpdate) {
        lastUpdate.textContent = 'Updated just now';
      }
      
      // Render sections
      renderRiskAreas(data.risk_areas);
      renderAlerts(data.active_alerts);
      renderEvents(data.recent_events);
      renderRoutes(data.suggested_routes);
      
      // Update sidebar user stats
      const sidebarRisk = document.getElementById('user-risk-score');
      const sidebarAlerts = document.getElementById('user-alerts');
      if (sidebarRisk) sidebarRisk.textContent = Math.round(data.kpis.average_risk);
      if (sidebarAlerts) sidebarAlerts.textContent = data.kpis.active_alerts;
      
    } catch (e) {
      console.error('Dashboard load error:', e);
      if (window.showFlash) {
        showFlash('Failed to load dashboard data', 'error');
      }
    }
  }

  // Initialize on DOM ready
  document.addEventListener('DOMContentLoaded', () => {
    load();
    
    // Refresh every 30 seconds
    setInterval(load, 30000);
    
    // Realtime updates via WebSocket/SSE
    if (window.Realtime) {
      Realtime.connect((alerts) => {
        renderAlerts(alerts);
        load(); // Full refresh
      });
    }
  });

  document.addEventListener('sr:user-ready', (ev) => {
    if (ev.detail.role !== 'PUBLIC_USER') {
      const title = document.getElementById('dash-title');
      const subtitle = document.getElementById('dash-subtitle');
      if (title) title.textContent = 'Community Overview';
      if (subtitle) subtitle.textContent = 'Real-time risk monitoring and route intelligence';
    }
  });
  
  // Add CSS animations
  const style = document.createElement('style');
  style.textContent = `
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(10px); }
      to { opacity: 1; transform: translateY(0); }
    }
    @keyframes slideIn {
      from { opacity: 0; transform: translateX(-10px); }
      to { opacity: 1; transform: translateX(0); }
    }
  `;
  document.head.appendChild(style);
})();
