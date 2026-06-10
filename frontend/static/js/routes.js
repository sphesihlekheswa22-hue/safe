(function () {
  "use strict";

  const DELETE_ROLES = ["TRANSPORT_OPERATOR", "SYSTEM_ANALYST", "SYSTEM_ADMIN"];
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
    if (risk >= 70) return "bg-rose-50 text-rose-700 border border-rose-200";
    if (risk >= 40) return "bg-amber-50 text-amber-700 border border-amber-200";
    return "bg-emerald-50 text-emerald-700 border border-emerald-200";
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

  function showResultPanel() {
    const panel = document.getElementById("route-result");
    if (!panel) return;
    panel.classList.remove("hidden");
    requestAnimationFrame(() => panel.classList.add("visible"));
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

  function renderSuggestionList(list, items, input, prefix) {
    if (!items.length) {
      list.innerHTML = `<li class="suggestion-divider" role="presentation">No addresses found — try a street name or suburb</li>`;
      list.classList.add("visible");
      list._items = [];
      return;
    }
    list.innerHTML = items.map((r, i) => `
      <li role="option" data-idx="${i}" tabindex="0">
        <i class="fas fa-location-dot"></i>
        <div>
          <div class="font-medium">${esc(r.name)}</div>
          <div class="sub">${esc(r.display_name)}</div>
        </div>
      </li>`).join("");
    list.classList.add("visible");
    list._items = items;
    list.querySelectorAll("li[role='option']").forEach((li) => {
      li.addEventListener("mousedown", (e) => {
        e.preventDefault();
        selectSuggestion(list, input, prefix, parseInt(li.dataset.idx, 10));
      });
    });
  }

  function selectSuggestion(list, input, prefix, idx) {
    const r = list._items[idx];
    if (!r) return;
    input.value = r.name;
    setCoords(prefix, r.lat, r.lng);
    input.dataset.selectedLabel = r.name;
    list.classList.remove("visible");
    list.innerHTML = "";
  }

  function showSuggestionsLoading(list) {
    list.innerHTML = `<li class="suggestion-divider" role="presentation"><i class="fas fa-spinner fa-spin mr-1"></i> Searching addresses…</li>`;
    list.classList.add("visible");
    list._items = [];
  }

  async function fetchSuggestions(q) {
    return SR.get("/api/routes/geocode?q=" + encodeURIComponent(q) + "&limit=10");
  }

  async function resolveField(prefix) {
    const input = document.getElementById(prefix + "-location");
    const lat = parseCoord(document.getElementById(prefix + "-lat").value);
    const lng = parseCoord(document.getElementById(prefix + "-lng").value);
    if (lat != null && lng != null) return true;

    const q = input.value.trim();
    if (q.length < 2) return false;

    const { results } = await fetchSuggestions(q);
    if (!results.length) return false;

    selectSuggestion(
      document.getElementById(prefix + "-suggestions"),
      input,
      prefix,
      0
    );
    return true;
  }

  async function resolvePayloadCoords() {
    const startOk = await resolveField("start");
    const endOk = await resolveField("end");
    if (!startOk) throw new Error("Could not find the origin. Select an address from the suggestions.");
    if (!endOk) throw new Error("Could not find the destination. Select an address from the suggestions.");
    return getPayload();
  }

  function setupAutocomplete(inputId, listId, prefix) {
    const input = document.getElementById(inputId);
    const list = document.getElementById(listId);
    let timer = null;
    let requestId = 0;

    input.addEventListener("input", () => {
      delete input.dataset.selectedLabel;
      clearCoords(prefix);
      const q = input.value.trim();
      clearTimeout(timer);
      if (q.length < 2) {
        list.classList.remove("visible");
        list.innerHTML = "";
        return;
      }
      timer = setTimeout(async () => {
        const id = ++requestId;
        showSuggestionsLoading(list);
        try {
          const { results } = await fetchSuggestions(q);
          if (id !== requestId) return;
          renderSuggestionList(list, results, input, prefix);
        } catch (err) {
          if (id !== requestId) return;
          list.innerHTML = `<li class="suggestion-divider" role="presentation">Search unavailable — ${esc(err.message || "try again")}</li>`;
          list.classList.add("visible");
        }
      }, 280);
    });

    input.addEventListener("focus", () => {
      const q = input.value.trim();
      if (q.length >= 2 && list._items && list._items.length) {
        list.classList.add("visible");
      } else if (q.length >= 2) {
        input.dispatchEvent(new Event("input"));
      }
    });

    input.addEventListener("keydown", (e) => {
      if (!list.classList.contains("visible") || !list._items || !list._items.length) return;
      const options = [...list.querySelectorAll("li[role='option']")];
      let active = options.findIndex((li) => li.classList.contains("is-active"));
      if (e.key === "ArrowDown") {
        e.preventDefault();
        active = Math.min(options.length - 1, active + 1);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        active = Math.max(0, active - 1);
      } else if (e.key === "Enter" && active >= 0) {
        e.preventDefault();
        selectSuggestion(list, input, prefix, active);
        return;
      } else if (e.key === "Escape") {
        list.classList.remove("visible");
        return;
      } else {
        return;
      }
      options.forEach((li, i) => li.classList.toggle("is-active", i === active));
    });

    input.addEventListener("blur", () => setTimeout(() => {
      list.classList.remove("visible");
    }, 180));
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
    routeMap = SRMap.createBaseMap("route-leaflet-map", { lat: -29.8587, lng: 31.0218 }, 11);
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
    const r = savedRoutes.find((x) => x.id === id);
    if (!r || !r.geojson) return;
    lastRouteEndpoints = r;
    showResultPanel();
    document.getElementById("route-explanation").textContent = `Saved route: ${r.start_location} → ${r.end_location}`;
    setRiskBadge(document.getElementById("route-risk"), r.risk_score, null);
    setRouteStats(r);
    showRoute(r.geojson, r.risk_score, null, false, r);
    document.getElementById("route-alternatives").classList.add("hidden");
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
            <span>${esc(a.explanation || formatDistance(a.distance_m) + " · " + formatDuration(a.duration_s))}</span>
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

  setupAutocomplete("start-location", "start-suggestions", "start");
  setupAutocomplete("end-location", "end-suggestions", "end");

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

      flash("Safest route found.", "success");
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
