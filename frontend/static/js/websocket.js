/* Realtime client.
 * Connects to the backend SSE endpoint (/api/realtime/stream) for live alert
 * updates and degrades gracefully to no-op if EventSource is unavailable.
 * (Named websocket.js to match the project layout; the transport is SSE.)
 */
window.Realtime = (function () {
  let source = null;

  function connect(onAlerts) {
    if (typeof EventSource === "undefined") return;
    try {
      source = new EventSource("/api/realtime/stream");
      source.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data);
          if (data.alerts && typeof onAlerts === "function") onAlerts(data.alerts);
        } catch (e) { /* ignore malformed frame */ }
      };
      source.onerror = () => {
        const ind = document.getElementById("realtime-indicator");
        if (ind) ind.classList.add("hidden");
      };
    } catch (e) {
      /* SSE not available; pages still work via manual refresh */
    }
  }

  function close() {
    if (source) source.close();
  }

  return { connect, close };
})();
