(function () {
  "use strict";

  const STORAGE_KEY = "sr-my-city";
  const DEFAULT_CITY = {
    city: "Pretoria",
    lat: -25.7461,
    lng: 28.1881,
    source: "default",
  };

  const $ = (id) => document.getElementById(id);

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;",
    }[c]));
  }

  function sevClass(s) {
    const n = parseInt(s, 10);
    if (n >= 1 && n <= 5) return "sev-" + n;
    if (n >= 4) return "sev-4";
    if (n === 3) return "sev-3";
    return "sev-2";
  }

  function sourceClass(source) {
    return source === "community" || source === "user" ? "community" : "system";
  }

  function readCache() {
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }

  function writeCache(data) {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    } catch {
      /* ignore */
    }
  }

  function setStatus(msg) {
    const el = $("city-status");
    if (el) {
      el.innerHTML = `<i class="fas fa-crosshairs mr-1.5 text-primary-400"></i>${esc(msg)}`;
    }
  }

  function updateCityUI(data) {
    $("city-label").textContent = data.city;
    $("city-badge-wrap").classList.remove("hidden");
    const picker = $("city-picker");
    if (picker) {
      const opt = [...picker.options].find((o) => o.value === data.city);
      if (opt) picker.value = data.city;
    }
    const sourceLabel = data.source === "geolocation" ? "Based on your location"
      : data.source === "manual" ? "City selected manually"
      : "Showing default area";
    setStatus(sourceLabel);
  }

  function buildQuery(data) {
    const params = new URLSearchParams();
    if (data.city) params.set("city", data.city);
    if (data.lat != null && data.lng != null) {
      params.set("lat", String(data.lat));
      params.set("lng", String(data.lng));
    }
    return params.toString();
  }

  function renderEvents(data) {
    const list = $("events-list");
    const count = data.count || 0;
    $("event-count-badge").textContent = count + " incident" + (count === 1 ? "" : "s");
    $("events-subtitle").textContent = count
      ? `Within ~${Math.round(data.radius_km || 25)} km of ${data.city || "your area"}`
      : `No incidents reported in ${data.city || "your area"} yet`;

    if (!count) {
      list.innerHTML = `
        <div class="a-empty">
          <div class="a-empty-icon"><i class="fas fa-shield-halved"></i></div>
          <h3>No incidents nearby</h3>
          <p>No incidents reported in ${esc(data.city || "your city")} yet — that's good news.</p>
        </div>`;
      return;
    }

    list.innerHTML = data.events.map((e, i) => `
      <div class="event-row a-in" style="animation-delay:${i * 0.05}s" onclick="location.href='/events'">
        <div class="event-sev ${sevClass(e.severity)}">${e.severity}</div>
        <div class="event-info">
          <p class="event-title">${esc(e.title)}</p>
          <div class="event-meta">
            <i class="fas fa-location-dot"></i>
            <span>${esc(e.location)}</span>
            <span class="event-meta-dot"></span>
            <span class="event-source ${sourceClass(e.source)}">${esc(e.source)}</span>
          </div>
          ${e.description ? `<p class="text-xs mt-1 line-clamp-2" style="color:var(--a-muted)">${esc(e.description)}</p>` : ""}
        </div>
        <i class="fas fa-chevron-right event-arrow"></i>
      </div>`).join("");
  }

  async function loadMyCityEvents(cityData) {
    $("events-list").innerHTML = `
      <div class="a-empty">
        <div class="a-empty-icon"><i class="fas fa-spinner fa-spin"></i></div>
        <h3>Loading incidents</h3>
        <p>Fetching events near your area...</p>
      </div>`;
    try {
      const res = await SR.get("/api/events/my-city?" + buildQuery(cityData));
      renderEvents(res);
    } catch (err) {
      $("events-list").innerHTML = `
        <div class="a-empty">
          <div class="a-empty-icon" style="background:rgba(239,68,68,0.15);border-color:rgba(239,68,68,0.2);">
            <i class="fas fa-triangle-exclamation" style="color:#f87171;"></i>
          </div>
          <h3 style="color:#f87171">${esc(err.message)}</h3>
        </div>`;
      flash(err.message, "error");
    }
  }

  function applyCity(cityData) {
    writeCache(cityData);
    updateCityUI(cityData);
    loadMyCityEvents(cityData);
  }

  function pickerCoords() {
    const picker = $("city-picker");
    const opt = picker.options[picker.selectedIndex];
    return {
      city: opt.value,
      lat: parseFloat(opt.dataset.lat),
      lng: parseFloat(opt.dataset.lng),
      source: "manual",
    };
  }

  function detectCity() {
    const btn = $("btn-use-location");
    if (btn) btn.classList.add("pulse-ring");
    setStatus("Detecting your location…");
    if (!navigator.geolocation) {
      if (btn) btn.classList.remove("pulse-ring");
      applyCity(readCache() || DEFAULT_CITY);
      return;
    }
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        try {
          const { result } = await SR.post("/api/routes/geocode/reverse", { lat, lng });
          applyCity({
            city: result.city || result.name || "Your area",
            lat,
            lng,
            source: "geolocation",
          });
        } catch {
          applyCity({ city: "Your area", lat, lng, source: "geolocation" });
        }
        if (btn) btn.classList.remove("pulse-ring");
      },
      () => {
        if (btn) btn.classList.remove("pulse-ring");
        const cached = readCache();
        if (cached) {
          applyCity(cached);
        } else {
          applyCity(DEFAULT_CITY);
          setStatus("Location unavailable — showing Pretoria. Pick your city or try again.");
        }
      },
      { enableHighAccuracy: false, timeout: 12000, maximumAge: 300000 }
    );
  }

  document.addEventListener("sr:user-ready", () => {
    const cached = readCache();
    if (cached) {
      applyCity(cached);
    } else {
      detectCity();
    }
  });

  $("city-picker").addEventListener("change", () => applyCity(pickerCoords()));
  $("btn-use-location").addEventListener("click", () => detectCity());
})();
