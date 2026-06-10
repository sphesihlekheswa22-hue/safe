/* Realtime client.
 * Connects to the backend SSE endpoint (/api/realtime/stream) for live alert
 * updates and falls back to JSON polling if SSE fails (common on gunicorn/Render).
 */
window.Realtime = (function () {
  let source = null;
  let pollTimer = null;
  let usingPoll = false;

  async function pollAlerts(onAlerts) {
    try {
      const res = await fetch("/api/realtime/alerts");
      if (!res.ok) return;
      const data = await res.json();
      if (data.alerts && typeof onAlerts === "function") onAlerts(data.alerts);
    } catch (e) {
      /* ignore transient network errors */
    }
  }

  function startPolling(onAlerts, intervalMs = 15000) {
    if (pollTimer) return;
    usingPoll = true;
    pollAlerts(onAlerts);
    pollTimer = setInterval(() => pollAlerts(onAlerts), intervalMs);
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

  function connect(onAlerts) {
    // SSE ties up gunicorn sync workers on Render and causes WORKER TIMEOUT; poll instead.
    const host = location.hostname || "";
    if (host.includes("onrender.com") || host.includes("render.com")) {
      startPolling(onAlerts);
      return;
    }

    if (typeof EventSource === "undefined") {
      startPolling(onAlerts);
      return;
    }

    try {
      source = new EventSource("/api/realtime/stream");
      source.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data);
          if (data.alerts && typeof onAlerts === "function") onAlerts(data.alerts);
        } catch (e) { /* ignore malformed frame */ }
      };
      source.onerror = () => {
        if (source) {
          source.close();
          source = null;
        }
        if (!usingPoll) startPolling(onAlerts);
      };
    } catch (e) {
      startPolling(onAlerts);
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
