import { useEffect, useRef, useState, useCallback } from 'react';
import type { DashboardState, ControlOverride, WarehouseControlOverride } from '../types';

const getWsUrl = () => {
  if (import.meta.env.VITE_WS_URL) return import.meta.env.VITE_WS_URL;
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return 'ws://localhost:8000/ws';
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}/ws`;
};

const getApiUrl = () => {
  if (import.meta.env.VITE_API_URL) return import.meta.env.VITE_API_URL;
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return 'http://localhost:8000';
  }
  return `${window.location.protocol}//${window.location.host}`;
};

const WS_URL = getWsUrl();
const API_URL = getApiUrl();

export function useWebSocket() {
  const [state, setState] = useState<DashboardState | null>(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef(0);

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        reconnectRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as DashboardState;
          setState(data);
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };

      ws.onclose = () => {
        setConnected(false);
        const delay = Math.min(5000, 1000 * Math.pow(2, reconnectRef.current));
        reconnectRef.current += 1;
        setTimeout(connect, delay);
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      const delay = Math.min(5000, 1000 * Math.pow(2, reconnectRef.current));
      reconnectRef.current += 1;
      setTimeout(connect, delay);
    }
  }, []);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
    };
  }, [connect]);

  const selectShipment = useCallback(async (shipmentId: string) => {
    try {
      await fetch(`${API_URL}/api/select/${shipmentId}`, { method: 'POST' });
    } catch (e) {
      console.error('Failed to select shipment:', e);
    }
  }, []);

  const setScenario = useCallback(async (scenario: string) => {
    try {
      await fetch(`${API_URL}/api/scenario/${scenario}`, { method: 'POST' });
    } catch (e) {
      console.error('Failed to set scenario:', e);
    }
  }, []);

  const applyIntervention = useCallback(async (shipmentId: string) => {
    try {
      await fetch(`${API_URL}/api/intervene/${shipmentId}`, { method: 'POST' });
    } catch (e) {
      console.error('Failed to apply intervention:', e);
    }
  }, []);

  const sendControl = useCallback(async (shipmentId: string, overrides: ControlOverride) => {
    try {
      await fetch(`${API_URL}/api/control/${shipmentId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(overrides),
      });
    } catch (e) {
      console.error('Failed to send control:', e);
    }
  }, []);

  const sendWarehouseControl = useCallback(async (warehouseId: string, overrides: WarehouseControlOverride) => {
    try {
      await fetch(`${API_URL}/api/warehouse/${warehouseId}/control`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(overrides),
      });
    } catch (e) {
      console.error('Failed to send warehouse control:', e);
    }
  }, []);

  return {
    state,
    connected,
    selectShipment,
    setScenario,
    applyIntervention,
    sendControl,
    sendWarehouseControl,
  };
}
