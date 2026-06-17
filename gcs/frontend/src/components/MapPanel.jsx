import { useEffect, useRef } from 'react';
import L from 'leaflet';
import { useDrone } from '../context/DroneContext';

/* ── Drone icon (orange triangle, rotates with heading) ── */
function createDroneIcon(heading) {
  return L.divIcon({
    className: '',
    iconSize: [32, 32],
    iconAnchor: [16, 16],
    html: `<div style="
      width:32px;height:32px;display:flex;align-items:center;justify-content:center;
      transform:rotate(${heading}deg);transition:transform 0.4s ease;
    ">
      <svg width="28" height="28" viewBox="0 0 28 28">
        <polygon points="14,2 24,24 14,18 4,24"
          fill="#f97316" stroke="#ea580c" stroke-width="1.5" opacity="0.95"/>
      </svg>
    </div>
    <div style="
      position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
      width:40px;height:40px;border-radius:50%;
      background:radial-gradient(circle,rgba(249,115,22,0.25) 0%,transparent 70%);
      pointer-events:none;
    "></div>`,
  });
}

/* ── Home icon (blue circle) ── */
const homeIcon = L.divIcon({
  className: '',
  iconSize: [20, 20],
  iconAnchor: [10, 10],
  html: `<div style="
    width:20px;height:20px;border-radius:50%;
    background:var(--info,#3b82f6);border:2px solid #60a5fa;
    display:flex;align-items:center;justify-content:center;
  ">
    <svg width="10" height="10" viewBox="0 0 10 10">
      <polygon points="5,1 9,6 7,6 7,9 3,9 3,6 1,6" fill="white"/>
    </svg>
  </div>`,
});

/* ── Waypoint icon (numbered circle) ── */
function wpIcon(index) {
  return L.divIcon({
    className: '',
    iconSize: [20, 20],
    iconAnchor: [10, 10],
    html: `<div style="
      width:20px;height:20px;border-radius:50%;
      background:rgba(249,115,22,0.2);border:1.5px solid rgba(249,115,22,0.5);
      display:flex;align-items:center;justify-content:center;
      font-family:var(--font-mono);font-size:9px;font-weight:600;color:#fb923c;
    ">${index + 1}</div>`,
  });
}

/* ── Detection marker (color-coded by threat level) ── */
function detIcon(threatLevel) {
  const colors = {
    LOW: { bg: 'rgba(34,197,94,0.2)', border: '#22c55e' },
    MEDIUM: { bg: 'rgba(234,179,8,0.2)', border: '#eab308' },
    HIGH: { bg: 'rgba(239,68,68,0.2)', border: '#ef4444' },
    CRITICAL: { bg: 'rgba(239,68,68,0.4)', border: '#ef4444' },
  };
  const c = colors[threatLevel] || colors.LOW;
  return L.divIcon({
    className: '',
    iconSize: [14, 14],
    iconAnchor: [7, 7],
    html: `<div style="
      width:14px;height:14px;border-radius:50%;
      background:${c.bg};border:2px solid ${c.border};
    "></div>`,
  });
}

