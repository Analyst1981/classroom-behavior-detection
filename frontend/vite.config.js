import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

const backend = process.env.VITE_BACKEND_URL || 'http://127.0.0.1:8080'
const aiService = process.env.VITE_AI_URL || 'http://127.0.0.1:5000'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      // 业务接口统一走 Spring Boot
      '/api': { target: backend, changeOrigin: true },
      // MJPEG 实时流走 Spring Boot 代理（后端再转发 Flask）
      '/static': { target: aiService, changeOrigin: true, ws: false }
    }
  },
  build: {
    outDir: 'dist',
    chunkSizeWarningLimit: 1500
  }
})
