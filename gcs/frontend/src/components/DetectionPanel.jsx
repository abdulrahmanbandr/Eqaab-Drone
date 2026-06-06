import { useDrone } from '../context/DroneContext';

const threatBadge = {
  LOW:      { cls: 'success', label: 'LOW' },
  MEDIUM:   { cls: 'warning', label: 'MED' },
  HIGH:     { cls: 'danger',  label: 'HIGH' },
  CRITICAL: { cls: 'danger',  label: 'CRIT' },
};

const iffStyle = {
  friendly: { color: 'var(--success)', label: 'FRIENDLY' },
  unknown:  { color: 'var(--warning)', label: 'UNKNOWN' },
  hostile:  { color: 'var(--danger)',  label: 'HOSTILE' },
};

function formatTime(ts) {
  return new Date(ts * 1000).toLocaleTimeString('en-US', { hour12: false });
}

function DetectionItem({ det }) {
  const tb = threatBadge[det.threat_level] || threatBadge.LOW;
  const iff = iffStyle[det.iff_status] || iffStyle.unknown;
  const isDrone = det.detection_class === 'drone';
  const isHighThreat = det.threat_level === 'HIGH' || det.threat_level === 'CRITICAL';

  return (
    <div style={{
      background: isHighThreat ? 'rgba(239,68,68,0.08)' : 'var(--bg-card)',
      border: `1px solid ${isHighThreat ? 'rgba(239,68,68,0.2)' : 'var(--border-subtle)'}`,
      borderRadius: 'var(--radius-md)',
      padding: '10px 12px',
      transition: 'all 0.2s',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{
            fontSize: 13, fontWeight: 600,
            color: isHighThreat ? 'var(--danger)' : 'var(--text-primary)',
            textTransform: 'capitalize',
          }}>
            {det.detection_class}
          </span>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: 10,
            color: 'var(--text-muted)',
          }}>
            #{det.track_id}
          </span>
        </div>
        <span className={`badge ${tb.cls}`}>{tb.label}</span>
      </div>

      <div style={{
        display: 'flex', gap: 12,
        fontSize: 11, color: 'var(--text-secondary)',
        fontFamily: 'var(--font-mono)',
      }}>
        <span>conf: {(det.confidence * 100).toFixed(0)}%</span>
        <span>model: {det.model_source}</span>
        {isDrone && (
          <span style={{ color: iff.color }}>IFF: {iff.label}</span>
        )}
      </div>

      {det.target_lat && (
        <div style={{
          fontSize: 10, color: 'var(--text-muted)',
          fontFamily: 'var(--font-mono)',
          marginTop: 4,
        }}>
          GPS: {det.target_lat.toFixed(4)}, {det.target_lon.toFixed(4)}
        </div>
      )}

      <div style={{
        fontSize: 10, color: 'var(--text-muted)',
        marginTop: 4,
      }}>
        {formatTime(det.timestamp)}
      </div>
    </div>
  );
}

export default function DetectionPanel() {
  const { state } = useDrone();
  const { detections } = state;

  const highCount = detections.filter(
    d => d.threat_level === 'HIGH' || d.threat_level === 'CRITICAL'
  ).length;

  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">AI Detections</span>
        <div style={{ display: 'flex', gap: 6 }}>
          <span className="badge accent" style={{ fontSize: 9 }}>
            {detections.length} total
          </span>
          {highCount > 0 && (
            <span className="badge danger" style={{ fontSize: 9 }}>
              {highCount} threats
            </span>
          )}
        </div>
      </div>
      <div className="panel-body" style={{
        display: 'flex', flexDirection: 'column', gap: 6,
        padding: 10,
      }}>
        {detections.length === 0 ? (
          <div style={{
            textAlign: 'center', padding: 20,
            color: 'var(--text-muted)', fontSize: 12,
          }}>
            No detections yet — waiting for AI feed
          </div>
        ) : (
          detections.slice(0, 20).map((det, i) => (
            <DetectionItem key={`${det.track_id}-${i}`} det={det} />
          ))
        )}
      </div>
    </div>
  );
}
