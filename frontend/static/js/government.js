(function () {

  "use strict";



  let govMap = null;

  let mapLayers = [];



  function esc(s) {

    return String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  }



  function badgeCls(level) {

    const m = { LOW: "badge-low", MEDIUM: "badge-medium", HIGH: "badge-high", CRITICAL: "badge-critical" };

    return m[level] || "badge-gray";

  }



  function renderMap(data) {

    const center = data.map_center || { lat: -25.7461, lng: 28.1881, zoom: 10 };

    if (!govMap) {

      govMap = SRMap.createBaseMap("gov-map", center, center.zoom);

    }

    SRMap.clearLayers(mapLayers);

    mapLayers = [

      SRMap.addRiskZones(govMap, data.risk_areas),

      SRMap.addIncidents(govMap, data.incidents),

      SRMap.addCityMarkers(govMap, data.cities),

    ];

    const incidents = (data.incidents || []).filter((i) => i.latitude != null);

    if (incidents.length > 1 && typeof L !== "undefined") {

      govMap.fitBounds(

        L.latLngBounds(incidents.map((i) => [i.latitude, i.longitude])),

        { padding: [40, 40], maxZoom: 11 }

      );

    }

  }



  function renderDashboard(d) {

    document.getElementById("gov-portal").classList.remove("hidden");

    const risk = d.city_risk;

    document.getElementById("gov-title").textContent = d.city || "City Safety Command";

    document.getElementById("gov-subtitle").textContent =

      (d.department ? d.department.name + " · " : "") + "City-wide public safety overview";



    const badge = document.getElementById("gov-city-badge");

    badge.textContent = `${risk.city_level} · ${risk.average_risk}/100`;

    badge.className = "badge " + badgeCls(risk.city_level) + " text-sm px-4 py-2";



    document.getElementById("kpi-city-risk").textContent = risk.average_risk + "/100";

    document.getElementById("kpi-safe").textContent = risk.safe_zones;

    document.getElementById("kpi-medium").textContent = risk.medium_zones;

    document.getElementById("kpi-high").textContent = risk.high_risk_zones;

    document.getElementById("kpi-alerts").textContent = (d.critical_incidents || d.critical_alerts || []).length;



    const patterns = d.unrest_patterns || {};

    const trend = patterns.escalation_trend || [];

    const max = Math.max(1, ...trend.map((t) => t.unrest_incidents + t.all_incidents));

    document.getElementById("gov-escalation-trend").innerHTML = trend.map((t) => {

      const h = Math.max(6, ((t.unrest_incidents + t.all_incidents) / max) * 100);

      const color = t.unrest_incidents > 0 ? "#dc2626" : "#94a3b8";

      return `<div class="flex-1 flex flex-col items-center" title="${t.date}: ${t.unrest_incidents} unrest / ${t.all_incidents} total">

        <div class="w-full h-14 flex items-end"><div class="w-full rounded-t" style="height:${h}%;background:${color}"></div></div>

        <span class="text-[8px] text-surface-400">${t.date.slice(5)}</span>

      </div>`;

    }).join("");



    const hotspots = patterns.protest_clusters || [];

    document.getElementById("gov-hotspots").innerHTML = hotspots.length

      ? hotspots.map((h) => `

        <div class="hotspot-card glass-card rounded-xl p-3">

          <div class="flex justify-between"><span class="font-semibold text-sm">${esc(h.location)}</span>

          <span class="badge badge-high text-[10px]">${h.incident_count} incidents</span></div>

          <p class="text-xs text-surface-500 mt-1">Max severity ${h.max_severity}/5 · latest: ${esc(h.latest.title)}</p>

        </div>`).join("")

      : '<p class="text-surface-400 text-sm">No protest clusters detected.</p>';



    document.getElementById("gov-decisions").innerHTML = (d.response_decisions || []).map((x) => `

      <div class="gov-decision urgency-${x.urgency} glass-card rounded-xl p-4">

        <p class="font-semibold text-sm text-surface-800">${esc(x.title)}</p>

        <p class="text-xs text-surface-500 mt-1">${esc(x.detail)}</p>

      </div>`).join("");



    const critical = d.critical_incidents || d.critical_alerts || [];
    document.getElementById("gov-alerts").innerHTML = critical.length
      ? critical.map((e) => `
        <div class="glass-card rounded-xl p-3 text-sm border-l-4 ${Number(e.severity) >= 4 ? 'border-l-rose-600' : 'border-l-amber-500'}">
          <span class="badge ${Number(e.severity) >= 4 ? 'badge-critical' : 'badge-high'} text-[10px]">${esc(e.severity)}/5</span>
          <strong>${esc(e.title)}</strong> — ${esc(e.location || '')}
        </div>`).join("")
      : '<p class="text-surface-400 text-sm">No critical incidents.</p>';



    document.getElementById("gov-incidents").innerHTML = (d.live_incidents || []).length

      ? d.live_incidents.map((e) => `

        <div class="flex justify-between py-1 border-b border-surface-100">

          <span><strong>${esc(e.title)}</strong><br><span class="text-surface-400">${esc(e.location)}</span></span>

          <span class="shrink-0 badge ${e.severity >= 4 ? 'badge-high' : 'badge-medium'}">sev ${e.severity}</span>

        </div>`).join("")

      : '<p class="text-surface-400">No live incidents.</p>';

  }



  async function load() {

    try {

      const dash = await SR.get("/api/government/dashboard");

      renderDashboard(dash);

      const mapData = await SR.get("/api/government/map-data");

      renderMap(mapData);

    } catch (e) {

      if (e.status === 403) {

        document.getElementById("gov-denied").classList.remove("hidden");

      } else {

        flash(e.message, "error");

      }

    }

  }



  document.getElementById("gov-warning-form").addEventListener("submit", async (e) => {

    e.preventDefault();

    const fd = new FormData(e.target);

    try {

      await SR.post("/api/government/warnings", {

        message: fd.get("message"),

        severity: fd.get("severity"),

        target_role: fd.get("target_role"),

      });

      flash("Public safety warning issued.", "success");

      e.target.reset();

      load();

    } catch (err) {

      flash(err.message, "error");

    }

  });



  document.getElementById("btn-gov-report").addEventListener("click", async () => {

    try {

      const token = localStorage.getItem("sr_token");

      const res = await fetch("/api/government/reports/download", {

        headers: token ? { Authorization: "Bearer " + token } : {},

      });

      if (!res.ok) throw new Error("Download failed.");

      const blob = await res.blob();

      const url = URL.createObjectURL(blob);

      const a = document.createElement("a");

      a.href = url;

      a.download = "city-safety-report.json";

      a.click();

      URL.revokeObjectURL(url);

      flash("City report downloaded.", "success");

    } catch (err) {

      flash(err.message, "error");

    }

  });



  document.addEventListener("sr:user-ready", (ev) => {

    if (!["GOVERNMENT_AUTHORITY", "SYSTEM_ADMIN"].includes(ev.detail.role)) {

      document.getElementById("gov-denied").classList.remove("hidden");

      return;

    }

    load();

    setInterval(load, 60000);

  });

})();

