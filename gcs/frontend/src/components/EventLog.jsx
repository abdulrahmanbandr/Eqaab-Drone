import { useDrone } from '../context/DroneContext';

const categoryColor = {
  command:   'var(--accent-text)',
  detection: 'var(--warning)',
  system:    'var(--info)',
  alert:     'var(--danger)',
};

function formatTime(ts) {
  return new Date(ts * 1000).toLocaleTimeString('en-US', { hour12: false });
}

export default function EventLog() {
  const { state } = useDrone();
  const { events } = state;

  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">Event log</span>
        <span style={{
          fontSize: 10, fontFamily: 'var(--font-mono)',
          color: 'var(--text-muted)',
        }}>
          {events.length} entries
        </span>
      </div>
      <div className="panel-body" style={{
        padding: '8px 12px',
        fontFamily: 'var(--font-mono)',
        fontSize: 11,
        lineHeight: 1.7,
      }}>
        {events.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 16 }}>
            Waiting for events...
          </div>
        ) : (
          events.map((evt, i) => (
            <div key={i} style={{
              display: 'flex', gap: 8,
              opacity: i === 0 ? 1 : Math.max(0.4, 1 - i * 0.04),
            }}>
              <span style={{ color: 'var(--text-muted)', flexShrink: 0 }}>
                {formatTime(evt.timestamp)}
              </span>
              <span style={{
                color: categoryColor[evt.category] || 'var(--text-secondary)',
                wordBreak: 'break-word',
              }}>
                {evt.message}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
