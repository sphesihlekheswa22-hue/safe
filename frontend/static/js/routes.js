(function () {
  "use strict";

  const DELETE_ROLES = ["SYSTEM_ADMIN"];
  const PAGE_SIZE = 8;

  let canDelete = false;
  let routeMap = null;
  let routeLayers = [];
  let mapOverlayLayers = [];
  let savedRoutes = [];
  let filteredRoutes = [];
  let currentPage = 1;
  let lastRouteEndpoints = null;

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  }

  function levelLabel(level, risk) {
    if (level) return level;
    if (risk >= 70) return "DANGEROUS";
    if (risk >= 40) return "WARNING";
    return "SAFE";
  }

  function riskBadgeClass(risk, level) {
    const lvl = (level || levelLabel(null, risk)).toUpperCase();
    if (lvl === "CRITICAL" || risk >= 85) return "risk-critical";
    if (lvl === "DANGEROUS" || lvl === "HIGH" || risk >= 70) return "risk-high";
    if (lvl === "WARNING" || lvl === "MEDIUM" || risk >= 40) return "risk-medium";
    return "risk-low";
  }

  function riskPillClass(risk) {
    if (risk >= 70) return "risk-pill-high";
    if (risk >= 40) return "risk-pill-medium";
    return "risk-pill-low";
  }

  function formatDistance(m) {
    if (m == null || !Number.isFinite(m)) return "—";
    return m >= 1000 ? (m / 1000).toFixed(1) + " km" : Math.round(m) + " m";
  }

  function formatDuration(s) {
    if (s == null || !Number.isFinite(s)) return "—";
    const mins = Math.round(s / 60);
    if (mins < 60) return mins + " min";
    return Math.floor(mins / 60) + "h " + (mins % 60) + "m";
  }

  function routeMetrics(route) {
    const props = route?.geojson?.properties || {};
    return {
      distance_m: route.distance_m ?? props.distance_m,
      duration_s: route.duration_s ?? props.duration_s,
    };
  }

  function setRouteStats(route) {
    const m = routeMetrics(route);
    const dist = document.getElementById("stat-distance");
    const dur = document.getElementById("stat-duration");
    const score = document.getElementById("stat-score");
    if (dist) dist.textContent = formatDistance(m.distance_m);
    if (dur) dur.textContent = formatDuration(m.duration_s);
    if (score) score.textContent = route.risk_score != null ? Math.round(route.risk_score) : "—";
  }

  function setRiskBadge(el, risk, level) {
    if (!el) return;
    const lbl = levelLabel(level, risk);
    el.className = "risk-badge " + riskBadgeClass(risk, lbl);
    el.innerHTML = `<i class="fas fa-circle text-[6px]"></i> ${lbl} · ${Math.round(risk)}`;
  }

  function refreshMapSize() {
    if (!routeMap) return;
    requestAnimationFrame(() => {
      routeMap.invalidateSize({ animate: false });
      setTimeout(() => routeMap.invalidateSize({ animate: false }), 320);
      setTimeout(() => routeMap.invalidateSize({ animate: false }), 600);
    });
  }

  function showResultPanel() {
    const panel = document.getElementById("route-result");
    const placeholder = document.getElementById("route-map-placeholder");
    if (!panel) return;
    if (placeholder) placeholder.classList.add("hidden");
    panel.classList.remove("hidden");
    requestAnimationFrame(() => {
      panel.classList.add("visible");
      refreshMapSize();
    });
  }

  function parseCoord(v) {
    const n = parseFloat(v);
    return Number.isFinite(n) ? n : null;
  }

  function clearCoords(prefix) {
    document.getElementById(prefix + "-lat").value = "";
    document.getElementById(prefix + "-lng").value = "";
  }

  function setCoords(prefix, lat, lng) {
    document.getElementById(prefix + "-lat").value = lat;
    document.getElementById(prefix + "-lng").value = lng;
  }

  function getPayload() {
    const startLat = parseCoord(document.getElementById("start-lat").value);
    const startLng = parseCoord(document.getElementById("start-lng").value);
    const endLat = parseCoord(document.getElementById("end-lat").value);
    const endLng = parseCoord(document.getElementById("end-lng").value);
    const payload = {
      start_location: document.getElementById("start-location").value.trim(),
      end_location: document.getElementById("end-location").value.trim(),
    };
    if (startLat != null && startLng != null) {
      payload.start_lat = startLat;
      payload.start_lng = startLng;
    }
    if (endLat != null && endLng != null) {
      payload.end_lat = endLat;
      payload.end_lng = endLng;
    }
    return payload;
  }

  async function resolveField(prefix) {
    const input = document.getElementById(prefix + "-location");
    const lat = parseCoord(document.getElementById(prefix + "-lat").value);
    const lng = parseCoord(document.getElementById(prefix + "-lng").value);
    if (lat != null && lng != null) return true;

    const q = input.value.trim();
    if (q.length < 2) return false;

    const near = typeof resolveNearCoords === "function" ? resolveNearCoords({}) : null;
    const { results } = await fetchLocationSuggestions(q, 5, near);
    if (!results.length) return false;

    const r = results[0];
    input.value = r.name;
    setCoords(prefix, r.lat, r.lng);
    input.dataset.selectedLabel = r.name;
    return true;
  }

  async function resolvePayloadCoords() {
    const startOk = await resolveField("start");
    const endOk = await resolveField("end");
    if (!startOk) throw new Error("Could not find the origin. Select an address from the suggestions.");
    if (!endOk) throw new Error("Could not find the destination. Select an address from the suggestions.");
    return getPayload();
  }

  async function loadMapOverlay() {
    try {
      const data = await SR.get("/api/ai/map-data");
      if (!routeMap) return;
      SRMap.clearLayers(mapOverlayLayers);
      mapOverlayLayers = [
        SRMap.addRiskZones(routeMap, data.risk_areas),
        SRMap.addIncidents(routeMap, data.incidents),
      ];
    } catch (_) {}
  }

  function ensureMap() {
    if (routeMap) return routeMap;
    routeMap = SRMap.createBaseMap("route-leaflet-map", { lat: -25.7461, lng: 28.1881 }, 11);
    loadMapOverlay();
    return routeMap;
  }

  function showRoute(geojson, risk, riskLevel, isAlt, endpoints) {
    ensureMap();
    SRMap.clearLayers(routeLayers);
    routeLayers = [];
    const color = SRMap.routeColor(levelLabel(riskLevel, risk), isAlt);
    const ep = endpoints || lastRouteEndpoints;
    routeLayers.push(SRMap.drawRoute(routeMap, geojson, {
      color,
      weight: isAlt ? 4 : 6,
      start: ep && ep.start_lat != null ? { lat: ep.start_lat, lng: ep.start_lng, label: ep.start_location } : null,
      end: ep && ep.end_lat != null ? { lat: ep.end_lat, lng: ep.end_lng, label: ep.end_location } : null,
    }));
    refreshMapSize();
  }

  function formatWhen(iso) {
    if (!iso) return "—";
    const d = new Date(iso);
    const diff = Date.now() - d.getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "Just now";
    if (mins < 60) return mins + "m ago";
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return hrs + "h ago";
    return d.toLocaleDateString();
  }

  function truncate(str, len) {
    const s = str || "";
    return s.length > len ? s.slice(0, len) + "…" : s;
  }

  function renderRoutesTable() {
    const body = document.getElementById("routes-body");
    const total = filteredRoutes.length;
    const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
    if (currentPage > totalPages) currentPage = totalPages;

    if (!total) {
      body.innerHTML = `<tr><td colspan="5"><div class="r-empty"><i class="fas fa-route"></i><span>No routes found yet.</span></div></td></tr>`;
    } else {
      const start = (currentPage - 1) * PAGE_SIZE;
      const page = filteredRoutes.slice(start, start + PAGE_SIZE);
      body.innerHTML = page.map((r) => `
        <tr data-route-id="${r.id}">
          <td>
            <div class="route-from">
              <i class="fas fa-circle"></i>
              <div>
                <div class="route-text">${esc(truncate(r.start_location, 42))}</div>
              </div>
            </div>
          </td>
          <td>
            <div class="route-to">
              <i class="fas fa-circle"></i>
              <div>
                <div class="route-text">${esc(truncate(r.end_location, 42))}</div>
              </div>
            </div>
          </td>
          <td class="text-center">
            <span class="risk-pill ${riskPillClass(r.risk_score)}">${Math.round(r.risk_score)}</span>
          </td>
          <td class="text-center text-surface-400 text-xs">${formatWhen(r.created_at)}</td>
          <td class="text-right pr-6">
            <div class="flex items-center justify-end gap-1">
              <button type="button" class="action-btn" data-preview="${r.id}" title="Preview"><i class="fas fa-eye"></i></button>
              ${canDelete ? `<button type="button" class="action-btn" data-del="${r.id}" title="Delete"><i class="fas fa-trash"></i></button>` : ""}
            </div>
          </td>
        </tr>`).join("");

      body.querySelectorAll("[data-preview], [data-route-id]").forEach((el) => {
        el.addEventListener("click", (e) => {
          if (e.target.closest("[data-del]")) return;
          const id = parseInt(el.dataset.preview || el.closest("[data-route-id]")?.dataset.routeId, 10);
          previewRoute(id);
        });
      });

      if (canDelete) {
        body.querySelectorAll("[data-del]").forEach((b) =>
          b.addEventListener("click", async (e) => {
            e.stopPropagation();
            try {
              await SR.del("/api/routes/" + b.dataset.del);
              flash("Route deleted.", "success");
              loadRoutes();
            } catch (err) {
              flash(err.message, "error");
            }
          })
        );
      }
    }

    const info = document.getElementById("route-table-info");
    const pageNum = document.getElementById("route-page-num");
    if (info) {
      if (!total) info.textContent = "Showing 0 of 0 routes";
      else {
        const start = (currentPage - 1) * PAGE_SIZE;
        const end = Math.min(start + PAGE_SIZE, total);
        info.textContent = `Showing ${start + 1}–${end} of ${total} routes`;
      }
    }
    if (pageNum) pageNum.textContent = String(currentPage);
  }

  function previewRoute(id) {
    const cached = savedRoutes.find((x) => x.id === id);
    if (!cached) return;

    const show = (r) => {
      if (!r || !r.geojson) {
        flash("Route map data unavailable.", "warning");
        return;
      }
      lastRouteEndpoints = r;
      document.getElementById("start-location").value = r.start_location || "";
      document.getElementById("end-location").value = r.end_location || "";
      if (r.start_lat != null) setCoords("start", r.start_lat, r.start_lng);
      if (r.end_lat != null) setCoords("end", r.end_lat, r.end_lng);
      showResultPanel();
      document.getElementById("route-explanation").textContent = `Saved route: ${r.start_location} → ${r.end_location}`;
      setRiskBadge(document.getElementById("route-risk"), r.risk_score, null);
      setRouteStats(r);
      showRoute(r.geojson, r.risk_score, null, false, r);
      document.getElementById("route-alternatives").classList.add("hidden");
      document.getElementById("route-result")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    };

    if (cached.geojson) {
      show(cached);
      return;
    }

    SR.get("/api/routes/" + id)
      .then(({ route }) => {
        const idx = savedRoutes.findIndex((x) => x.id === id);
        if (idx >= 0) savedRoutes[idx] = route;
        show(route);
      })
      .catch((err) => flash(err.message, "error"));
  }

  async function loadRoutes() {
    try {
      const { routes } = await SR.get("/api/routes");
      savedRoutes = routes || [];
      const search = document.getElementById("route-search");
      applyRouteFilter(search ? search.value : "");
    } catch (err) {
      flash(err.message, "error");
    }
  }

  function applyRouteFilter(query) {
    const q = (query || "").trim().toLowerCase();
    filteredRoutes = q
      ? savedRoutes.filter((r) =>
          (r.start_location || "").toLowerCase().includes(q) ||
          (r.end_location || "").toLowerCase().includes(q)
        )
      : [...savedRoutes];
    currentPage = 1;
    renderRoutesTable();
  }

  window.filterRouteTable = applyRouteFilter;
  window.changeRoutePage = (delta) => {
    const totalPages = Math.max(1, Math.ceil(filteredRoutes.length / PAGE_SIZE));
    currentPage = Math.min(totalPages, Math.max(1, currentPage + delta));
    renderRoutesTable();
  };

  function renderAlternatives(alts, route, badge) {
    const altEl = document.getElementById("route-alternatives");
    if (!alts.length) {
      altEl.classList.add("hidden");
      altEl.innerHTML = "";
      return;
    }
    altEl.classList.remove("hidden");
    altEl.classList.add("r-alt-list");
    altEl.innerHTML = `
      <div class="flex items-center justify-between mb-2">
        <span class="text-[11px] font-bold uppercase tracking-wider text-surface-400">Alternative Routes</span>
        <span class="text-[10px] text-surface-400">Tap to compare</span>
      </div>
      ${alts.map((a, i) => `
        <button type="button" class="r-alt-item" data-alt-idx="${i}">
          <span class="r-alt-num">${i + 1}</span>
            <span class="r-alt-info">
            <strong>${esc(a.label || "Alternative " + (i + 1))}</strong>
            <span>${esc(a.explanation || formatDistance(a.distance_m) + " · " + formatDuration(a.duration_s))}${a.incidents_on_route != null ? " · " + (a.incidents_on_route === 0 ? "Clear of incidents" : a.incidents_on_route + " incident(s) nearby") : ""}</span>
          </span>
          <span class="r-alt-risk ${riskPillClass(a.risk_score)}">${Math.round(a.risk_score)}</span>
        </button>`).join("")}`;

    altEl.querySelectorAll("[data-alt-idx]").forEach((btn) => {
      btn.addEventListener("click", () => {
        altEl.querySelectorAll(".r-alt-item").forEach((x) => x.classList.remove("selected"));
        btn.classList.add("selected");
        const a = alts[parseInt(btn.dataset.altIdx, 10)];
        showRoute(a.geojson, a.risk_score, a.risk_level, true, route);
        setRiskBadge(badge, a.risk_score, a.risk_level);
        setRouteStats(a);
        document.getElementById("route-explanation").textContent = a.explanation || "";
      });
    });
  }

  function resetSubmitBtn() {
    const btn = document.getElementById("route-submit-btn");
    if (!btn) return;
    btn.disabled = false;
    btn.innerHTML = '<i class="fas fa-wand-magic-sparkles"></i> Find Safest Route';
  }

  setupLocationAutocomplete(
    document.getElementById("start-location"),
    document.getElementById("start-suggestions"),
    {
      onInputChange: () => clearCoords("start"),
      onSelect: (r) => setCoords("start", r.lat, r.lng),
    }
  );
  setupLocationAutocomplete(
    document.getElementById("end-location"),
    document.getElementById("end-suggestions"),
    {
      onInputChange: () => clearCoords("end"),
      onSelect: (r) => setCoords("end", r.lat, r.lng),
    }
  );

  document.addEventListener("sr:user-ready", (ev) => {
    canDelete = DELETE_ROLES.includes(ev.detail.role);
    loadRoutes();
  });

  document.getElementById("route-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = document.getElementById("route-submit-btn");
    const result = document.getElementById("route-result");
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Calculating safest path…';
    if (result) result.classList.remove("visible");

    try {
      const payload = await resolvePayloadCoords();
      const { route } = await SR.post("/api/routes/generate", payload);
      lastRouteEndpoints = route;

      const badge = document.getElementById("route-risk");
      setRiskBadge(badge, route.risk_score, route.risk_level);
      document.getElementById("route-explanation").textContent = route.explanation || "Route generated from live risk data.";
      setRouteStats(route);
      showResultPanel();
      showRoute(route.geojson, route.risk_score, route.risk_level, false, route);
      renderAlternatives(route.alternatives || [], route, badge);
      document.getElementById("route-result")?.scrollIntoView({ behavior: "smooth", block: "nearest" });

      if (route.incidents_on_route > 0 && (route.alternatives || []).some((a) => a.incidents_on_route === 0)) {
        flash("A detour avoiding nearby incidents is available — compare alternate routes below.", "info");
      } else if (route.incidents_on_route === 0) {
        flash("Safest route found — clear of nearby incidents.", "success");
      } else {
        flash("Safest route found.", "success");
      }
      loadRoutes();
    } catch (err) {
      flash(err.message, "error");
    } finally {
      resetSubmitBtn();
      if (result && !result.classList.contains("hidden")) {
        requestAnimationFrame(() => result.classList.add("visible"));
      }
    }
  });
})();
