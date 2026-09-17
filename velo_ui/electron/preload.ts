import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('electronAPI', {
  setClickThrough: (enabled: boolean) => ipcRenderer.send('set-click-through', enabled),
  minimizeWindow: () => ipcRenderer.send('window-minimize'),
  closeWindow: () => ipcRenderer.send('window-close'),
  onNotchStateChange: (callback: (state: string) => void) => {
    ipcRenderer.on('notch-state-change', (_event, state: string) => callback(state));
    return () => ipcRenderer.removeAllListeners('notch-state-change');
  },
});