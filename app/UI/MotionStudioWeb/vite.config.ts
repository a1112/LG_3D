import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      // 代理到 FastAPI 后端（端口 5010）
      // 移除 /api 前缀，因为后端路径不带 /api
      '/api': {
        target: 'http://127.0.0.1:5010',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      '/ws': {
        target: 'ws://127.0.0.1:5010',
        ws: true,
      },
    },
  },
})
