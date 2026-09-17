import { createContext, useContext, useState, useCallback, useEffect, ReactNode } from 'react';
import type { NotchState, PermissionRequest, ToolStatus, NotificationItem } from '../types/notch';

interface NotchContextType {
  state: NotchState;
  setState: (state: NotchState) => void;
  transcription: string;
  setTranscription: (text: string, final?: boolean) => void;
  permissionQueue: PermissionRequest[];
  addPermissionRequest: (request: PermissionRequest) => void;
  resolvePermission: (id: string, allowed: boolean) => void;
  toolStatus: ToolStatus | null;
  setToolStatus: (status: ToolStatus | null) => void;
  notification: NotificationItem | null;
  showNotification: (notification: NotificationItem) => void;
  hideNotification: () => void;
  activationPhrase: string | null;
  triggerActivation: (phrase: string) => void;
}

const NotchContext = createContext<NotchContextType | undefined>(undefined);

export const NotchProvider = ({ children }: { children: ReactNode }) => {
  const [state, setState] = useState<NotchState>('idle');
  const [transcription, setTranscriptionState] = useState('');
  const [permissionQueue, setPermissionQueue] = useState<PermissionRequest[]>([]);
  const [toolStatus, setToolStatus] = useState<ToolStatus | null>(null);
  const [notification, setNotification] = useState<NotificationItem | null>(null);
  const [activationPhrase, setActivationPhrase] = useState<string | null>(null);
  const [notificationTimeout, setNotificationTimeout] = useState<NodeJS.Timeout | null>(null);
  const [activationTimeout, setActivationTimeout] = useState<NodeJS.Timeout | null>(null);

  const setTranscription = useCallback((text: string, final = false) => {
    setTranscriptionState(text);
    if (final) {
      setTimeout(() => setTranscriptionState(''), 2000);
    }
  }, []);

  const addPermissionRequest = useCallback((request: PermissionRequest) => {
    setPermissionQueue(prev => [...prev, request]);
    setState('permission');
  }, []);

  const resolvePermission = useCallback((id: string, allowed: boolean) => {
    setPermissionQueue(prev => prev.filter(p => p.id !== id));
    if (permissionQueue.length <= 1) {
      setState(allowed ? 'expanded' : 'idle');
    }
  }, [permissionQueue.length]);

  const showNotification = useCallback((notif: NotificationItem) => {
    setNotification(notif);
    setState('notification');
    
    if (notificationTimeout) clearTimeout(notificationTimeout);
    const timeout = setTimeout(() => {
      hideNotification();
    }, 5000);
    setNotificationTimeout(timeout);
  }, []);

  const hideNotification = useCallback(() => {
    setNotification(null);
    if (state === 'notification') {
      setState('idle');
    }
  }, [state]);

  const triggerActivation = useCallback((phrase: string) => {
    setActivationPhrase(phrase);
    setState('activation');
    
    if (activationTimeout) clearTimeout(activationTimeout);
    const timeout = setTimeout(() => {
      setActivationPhrase(null);
      if (state === 'activation') {
        setState('listening');
      }
    }, 1500);
    setActivationTimeout(timeout);
  }, [state]);

  useEffect(() => {
    return () => {
      if (notificationTimeout) clearTimeout(notificationTimeout);
      if (activationTimeout) clearTimeout(activationTimeout);
    };
  }, [notificationTimeout, activationTimeout]);

  return (
    <NotchContext.Provider
      value={{
        state,
        setState,
        transcription,
        setTranscription,
        permissionQueue,
        addPermissionRequest,
        resolvePermission,
        toolStatus,
        setToolStatus,
        notification,
        showNotification,
        hideNotification,
        activationPhrase,
        triggerActivation,
      }}
    >
      {children}
    </NotchContext.Provider>
  );
};

export const useNotch = () => {
  const context = useContext(NotchContext);
  if (!context) throw new Error('useNotch must be used within NotchProvider');
  return context;
};