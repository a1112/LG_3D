import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const host = env.TAURI_DEV_HOST || process.env.TAURI_DEV_HOST
  const apiProxyTarget = env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:5011'
  const imageProxyTarget = env.VITE_IMAGE_PROXY_TARGET || apiProxyTarget
  const wsProxyTarget =
    env.VITE_WS_PROXY_TARGET ||
    apiProxyTarget.replace(/^http:\/\//, 'ws://').replace(/^https:\/\//, 'wss://')

  return {
    plugins: [react()],
    clearScreen: false,
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port: 3015,
      strictPort: true,
      host: host || false,
      hmr: host
        ? {
            protocol: 'ws',
            host,
            port: 3016,
          }
        : undefined,
      watch: {
        ignored: ['**/src-tauri/**'],
      },
      proxy: {
        // Main API proxy; .env.development can point this at Rust API 5011.
        '/api': {
          target: apiProxyTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
        // Image API can point separately at the Rust image service 6013.
        '/image-api': {
          target: imageProxyTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/image-api/, ''),
        },
        '/ws': {
          target: wsProxyTarget,
          ws: true,
        },
      },
    },
  }
})
