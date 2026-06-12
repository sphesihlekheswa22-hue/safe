/** Live address/area suggestions via GET /api/routes/geocode */
(function () {
  "use strict";

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;",
    }[c]));
  }

  async function fetchLocationSuggestions(q, limit) {
    const lim = limit || 10;
    return SR.get("/api/routes/geocode?q=" + encodeURIComponent(q) + "&limit=" + lim);
  }

  function showSuggestionsLoading(list) {
    list.innerHTML = `<li class="suggestion-divider" role="presentation"><i class="fas fa-spinner fa-spin mr-1"></i> Searching addresses…</li>`;
    list.classList.add("visible");
    list._items = [];
  }

  function renderSuggestionList(list, items, input, onSelect) {
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
    input.value = r.name;
    input.dataset.selectedLabel = r.name;
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
    const minChars = opts.minChars != null ? opts.minChars : 3;
    const debounceMs = opts.debounceMs != null ? opts.debounceMs : 450;
    const limit = opts.limit || 10;

    inputEl.setAttribute("autocomplete", "off");

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
          const { results } = await fetchLocationSuggestions(q, limit);
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
})();
