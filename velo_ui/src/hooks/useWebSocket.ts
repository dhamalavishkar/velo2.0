import { useEffect, useRef, useCallback, useState } from 'react';
import type { WSMessage } from '../types/notch';
import { useNotch } from '../context/NotchContext';

export const useWebSocket = () => {
  const { 
    setState, 
    setTranscription, 
    addPermissionRequest, 
    setToolStatus,
    showNotification,
    triggerActivation
  } = useNotch();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const [connected, setConnected] = useState(false);
  const url = (import.meta as any).env?.VITE_WS_URL || 'ws://localhost:8000/ws';

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('[WS] Connected');
        setConnected(true);
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = null;
        }
      };

      ws.onmessage = (event) => {
        try {
          const message: WSMessage = JSON.parse(event.data);
          handleMessage(message);
        } catch (e) {
          console.error('[WS] Parse error:', e);
        }
      };

      ws.onclose = () => {
        console.log('[WS] Disconnected');
        setConnected(false);
        scheduleReconnect();
      };

      ws.onerror = (error) => {
        console.error('[WS] Error:', error);
      };
    } catch (e) {
      console.error('[WS] Connection failed:', e);
      scheduleReconnect();
    }
  }, [url]);

  const scheduleReconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) return;
    reconnectTimeoutRef.current = window.setTimeout(() => {
      reconnectTimeoutRef.current = null;
      connect();
    }, 3000);
  }, [connect]);

  const handleMessage = (message: WSMessage) => {
    switch (message.type) {
      case 'notch_state':
        setState(message.state);
        break;
      case 'transcription':
        setTranscription(message.text, message.final);
        break;
      case 'permission_request':
        addPermissionRequest({
          id: message.id,
          tool: message.tool,
          args: message.args,
          risk: message.risk,
          description: `Execute ${message.tool}?`,
          timestamp: Date.now(),
        });
        break;
      case 'tool_call':
        setToolStatus({
          id: message.id,
          tool: message.tool,
          status: 'executing',
        });
        break;
      case 'tool_result':
        setToolStatus({
          id: message.request_id,
          tool: '',
          status: message.success ? 'success' : 'error',
          output: message.output,
          error: message.error,
        });
        setTimeout(() => setToolStatus(null), 3000);
        break;
      case 'notification':
        showNotification({
          id: message.id,
          summary: message.summary,
          sentiment: message.sentiment,
          timestamp: Date.now(),
        });
        break;
      case 'activation':
        triggerActivation(message.phrase);
        break;
      case 'error':
        console.error('[WS] Server error:', message.message);
        break;
    }
  };

  const send = useCallback((message: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    wsRef.current?.close();
    wsRef.current = null;
    setConnected(false);
  }, []);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return { send, connected };
};

export const usePermissionHandler = () => {
  useEffect(() => {
    const handleResponse = (event: CustomEvent<{ id: string; allowed: boolean }>) => {
      void event;
    };
    window.addEventListener('permission-response', handleResponse as EventListener);
    return () => window.removeEventListener('permission-response', handleResponse as EventListener);
  }, []);
};