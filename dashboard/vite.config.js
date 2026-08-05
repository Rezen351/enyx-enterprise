import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// The dashboard talks to the backend through the Kong API Gateway.
// By default the API client calls Kong directly (VITE_API_URL, default
// http://localhost:8000) and relies on Kong's CORS plugin. The proxy below
// is an optional dev fallback if you prefer same-origin requests.
const KONG_URL = process.env.VITE_API_URL || 'http://localhost:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    allowedHosts: true,
    proxy: {
      '/v1': { target: KONG_URL, changeOrigin: true, ws: true },
      '/auth': { target: KONG_URL, changeOrigin: true },
      '/health': { target: KONG_URL, changeOrigin: true },
      '/modules': { target: KONG_URL, changeOrigin: true },
      '/nodes': { target: KONG_URL, changeOrigin: true },
      '/analytics': { target: KONG_URL, changeOrigin: true },
      '/control': { target: KONG_URL, changeOrigin: true },
      '/audit': { target: KONG_URL, changeOrigin: true },
      '/alerts': { target: KONG_URL, changeOrigin: true },
      '/thresholds': { target: KONG_URL, changeOrigin: true },
      '/streams': { target: KONG_URL, changeOrigin: true },
      '/snapshots': { target: KONG_URL, changeOrigin: true },
      '/ml': { target: KONG_URL, changeOrigin: true },
      '/notifications': { target: KONG_URL, changeOrigin: true },
      '/hls': {
        target: KONG_URL,
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on('proxyRes', (proxyRes) => {
            const loc = proxyRes.headers['location'] || proxyRes.headers['Location'];
            if (loc && typeof loc === 'string' && loc.startsWith('/') && !loc.startsWith('/hls')) {
              proxyRes.headers['location'] = '/hls' + loc;
            }
          });
        },
      },
      '^/.*\\.m3u8': {
        target: KONG_URL,
        changeOrigin: true,
        rewrite: (path) => path.startsWith('/hls') ? path : '/hls' + path,
      },
      '^/.*\\.ts': {
        target: KONG_URL,
        changeOrigin: true,
        rewrite: (path) => path.startsWith('/hls') ? path : '/hls' + path,
      },
      '^/.*\\.mp4': {
        target: KONG_URL,
        changeOrigin: true,
        rewrite: (path) => path.startsWith('/hls') ? path : '/hls' + path,
      },
      // WebSocket live telemetry bridge (wsgateway behind Kong).
      // `ws: true` lets Vite forward the WebSocket upgrade handshake so the
      // dashboard's live MQTT monitor works against the dev server on :5173.
      '/ws': {
        target: KONG_URL,
        changeOrigin: true,
        ws: true,
      },
      // MinIO object storage — serves snapshot/recording/images. The
      // Stream Service proxies /storage through Kong using its scoped
      // MinIO credentials, so the bucket stays private (no public-read).
      // /storage/{bucket}/{key}  ->  Kong -> stream:8080 -> MinIO
      '/storage': {
        target: KONG_URL,
        changeOrigin: true,
      },
      // Mirrors the Aeroponik-Docker nginx `/live/` → mediamtx:8888 proxy.
      // /live/{name}/  ->  mediamtx:8888/{name}/
      //
      // MediaMTX v1.18+ performs an HLS cookie/session check that answers the
      // first manifest request with a 302 whose `Location` is ROOT-relative
      // (e.g. `/cctv-1/index.m3u8?cookieCheck=1`), dropping the `/live` prefix.
      // Without rewriting it, the browser follows the redirect to
      // `localhost:5173/cctv-1/...` (not proxied) and hls.js fails with
      // "EXTM3U delimiter error". We re-add the `/live` prefix to every
      // relative Location, exactly like nginx `proxy_redirect / /live/`.
      '/live': {
        target: 'http://mediamtx:8888',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/live/, ''),
        configure: (proxy) => {
          proxy.on('proxyRes', (proxyRes) => {
            const loc = proxyRes.headers['location'] || proxyRes.headers['Location'];
            if (loc && typeof loc === 'string' && loc.startsWith('/')) {
              proxyRes.headers['location'] = '/live' + loc;
            }
          });
        },
      },
    },
  },
})
