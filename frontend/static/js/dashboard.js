/* Dashboard — wired to premium dashboard.html layout */
(function () {
  "use strict";

  let riskTrendChart = null;
  let categoryChart = null;
  let chartsReady = false;

  const CATEGORY_COLORS = {
    Theft: "#ef4444",
    Assault: "#f59e0b",
    Accident: "#3b82f6",
    Vandalism: "#8b5cf6",
    Other: "#94a3b8",
  };

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  }

  function timeAgo(iso) {
    if (!iso) return "—";
    const diff = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "Just now";
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    return new Date(iso).toLocaleDateString([], { month: "short", day: "numeric" });
  }

  function riskBarColor(level) {
    if (level === "CRITICAL") return "#dc2626";
    if (level === "HIGH") return "#ef4444";
    if (level === "MEDIUM") return "#f59e0b";
    return "#10b981";
  }

  function riskIconWrap(level) {
    const styles = {
      CRITICAL: "background:rgba(239,68,68,0.1);color:#dc2626",
      HIGH: "background:rgba(239,68,68,0.08);color:#ef4444",
      MEDIUM: "background:rgba(245,158,11,0.1);color:#f59e0b",
      LOW: "background:rgba(16,185,129,0.1);color:#10b981",
    };
    const icons = {
      CRITICAL: "fa-triangle-exclamation",
      HIGH: "fa-triangle-exclamation",
      MEDIUM: "fa-circle-exclamation",
      LOW: "fa-shield-halved",
    };
    return `<div class="risk-item-icon" style="${styles[level] || styles.LOW}"><i class="fas ${icons[level] || icons.LOW}"></i></div>`;
  }

  function riskScoreColor(level) {
    if (level === "CRITICAL") return "#dc2626";
    if (level === "HIGH") return "#ef4444";
    if (level === "MEDIUM") return "#d97706";
    return "#059669";
  }

  function eventDotStyle(sev) {
    if (sev >= 4) return "background:#ef4444;color:#ef4444";
    if (sev === 3) return "background:#f59e0b;color:#f59e0b";
    return "background:#94a3b8;color:#94a3b8";
  }

  function eventBadge(sev) {
    if (sev >= 4) return '<span class="event-badge" style="background:rgba(239,68,68,0.15);color:#f87171">Critical</span>';
    if (sev === 3) return '<span class="event-badge" style="background:rgba(245,158,11,0.15);color:#fbbf24">Moderate</span>';
    if (sev === 2) return '<span class="event-badge" style="background:rgba(148,163,184,0.12);color:#94a3b8">Minor</span>';
    return '<span class="event-badge" style="background:rgba(16,185,129,0.15);color:#34d399">Low</span>';
  }

  function routeRiskBadge(score) {
    if (score >= 70) return '<span class="route-risk" style="background:rgba(239,68,68,0.15);color:#f87171">High</span>';
    if (score >= 40) return '<span class="route-risk" style="background:rgba(245,158,11,0.15);color:#fbbf24">Medium</span>';
    return '<span class="route-risk" style="background:rgba(16,185,129,0.15);color:#34d399">Safe</span>';
  }

  function animateNumber(element, target, suffix, duration) {
    if (!element || isNaN(target)) return;
    suffix = suffix || "";
    duration = duration || 800;
    const start = 0;
    const startTime = performance.now();

    function update(now) {
      const progress = Math.min((now - startTime) / duration, 1);
      const ease = 1 - Math.pow(1 - progress, 3);
      element.textContent = Math.floor(start + (target - start) * ease) + suffix;
      if (progress < 1) requestAnimationFrame(update);
      else element.textContent = target + suffix;
    }
    requestAnimationFrame(update);
  }

  function setBarWidth(id, pct, delay) {
    const bar = document.getElementById(id);
    if (!bar) return;
    setTimeout(() => { bar.style.width = Math.min(100, Math.max(0, pct)) + "%"; }, delay || 200);
  }

  function updateTrend(cardIndex, type, label) {
    const cards = document.querySelectorAll(".kpi-card .kpi-trend");
    const el = cards[cardIndex];
    if (!el) return;
    el.className = "kpi-trend " + (type === "up" ? "trend-up" : type === "down" ? "trend-down" : "trend-flat");
    const icon = type === "up" ? "fa-arrow-trend-up" : type === "down" ? "fa-arrow-trend-down" : "fa-minus";
    el.innerHTML = `<i class="fas ${icon} text-[8px]"></i> ${esc(label)}`;
  }

  function heatmapColor(count, maxCount) {
    if (!maxCount) return "rgba(16,185,129,0.12)";
    const ratio = count / maxCount;
    if (ratio <= 0.15) return "rgba(16,185,129,0.15)";
    if (ratio <= 0.35) return "rgba(16,185,129,0.35)";
    if (ratio <= 0.55) return "rgba(245,158,11,0.35)";
    if (ratio <= 0.75) return "rgba(245,158,11,0.6)";
    return "rgba(239,68,68,0.5)";
  }

  function animateSafetyRing(score) {
    const ring = document.getElementById("safety-ring-fill");
    const valEl = document.getElementById("safety-score-val");
    if (!ring || !valEl) return;

    const circumference = 2 * Math.PI * 60;
    const offset = circumference - (score / 100) * circumference;
    let color = "#10b981";
    if (score < 40) color = "#ef4444";
    else if (score < 60) color = "#f59e0b";
    else if (score < 80) color = "#818cf8";

    ring.style.stroke = color;
    setTimeout(() => { ring.style.strokeDashoffset = offset; }, 300);

    const duration = 1200;
    const startTime = performance.now();
    function update(now) {
      const progress = Math.min((now - startTime) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      valEl.textContent = Math.round(eased * score);
      if (progress < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
  }

  function ensureCharts() {
    if (chartsReady || typeof Chart === "undefined") return;

    const trendCtx = document.getElementById("riskTrendChart");
    if (trendCtx) {
      riskTrendChart = new Chart(trendCtx, {
        type: "line",
        data: {
          labels: [],
          datasets: [{
            label: "Risk Score",
            data: [],
            borderColor: "#818cf8",
            backgroundColor: "rgba(99,102,241,0.12)",
            borderWidth: 3,
            fill: true,
            tension: 0.4,
            pointBackgroundColor: "#818cf8",
            pointBorderColor: "#1e293b",
            pointBorderWidth: 2,
            pointRadius: 5,
            pointHoverRadius: 7,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              backgroundColor: "#0f172a",
              titleFont: { size: 12, weight: "bold" },
              bodyFont: { size: 12 },
              padding: 12,
              cornerRadius: 8,
              displayColors: false,
            },
          },
          scales: {
            x: { grid: { display: false }, ticks: { font: { size: 10 }, color: "#94a3b8" } },
            y: {
              grid: { color: "rgba(148,163,184,0.12)", drawBorder: false },
              ticks: { font: { size: 10 }, color: "#94a3b8" },
              min: 0,
              max: 100,
            },
          },
          animation: { duration: 900, easing: "easeOutQuart" },
        },
      });
    }

    const catCtx = document.getElementById("categoryChart");
    if (catCtx) {
      categoryChart = new Chart(catCtx, {
        type: "doughnut",
        data: {
          labels: [],
          datasets: [{
            data: [],
            backgroundColor: [],
            borderWidth: 0,
            hoverOffset: 8,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutout: "65%",
          plugins: {
            legend: {
              position: "right",
              labels: {
                boxWidth: 10,
                padding: 15,
                font: { size: 11, weight: "600" },
                color: "#94a3b8",
                usePointStyle: true,
                pointStyle: "circle",
              },
            },
            tooltip: {
              backgroundColor: "#0f172a",
              bodyFont: { size: 12 },
              padding: 12,
              cornerRadius: 8,
            },
          },
          animation: { animateRotate: true, duration: 900, easing: "easeOutQuart" },
        },
      });
    }

    chartsReady = true;
  }

  function updateRiskTrendChart(trend) {
    ensureCharts();
    if (!riskTrendChart || !trend) return;
    riskTrendChart.data.labels = trend.map((d) => d.label);
    riskTrendChart.data.datasets[0].data = trend.map((d) => d.score);
    riskTrendChart.update();
  }

  function updateCategoryChart(categories) {
    ensureCharts();
    if (!categoryChart || !categories) return;
    const entries = Object.entries(categories).filter(([, count]) => count > 0);
    if (!entries.length) {
      categoryChart.data.labels = ["No incidents"];
      categoryChart.data.datasets[0].data = [1];
      categoryChart.data.datasets[0].backgroundColor = ["#334155"];
    } else {
      categoryChart.data.labels = entries.map(([label]) => label);
      categoryChart.data.datasets[0].data = entries.map(([, count]) => count);
      categoryChart.data.datasets[0].backgroundColor = entries.map(([label]) => CATEGORY_COLORS[label] || "#94a3b8");
    }
    categoryChart.update();
  }

  function renderHeatmap(cells) {
    const container = document.getElementById("incident-heatmap");
    if (!container) return;
    if (!cells || !cells.length) {
      container.innerHTML = `<p class="text-xs text-center py-4" style="color:#94a3b8">No incident activity yet</p>`;
      return;
    }
    const maxCount = Math.max(...cells.map((c) => c.count), 1);
    container.innerHTML = cells.map((cell) => `
      <div class="heatmap-cell a-fade-in"
           style="background:${heatmapColor(cell.count, maxCount)}"
           data-day="${esc(cell.label)} · ${cell.count} incident${cell.count === 1 ? "" : "s"}"
           title="${esc(cell.label)}: ${cell.count}"></div>`).join("");
  }

  function renderProgressRings(analytics) {
    const container = document.getElementById("progress-rings");
    if (!container || !analytics) return;

    const rings = [
      { label: "Covered", value: analytics.coverage_pct || 0, color: "#10b981" },
      { label: "Incidents", value: analytics.incident_load_pct || 0, color: "#f59e0b" },
      { label: "Safe Routes", value: analytics.route_safety_pct || 0, color: "#818cf8" },
    ];

    const circumference = 2 * Math.PI * 28;
    container.innerHTML = rings.map((ring, i) => `
      <div class="ring-item a-fade-in" style="animation-delay:${i * 0.08}s">
        <svg width="70" height="70" viewBox="0 0 70 70" style="transform:rotate(-90deg)">
          <circle cx="35" cy="35" r="28" fill="none" stroke="rgba(148,163,184,0.15)" stroke-width="6"/>
          <circle class="progress-ring-fill" cx="35" cy="35" r="28" fill="none" stroke="${ring.color}" stroke-width="6"
            stroke-linecap="round" stroke-dasharray="${circumference}" stroke-dashoffset="${circumference}"
            data-target="${ring.value}" style="transition:stroke-dashoffset 1.2s cubic-bezier(0.22,1,0.36,1) ${i * 0.15}s"/>
        </svg>
        <div class="ring-item-label">${ring.label}</div>
        <div style="font-size:0.75rem;font-weight:800;color:${ring.color};margin-top:2px">${ring.value}%</div>
      </div>`).join("");

    setTimeout(() => {
      container.querySelectorAll(".progress-ring-fill").forEach((circle) => {
        const val = parseFloat(circle.dataset.target) || 0;
        circle.style.strokeDashoffset = circumference - (val / 100) * circumference;
      });
    }, 400);
  }

  function updateSafetyPanel(kpis, trend) {
    const score = kpis.safety_score != null ? kpis.safety_score : Math.max(0, Math.min(100, 100 - Math.round(kpis.average_risk || 0)));
    animateSafetyRing(score);

    const updated = document.getElementById("safety-score-updated");
    if (updated) updated.textContent = "Updated just now";

    const trendEl = document.getElementById("safety-score-trend");
    if (trendEl && trend && trend.length >= 2) {
      const delta = trend[trend.length - 1].score - trend[trend.length - 2].score;
      if (delta > 0) {
        trendEl.className = "text-rose-400 font-bold flex items-center gap-1";
        trendEl.innerHTML = `<i class="fas fa-arrow-trend-up text-[10px]"></i> Risk +${delta}`;
      } else if (delta < 0) {
        trendEl.className = "text-emerald-400 font-bold flex items-center gap-1";
        trendEl.innerHTML = `<i class="fas fa-arrow-trend-down text-[10px]"></i> Risk ${delta}`;
      } else {
        trendEl.className = "text-surface-400 font-bold flex items-center gap-1";
        trendEl.textContent = "Stable";
      }
    }
  }

  function renderRiskAreas(areas) {
    const container = document.getElementById("risk-areas-container");
    if (!container) return;

    if (!areas.length) {
      container.innerHTML = `
        <div class="text-center py-10">
          <div class="w-12 h-12 mx-auto mb-3 rounded-xl flex items-center justify-center" style="background:rgba(148,163,184,0.12);color:#94a3b8">
            <i class="fas fa-map-location-dot"></i>
          </div>
          <p class="text-sm" style="color:#94a3b8">No risk areas monitored yet</p>
        </div>`;
      return;
    }

    const sorted = [...areas].sort((a, b) => b.risk_score - a.risk_score);

    container.innerHTML = sorted.slice(0, 6).map((area, i) => {
      const width = Math.min(100, Math.max(5, area.risk_score));
      const lat = area.latitude != null ? area.latitude : "";
      const lng = area.longitude != null ? area.longitude : "";
      const href = lat !== "" && lng !== "" ? `/map?lat=${lat}&lng=${lng}` : "/map";

      return `
        <div class="risk-item a-fade-in" style="animation-delay:${i * 0.05}s"
             data-lat="${lat}" data-lng="${lng}" data-name="${esc(area.area_name)}"
             onclick="location.href='${href}'">
          ${riskIconWrap(area.risk_level)}
          <div class="risk-item-info">
            <p class="risk-item-name">${esc(area.area_name)}</p>
            <p class="risk-item-meta">${esc(area.risk_level)} risk · updated ${timeAgo(area.updated_at)}</p>
            <div class="risk-item-bar-wrap">
              <div class="risk-item-bar" style="width:0%;background:${riskBarColor(area.risk_level)}" data-width="${width}%"></div>
            </div>
          </div>
          <span class="risk-item-score" style="color:${riskScoreColor(area.risk_level)}">${Math.round(area.risk_score)}</span>
          <i class="fas fa-chevron-right risk-item-arrow"></i>
        </div>`;
    }).join("");

    setTimeout(() => {
      container.querySelectorAll("[data-width]").forEach((bar) => {
        bar.style.width = bar.dataset.width;
      });
    }, 120);
  }

  function renderEvents(events) {
    const container = document.getElementById("events-feed");
    if (!container) return;

    if (!events.length) {
      container.innerHTML = `<p class="text-sm text-center py-6" style="color:#94a3b8">No recent events</p>`;
      return;
    }

    container.innerHTML = events.slice(0, 8).map((event, i) => `
      <div class="event-item a-fade-in" style="animation-delay:${i * 0.05}s"
           onclick="location.href='/events'">
        <span class="event-dot" style="${eventDotStyle(event.severity)}"></span>
        <div class="event-info">
          <p class="event-title">${esc(event.title)}</p>
          <p class="event-meta"><i class="fas fa-location-dot text-[9px]"></i> ${esc(event.location)} · ${esc(event.source)}</p>
        </div>
        ${eventBadge(event.severity)}
      </div>`).join("");
  }

  function renderRoutes(routes) {
    const container = document.getElementById("routes-feed");
    if (!container) return;

    if (!routes.length) {
      container.innerHTML = `
        <div class="text-center py-8">
          <div class="w-10 h-10 mx-auto mb-2 rounded-lg flex items-center justify-center" style="background:rgba(148,163,184,0.12);color:#94a3b8">
            <i class="fas fa-route"></i>
          </div>
          <p class="text-xs mb-3" style="color:#94a3b8">No routes generated yet</p>
          <a href="/routes" class="dash-hero-cta" style="padding:0.5rem 1rem;font-size:0.75rem">
            <i class="fas fa-route"></i> Plan a Route
          </a>
        </div>`;
      return;
    }

    container.innerHTML = routes.slice(0, 5).map((route, i) => `
      <div class="route-card a-fade-in" style="animation-delay:${i * 0.05}s"
           onclick="location.href='/routes'">
        <span class="route-num">${i + 1}</span>
        <div class="route-info">
          <p class="route-path">
            ${esc(route.start_location)}
            <i class="fas fa-arrow-right"></i>
            ${esc(route.end_location)}
          </p>
          <p class="route-sub">Risk score ${Math.round(route.risk_score)}/100 · ${timeAgo(route.created_at)}</p>
        </div>
        ${routeRiskBadge(route.risk_score)}
      </div>`).join("");
  }

  function updateKPIs(kpis) {
    const avg = Math.round(kpis.average_risk || 0);
    animateNumber(document.getElementById("kpi-avg-risk"), avg);
    animateNumber(document.getElementById("kpi-high-risk"), kpis.high_risk_areas || 0);
    animateNumber(document.getElementById("kpi-high-severity"), kpis.high_severity_events || 0);
    animateNumber(document.getElementById("kpi-events"), kpis.total_events || 0);

    setBarWidth("kpi-avg-risk-bar", avg, 300);
    const monitored = Math.max(kpis.monitored_areas || 1, 1);
    setBarWidth("kpi-high-risk-bar", ((kpis.high_risk_areas || 0) / monitored) * 100, 450);
    setBarWidth("kpi-high-severity-bar", Math.min(100, (kpis.high_severity_events || 0) * 15), 600);
    setBarWidth("kpi-events-bar", Math.min(100, (kpis.total_events || 0) * 4), 750);

    updateTrend(0, avg >= 50 ? "up" : "down", avg >= 50 ? "Elevated" : "Improving");
    updateTrend(1, (kpis.high_risk_areas || 0) > 0 ? "up" : "flat", String(kpis.high_risk_areas || 0));
    updateTrend(2, (kpis.high_severity_events || 0) > 0 ? "up" : "flat", String(kpis.high_severity_events || 0));
    updateTrend(3, (kpis.total_events || 0) > 0 ? "up" : "flat", String(kpis.total_events || 0));

    const safeRoutes = document.getElementById("safe-routes-count");
    const monitoredAreas = document.getElementById("monitored-areas-count");
    const community = document.getElementById("community-count");
    const health = document.getElementById("health-count");

    if (safeRoutes) animateNumber(safeRoutes, kpis.safe_routes != null ? kpis.safe_routes : kpis.total_routes || 0);
    if (monitoredAreas) animateNumber(monitoredAreas, kpis.monitored_areas || 0);
    if (community) animateNumber(community, kpis.total_events || 0);
    if (health) {
      const score = kpis.safety_score != null ? kpis.safety_score : Math.max(0, Math.min(100, 100 - avg));
      animateNumber(health, score, "%");
    }
  }

  function applyDashboardData(data) {
    updateKPIs(data.kpis);
    renderRiskAreas(data.risk_areas || []);
    renderEvents(data.recent_events || []);
    renderRoutes(data.suggested_routes || []);

    const analytics = data.analytics || {};
    updateRiskTrendChart(analytics.risk_trend);
    updateCategoryChart(analytics.categories);
    renderHeatmap(analytics.heatmap);
    renderProgressRings(analytics);
    updateSafetyPanel(data.kpis, analytics.risk_trend);

    document.dispatchEvent(new CustomEvent("sr:events-updated", { detail: data.recent_events || [] }));

    const sidebarRisk = document.getElementById("user-risk-score");
    const sidebarEvents = document.getElementById("user-events");
    if (sidebarRisk) sidebarRisk.textContent = Math.round(data.kpis.average_risk || 0);
    if (sidebarEvents) sidebarEvents.textContent = data.kpis.total_events || 0;
  }

  async function load() {
    try {
      const data = await SR.get("/api/dashboard/summary");
      applyDashboardData(data);
    } catch (e) {
      console.error("Dashboard load error:", e);
      if (window.flash) flash("Failed to load dashboard data", "error");
      ["risk-areas-container", "events-feed", "routes-feed"].forEach((id) => {
        const el = document.getElementById(id);
        if (el) {
          el.innerHTML = `<div class="text-center py-8"><p class="text-sm" style="color:#94a3b8">${esc(e.message || "Unable to load")}</p><button type="button" class="btn-secondary mt-3" onclick="location.reload()">Retry</button></div>`;
        }
      });
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    ensureCharts();
    load();
    setInterval(load, 30000);
    if (window.Realtime) {
      Realtime.connect(() => load());
    }
  });

  document.addEventListener("sr:user-ready", (ev) => {
    const user = ev.detail || {};
    const greet = document.querySelector(".dash-hero-greet");
    const name = user.name || user.full_name;
    if (greet && name) greet.textContent = `Welcome back, ${name.split(" ")[0]}`;

    const title = document.getElementById("dash-title");
    const subtitle = document.getElementById("dash-subtitle");
    if (user.role && user.role !== "PUBLIC_USER") {
      if (title) title.innerHTML = "Community<br>Overview";
      if (subtitle) subtitle.textContent = "Real-time risk monitoring and route intelligence across your network.";
    }
  });
})();
