import { useEffect } from 'react';
import { useWebSocket } from './useWebSocket';
import { useNotch } from '../context/NotchContext';

export const useNotchController = () => {
  const { send } = useWebSocket();
  const { permissionQueue, resolvePermission } = useNotch();

  useEffect(() => {
    const handleResponse = (event: CustomEvent) => {
      const { id, allowed } = event.detail;
      resolvePermission(id, allowed);
      send({ type: 'permission_response', request_id: id, allowed });
    };
    window.addEventListener('permission-response', handleResponse as EventListener);
    return () => window.removeEventListener('permission-response', handleResponse as EventListener);
  }, [resolvePermission, send]);

  useEffect(() => {
    if (permissionQueue.length === 0) return;
    // Auto-deny after 30 seconds
    const timer = setTimeout(() => {
      resolvePermission(permissionQueue[0].id, false);
      send({ type: 'permission_response', request_id: permissionQueue[0].id, allowed: false });
    }, 30000);
    return () => clearTimeout(timer);
  }, [permissionQueue, resolvePermission, send]);
};