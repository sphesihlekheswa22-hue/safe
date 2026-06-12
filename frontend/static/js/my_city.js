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
    if (s >= 4) return "sev-4";
    if (s === 3) return "sev-3";
    return "sev-2";
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
    if (el) el.textContent = msg;
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
        <div class="py-14 text-center px-6">
          <div class="empty-icon"><i class="fas fa-shield-halved"></i></div>
          <p class="text-surface-600 font-medium">No incidents in ${esc(data.city || "your city")}</p>
          <p class="text-sm text-surface-400 mt-1">That's good news — or be the first to report something.</p>
        </div>`;
      return;
    }

    list.innerHTML = data.events.map((e) => `
      <div class="event-row">
        <div class="event-sev ${sevClass(e.severity)}">${e.severity}</div>
        <div class="flex-1 min-w-0">
          <p class="font-semibold text-surface-800 text-sm">${esc(e.title)}</p>
          <p class="text-xs text-surface-500 mt-0.5"><i class="fas fa-location-dot"></i> ${esc(e.location)} · ${esc(e.source)}</p>
          ${e.description ? `<p class="text-xs text-surface-400 mt-1 line-clamp-2">${esc(e.description)}</p>` : ""}
        </div>
      </div>`).join("");
  }

  async function loadMyCityEvents(cityData) {
    $("events-list").innerHTML = '<div class="py-12 text-center text-surface-400 text-sm">Loading events…</div>';
    try {
      const res = await SR.get("/api/events/my-city?" + buildQuery(cityData));
      renderEvents(res);
    } catch (err) {
      $("events-list").innerHTML = `<div class="py-12 text-center text-rose-600 text-sm px-6">${esc(err.message)}</div>`;
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
    setStatus("Detecting your location…");
    if (!navigator.geolocation) {
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
      },
      () => {
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
