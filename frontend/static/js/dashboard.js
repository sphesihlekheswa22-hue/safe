/* Dashboard — wired to premium dashboard.html layout */
(function () {
  "use strict";

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

  function alertClass(sev) {
    if (sev === "CRITICAL" || sev === "HIGH") return "alert-high";
    if (sev === "MEDIUM") return "alert-medium";
    return "alert-low";
  }

  function alertIcon(sev) {
    if (sev === "CRITICAL" || sev === "HIGH") return "fa-bell";
    if (sev === "MEDIUM") return "fa-circle-exclamation";
    return "fa-circle-check";
  }

  function eventDotStyle(sev) {
    if (sev >= 4) return "background:#ef4444;color:#ef4444";
    if (sev === 3) return "background:#f59e0b;color:#f59e0b";
    return "background:#94a3b8;color:#94a3b8";
  }

  function eventBadge(sev) {
    if (sev >= 4) return '<span class="event-badge" style="background:rgba(239,68,68,0.1);color:#dc2626">Critical</span>';
    if (sev === 3) return '<span class="event-badge" style="background:rgba(245,158,11,0.1);color:#d97706">Moderate</span>';
    if (sev === 2) return '<span class="event-badge" style="background:rgba(148,163,184,0.12);color:#64748b">Minor</span>';
    return '<span class="event-badge" style="background:rgba(16,185,129,0.1);color:#059669">Low</span>';
  }

  function routeRiskBadge(score) {
    if (score >= 70) return '<span class="route-risk" style="background:rgba(239,68,68,0.1);color:#dc2626">High</span>';
    if (score >= 40) return '<span class="route-risk" style="background:rgba(245,158,11,0.1);color:#d97706">Medium</span>';
    return '<span class="route-risk" style="background:rgba(16,185,129,0.1);color:#059669">Safe</span>';
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
    const institutions = document.getElementById("institutions-count");
    const community = document.getElementById("community-count");
    const health = document.getElementById("health-count");

    if (safeRoutes) animateNumber(safeRoutes, kpis.total_routes || 0);
    if (institutions) animateNumber(institutions, kpis.monitored_areas || 0);
    if (community) animateNumber(community, kpis.total_events || 0);
    if (health) {
      const score = Math.max(0, Math.min(100, 100 - avg));
      animateNumber(health, score, "%");
    }
  }

  async function load() {
    try {
      const data = await SR.get("/api/dashboard/summary");
      updateKPIs(data.kpis);
      renderRiskAreas(data.risk_areas || []);
      renderEvents(data.recent_events || []);
      renderRoutes(data.suggested_routes || []);

      document.dispatchEvent(new CustomEvent("sr:events-updated", { detail: data.recent_events || [] }));

      const sidebarRisk = document.getElementById("user-risk-score");
      const sidebarEvents = document.getElementById("user-events");
      if (sidebarRisk) sidebarRisk.textContent = Math.round(data.kpis.average_risk || 0);
      if (sidebarEvents) sidebarEvents.textContent = data.kpis.total_events || 0;
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
    load();
    setInterval(load, 30000);
    if (window.Realtime) {
      Realtime.connect(() => load());
    }
  });

  document.addEventListener("sr:user-ready", (ev) => {
    const user = ev.detail || {};
    const greet = document.querySelector(".dash-hero-greet");
    if (greet && user.full_name) greet.textContent = `Welcome back, ${user.full_name.split(" ")[0]}`;

    const title = document.getElementById("dash-title");
    const subtitle = document.getElementById("dash-subtitle");
    if (user.role && user.role !== "PUBLIC_USER") {
      if (title) title.innerHTML = "Community<br>Overview";
      if (subtitle) subtitle.textContent = "Real-time risk monitoring and route intelligence across your network.";
    }
  });
})();
