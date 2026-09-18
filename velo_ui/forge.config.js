import { defineConfig } from '@electron-forge/config';
import { MakerZip } from '@electron-forge/maker-zip';
import { VitePlugin } from '@electron-forge/plugin-vite';
export default defineConfig({
    packagerConfig: {
        asar: true,
        icon: 'assets/icon.ico',
    },
    rebuildConfig: {},
    makers: [new MakerZip({ platforms: ['win32'] })],
    plugins: [
        new VitePlugin({
            build: [
                { entry: 'electron/main.ts', config: 'vite.config.ts', target: 'main' },
                { entry: 'electron/preload.ts', config: 'vite.config.ts', target: 'preload' },
            ],
            renderer: [
                { name: 'main_window', config: 'vite.config.ts' },
            ],
        }),
    ],
});
