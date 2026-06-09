/* Minimal dependency-free chart helpers (horizontal bar charts rendered with
 * plain HTML/CSS). Avoids pulling in a charting library. */
window.Charts = (function () {
  function escapeHtml(s) {
    return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  }

  function barChart(containerId, data, { color = "#2563eb", max } = {}) {
    const el = document.getElementById(containerId);
    if (!el) return;
    const values = data.map((d) => d.value);
    const ceiling = max || Math.max(1, ...values);
    el.innerHTML = data
      .map((d) => {
        const pct = Math.round((d.value / ceiling) * 100);
        return `
          <div>
            <div class="flex justify-between text-xs text-slate-600 mb-1">
              <span>${escapeHtml(d.label)}</span><span class="font-semibold">${d.value}</span>
            </div>
            <div class="h-2.5 rounded-full bg-slate-100 overflow-hidden">
              <div class="h-full rounded-full" style="width:${pct}%;background:${d.color || color}"></div>
            </div>
          </div>`;
      })
      .join("");
  }

  return { barChart };
})();
