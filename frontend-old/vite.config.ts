import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      // Auto-update service worker when new content is available
      registerType: 'autoUpdate',
      // Static assets to precache
      includeAssets: ['favicon.ico', 'apple-touch-icon.png', 'mask-icon.svg'],
      manifest: {
        name: 'Flux Life Assistant',
        short_name: 'Flux',
        description: 'AI-powered life assistant that transforms goals into daily actions',
        theme_color: '#20B2AA',
        background_color: '#FFFFFF',
        display: 'standalone',
        scope: '/',
        start_url: '/',
        icons: [
          {
            src: 'pwa-192x192.png',
            sizes: '192x192',
            type: 'image/png',
          },
          {
            src: 'pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png',
          },
          {
            src: 'pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            // Enables adaptive icons on Android
            purpose: 'any maskable',
          },
        ],
      },
      devOptions: {
        // Enable PWA in dev mode for testing service worker behavior
        enabled: true,
      },
    }),
  ],
  server: {
    port: 5173,
    // Auto-open browser on dev server start
    open: true,
  },
  build: {
    outDir: 'dist',
    // Enable source maps for production debugging
    sourcemap: true,
  },
});
