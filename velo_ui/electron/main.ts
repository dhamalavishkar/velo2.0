import { app, BrowserWindow, screen, ipcMain } from 'electron';
import { join } from 'path';
import { isDev } from './util.js';

let mainWindow: BrowserWindow | null = null;
let isClickThrough = true;

function createWindow() {
  const { width: screenWidth } = screen.getPrimaryDisplay().workAreaSize;
  const windowWidth = 460;   // slightly wider than max notch width (420) for shadows
  const windowHeight = 220;  // tall enough for permission state (160h) + glow effects

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
    // Uncomment to open devtools: mainWindow.webContents.openDevTools({ mode: 'detach' });
  } else {
    mainWindow.loadFile(join(__dirname, '../dist/index.html'));
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  mainWindow.on('blur', () => {
    if (isClickThrough) return;
    setClickThrough(true);
  });
}

function setClickThrough(enabled: boolean) {
  if (!mainWindow) return;
  isClickThrough = enabled;
  mainWindow.setIgnoreMouseEvents(enabled, { forward: true });
}

ipcMain.on('set-click-through', (_event, enabled: boolean) => {
  setClickThrough(enabled);
});

ipcMain.on('window-minimize', () => {
  mainWindow?.minimize();
});

ipcMain.on('window-close', () => {
  app.quit();
});

app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

export { setClickThrough };