/* Realtime client — SSE/polling for recent incidents (events). */
window.Realtime = (function () {
  let source = null;
  let pollTimer = null;
  let usingPoll = false;

  async function pollEvents(onEvents) {
    try {
      const res = await fetch("/api/realtime/events");
      if (!res.ok) return;
      const data = await res.json();
      if (data.events && typeof onEvents === "function") onEvents(data.events);
    } catch (e) {
      /* ignore transient network errors */
    }
  }

  function startPolling(onEvents, intervalMs = 15000) {
    if (pollTimer) return;
    usingPoll = true;
    pollEvents(onEvents);
    pollTimer = setInterval(() => pollEvents(onEvents), intervalMs);
    const ind = document.getElementById("realtime-indicator");
    if (ind) ind.classList.remove("hidden");
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
    usingPoll = false;
  }

  function connect(onEvents) {
    const host = location.hostname || "";
    if (host.includes("onrender.com") || host.includes("render.com")) {
      startPolling(onEvents);
      return;
    }

    if (typeof EventSource === "undefined") {
      startPolling(onEvents);
      return;
    }

    try {
      source = new EventSource("/api/realtime/stream");
      source.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data);
          if (data.events && typeof onEvents === "function") onEvents(data.events);
        } catch (e) { /* ignore malformed frame */ }
      };
      source.onerror = () => {
        if (source) {
          source.close();
          source = null;
        }
        if (!usingPoll) startPolling(onEvents);
      };
    } catch (e) {
      startPolling(onEvents);
    }
  }

  function close() {
    if (source) {
      source.close();
      source = null;
    }
    stopPolling();
  }

  return { connect, close };
})();
