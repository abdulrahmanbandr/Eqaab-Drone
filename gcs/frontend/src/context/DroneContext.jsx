import { createContext, useContext, useReducer, useCallback } from 'react';

const DroneContext = createContext(null);

const MAX_EVENTS = 80;
const MAX_DETECTIONS = 30;
const MAX_TRAIL = 200;

const initialState = {
  // Connection
  connected: false,
  lastPong: null,

  // Telemetry
  telemetry: {
    lat: 21.4858, lon: 39.1925, alt: 0, heading: 0,
    speed: 0, vertical_speed: 0,
    battery: 100, voltage: 16.8,
    gps_fix: 0, satellites: 0,
    armed: false, flight_mode: 'HOLD', drone_state: 'IDLE',
    signal_latency_ms: 0,
  },

  // Trail (array of {lat, lon})
  trail: [],

  // Detections (most recent first)
  detections: [],

  // Alerts (high-threat only)
  alerts: [],

  // Event log
  events: [],

  // Mission config (from initial_state)
  config: {
    home_lat: 21.4858,
    home_lon: 39.1925,
    geofence: [],
    patrol_waypoints: [],
    friendly_drone_ids: [],
  },
};

function reducer(state, action) {
  switch (action.type) {
    case 'SET_CONNECTED':
      return { ...state, connected: action.payload };

    case 'TELEMETRY': {
      const t = action.payload;
      const newTrail = [...state.trail, { lat: t.lat, lon: t.lon }];
      if (newTrail.length > MAX_TRAIL) newTrail.shift();
      return {
        ...state,
        telemetry: { ...state.telemetry, ...t },
        trail: newTrail,
      };
    }

    case 'DETECTION': {
      const dets = [action.payload, ...state.detections];
      if (dets.length > MAX_DETECTIONS) dets.pop();
      return { ...state, detections: dets };
    }

    case 'ALERT': {
      const alerts = [action.payload, ...state.alerts];
      if (alerts.length > MAX_DETECTIONS) alerts.pop();
      return { ...state, alerts: alerts };
    }

    case 'EVENT': {
      const events = [action.payload, ...state.events];
      if (events.length > MAX_EVENTS) events.pop();
      return { ...state, events: events };
    }

    case 'COMMAND_ACK': {
      const ack = action.payload;
      const evt = {
        type: 'event',
        timestamp: ack.timestamp,
        category: 'command',
        message: `${ack.success ? '✓' : '✗'} ${ack.command}: ${ack.message}`,
      };
      const events = [evt, ...state.events];
      if (events.length > MAX_EVENTS) events.pop();
      return { ...state, events };
    }

    case 'INITIAL_STATE':
      return {
        ...state,
        config: {
          home_lat: action.payload.home_lat,
          home_lon: action.payload.home_lon,
          geofence: action.payload.geofence || [],
          patrol_waypoints: action.payload.patrol_waypoints || [],
          friendly_drone_ids: action.payload.friendly_drone_ids || [],
        },
      };

    case 'PONG':
      return { ...state, lastPong: Date.now() };

    default:
      return state;
  }
}

export function DroneProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, initialState);

  const handleMessage = useCallback((data) => {
    switch (data.type) {
      case 'telemetry':
        dispatch({ type: 'TELEMETRY', payload: data });
        break;
      case 'detection':
        dispatch({ type: 'DETECTION', payload: data });
        break;
      case 'alert':
        dispatch({ type: 'ALERT', payload: data });
        break;
      case 'event':
        dispatch({ type: 'EVENT', payload: data });
        break;
      case 'command_ack':
        dispatch({ type: 'COMMAND_ACK', payload: data });
        break;
      case 'initial_state':
        dispatch({ type: 'INITIAL_STATE', payload: data });
        break;
      case 'pong':
        dispatch({ type: 'PONG' });
        break;
    }
  }, []);

  return (
    <DroneContext.Provider value={{ state, dispatch, handleMessage }}>
      {children}
    </DroneContext.Provider>
  );
}

export function useDrone() {
  const ctx = useContext(DroneContext);
  if (!ctx) throw new Error('useDrone must be inside DroneProvider');
  return ctx;
}
