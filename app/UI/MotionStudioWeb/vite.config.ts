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
      '/api': {
        target: 'http://localhost:5010',
        changeOrigin: true,
        rewrite: (path) => path, // 保持路径不变
      },
      '/ws': {
        target: 'ws://localhost:5010',
        ws: true,
      },
    },
  },
})
