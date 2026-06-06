import { useEffect, useRef, useMemo } from 'react';
import { MapContainer, TileLayer, Marker, Polyline, Polygon, CircleMarker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import { useDrone } from '../context/DroneContext';

/* ── Drone icon (orange triangle) ── */
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

/* ── Home icon ── */
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

/* ── Waypoint icon ── */
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

/* ── Detection marker ── */
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

/* ── Map auto-follow ── */
function MapFollow({ lat, lon }) {
  const map = useMap();
  const initialized = useRef(false);
  useEffect(() => {
    if (lat && lon && !initialized.current) {
      map.setView([lat, lon], 16);
      initialized.current = true;
    }
  }, [map, lat, lon]);
  return null;
}

export default function MapPanel() {
  const { state } = useDrone();
  const { telemetry: t, trail, config: cfg, detections } = state;

  const droneIcon = useMemo(() => createDroneIcon(t.heading), [t.heading]);

  const geofencePositions = cfg.geofence.map(p => [p.lat, p.lon]);
  const trailPositions = trail.map(p => [p.lat, p.lon]);

  // Recent detections with GPS (last 15)
  const detMarkers = detections
    .filter(d => d.target_lat && d.target_lon)
    .slice(0, 15);

  return (
    <div className="panel" style={{ position: 'relative' }}>
      <MapContainer
        center={[cfg.home_lat, cfg.home_lon]}
        zoom={16}
        style={{ height: '100%', width: '100%', borderRadius: 'var(--radius-lg)' }}
        zoomControl={false}
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; OSM'
        />
        <MapFollow lat={t.lat} lon={t.lon} />

        {/* Geofence polygon */}
        {geofencePositions.length > 0 && (
          <Polygon
            positions={geofencePositions}
            pathOptions={{
              color: '#f97316', weight: 1.5, opacity: 0.6,
              fillColor: '#f97316', fillOpacity: 0.04,
              dashArray: '8 4',
            }}
          />
        )}

        {/* Flight trail */}
        {trailPositions.length > 1 && (
          <Polyline
            positions={trailPositions}
            pathOptions={{
              color: '#f97316', weight: 2, opacity: 0.5,
            }}
          />
        )}

        {/* Patrol waypoints */}
        {cfg.patrol_waypoints.map((wp, i) => (
          <Marker key={`wp-${i}`} position={[wp.lat, wp.lon]} icon={wpIcon(i)}>
            <Popup>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11 }}>
                WP{i + 1}: {wp.alt}m
              </span>
            </Popup>
          </Marker>
        ))}

        {/* Home marker */}
        <Marker position={[cfg.home_lat, cfg.home_lon]} icon={homeIcon}>
          <Popup>Home / Launch Point</Popup>
        </Marker>

        {/* Detection markers */}
        {detMarkers.map((d, i) => (
          <Marker
            key={`det-${d.track_id}-${i}`}
            position={[d.target_lat, d.target_lon]}
            icon={detIcon(d.threat_level)}
          >
            <Popup>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11 }}>
                <div><b>{d.detection_class}</b> #{d.track_id}</div>
                <div>Conf: {(d.confidence * 100).toFixed(0)}%</div>
                <div>IFF: {d.iff_status}</div>
                <div>Threat: {d.threat_level}</div>
              </div>
            </Popup>
          </Marker>
        ))}

        {/* Drone marker */}
        <Marker position={[t.lat, t.lon]} icon={droneIcon} />
      </MapContainer>

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
