/** Shared Leaflet helpers for SafeRoute AI maps. */
(function (global) {
  "use strict";

  const RISK_COLORS = {
    LOW: { fill: "#10b981", stroke: "#059669" },
    MEDIUM: { fill: "#f59e0b", stroke: "#d97706" },
    HIGH: { fill: "#f43f5e", stroke: "#e11d48" },
    CRITICAL: { fill: "#991b1b", stroke: "#7f1d1d" },
  };

  const ROUTE_COLORS = {
    SAFE: "#059669",
    WARNING: "#d97706",
    DANGEROUS: "#dc2626",
    ALT: "#6366f1",
  };

  function riskColor(level) {
    return RISK_COLORS[level] || RISK_COLORS.LOW;
  }

  function routeColor(level, isAlt) {
    if (isAlt) return ROUTE_COLORS.ALT;
    if (level === "DANGEROUS") return ROUTE_COLORS.DANGEROUS;
    if (level === "WARNING") return ROUTE_COLORS.WARNING;
    return ROUTE_COLORS.SAFE;
  }

  function createBaseMap(containerId, center, zoom, options) {
    options = options || {};
    const map = L.map(containerId, { zoomControl: true, scrollWheelZoom: true });
    const tileUrl = options.dark
      ? "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
      : "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
    L.tileLayer(tileUrl, {
      attribution: options.dark
        ? '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
        : '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      maxZoom: 19,
      subdomains: options.dark ? "abcd" : "abc",
    }).addTo(map);
    map.setView([center.lat, center.lng], zoom || 11);
    return map;
  }

  function addCityMarkers(map, cities) {
    const layer = L.layerGroup();
    (cities || []).forEach((c) => {
      const icon = L.divIcon({
        className: "",
        html: `<div style="background:#2563eb;color:#fff;font-size:10px;font-weight:700;padding:2px 6px;border-radius:4px;white-space:nowrap;box-shadow:0 2px 6px rgba(0,0,0,.25)">${c.name}</div>`,
        iconSize: [80, 20],
        iconAnchor: [40, 10],
      });
      L.marker([c.lat, c.lng], { icon }).addTo(layer).bindPopup(`<b>${c.name}</b>`);
    });
    layer.addTo(map);
    return layer;
  }

  function addRiskZones(map, areas) {
    const layer = L.layerGroup();
    (areas || []).forEach((a) => {
      if (a.latitude == null || a.longitude == null) return;
      const c = riskColor(a.risk_level);
      const radiusM = (a.radius_km || 2.5) * 1000;
      const circle = L.circle([a.latitude, a.longitude], {
        radius: radiusM,
        color: c.stroke,
        fillColor: c.fill,
        fillOpacity: 0.25,
        weight: 2,
      });
      circle.bindPopup(
        `<b>${a.area_name}</b><br>Risk: ${a.risk_score}/100 (${a.risk_level})`
      );
      circle.addTo(layer);
      L.circleMarker([a.latitude, a.longitude], {
        radius: 6,
        color: c.stroke,
        fillColor: c.fill,
        fillOpacity: 0.9,
        weight: 2,
      })
        .bindPopup(`<b>${a.area_name}</b><br>Score: ${a.risk_score}`)
        .addTo(layer);
    });
    layer.addTo(map);
    return layer;
  }

  function addIncidents(map, incidents) {
    const layer = L.layerGroup();
    (incidents || []).forEach((ev) => {
      if (ev.latitude == null || ev.longitude == null) return;
      const sev = ev.severity || 1;
      const color = sev >= 4 ? "#dc2626" : sev >= 3 ? "#d97706" : "#64748b";
      const m = L.circleMarker([ev.latitude, ev.longitude], {
        radius: 7,
        color: "#fff",
        fillColor: color,
        fillOpacity: 0.95,
        weight: 2,
      });
      const sevLabel = sev >= 5 ? "Critical" : sev >= 4 ? "High" : sev >= 3 ? "Moderate" : "Low";
      m.bindPopup(
        `<b>${ev.title}</b><br><span style="color:#64748b">${ev.location}</span><br>` +
        `<strong>Severity:</strong> ${sev}/5 (${sevLabel})` +
        (ev.description ? `<br><span style="font-size:11px">${ev.description}</span>` : "")
      );
      m.addTo(layer);
    });
    layer.addTo(map);
    return layer;
  }

  function drawRoute(map, geojson, options) {
    const opts = options || {};
    const color = opts.color || ROUTE_COLORS.SAFE;
    const layer = L.geoJSON(geojson, {
      style: {
        color,
        weight: opts.weight || 5,
        opacity: 0.9,
        lineCap: "round",
        lineJoin: "round",
      },
    }).addTo(map);
    const group = L.layerGroup([layer]);
    if (opts.start) {
      L.marker([opts.start.lat, opts.start.lng], {
        icon: L.divIcon({
          className: "",
          html: '<div style="background:#2563eb;width:14px;height:14px;border-radius:50%;border:3px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,.35)"></div>',
          iconSize: [14, 14],
          iconAnchor: [7, 7],
        }),
      })
        .bindPopup(`<b>Origin</b><br>${opts.start.label || ""}`)
        .addTo(group);
    }
    if (opts.end) {
      L.marker([opts.end.lat, opts.end.lng], {
        icon: L.divIcon({
          className: "",
          html: '<div style="background:#10b981;width:14px;height:14px;border-radius:50%;border:3px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,.35)"></div>',
          iconSize: [14, 14],
          iconAnchor: [7, 7],
        }),
      })
        .bindPopup(`<b>Destination</b><br>${opts.end.label || ""}`)
        .addTo(group);
    }
    group.addTo(map);
    try {
      const bounds = group.getBounds();
      if (bounds.isValid()) map.fitBounds(bounds, { padding: [40, 40] });
    } catch (_) {}
    return group;
  }

  function clearLayers(layers) {
    (layers || []).forEach((l) => {
      if (l && l.remove) l.remove();
    });
  }

  global.SRMap = {
    RISK_COLORS,
    ROUTE_COLORS,
    riskColor,
    routeColor,
    createBaseMap,
    addCityMarkers,
    addRiskZones,
    addIncidents,
    drawRoute,
    clearLayers,
  };
})(window);
