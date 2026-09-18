import { contextBridge, ipcRenderer } from 'electron';
contextBridge.exposeInMainWorld('electronAPI', {
    setClickThrough: function (enabled) { return ipcRenderer.send('set-click-through', enabled); },
    minimizeWindow: function () { return ipcRenderer.send('window-minimize'); },
    closeWindow: function () { return ipcRenderer.send('window-close'); },
    onNotchStateChange: function (callback) {
        ipcRenderer.on('notch-state-change', function (_event, state) { return callback(state); });
        return function () { return ipcRenderer.removeAllListeners('notch-state-change'); };
    },
});
