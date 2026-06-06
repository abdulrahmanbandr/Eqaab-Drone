import { DroneProvider } from './context/DroneContext';
import { useWebSocket } from './hooks/useWebSocket';
import TopBar from './components/TopBar';
import MapPanel from './components/MapPanel';
import TelemetryPanel from './components/TelemetryPanel';
import DetectionPanel from './components/DetectionPanel';
import CommandPanel from './components/CommandPanel';
import EventLog from './components/EventLog';

function Dashboard() {
  useWebSocket();

  return (
    <div style={{
      height: '100vh',
      display: 'flex',
      flexDirection: 'column',
      background: 'var(--bg-deep)',
    }}>
      <TopBar />

      <div style={{
        flex: 1,
        display: 'grid',
        gridTemplateColumns: '1fr 320px 320px',
        gridTemplateRows: '1fr 1fr',
        gap: 6,
        padding: 6,
        minHeight: 0,
      }}>
        {/* Map — full left column */}
        <div style={{ gridRow: '1 / 3' }}>
          <MapPanel />
        </div>

        {/* Telemetry — top middle */}
        <TelemetryPanel />

        {/* Commands — top right */}
        <CommandPanel />

        {/* Detections — bottom middle */}
        <DetectionPanel />

        {/* Event log — bottom right */}
        <EventLog />
      </div>
    </div>
  );
}

export default function App() {
  return (
    <DroneProvider>
      <Dashboard />
    </DroneProvider>
  );
}
