(function () {

  "use strict";

  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));



  let map = null;

  let overlayLayers = [];



  function levelBadge(level) {

    const cls = { LOW: "badge-low", MEDIUM: "badge-medium", HIGH: "badge-high", CRITICAL: "badge-critical" };

    return `<span class="badge ${cls[level] || "badge-gray"}">${level}</span>`;

  }



  function renderTable(areas) {

    const body = document.getElementById("map-areas-body");

    if (!areas.length) {

      body.innerHTML = '<tr><td colspan="4" class="text-surface-400 py-6 text-center">No areas.</td></tr>';

      return;

    }

    body.innerHTML = areas.map((a) => `

      <tr>

        <td class="font-semibold text-surface-800">${esc(a.area_name)}</td>

        <td>${a.risk_score}/100</td>

        <td>${levelBadge(a.risk_level)}</td>

        <td class="text-surface-500">${a.updated_at ? new Date(a.updated_at).toLocaleString() : "—"}</td>

      </tr>`).join("");

  }



  function renderMap(data) {

    const center = data.map_center || { lat: -29.8587, lng: 31.0218, zoom: 11 };

    if (!map) {

      map = SRMap.createBaseMap("safety-map", center, center.zoom);

    }

    SRMap.clearLayers(overlayLayers);

    overlayLayers = [

      SRMap.addRiskZones(map, data.risk_areas),

      SRMap.addIncidents(map, data.incidents),

      SRMap.addCityMarkers(map, data.cities),

    ];

    const incidents = (data.incidents || []).filter((i) => i.latitude != null && i.longitude != null);
    if (incidents.length > 1 && typeof L !== "undefined") {
      const bounds = L.latLngBounds(incidents.map((i) => [i.latitude, i.longitude]));
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 11 });
    }



    const status = document.getElementById("map-status");

    const nAreas = (data.risk_areas || []).length;

    const nInc = (data.incidents || []).length;

    const nAlerts = (data.alerts || []).length;

    status.textContent = `${nAreas} risk zone(s) · ${nInc} incident(s) · ${nAlerts} alert(s) — refreshes every 30s`;

  }



  async function load() {

    try {

      const data = await SR.get("/api/ai/map-data");

      renderMap(data);

      renderTable(data.risk_areas || []);

    } catch (e) {

      flash(e.message, "error");

      document.getElementById("map-status").textContent = "Failed to load map data.";

    }

  }



  document.addEventListener("sr:user-ready", () => {

    load();

    setInterval(load, 30000);

  });

})();

