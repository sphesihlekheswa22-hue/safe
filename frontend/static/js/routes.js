(function () {

  "use strict";



  const DELETE_ROLES = ["TRANSPORT_OPERATOR", "SYSTEM_ANALYST", "SYSTEM_ADMIN"];

  let canDelete = false;

  let routeMap = null;

  let routeLayers = [];

  let mapOverlayLayers = [];

  let savedRoutes = [];

  let lastRouteEndpoints = null;



  function esc(s) {

    return String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  }



  function riskBadgeCls(r) {

    return r >= 70 ? "badge-high hover:scale-105 transition-transform" : r >= 40 ? "badge-medium hover:scale-105 transition-transform" : "badge-low hover:scale-105 transition-transform";

  }



  function levelLabel(level, risk) {

    if (level) return level;

    if (risk >= 70) return "DANGEROUS";

    if (risk >= 40) return "WARNING";

    return "SAFE";

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



  /* --- Address autocomplete --- */

  function setupAutocomplete(inputId, listId, prefix) {

    const input = document.getElementById(inputId);

    const list = document.getElementById(listId);

    let timer = null;



    function hide() {

      list.classList.add("hidden");

      list.innerHTML = "";

    }



    input.addEventListener("input", () => {

      clearCoords(prefix);

      const q = input.value.trim();

      clearTimeout(timer);

      if (q.length < 2) {

        hide();

        return;

      }

      timer = setTimeout(async () => {

        try {

          const { results } = await SR.get("/api/routes/geocode?q=" + encodeURIComponent(q));

          if (!results.length) {

            hide();

            return;

          }

          list.innerHTML = results.map((r, i) => `

            <li role="option" data-idx="${i}" tabindex="0">

              <div class="font-medium text-surface-800">${esc(r.name)}</div>

              <div class="sub">${esc(r.display_name)}</div>

            </li>`).join("");

          list.classList.remove("hidden");

          list._items = results;

          list.querySelectorAll("li").forEach((li) => {

            li.addEventListener("mousedown", (e) => {

              e.preventDefault();

              const r = list._items[parseInt(li.dataset.idx, 10)];

              input.value = r.name;

              setCoords(prefix, r.lat, r.lng);

              hide();

            });

          });

        } catch (_) {

          hide();

        }

      }, 400);

    });



    input.addEventListener("blur", () => setTimeout(hide, 150));

  }



  /* --- Current location --- */

  document.getElementById("btn-my-location").addEventListener("click", () => {

    const btn = document.getElementById("btn-my-location");

    if (!navigator.geolocation) {

      flash("Geolocation is not supported by your browser.", "error");

      return;

    }

    btn.disabled = true;

    btn.textContent = "…";

    navigator.geolocation.getCurrentPosition(

      async (pos) => {

        const lat = pos.coords.latitude;

        const lng = pos.coords.longitude;

        try {

          const { result } = await SR.post("/api/routes/geocode/reverse", { lat, lng });

          document.getElementById("start-location").value = result.name;

          setCoords("start", result.lat, result.lng);

          flash("Current location set as origin.", "success");

        } catch (err) {

          document.getElementById("start-location").value = lat.toFixed(5) + ", " + lng.toFixed(5);

          setCoords("start", lat, lng);

          flash(err.message || "Location set (address lookup failed).", "warning");

        }

        btn.disabled = false;

        btn.innerHTML = '<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z"/></svg>';

      },

      (err) => {

        btn.disabled = false;

        btn.innerHTML = '<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z"/></svg>';

        const msgs = {

          1: "Location permission denied. Allow location access in your browser.",

          2: "Could not determine your position.",

          3: "Location request timed out.",

        };

        flash(msgs[err.code] || "Could not get your location.", "error");

      },

      { enableHighAccuracy: true, timeout: 15000, maximumAge: 60000 }

    );

  });



  setupAutocomplete("start-location", "start-suggestions", "start");

  setupAutocomplete("end-location", "end-suggestions", "end");



  /* --- Map --- */

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



  async function loadRoutes() {

    const { routes } = await SR.get("/api/routes");

    savedRoutes = routes || [];

    const body = document.getElementById("routes-body");

    if (!savedRoutes.length) {

      body.innerHTML = '<tr><td colspan="4" class="text-center py-8"><div class="w-12 h-12 mx-auto mb-3 rounded-xl bg-surface-100 text-surface-400 flex items-center justify-center"><svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 6.75V15m6-6v8.25m.503 3.498l4.875-2.437c.381-.19.622-.58.622-1.006V4.82c0-.836-.88-1.38-1.628-1.006l-3.869 1.934c-.317.159-.69.159-1.006 0L9.503 3.252a1.125 1.125 0 00-1.006 0L3.622 5.689C3.24 5.88 3 6.27 3 6.695V19.18c0 .836.88 1.38 1.628 1.006l3.869-1.934c.317-.159.69-.159 1.006 0l4.994 2.497c.317.158.69.158 1.006 0z"/></svg></div><p class="text-surface-400 text-sm">No routes generated yet.</p></td></tr>';

      return;

    }

    body.innerHTML = savedRoutes.map((r) => `

      <tr class="cursor-pointer hover:bg-surface-50/80 transition-colors" data-route-id="${r.id}">

        <td class="font-medium text-surface-700">${esc(r.start_location)}</td>

        <td>${esc(r.end_location)}</td>

        <td><span class="badge ${riskBadgeCls(r.risk_score)}">${r.risk_score}</span></td>

        <td class="text-right">${canDelete ? `<button class="btn-danger magnetic-btn ripple" data-del="${r.id}">Delete</button>` : ""}</td>

      </tr>`).join("");



    body.querySelectorAll("[data-route-id]").forEach((row) => {

      row.addEventListener("click", (e) => {

        if (e.target.closest("[data-del]")) return;

        const r = savedRoutes.find((x) => x.id === parseInt(row.dataset.routeId, 10));

        if (!r || !r.geojson) return;

        lastRouteEndpoints = r;

        document.getElementById("route-result").classList.remove("hidden");

        document.getElementById("route-explanation").textContent = `Saved route: ${r.start_location} → ${r.end_location}`;

        const badge = document.getElementById("route-risk");

        badge.textContent = `risk ${r.risk_score}`;

        badge.className = "badge " + riskBadgeCls(r.risk_score);

        showRoute(r.geojson, r.risk_score, null, false, r);

        document.getElementById("route-alternatives").classList.add("hidden");

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



  document.addEventListener("sr:user-ready", (ev) => {

    canDelete = DELETE_ROLES.includes(ev.detail.role);

    loadRoutes();

  });



  document.getElementById("route-form").addEventListener("submit", async (e) => {

    e.preventDefault();

    const btn = document.getElementById("route-submit-btn");

    btn.disabled = true;

    btn.textContent = "Finding route…";

    try {

      const { route } = await SR.post("/api/routes/generate", getPayload());

      lastRouteEndpoints = route;



      const badge = document.getElementById("route-risk");

      const lvl = levelLabel(route.risk_level, route.risk_score);

      badge.textContent = `${lvl} · ${route.risk_score}`;

      badge.className = "badge " + riskBadgeCls(route.risk_score);



      document.getElementById("route-explanation").textContent = route.explanation || "Route generated from live risk data.";

      document.getElementById("route-result").classList.remove("hidden");

      showRoute(route.geojson, route.risk_score, route.risk_level, false, route);



      const altEl = document.getElementById("route-alternatives");

      const alts = route.alternatives || [];

      if (alts.length) {

        altEl.classList.remove("hidden");

        altEl.innerHTML =

          `<p class="text-xs font-semibold text-surface-500 uppercase tracking-wide mb-2">Alternative routes</p>` +

          alts.map((a, i) => `

            <button type="button" class="w-full text-left glass-card rounded-xl p-3 hover:shadow-md transition-all border-l-4 ${a.risk_score >= 70 ? "border-l-rose-500" : a.risk_score >= 40 ? "border-l-amber-500" : "border-l-emerald-500"}" data-alt-idx="${i}">

              <div class="flex items-center justify-between mb-1">

                <span class="text-sm font-medium text-surface-800">${esc(a.label || "Alternative")}</span>

                <span class="badge ${riskBadgeCls(a.risk_score)}">${levelLabel(a.risk_level, a.risk_score)} · ${a.risk_score}</span>

              </div>

              <p class="text-xs text-surface-500">${esc(a.explanation || "")}</p>

            </button>`).join("");



        altEl.querySelectorAll("[data-alt-idx]").forEach((btn) => {

          btn.addEventListener("click", () => {

            const a = alts[parseInt(btn.dataset.altIdx, 10)];

            showRoute(a.geojson, a.risk_score, a.risk_level, true, route);

            badge.textContent = `${levelLabel(a.risk_level, a.risk_score)} · ${a.risk_score}`;

            badge.className = "badge " + riskBadgeCls(a.risk_score);

            document.getElementById("route-explanation").textContent = a.explanation || "";

          });

        });

      } else {

        altEl.classList.add("hidden");

        altEl.innerHTML = "";

      }



      flash("Safest route found.", "success");

      loadRoutes();

    } catch (err) {

      flash(err.message, "error");

    } finally {

      btn.disabled = false;

      btn.textContent = "Find safest route";

    }

  });

})();

