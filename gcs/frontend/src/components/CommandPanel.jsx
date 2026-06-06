import { useState } from 'react';
import { useDrone } from '../context/DroneContext';
import { sendCommand } from '../services/api';

export default function CommandPanel() {
  const { state } = useDrone();
  const t = state.telemetry;
  const [loading, setLoading] = useState(null);

  async function exec(command, params = {}) {
    setLoading(command);
    try {
      await sendCommand(command, params);
    } catch (e) {
      console.error('Command failed:', e);
    }
    setTimeout(() => setLoading(null), 600);
  }

  const isIdle = t.drone_state === 'IDLE' || t.drone_state === 'LANDED';
  const isArmed = t.armed;
  const isAirborne = t.alt > 1;
  const isFlying = t.drone_state === 'FLYING';

  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">Commands</span>
        {loading && (
          <span style={{
            fontSize: 10, color: 'var(--accent)',
            fontFamily: 'var(--font-mono)',
          }}>
            Sending...
          </span>
        )}
      </div>
      <div className="panel-body" style={{ padding: 10 }}>
        {/* Primary flight commands */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 6,
          marginBottom: 10,
        }}>
          <button
            className={`cmd-btn ${!isArmed ? 'success' : ''}`}
            disabled={isArmed || loading}
            onClick={() => exec('arm')}
          >
            {loading === 'arm' ? '...' : 'ARM'}
          </button>
          <button
            className={`cmd-btn ${isArmed && !isAirborne ? 'danger' : ''}`}
            disabled={!isArmed || isAirborne || loading}
            onClick={() => exec('disarm')}
          >
            {loading === 'disarm' ? '...' : 'DISARM'}
          </button>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 6,
          marginBottom: 10,
        }}>
          <button
            className="cmd-btn primary"
            disabled={!isArmed || isAirborne || loading}
            onClick={() => exec('takeoff', { altitude: 15 })}
          >
            {loading === 'takeoff' ? '...' : 'TAKEOFF'}
          </button>
          <button
            className="cmd-btn danger"
            disabled={!isAirborne || loading}
            onClick={() => exec('land')}
          >
            {loading === 'land' ? '...' : 'LAND'}
          </button>
        </div>

        {/* Emergency RTL */}
        <button
          className="cmd-btn danger"
          style={{
            width: '100%', marginBottom: 10,
            fontSize: 13, padding: '10px 16px',
            border: '1.5px solid rgba(239,68,68,0.4)',
          }}
          disabled={!isArmed || loading}
          onClick={() => exec('rtl')}
        >
          {loading === 'rtl' ? '...' : 'RETURN TO LAUNCH'}
        </button>

        {/* Mission commands */}
        <div style={{
          borderTop: '1px solid var(--border-subtle)',
          paddingTop: 10,
          marginBottom: 8,
        }}>
          <div className="panel-title" style={{ marginBottom: 8 }}>Mission</div>
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr 1fr',
            gap: 6,
          }}>
            <button
              className="cmd-btn"
              disabled={!isArmed || loading}
              onClick={() => exec('start_mission')}
            >
              START
            </button>
            <button
              className="cmd-btn"
              disabled={!isFlying || loading}
              onClick={() => exec('pause_mission')}
            >
              PAUSE
            </button>
            <button
              className="cmd-btn"
              disabled={!isFlying || loading}
              onClick={() => exec('hold')}
            >
              HOLD
            </button>
          </div>
        </div>

        {/* Speed control */}
        <div style={{
          borderTop: '1px solid var(--border-subtle)',
          paddingTop: 10,
        }}>
          <div style={{
            display: 'flex', justifyContent: 'space-between',
            alignItems: 'center', marginBottom: 6,
          }}>
            <span className="panel-title">Speed</span>
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: 12,
              color: 'var(--accent-text)',
            }}>
              {t.speed.toFixed(1)} m/s
            </span>
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            {[3, 5, 8, 12].map(s => (
              <button
                key={s}
                className="cmd-btn"
                style={{ flex: 1, fontSize: 11 }}
                disabled={!isFlying || loading}
                onClick={() => exec('set_speed', { speed: s })}
              >
                {s} m/s
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
