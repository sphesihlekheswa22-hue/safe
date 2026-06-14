/** Live address/area suggestions via GET /api/routes/geocode */
(function () {
  "use strict";

  const MY_CITY_KEY = "sr-my-city";
  const USER_LOC_KEY = "sr-user-loc";

  const POI_ICONS = {
    police: "fa-shield-halved",
    hospital: "fa-hospital",
    clinic: "fa-kit-medical",
    station: "fa-train",
    landmark: "fa-landmark",
  };

  let warmedNear = null;
  let warmPromise = null;

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;",
    }[c]));
  }

  function readStoredCoords(key) {
    try {
      const raw = sessionStorage.getItem(key);
      if (!raw) return null;
      const data = JSON.parse(raw);
      if (data && data.lat != null && data.lng != null) {
        return { lat: data.lat, lng: data.lng };
      }
    } catch {
      /* ignore */
    }
    return null;
  }

  function resolveNearCoords(options) {
    const opts = options || {};
    if (opts.nearLat != null && opts.nearLng != null) {
      return { lat: opts.nearLat, lng: opts.nearLng };
    }
    if (warmedNear) return warmedNear;
    const fromCity = readStoredCoords(MY_CITY_KEY);
    if (fromCity) return fromCity;
    return readStoredCoords(USER_LOC_KEY);
  }

  function warmUserLocation() {
    if (warmedNear) return Promise.resolve(warmedNear);
    if (warmPromise) return warmPromise;

    const existing = resolveNearCoords({});
    if (existing) {
      warmedNear = existing;
      return Promise.resolve(existing);
    }

    if (!navigator.geolocation) {
      return Promise.resolve(null);
    }

    warmPromise = new Promise((resolve) => {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          warmedNear = {
            lat: pos.coords.latitude,
            lng: pos.coords.longitude,
          };
          try {
            sessionStorage.setItem(USER_LOC_KEY, JSON.stringify(warmedNear));
          } catch {
            /* ignore */
          }
          resolve(warmedNear);
        },
        () => resolve(null),
        { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 }
      );
    }).finally(() => {
      warmPromise = null;
    });

    return warmPromise;
  }

  async function fetchLocationSuggestions(q, limit, near) {
    const lim = limit || 10;
    let url = "/api/routes/geocode?q=" + encodeURIComponent(q) + "&limit=" + lim;
    if (near && near.lat != null && near.lng != null) {
      url += "&lat=" + encodeURIComponent(near.lat) + "&lng=" + encodeURIComponent(near.lng);
    }
    return SR.get(url);
  }

  function iconForResult(r) {
    if (r && r.category && POI_ICONS[r.category]) {
      return POI_ICONS[r.category];
    }
    return "fa-location-dot";
  }

  function labelForResult(r) {
    if (!r) return "";
    return r.name || r.display_name || "";
  }

  function subtitleForResult(r) {
    const full = r.display_name || "";
    const short = labelForResult(r);
    if (full && full !== short) return full;
    if (r.distance_km != null) return r.distance_km + " km away";
    return "";
  }

  function showSuggestionsLoading(list) {
    list.innerHTML = `<li class="suggestion-divider" role="presentation"><i class="fas fa-spinner fa-spin mr-1"></i> Searching South African addresses…</li>`;
    list.classList.add("visible");
    list._items = [];
  }

  function renderSuggestionList(list, items, input, onSelect) {
    if (!items.length) {
      list.innerHTML = `<li class="suggestion-divider" role="presentation">No addresses found — try a street name, suburb, or landmark</li>`;
      list.classList.add("visible");
      list._items = [];
      return;
    }
    list.innerHTML = items.map((r, i) => `
      <li role="option" data-idx="${i}" tabindex="0">
        <i class="fas ${iconForResult(r)}"></i>
        <div>
          <div class="font-medium">${esc(labelForResult(r))}</div>
          ${subtitleForResult(r) ? `<div class="sub">${esc(subtitleForResult(r))}</div>` : ""}
        </div>
      </li>`).join("");
    list.classList.add("visible");
    list._items = items;
    list._onSelect = onSelect;
    list.querySelectorAll("li[role='option']").forEach((li) => {
      li.addEventListener("mousedown", (e) => {
        e.preventDefault();
        selectSuggestion(list, input, parseInt(li.dataset.idx, 10));
      });
    });
  }

  function selectSuggestion(list, input, idx) {
    const r = list._items[idx];
    if (!r) return;
    input.value = labelForResult(r);
    input.dataset.selectedLabel = labelForResult(r);
    if (typeof list._onSelect === "function") {
      list._onSelect(r);
    }
    list.classList.remove("visible");
    list.innerHTML = "";
    list._items = [];
  }

  function setupLocationAutocomplete(inputEl, listEl, options) {
    if (!inputEl || !listEl) return;

    const opts = options || {};
    const minChars = opts.minChars != null ? opts.minChars : 2;
    const debounceMs = opts.debounceMs != null ? opts.debounceMs : 450;
    const limit = opts.limit || 10;

    inputEl.setAttribute("autocomplete", "off");
    warmUserLocation();

    let timer = null;
    let requestId = 0;

    function onSelectWrapper(r) {
      if (typeof opts.onSelect === "function") {
        opts.onSelect(r);
      }
    }

    inputEl.addEventListener("input", () => {
      delete inputEl.dataset.selectedLabel;
      if (typeof opts.onInputChange === "function") {
        opts.onInputChange();
      }
      const q = inputEl.value.trim();
      clearTimeout(timer);
      if (q.length < minChars) {
        listEl.classList.remove("visible");
        listEl.innerHTML = "";
        listEl._items = [];
        return;
      }
      timer = setTimeout(async () => {
        const id = ++requestId;
        showSuggestionsLoading(listEl);
        try {
          await warmUserLocation();
          const near = resolveNearCoords(opts);
          const { results } = await fetchLocationSuggestions(q, limit, near);
          if (id !== requestId) return;
          renderSuggestionList(listEl, results || [], inputEl, onSelectWrapper);
        } catch (err) {
          if (id !== requestId) return;
          listEl.innerHTML = `<li class="suggestion-divider" role="presentation">Search unavailable — ${esc(err.message || "try again")}</li>`;
          listEl.classList.add("visible");
          listEl._items = [];
        }
      }, debounceMs);
    });

    inputEl.addEventListener("focus", () => {
      warmUserLocation();
      const q = inputEl.value.trim();
      if (q.length >= minChars && listEl._items && listEl._items.length) {
        listEl.classList.add("visible");
      } else if (q.length >= minChars) {
        inputEl.dispatchEvent(new Event("input"));
      }
    });

    inputEl.addEventListener("keydown", (e) => {
      if (!listEl.classList.contains("visible") || !listEl._items || !listEl._items.length) return;
      const options_ = [...listEl.querySelectorAll("li[role='option']")];
      let active = options_.findIndex((li) => li.classList.contains("is-active"));
      if (e.key === "ArrowDown") {
        e.preventDefault();
        active = Math.min(options_.length - 1, active + 1);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        active = Math.max(0, active - 1);
      } else if (e.key === "Enter" && active >= 0) {
        e.preventDefault();
        selectSuggestion(listEl, inputEl, active);
        return;
      } else if (e.key === "Escape") {
        listEl.classList.remove("visible");
        return;
      } else {
        return;
      }
      options_.forEach((li, i) => li.classList.toggle("is-active", i === active));
    });

    inputEl.addEventListener("blur", () => {
      setTimeout(() => {
        listEl.classList.remove("visible");
      }, 180);
    });

    document.addEventListener("click", (e) => {
      if (!inputEl.contains(e.target) && !listEl.contains(e.target)) {
        listEl.classList.remove("visible");
      }
    });
  }

  window.fetchLocationSuggestions = fetchLocationSuggestions;
  window.setupLocationAutocomplete = setupLocationAutocomplete;
  window.resolveNearCoords = resolveNearCoords;
  window.warmUserLocation = warmUserLocation;
})();