export default function MapPanel() {
  const { state } = useDrone();
  const { telemetry: t, trail, config: cfg, detections } = state;

  // DOM node + Leaflet instance + persistent layer refs
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const droneMarkerRef = useRef(null);
  const trailRef = useRef(null);
  const geofenceRef = useRef(null);
  const staticLayerRef = useRef(null);   // home + waypoints
  const detLayerRef = useRef(null);      // detection markers
  const centeredRef = useRef(false);

  /* ── 1. Initialize the map once ── */
  useEffect(() => {
    if (mapRef.current || !containerRef.current) return;

    const map = L.map(containerRef.current, {
      center: [cfg.home_lat, cfg.home_lon],
      zoom: 16,
      zoomControl: false,
      attributionControl: true,
    });
    mapRef.current = map;

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OSM',
      maxZoom: 19,
    }).addTo(map);

    // Persistent layers (created once, mutated on data change)
    geofenceRef.current = L.layerGroup().addTo(map);
    trailRef.current = L.layerGroup().addTo(map);
    staticLayerRef.current = L.layerGroup().addTo(map);
    detLayerRef.current = L.layerGroup().addTo(map);

    droneMarkerRef.current = L.marker([t.lat, t.lon], {
      icon: createDroneIcon(t.heading),
      zIndexOffset: 1000,
    }).addTo(map);

    // Leaflet renders into a 0px box until the container has real pixels.
    // Force a recalculation after the browser has laid the panel out, and
    // keep it correct on any future container resize.
    const invalidate = () => map.invalidateSize();
    const raf = requestAnimationFrame(invalidate);
    const t0 = setTimeout(invalidate, 200);

    const ro = new ResizeObserver(invalidate);
    ro.observe(containerRef.current);

    return () => {
      cancelAnimationFrame(raf);
      clearTimeout(t0);
      ro.disconnect();
      map.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* ── 2. Drone marker: position + heading + follow ── */
  useEffect(() => {
    const m = droneMarkerRef.current;
    if (!m) return;
    m.setLatLng([t.lat, t.lon]);
    m.setIcon(createDroneIcon(t.heading));

    // Auto-follow: snap-zoom to the first fix, then smoothly pan to keep the
    // drone centred as it flies to each patrol waypoint.
    if (mapRef.current && t.lat && t.lon) {
      if (!centeredRef.current) {
        mapRef.current.setView([t.lat, t.lon], 16);
        centeredRef.current = true;
      } else {
        mapRef.current.panTo([t.lat, t.lon], { animate: true, duration: 0.5 });
      }
    }
  }, [t.lat, t.lon, t.heading]);

  /* ── 3. Flight trail (orange polyline) ── */
  useEffect(() => {
    const layer = trailRef.current;
    if (!layer) return;
    layer.clearLayers();
    const positions = trail.map(p => [p.lat, p.lon]);
    if (positions.length > 1) {
      L.polyline(positions, {
        color: '#f97316', weight: 2, opacity: 0.5,
      }).addTo(layer);
    }
  }, [trail]);

  /* ── 4. Geofence (dashed orange polygon) ── */
  useEffect(() => {
    const layer = geofenceRef.current;
    if (!layer) return;
    layer.clearLayers();
    const positions = cfg.geofence.map(p => [p.lat, p.lon]);
    if (positions.length > 0) {
      L.polygon(positions, {
        color: '#f97316', weight: 1.5, opacity: 0.6,
        fillColor: '#f97316', fillOpacity: 0.04,
        dashArray: '8 4',
      }).addTo(layer);
    }
  }, [cfg.geofence]);

  /* ── 5. Home marker + patrol waypoints ── */
  useEffect(() => {
    const layer = staticLayerRef.current;
    if (!layer) return;
    layer.clearLayers();

    L.marker([cfg.home_lat, cfg.home_lon], { icon: homeIcon })
      .bindPopup('Home / Launch Point')
      .addTo(layer);

    cfg.patrol_waypoints.forEach((wp, i) => {
      L.marker([wp.lat, wp.lon], { icon: wpIcon(i) })
        .bindPopup(
          `<span style="font-family:var(--font-mono);font-size:11px;">WP${i + 1}: ${wp.alt}m</span>`
        )
        .addTo(layer);
    });
  }, [cfg.home_lat, cfg.home_lon, cfg.patrol_waypoints]);

  /* ── 6. Detection markers (color-coded, last 15 with GPS) ── */
  useEffect(() => {
    const layer = detLayerRef.current;
    if (!layer) return;
    layer.clearLayers();

    detections
      .filter(d => d.target_lat && d.target_lon)
      .slice(0, 15)
      .forEach(d => {
        L.marker([d.target_lat, d.target_lon], { icon: detIcon(d.threat_level) })
          .bindPopup(
            `<div style="font-family:var(--font-mono);font-size:11px;">
              <div><b>${d.detection_class}</b> #${d.track_id}</div>
              <div>Conf: ${(d.confidence * 100).toFixed(0)}%</div>
              <div>IFF: ${d.iff_status}</div>
              <div>Threat: ${d.threat_level}</div>
            </div>`
          )
          .addTo(layer);
      });
  }, [detections]);

  return (
    <div className="panel" style={{ position: 'relative', padding: 0 }}>
      {/* Guaranteed pixel height — Leaflet cannot size against a flex/grid 0px box */}
      <div
        ref={containerRef}
        style={{
          height: 'calc(100vh - 60px)',
          width: '100%',
          borderRadius: 'var(--radius-lg)',
        }}
      />

      {/* Overlay: coordinates + altitude */}
      <div style={{
        position: 'absolute', bottom: 10, left: 10, zIndex: 1000,
        background: 'rgba(12,14,20,0.85)',
        border: '1px solid var(--border-default)',
        borderRadius: 'var(--radius-md)',
        padding: '6px 10px',
        fontFamily: 'var(--font-mono)',
        fontSize: 11,
        color: 'var(--text-secondary)',
        backdropFilter: 'blur(8px)',
      }}>
        {t.lat.toFixed(5)}°N, {t.lon.toFixed(5)}°E
        <span style={{ color: 'var(--accent)', marginLeft: 8 }}>
          ALT {t.alt.toFixed(1)}m
        </span>
      </div>

      {/* Overlay: compass heading */}
      <div style={{
        position: 'absolute', top: 10, right: 10, zIndex: 1000,
        background: 'rgba(12,14,20,0.85)',
        border: '1px solid var(--border-default)',
        borderRadius: '50%',
        width: 48, height: 48,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        backdropFilter: 'blur(8px)',
      }}>
        <div style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 13, fontWeight: 600,
          color: 'var(--accent)',
        }}>
          {Math.round(t.heading)}°
        </div>
      </div>
    </div>
  );
}
