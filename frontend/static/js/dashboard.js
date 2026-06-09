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

  // Render Risk Areas with progress bars
  function renderRiskAreas(areas) {
    const container = document.getElementById('risk-areas-container');
    if (!areas.length) {
      container.innerHTML = `
        <div class="text-center py-8">
          <div class="w-16 h-16 mx-auto mb-3 rounded-full bg-surface-100 flex items-center justify-center text-2xl">📊</div>
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
      
      const icon = area.risk_level === 'CRITICAL' ? '🚨' : area.risk_level === 'HIGH' ? '🔥' : area.risk_level === 'MEDIUM' ? '⚠️' : '✅';
      const scoreColor = area.risk_level === 'CRITICAL' ? 'text-red-700' : area.risk_level === 'HIGH' ? 'text-rose-600' : area.risk_level === 'MEDIUM' ? 'text-amber-600' : 'text-emerald-600';
      
      return `
        <div class="group" style="animation: fadeIn 0.3s ease ${index * 0.05}s both;">
          <div class="flex items-center justify-between mb-2">
            <div class="flex items-center gap-3">
              <div class="w-8 h-8 rounded-lg ${colors[1]} flex items-center justify-center text-sm">
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
          <div class="w-12 h-12 mx-auto mb-2 rounded-full bg-emerald-50 flex items-center justify-center text-xl">🎉</div>
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

    // Update alert badges
    const navBadge = document.getElementById('nav-alert-badge');
    const sidebarBadge = document.getElementById('alerts-badge');
    const sidebarIndicator = document.getElementById('alerts-indicator');
    const criticalCount = alerts.filter(a => a.severity === 'CRITICAL' || a.severity === 'HIGH').length;
    
    if (navBadge) {
      if (criticalCount > 0) {
        navBadge.textContent = Math.min(criticalCount, 9);
        navBadge.classList.remove('hidden');
      } else {
        navBadge.classList.add('hidden');
      }
    }
    
    if (sidebarBadge) {
      sidebarBadge.textContent = alerts.length;
      sidebarBadge.classList.toggle('hidden', alerts.length === 0);
    }
    
    if (sidebarIndicator) {
      sidebarIndicator.classList.toggle('hidden', criticalCount === 0);
    }
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
        <div class="w-10 h-10 rounded-lg ${event.severity >= 4 ? 'bg-rose-50 text-rose-600' : event.severity === 3 ? 'bg-amber-50 text-amber-600' : 'bg-surface-100 text-surface-500'} flex items-center justify-center text-lg flex-shrink-0">
          ${event.severity >= 4 ? '🚨' : event.severity === 3 ? '⚠️' : '📋'}
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-sm font-semibold text-surface-800 truncate group-hover:text-primary-600 transition-colors">${esc(event.title)}</p>
          <p class="text-[10px] text-surface-400 flex items-center gap-2">
            <span>📍 ${esc(event.location)}</span>
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
          <div class="w-12 h-12 mx-auto mb-2 rounded-full bg-surface-100 flex items-center justify-center text-xl">🗺️</div>
          <p class="text-surface-400 text-xs">No routes generated yet</p>
          <button onclick="location.href='/routes'" class="mt-3 px-4 py-2 bg-primary-100 text-primary-700 text-xs font-medium rounded-lg hover:bg-primary-200 transition-colors">
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
            <div class="w-10 h-10 rounded-lg ${colors[1]} flex items-center justify-center text-lg">
              🛣️
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
