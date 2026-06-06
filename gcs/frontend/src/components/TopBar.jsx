import { useDrone } from '../context/DroneContext';

export default function TopBar() {
  const { state } = useDrone();
  const { telemetry: t, connected } = state;

  const stateColor = {
    IDLE: 'var(--text-muted)',
    ARMED: 'var(--warning)',
    TAKING_OFF: 'var(--accent)',
    FLYING: 'var(--success)',
    RETURNING: 'var(--warning)',
    LANDING: 'var(--accent)',
    LANDED: 'var(--info)',
    EMERGENCY: 'var(--danger)',
  };

  return (
    <header style={{
      height: 'var(--header-h)',
      background: 'var(--bg-surface)',
      borderBottom: '1px solid var(--border-subtle)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 20px',
      flexShrink: 0,
    }}>
      {/* Left — Logo + connection */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <img
            src="/logo.png"
            alt="Eqaab Drone"
            style={{
              height: 36,
              width: 'auto',
              objectFit: 'contain',
              filter: 'brightness(0) invert(1)',
            }}
          />
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontWeight: 700,
            fontSize: 11,
            color: 'var(--text-muted)',
            letterSpacing: '0.08em',
          }}>
            GCS
          </span>
        </div>
        <div style={{
          width: 1, height: 20,
          background: 'var(--border-default)',
        }}/>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div className={`glow-dot ${connected ? 'green' : 'red'}`} />
          <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
            {connected ? 'DRONE-01 connected' : 'Disconnected'}
          </span>
        </div>
      </div>

      {/* Center — State badges */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span className={`badge ${t.armed ? 'warning' : ''}`}
          style={!t.armed ? { background: 'var(--bg-card)', color: 'var(--text-muted)' } : {}}>
          {t.armed ? 'ARMED' : 'DISARMED'}
        </span>
        <span className="badge accent">{t.flight_mode}</span>
        <span className="badge" style={{
          background: 'transparent',
          border: `1px solid ${stateColor[t.drone_state] || 'var(--text-muted)'}`,
          color: stateColor[t.drone_state] || 'var(--text-muted)',
        }}>
          {t.drone_state}
        </span>
      </div>

      {/* Right — Stats */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, fontSize: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
          <span style={{ color: 'var(--text-muted)' }}>SAT</span>
          <span style={{ fontFamily: 'var(--font-mono)', color: t.satellites >= 10 ? 'var(--success)' : 'var(--warning)' }}>
            {t.satellites}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
          <span style={{ color: 'var(--text-muted)' }}>PING</span>
          <span style={{
            fontFamily: 'var(--font-mono)',
            color: t.signal_latency_ms < 100 ? 'var(--success)' : t.signal_latency_ms < 200 ? 'var(--warning)' : 'var(--danger)',
          }}>
            {t.signal_latency_ms}ms
          </span>
        </div>
        <div style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 13, fontWeight: 500,
          color: 'var(--text-secondary)',
        }}>
          {new Date().toLocaleTimeString('en-US', { hour12: false })}
        </div>
      </div>
    </header>
  );
}
