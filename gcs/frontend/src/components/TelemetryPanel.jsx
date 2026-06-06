import { useDrone } from '../context/DroneContext';

function MetricCard({ label, value, unit, color }) {
  return (
    <div className="metric">
      <div className="metric-label">{label}</div>
      <div className="metric-value" style={color ? { color } : {}}>
        {value}
        {unit && <span className="metric-unit">{unit}</span>}
      </div>
    </div>
  );
}

function BatteryBar({ level }) {
  const color = level > 50 ? 'var(--success)' : level > 25 ? 'var(--warning)' : 'var(--danger)';
  return (
    <div className="metric" style={{ gridColumn: 'span 2' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
        <span className="metric-label" style={{ margin: 0 }}>Battery</span>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 14, fontWeight: 600, color }}>
          {level.toFixed(1)}%
        </span>
      </div>
      <div style={{
        height: 6, borderRadius: 3,
        background: 'var(--bg-elevated)',
        overflow: 'hidden',
      }}>
        <div style={{
          height: '100%', borderRadius: 3,
          width: `${Math.min(100, Math.max(0, level))}%`,
          background: color,
          transition: 'width 0.5s ease, background 0.5s ease',
        }} />
      </div>
    </div>
  );
}

export default function TelemetryPanel() {
  const { state } = useDrone();
  const t = state.telemetry;

  const speedColor = t.speed > 10 ? 'var(--warning)' : 'var(--text-primary)';
  const altColor = t.alt > 0 ? 'var(--accent-text)' : 'var(--text-primary)';
  const vsColor = t.vertical_speed > 0.5 ? 'var(--success)' :
                  t.vertical_speed < -0.5 ? 'var(--danger)' : 'var(--text-primary)';

  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">Telemetry</span>
        <span style={{
          fontSize: 10, fontFamily: 'var(--font-mono)',
          color: 'var(--text-muted)',
        }}>
          2 Hz
        </span>
      </div>
      <div className="panel-body" style={{ padding: 10 }}>
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 8,
        }}>
          <MetricCard label="Altitude" value={t.alt.toFixed(1)} unit="m" color={altColor} />
          <MetricCard label="Speed" value={t.speed.toFixed(1)} unit="m/s" color={speedColor} />
          <MetricCard label="V/S" value={(t.vertical_speed >= 0 ? '+' : '') + t.vertical_speed.toFixed(1)} unit="m/s" color={vsColor} />
          <MetricCard label="Heading" value={Math.round(t.heading)} unit="°" />
          <MetricCard label="GPS fix" value={t.gps_fix === 3 ? '3D' : t.gps_fix === 2 ? '2D' : 'None'}
            color={t.gps_fix === 3 ? 'var(--success)' : 'var(--danger)'} />
          <MetricCard label="Voltage" value={t.voltage.toFixed(1)} unit="V" />
          <BatteryBar level={t.battery} />
        </div>
      </div>
    </div>
  );
}
