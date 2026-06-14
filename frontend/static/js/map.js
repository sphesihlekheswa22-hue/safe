(function () {
  "use strict";

  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  let map = null;
  let overlayLayers = [];
  let userMarkerLayer = null;
  let lastData = null;
  let allAreas = [];
  let filteredAreas = [];
  let currentFilter = "all";
  let currentPage = 1;
  let centerMode = "default";
  let userLocation = null;
  const PAGE_SIZE = 10;

  window.map = null;

  const geoPromise = getUserLocation();

  function getUserLocation() {
    return new Promise((resolve) => {
      if (!navigator.geolocation) {
        resolve(null);
        return;
      }
      navigator.geolocation.getCurrentPosition(
        (pos) => resolve({
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
          accuracy: pos.coords.accuracy,
        }),
        () => resolve(null),
        { enableHighAccuracy: true, timeout: 15000, maximumAge: 45000 }
      );
    });
  }

  function showUserMarker(lat, lng) {
    if (!map || typeof L === "undefined") return;
    if (userMarkerLayer) {
      userMarkerLayer.remove();
      userMarkerLayer = null;
    }
    userMarkerLayer = L.layerGroup();
    L.circle([lat, lng], {
      radius: Math.min(Math.max(80, (userLocation?.accuracy || 120)), 400),
      color: "#2563eb",
      fillColor: "#2563eb",
      fillOpacity: 0.12,
      weight: 2,
    }).addTo(userMarkerLayer);
    L.marker([lat, lng], {
      icon: L.divIcon({
        className: "",
        html: '<div style="width:16px;height:16px;background:#2563eb;border:3px solid #fff;border-radius:50%;box-shadow:0 2px 12px rgba(37,99,235,0.45);"></div>',
        iconSize: [16, 16],
        iconAnchor: [8, 8],
      }),
    })
      .bindPopup("<b>You are here</b>")
      .addTo(userMarkerLayer);
    userMarkerLayer.addTo(map);
  }

  async function resolveMapCenter(data) {
    const params = new URLSearchParams(location.search);
    const qLat = parseFloat(params.get("lat"));
    const qLng = parseFloat(params.get("lng"));
    if (!Number.isNaN(qLat) && !Number.isNaN(qLng)) {
      centerMode = "query";
      return { lat: qLat, lng: qLng, zoom: 14 };
    }

    userLocation = await geoPromise;
    if (userLocation) {
      centerMode = "user";
      return { lat: userLocation.lat, lng: userLocation.lng, zoom: 14 };
    }

    centerMode = "default";
    const fallback = data.map_center || { lat: -25.7461, lng: 28.1881, zoom: 11 };
    return { lat: fallback.lat, lng: fallback.lng, zoom: fallback.zoom || 11 };
  }

  function levelBadge(level) {
    const cls = { LOW: "badge-low", MEDIUM: "badge-medium", HIGH: "badge-high", CRITICAL: "badge-critical" };
    return `<span class="area-badge ${cls[level] || "badge-low"}">${level}</span>`;
  }

  function scoreColor(level) {
    return {
      LOW: "text-emerald-400",
      MEDIUM: "text-amber-400",
      HIGH: "text-rose-400",
      CRITICAL: "text-red-400",
    }[level] || "text-surface-400";
  }

  function trendCell(score) {
    const up = score >= 60;
    const cls = up ? "trend-up" : "trend-down";
    const icon = up ? "fa-arrow-trend-up" : "fa-arrow-trend-down";
    const label = up ? "Rising" : "Stable";
    return `<span class="inline-flex items-center gap-1 text-xs font-semibold ${cls}"><i class="fas ${icon} trend-arrow"></i> ${label}</span>`;
  }

  function updateStats(data) {
    const areas = data.risk_areas || [];
    const incidents = data.incidents || [];
    const counts = { LOW: 0, MEDIUM: 0, HIGH: 0, CRITICAL: 0 };
    areas.forEach((a) => { if (counts[a.risk_level] != null) counts[a.risk_level]++; });

    const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    set("stat-safe", counts.LOW);
    set("stat-med", counts.MEDIUM);
    set("stat-high", counts.HIGH + counts.CRITICAL);
    set("stat-total", incidents.filter((e) => Number(e.severity) >= 4).length);

    const updated = document.getElementById("last-updated");
    if (updated) {
      updated.textContent = "Updated just now";
      updated.dataset.timestamp = String(Date.now());
    }
  }

  function renderTablePage() {
    const body = document.getElementById("map-areas-body");
    const total = filteredAreas.length;
    const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
    if (currentPage > totalPages) currentPage = totalPages;

    const start = (currentPage - 1) * PAGE_SIZE;
    const pageItems = filteredAreas.slice(start, start + PAGE_SIZE);

    if (!total) {
      body.innerHTML = '<tr><td colspan="5" class="text-surface-400 py-8 text-center">No areas match your search.</td></tr>';
    } else {
      body.innerHTML = pageItems.map((a) => `
        <tr>
          <td class="font-semibold text-surface-300 pl-6">${esc(a.area_name)}</td>
          <td class="text-center">
            <span class="score-ring ${scoreColor(a.risk_level)}">${a.risk_score}</span>
          </td>
          <td class="text-center">${levelBadge(a.risk_level)}</td>
          <td class="text-center">${trendCell(a.risk_score)}</td>
          <td class="text-surface-400 text-right pr-6">${a.updated_at ? new Date(a.updated_at).toLocaleString() : "—"}</td>
        </tr>`).join("");
    }

    const info = document.getElementById("table-info");
    const pageNum = document.getElementById("page-num");
    if (info) {
      const end = Math.min(start + PAGE_SIZE, total);
      info.textContent = total ? `Showing ${start + 1}–${end} of ${total} areas` : "Showing 0 of 0 areas";
    }
    if (pageNum) pageNum.textContent = String(currentPage);
  }

  function applyAreaSearch(query) {
    const q = (query || "").trim().toLowerCase();
    filteredAreas = q
      ? allAreas.filter((a) => (a.area_name || "").toLowerCase().includes(q))
      : [...allAreas];
    currentPage = 1;
    renderTablePage();
  }

  function filteredMapData(data) {
    let areas = data.risk_areas || [];
    let incidents = data.incidents || [];

    if (currentFilter === "incident") {
      areas = [];
    } else if (currentFilter !== "all") {
      const level = currentFilter.toUpperCase();
      areas = areas.filter((a) => a.risk_level === level);
      incidents = [];
    }

    return { ...data, risk_areas: areas, incidents };
  }

  function renderOverlays(data) {
    if (!map) return;
    SRMap.clearLayers(overlayLayers);

    const view = filteredMapData(data);
    overlayLayers = [
      SRMap.addRiskZones(map, view.risk_areas),
      SRMap.addIncidents(map, view.incidents),
      SRMap.addCityMarkers(map, data.cities),
    ];

    const incidents = (view.incidents || []).filter((i) => i.latitude != null && i.longitude != null);
    if (centerMode === "default") {
      if (incidents.length > 1 && typeof L !== "undefined") {
        const bounds = L.latLngBounds(incidents.map((i) => [i.latitude, i.longitude]));
        map.fitBounds(bounds, { padding: [40, 40], maxZoom: 11 });
      } else if (currentFilter === "all" && (data.risk_areas || []).length) {
        const withCoords = (data.risk_areas || []).filter((a) => a.latitude != null && a.longitude != null);
        if (withCoords.length > 1) {
          const bounds = L.latLngBounds(withCoords.map((a) => [a.latitude, a.longitude]));
          map.fitBounds(bounds, { padding: [40, 40], maxZoom: 11 });
        }
      }
    }
  }

  function focusFromQuery() {
    if (!map || centerMode !== "query") return;
    const params = new URLSearchParams(location.search);
    const lat = parseFloat(params.get("lat"));
    const lng = parseFloat(params.get("lng"));
    if (!Number.isNaN(lat) && !Number.isNaN(lng)) {
      map.setView([lat, lng], 14);
    }
  }

  function renderMap(data, center) {
    const mapCenter = center || data.map_center || { lat: -25.7461, lng: 28.1881, zoom: 11 };
    if (!map) {
      map = SRMap.createBaseMap("safety-map", mapCenter, mapCenter.zoom || 11, { dark: true });
      window.map = map;
    } else if (centerMode === "user" || centerMode === "query") {
      map.setView([mapCenter.lat, mapCenter.lng], mapCenter.zoom || 14);
    }

    if (centerMode === "user" && userLocation) {
      showUserMarker(userLocation.lat, userLocation.lng);
    }

    renderOverlays(data);

    const status = document.getElementById("map-status");
    const nAreas = (data.risk_areas || []).length;
    const nInc = (data.incidents || []).length;
    const nHigh = (data.incidents || []).filter((e) => Number(e.severity) >= 4).length;
    if (status) {
      const dotColor = centerMode === "user" ? "#3b82f6" : "#10b981";
      const locateNote = centerMode === "user" ? "Centered on your location · " : "";
      status.innerHTML = `<span class="status-dot" style="background:${dotColor}"></span> ${locateNote}${nAreas} risk zone(s) · ${nInc} incident(s) · ${nHigh} high-severity — refreshes every 30s`;
    }

    updateStats(data);
    focusFromQuery();
  }

  async function load() {
    try {
      const data = await SR.get("/api/ai/map-data");
      const center = await resolveMapCenter(data);
      lastData = data;
      renderMap(data, center);
      allAreas = data.risk_areas || [];
      const search = document.getElementById("area-search");
      applyAreaSearch(search ? search.value : "");
      return data;
    } catch (e) {
      flash(e.message, "error");
      const status = document.getElementById("map-status");
      if (status) status.textContent = "Failed to load map data.";
      throw e;
    }
  }

  window.loadMapData = load;
  window.centerOnMyLocation = async () => {
    const loc = await getUserLocation();
    if (!loc) {
      if (window.flash) flash("Could not get your location. Check browser permissions.", "error");
      return false;
    }
    userLocation = loc;
    centerMode = "user";
    if (map) {
      map.setView([loc.lat, loc.lng], 14);
      showUserMarker(loc.lat, loc.lng);
      const status = document.getElementById("map-status");
      if (status && lastData) {
        const nAreas = (lastData.risk_areas || []).length;
        const nInc = (lastData.incidents || []).length;
        const nHigh = (lastData.incidents || []).filter((e) => Number(e.severity) >= 4).length;
        status.innerHTML = `<span class="status-dot" style="background:#3b82f6"></span> Centered on your location · ${nAreas} risk zone(s) · ${nInc} incident(s) · ${nHigh} high-severity — refreshes every 30s`;
      }
    }
    return true;
  };
  window.filterMapMarkers = (filter) => {
    currentFilter = filter;
    if (lastData) renderOverlays(lastData);
  };
  window.filterTableAreas = applyAreaSearch;
  window.changePage = (delta) => {
    const totalPages = Math.max(1, Math.ceil(filteredAreas.length / PAGE_SIZE));
    currentPage = Math.min(totalPages, Math.max(1, currentPage + delta));
    renderTablePage();
  };
  window.exportAreaData = () => {
    let csv = "Area,Score,Level,Last Updated\n";
    filteredAreas.forEach((a) => {
      csv += `"${(a.area_name || "").replace(/"/g, '""')}",${a.risk_score},"${a.risk_level}","${a.updated_at || ""}"\n`;
    });
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "safety-areas-" + new Date().toISOString().slice(0, 10) + ".csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  let mapPageInited = false;

  function initMapPage() {
    if (mapPageInited) return;
    mapPageInited = true;
    load();
    setInterval(load, 30000);
  }

  document.addEventListener("sr:user-ready", initMapPage);
  if (window.SR_USER) initMapPage();
})();
