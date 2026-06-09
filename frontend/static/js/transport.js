(function () {

  "use strict";



  let transportMap = null;

  let mapLayers = [];

  let lastSuggestion = null;



  function esc(s) {

    return String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  }



  function corridorCls(level) {

    return level === "DANGEROUS" ? "corridor-danger" : level === "WARNING" ? "corridor-warning" : "corridor-safe";

  }



  function badgeCls(level) {

    return level === "DANGEROUS" ? "badge-high" : level === "WARNING" ? "badge-medium" : "badge-low";

  }



  function fleetCls(status) {

    return status === "HOLD" ? "fleet-hold" : status === "CAUTION" ? "fleet-caution" : "fleet-clear";

  }



  function renderMap(data, corridors) {

    const center = data.map_center || { lat: -29.8587, lng: 31.0218, zoom: 11 };

    if (!transportMap) {

      transportMap = SRMap.createBaseMap("transport-map", center, center.zoom);

    }

    SRMap.clearLayers(mapLayers);

    mapLayers = [SRMap.addIncidents(transportMap, data.incidents || [])];



    (corridors || []).forEach((c) => {

      if (!c.geojson) return;

      const color = c.risk_level === "DANGEROUS" ? "#dc2626" : c.risk_level === "WARNING" ? "#d97706" : "#059669";

      const layer = SRMap.drawRoute(transportMap, c.geojson, { color, weight: 4 });

      mapLayers.push(layer);

    });



    if (data.operator && data.operator.latitude != null) {

      L.circle([data.operator.latitude, data.operator.longitude], {

        radius: (data.operator.radius_km || 25) * 1000,

        color: "#0d9488", fillColor: "#14b8a6", fillOpacity: 0.06, weight: 2, dashArray: "8 4",

      }).addTo(transportMap);

    }

  }



  function renderDashboard(d) {

    document.getElementById("transport-portal").classList.remove("hidden");

    document.getElementById("transport-title").textContent = d.operator.name;



    const cs = d.corridor_safety;

    document.getElementById("kpi-safe").textContent = cs.safe.length;

    document.getElementById("kpi-warning").textContent = cs.warning.length;

    document.getElementById("kpi-danger").textContent = cs.dangerous.length;

    document.getElementById("kpi-alerts").textContent = (d.transport_alerts || []).length;

    document.getElementById("kpi-ratio").textContent = (d.performance.safe_ratio_pct || 0) + "%";



    document.getElementById("corridor-list").innerHTML = (cs.all || []).map((c) => `

      <div class="glass-card rounded-xl p-3 ${corridorCls(c.risk_level)}">

        <div class="flex justify-between items-start gap-2">

          <span class="text-sm font-medium text-surface-800">${esc(c.corridor)}</span>

          <span class="badge ${badgeCls(c.risk_level)} shrink-0">${c.risk_score}</span>

        </div>

        <p class="text-xs text-surface-500 mt-1">${esc(c.explanation || "")}</p>

      </div>`).join("");



    document.getElementById("transport-alerts").innerHTML = (d.transport_alerts || []).length

      ? d.transport_alerts.map((a) => `<div class="glass-card rounded-xl p-3 text-sm border-l-4 border-l-amber-500"><span class="badge badge-medium text-[10px]">${esc(a.severity)}</span> ${esc(a.message)}</div>`).join("")

      : '<p class="text-surface-400 text-sm">No transport alerts.</p>';



    document.getElementById("incident-list").innerHTML = (d.live_incidents || []).length

      ? d.live_incidents.map((e) => `<div class="flex justify-between py-1 border-b border-surface-100"><span>${esc(e.title)}</span><span class="text-rose-600 font-medium shrink-0">sev ${e.severity}</span></div>`).join("")

      : '<p class="text-surface-400">No incidents in operating area.</p>';



    document.getElementById("fleet-list").innerHTML = (d.fleet || []).map((v) => `

      <div class="flex items-center justify-between p-3 rounded-xl ${fleetCls(v.status)}">

        <div>

          <p class="font-semibold text-sm">${esc(v.id)} · ${esc(v.type)}</p>

          <p class="text-xs opacity-80">${esc(v.driver)} — ${esc(v.corridor)}</p>

        </div>

        <span class="text-xs font-bold px-2 py-1 rounded-full bg-white/60">${esc(v.status)}</span>

      </div>`).join("");



    const p = d.performance || {};

    document.getElementById("perf-total").textContent = p.total_routes || 0;

    document.getElementById("perf-safe").textContent = p.safe_routes || 0;

    document.getElementById("perf-warning").textContent = p.warning_routes || 0;

    document.getElementById("perf-danger").textContent = p.dangerous_routes || 0;



    const trend = p.weekly_trend || [];

    const max = Math.max(1, ...trend.map((t) => t.safe + t.warning + t.dangerous));

    document.getElementById("perf-trend").innerHTML = trend.map((t) => {

      const total = t.safe + t.warning + t.dangerous;

      const h = Math.max(8, (total / max) * 100);

      return `<div class="flex-1 flex flex-col items-center" title="${t.date}: ${total} routes">

        <div class="w-full bg-surface-100 rounded-t h-12 flex items-end overflow-hidden">

          <div class="w-full bg-teal-500 rounded-t" style="height:${h}%"></div>

        </div>

        <span class="text-[9px] text-surface-400">${t.date.slice(5)}</span>

      </div>`;

    }).join("");



    const routes = d.saved_routes || [];

    const body = document.getElementById("saved-routes-body");

    body.innerHTML = routes.length

      ? routes.map((r) => `

        <tr>

          <td>${esc(r.start_location)}</td>

          <td>${esc(r.end_location)}</td>

          <td>${r.risk_score}</td>

          <td><span class="badge ${badgeCls(r.risk_level)}">${esc(r.risk_level)}</span></td>

          <td class="text-right"><button class="btn-danger text-xs px-2 py-1 rounded" data-del-route="${r.id}">Remove</button></td>

        </tr>`).join("")

      : '<tr><td colspan="5" class="text-surface-400 text-center py-4">No saved routes yet.</td></tr>';



    body.querySelectorAll("[data-del-route]").forEach((btn) => {

      btn.addEventListener("click", async () => {

        try {

          await SR.del("/api/transport/routes/" + btn.dataset.delRoute);

          flash("Route removed.", "success");

          load();

        } catch (err) {

          flash(err.message, "error");

        }

      });

    });

  }



  async function load() {

    try {

      const dash = await SR.get("/api/transport/dashboard");

      renderDashboard(dash);

      const mapData = await SR.get("/api/transport/map-data");

      renderMap(mapData, dash.corridor_safety.all);

    } catch (e) {

      if (e.status === 403 || (e.message && e.message.includes("transport"))) {

        document.getElementById("transport-denied").classList.remove("hidden");

      } else {

        flash(e.message, "error");

      }

    }

  }



  document.getElementById("transport-route-form").addEventListener("submit", async (e) => {

    e.preventDefault();

    const fd = new FormData(e.target);

    try {

      const result = await SR.post("/api/transport/suggest-route", {

        start_location: fd.get("start_location"),

        end_location: fd.get("end_location"),

      });

      lastSuggestion = result;

      const r = result.route;

      document.getElementById("route-suggestion").classList.remove("hidden");

      document.getElementById("btn-save-route").classList.remove("hidden");

      document.getElementById("route-suggestion-text").innerHTML =

        `<strong>${esc(r.start_location)} → ${esc(r.end_location)}</strong><br>` +

        `<span class="badge ${badgeCls(r.risk_level)}">${esc(r.risk_level)} · ${r.risk_score}</span> ${esc(r.explanation || "")}`;



      const altEl = document.getElementById("route-alternatives");

      const alts = result.alternatives || [];

      altEl.innerHTML = alts.length

        ? alts.map((a) => `<div class="text-xs p-2 bg-surface-50 rounded-lg">${esc(a.label || "Alt")}: <span class="badge ${badgeCls(a.risk_level)}">${a.risk_score}</span></div>`).join("")

        : "";



      if (r.geojson && transportMap) {

        SRMap.clearLayers(mapLayers.filter((l) => l._isPreview));

        const preview = SRMap.drawRoute(transportMap, r.geojson, { color: "#0d9488", weight: 6 });

        preview._isPreview = true;

        mapLayers.push(preview);

      }

    } catch (err) {

      flash(err.message, "error");

    }

  });



  document.getElementById("btn-save-route").addEventListener("click", async () => {

    const fd = new FormData(document.getElementById("transport-route-form"));

    try {

      await SR.post("/api/transport/routes", {

        start_location: fd.get("start_location"),

        end_location: fd.get("end_location"),

      });

      flash("Transport route saved.", "success");

      load();

    } catch (err) {

      flash(err.message, "error");

    }

  });



  document.addEventListener("sr:user-ready", (ev) => {

    if (!["TRANSPORT_OPERATOR", "SYSTEM_ADMIN"].includes(ev.detail.role)) {

      document.getElementById("transport-denied").classList.remove("hidden");

      return;

    }

    load();

    setInterval(load, 90000);

  });

})();

