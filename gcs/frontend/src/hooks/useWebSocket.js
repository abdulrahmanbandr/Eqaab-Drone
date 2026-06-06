import { useEffect, useRef, useCallback } from 'react';
import { useDrone } from '../context/DroneContext';

const WS_URL = `ws://${window.location.hostname}:8000/ws`;
const RECONNECT_DELAY = 2000;
const PING_INTERVAL = 3000;

export function useWebSocket() {
  const { dispatch, handleMessage } = useDrone();
  const wsRef = useRef(null);
  const pingRef = useRef(null);
  const reconnectRef = useRef(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      dispatch({ type: 'SET_CONNECTED', payload: true });
      // Start heartbeat
      pingRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }));
        }
      }, PING_INTERVAL);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleMessage(data);
      } catch (e) {
        console.warn('Invalid WS message:', e);
      }
    };

    ws.onclose = () => {
      dispatch({ type: 'SET_CONNECTED', payload: false });
      clearInterval(pingRef.current);
      // Auto-reconnect
      reconnectRef.current = setTimeout(connect, RECONNECT_DELAY);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [dispatch, handleMessage]);

  useEffect(() => {
    connect();
    return () => {
      clearInterval(pingRef.current);
      clearTimeout(reconnectRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const sendCommand = useCallback((command, params = {}) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'command', command, params }));
    }
  }, []);

  return { sendCommand };
}
