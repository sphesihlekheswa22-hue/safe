(function () {

  "use strict";



  let instMap = null;

  let mapLayers = [];



  function esc(s) {

    return String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  }



  function riskBadgeCls(level) {

    const m = { LOW: "badge-low", MEDIUM: "badge-medium", HIGH: "badge-high", CRITICAL: "badge-critical" };

    return m[level] || "badge-gray";

  }



  function renderTrend(trend) {

    const el = document.getElementById("inst-trend");

    if (!trend || !trend.length) {

      el.innerHTML = '<p class="text-surface-400 text-xs">No trend data yet.</p>';

      return;

    }

    const max = Math.max(1, ...trend.map((t) => t.incidents));

    el.innerHTML = trend.map((t) => {

      const pct = Math.round((t.incidents / max) * 100);

      return `<div class="flex-1 flex flex-col items-center gap-1" title="${t.date}: ${t.incidents}">

        <div class="w-full bg-surface-100 rounded-full h-12 flex items-end overflow-hidden">

          <div class="trend-bar w-full" style="height:${Math.max(8, pct)}%"></div>

        </div>

        <span class="text-[9px] text-surface-400">${t.date.slice(5)}</span>

      </div>`;

    }).join("");

  }



  function renderMap(data) {

    const inst = data.institution;

    const center = data.map_center || { lat: inst.latitude, lng: inst.longitude, zoom: 13 };

    if (!instMap) {

      instMap = SRMap.createBaseMap("inst-map", center, center.zoom);

    }

    SRMap.clearLayers(mapLayers);

    mapLayers = [

      SRMap.addRiskZones(instMap, data.risk_areas),

      SRMap.addIncidents(instMap, data.incidents),

    ];

    if (inst.latitude != null && inst.longitude != null) {

      const radiusM = (inst.radius_km || 8) * 1000;

      const campus = L.circle([inst.latitude, inst.longitude], {

        radius: radiusM,

        color: "#4f46e5",

        fillColor: "#6366f1",

        fillOpacity: 0.08,

        weight: 2,

        dashArray: "6 4",

      }).bindPopup(`<b>${esc(inst.name)}</b><br>Monitor radius: ${inst.radius_km || 8} km`);

      campus.addTo(instMap);

      L.marker([inst.latitude, inst.longitude], {

        icon: L.divIcon({

          className: "",

          html: '<div style="background:#4f46e5;color:#fff;font-size:11px;font-weight:700;padding:4px 8px;border-radius:6px;white-space:nowrap;box-shadow:0 2px 8px rgba(0,0,0,.3)">🏫 Campus</div>',

          iconAnchor: [30, 20],

        }),

      }).addTo(instMap);

      mapLayers.push(campus);

      instMap.setView([inst.latitude, inst.longitude], center.zoom || 13);

    }

  }



  function renderDashboard(d) {

    document.getElementById("inst-portal").classList.remove("hidden");

    const inst = d.institution;

    const risk = d.campus_risk;



    document.getElementById("inst-title").textContent = inst.name;

    document.getElementById("inst-subtitle").textContent = `${inst.location || "South Africa"} · ${inst.type}`;



    const badge = document.getElementById("inst-risk-badge");

    badge.textContent = `${risk.risk_level} · ${risk.risk_score}/100`;

    badge.className = "badge " + riskBadgeCls(risk.risk_level) + " text-sm px-4 py-2";



    document.getElementById("kpi-risk").textContent = `${risk.risk_score}/100`;

    document.getElementById("kpi-incidents").textContent = risk.nearby_incidents;

    document.getElementById("kpi-alerts").textContent = (d.institution_alerts || []).length;

    document.getElementById("kpi-people").textContent = `${d.staff_count || inst.staff_count} / ${d.student_count || inst.student_count}`;



    document.getElementById("pf-name").value = inst.name;

    document.getElementById("pf-type").value = inst.type || "EDUCATION";

    document.getElementById("pf-location").value = inst.location || "";

    document.getElementById("pf-staff").value = inst.staff_count || 0;

    document.getElementById("pf-students").value = inst.student_count || 0;

    document.getElementById("pf-radius").value = inst.radius_km || 8;



    renderTrend(d.safety_trend);



    const alertsEl = document.getElementById("inst-alerts");

    const alerts = d.institution_alerts || [];

    alertsEl.innerHTML = alerts.length

      ? alerts.map((a) => `<div class="glass-card rounded-xl p-3 text-sm border-l-4 border-l-amber-500"><span class="badge badge-medium text-[10px]">${esc(a.severity)}</span> ${esc(a.message)}</div>`).join("")

      : '<p class="text-surface-400 text-sm">No institution-specific alerts.</p>';



    const incEl = document.getElementById("inst-incidents");

    const incs = d.nearby_incidents || [];

    incEl.innerHTML = incs.length

      ? incs.map((e) => `<div class="flex justify-between gap-2 py-1 border-b border-surface-100"><span>${esc(e.title)}</span><span class="text-surface-400 shrink-0">sev ${e.severity}</span></div>`).join("")

      : '<p class="text-surface-400">No nearby incidents.</p>';



    const decEl = document.getElementById("inst-decisions");

    decEl.innerHTML = (d.operational_decisions || []).map((x) => `

      <div class="decision-card urgency-${x.urgency} glass-card rounded-xl p-4">

        <p class="font-semibold text-surface-800 text-sm">${esc(x.title)}</p>

        <p class="text-xs text-surface-500 mt-1">${esc(x.detail)}</p>

      </div>`).join("");



    const commuteEl = document.getElementById("inst-commute");

    const routes = d.commute_routes || [];

    commuteEl.innerHTML = routes.length

      ? routes.map((r) => `

        <div class="glass-card rounded-xl p-4 border-l-4 ${r.risk_score >= 70 ? "border-l-rose-500" : r.risk_score >= 40 ? "border-l-amber-500" : "border-l-emerald-500"}">

          <p class="font-medium text-sm">${esc(r.from)} → ${esc(r.to)}</p>

          <p class="text-xs text-surface-500 mt-1">${esc(r.explanation || "")}</p>

          <span class="badge ${r.risk_score >= 70 ? "badge-high" : r.risk_score >= 40 ? "badge-medium" : "badge-low"} mt-2">${esc(r.risk_level || "")} · ${r.risk_score}</span>

        </div>`).join("")

      : '<p class="text-surface-400 text-sm col-span-full">No commute routes calculated yet.</p>';



    document.getElementById("inst-safe-zones").innerHTML = (d.safe_zones || []).length

      ? d.safe_zones.map((z) => `<div class="flex justify-between"><span>${esc(z.area_name)}</span><span class="badge badge-low">${z.risk_score}</span></div>`).join("")

      : '<p class="text-surface-400">No low-risk zones flagged nearby.</p>';



    document.getElementById("inst-danger-zones").innerHTML = (d.danger_zones || []).length

      ? d.danger_zones.map((z) => `<div class="flex justify-between"><span>${esc(z.area_name)}</span><span class="badge badge-high">${z.risk_score}</span></div>`).join("")

      : '<p class="text-surface-400">No high-risk zones near campus.</p>';

  }



  async function load() {

    try {

      const dash = await SR.get("/api/institution/dashboard");

      renderDashboard(dash);

      const mapData = await SR.get("/api/institution/map-data");

      renderMap(mapData);

    } catch (e) {

      if (e.message && (e.message.includes("institution") || e.message.includes("403"))) {

        document.getElementById("inst-no-access").classList.remove("hidden");

      } else {

        flash(e.message, "error");

      }

    }

  }



  document.getElementById("inst-profile-form").addEventListener("submit", async (e) => {

    e.preventDefault();

    const fd = new FormData(e.target);

    try {

      await SR.put("/api/institution/profile", {

        type: fd.get("type"),

        location: fd.get("location"),

        staff_count: parseInt(fd.get("staff_count"), 10) || 0,

        student_count: parseInt(fd.get("student_count"), 10) || 0,

        radius_km: parseFloat(fd.get("radius_km")) || 8,

      });

      flash("Institution profile saved.", "success");

      load();

    } catch (err) {

      flash(err.message, "error");

    }

  });



  document.getElementById("btn-download-report").addEventListener("click", async () => {

    try {

      const token = localStorage.getItem("sr_token");

      const res = await fetch("/api/institution/reports/download", {

        headers: token ? { Authorization: "Bearer " + token } : {},

      });

      if (!res.ok) throw new Error("Download failed.");

      const blob = await res.blob();

      const url = URL.createObjectURL(blob);

      const a = document.createElement("a");

      a.href = url;

      a.download = "institution-safety-report.json";

      a.click();

      URL.revokeObjectURL(url);

      flash("Report downloaded.", "success");

    } catch (err) {

      flash(err.message, "error");

    }

  });



  document.addEventListener("sr:user-ready", (ev) => {

    if (!["INSTITUTION_ADMIN", "SYSTEM_ADMIN"].includes(ev.detail.role)) {

      document.getElementById("inst-no-access").classList.remove("hidden");

      return;

    }

    load();

    setInterval(load, 60000);

  });

})();

