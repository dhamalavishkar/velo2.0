import { useEffect, useRef, useCallback, useState } from 'react';
import type { WSMessage } from '../types/notch';
import { useNotch } from '../context/NotchContext';

export const useWebSocket = () => {
  const {
    setState,
    setTranscription,
    addPermissionRequest,
    resolvePermission,
    setToolStatus,
    showNotification,
    triggerActivation,
  } = useNotch();

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const [connected, setConnected] = useState(false);
  const url = (import.meta as any).env?.VITE_WS_URL || 'ws://localhost:8000/ws';

  const send = useCallback((message: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
      return true;
    }
    return false;
  }, []);

  const sendPermissionResponse = useCallback(
    (id: string, allowed: boolean) => {
      send({ type: 'permission_response', request_id: id, allowed });
      resolvePermission(id, allowed);
    },
    [send, resolvePermission]
  );

  const handleMessage = useCallback(
    (message: WSMessage) => {
      switch (message.type) {
        case 'notch_state':
          setState(message.state as any);
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
            description: message.description,
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
          // Clear after 4s
          setTimeout(() => setToolStatus(null), 4000);
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
        default:
          console.debug('[WS] Unhandled message type:', (message as any).type);
      }
    },
    [setState, setTranscription, addPermissionRequest, setToolStatus, showNotification, triggerActivation]
  );

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('[WS] Connected to VELO backend');
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
        console.log('[WS] Disconnected — reconnecting in 3s...');
        setConnected(false);
        scheduleReconnect();
      };

      ws.onerror = (error) => {
        console.error('[WS] Connection error:', error);
      };
    } catch (e) {
      console.error('[WS] Failed to connect:', e);
      scheduleReconnect();
    }
  }, [url, handleMessage]);

  const scheduleReconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) return;
    reconnectTimeoutRef.current = window.setTimeout(() => {
      reconnectTimeoutRef.current = null;
      connect();
    }, 3000);
  }, [connect]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
    wsRef.current?.close();
    wsRef.current = null;
    setConnected(false);
  }, []);

  // Wire permission-response custom events to WebSocket send
  useEffect(() => {
    const handlePermEvent = (event: CustomEvent<{ id: string; allowed: boolean }>) => {
      sendPermissionResponse(event.detail.id, event.detail.allowed);
    };
    window.addEventListener('permission-response', handlePermEvent as EventListener);
    return () => window.removeEventListener('permission-response', handlePermEvent as EventListener);
  }, [sendPermissionResponse]);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return { send, connected, sendPermissionResponse };
};

/**
 * Hook for submitting text input from UI without wake word.
 * Sends {type: "user_input", text} over WebSocket.
 */
export const useTextInput = (send: (msg: object) => boolean) => {
  const submit = useCallback(
    (text: string) => {
      if (!text.trim()) return false;
      return send({ type: 'user_input', text: text.trim() });
    },
    [send]
  );
  return { submit };
};

/** @deprecated - permission events now handled in useWebSocket */
export const usePermissionHandler = () => {};