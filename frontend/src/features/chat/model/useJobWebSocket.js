import { useState, useEffect, useRef, useCallback } from 'react';

const MAX_RECONNECT_ATTEMPTS = 5;
const INITIAL_RECONNECT_DELAY_MS = 1000;
const MAX_RECONNECT_DELAY_MS = 30000;

function buildJobWsUrl(jobId, lastId) {
  const rawBase =
    import.meta.env?.VITE_WS_BASE_URL ||
    import.meta.env?.VITE_API_BASE_URL ||
    '';

  let base = rawBase.trim().replace(/\/$/, '');
  if (!base) {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    base = `${proto}//${window.location.host}`;
  } else if (base.startsWith('http://')) {
    base = `ws://${base.slice(7)}`;
  } else if (base.startsWith('https://')) {
    base = `wss://${base.slice(8)}`;
  }

  const params = lastId ? `?last_id=${encodeURIComponent(lastId)}` : '';
  return `${base}/api/jobs/v1/${jobId}/ws${params}`;
}

/**
 * useJobWebSocket — connects to /api/jobs/v1/{jobId}/ws and streams job events.
 *
 * @param {string|null} jobId
 * @param {Object} callbacks
 * @param {function} callbacks.onEvent - called with each parsed event payload
 * @param {function} callbacks.onHeartbeat - called on heartbeat
 * @param {function} callbacks.onError - called on error
 * @param {function} callbacks.onConnect
 * @param {function} callbacks.onDisconnect
 */
export function useJobWebSocket(jobId, callbacks = {}) {
  const [isConnected, setIsConnected] = useState(false);
  const [connectionState, setConnectionState] = useState('disconnected');

  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectDelayRef = useRef(INITIAL_RECONNECT_DELAY_MS);
  const connectingRef = useRef(false);
  const prevJobIdRef = useRef(null);
  const lastIdRef = useRef(null);
  const connectRef = useRef(null);

  const { onEvent, onHeartbeat, onError, onConnect, onDisconnect } = callbacks;

  const scheduleReconnect = useCallback(() => {
    if (reconnectAttemptsRef.current >= MAX_RECONNECT_ATTEMPTS) return;
    reconnectAttemptsRef.current += 1;
    const delay = reconnectDelayRef.current;
    reconnectDelayRef.current = Math.min(delay * 2, MAX_RECONNECT_DELAY_MS);
    reconnectTimeoutRef.current = setTimeout(() => connectRef.current?.(), delay);
  }, []);

  const connect = useCallback(() => {
    if (connectingRef.current || !jobId) return;
    if (wsRef.current?.readyState === WebSocket.OPEN || wsRef.current?.readyState === WebSocket.CONNECTING) return;

    connectingRef.current = true;
    setConnectionState('connecting');

    setTimeout(() => {
      if (!connectingRef.current) return;
      try {
        const wsUrl = buildJobWsUrl(jobId, lastIdRef.current);
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          setIsConnected(true);
          setConnectionState('connected');
          reconnectAttemptsRef.current = 0;
          reconnectDelayRef.current = INITIAL_RECONNECT_DELAY_MS;
          connectingRef.current = false;
          onConnect?.(jobId);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.id) lastIdRef.current = data.id;
            if (data.type === 'heartbeat') {
              onHeartbeat?.();
            } else {
              onEvent?.(data);
            }
          } catch (err) {
            onError?.(err);
          }
        };

        ws.onclose = (event) => {
          setIsConnected(false);
          setConnectionState('disconnected');
          connectingRef.current = false;
          onDisconnect?.(event);
          if (event.code !== 1000 && reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
            scheduleReconnect();
          }
        };

        ws.onerror = () => {
          setConnectionState('error');
          connectingRef.current = false;
          onError?.(new Error('Job WebSocket connection error'));
        };
      } catch (err) {
        setConnectionState('error');
        connectingRef.current = false;
        onError?.(err);
      }
    }, 50);
  }, [jobId, onEvent, onHeartbeat, onError, onConnect, onDisconnect, scheduleReconnect]);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  const disconnect = useCallback(() => {
    wsRef.current?.close(1000, 'Manual disconnect');
  }, []);

  // Connect when jobId changes
  useEffect(() => {
    const jobChanged = prevJobIdRef.current !== jobId;
    if (jobId && jobChanged) {
      connectingRef.current = false;
      setConnectionState('disconnected');
      setIsConnected(false);
      lastIdRef.current = null;
      connectRef.current?.();
    }
    prevJobIdRef.current = jobId;

    return () => {
      wsRef.current?.close(1000, 'Job ID changed');
      wsRef.current = null;
      connectingRef.current = false;
    };
  }, [jobId]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      wsRef.current?.close(1000, 'Component unmount');
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      connectingRef.current = false;
    };
  }, []);

  return {
    isConnected,
    connectionState,
    disconnect,
    reconnectAttempts: reconnectAttemptsRef.current,
  };
}
