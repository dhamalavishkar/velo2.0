import { app, BrowserWindow, screen, ipcMain } from 'electron';
import { join } from 'path';
import { isDev } from './util.js';
var mainWindow = null;
var isClickThrough = true;
function createWindow() {
    var _a = screen.getPrimaryDisplay().workAreaSize, screenWidth = _a.width, screenHeight = _a.height;
    var windowWidth = 400;
    var windowHeight = 120;
    mainWindow = new BrowserWindow({
        width: windowWidth,
        height: windowHeight,
        x: Math.round((screenWidth - windowWidth) / 2),
        y: 0,
        frame: false,
        transparent: true,
        alwaysOnTop: true,
        skipTaskbar: true,
        resizable: false,
        movable: false,
        focusable: true,
        webPreferences: {
            preload: join(__dirname, 'preload.js'),
            contextIsolation: true,
            nodeIntegration: false,
            sandbox: false,
        },
    });
    setClickThrough(true);
    if (isDev()) {
        mainWindow.loadURL('http://localhost:5173');
        mainWindow.webContents.openDevTools({ mode: 'detach' });
    }
    else {
        mainWindow.loadFile(join(__dirname, '../dist/index.html'));
    }
    mainWindow.on('closed', function () {
        mainWindow = null;
    });
    mainWindow.on('blur', function () {
        if (isClickThrough)
            return;
        setClickThrough(true);
    });
}
function setClickThrough(enabled) {
    if (!mainWindow)
        return;
    isClickThrough = enabled;
    mainWindow.setIgnoreMouseEvents(enabled, { forward: true });
}
ipcMain.on('set-click-through', function (_event, enabled) {
    setClickThrough(enabled);
});
ipcMain.on('window-minimize', function () {
    mainWindow === null || mainWindow === void 0 ? void 0 : mainWindow.minimize();
});
ipcMain.on('window-close', function () {
    app.quit();
});
app.whenReady().then(function () {
    createWindow();
    app.on('activate', function () {
        if (BrowserWindow.getAllWindows().length === 0)
            createWindow();
    });
});
app.on('window-all-closed', function () {
    if (process.platform !== 'darwin')
        app.quit();
});
export { setClickThrough };
