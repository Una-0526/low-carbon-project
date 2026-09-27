import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 后端地址可用环境变量覆盖（默认 127.0.0.1:8000）
const API_TARGET = process.env.VITE_API_TARGET || 'http://127.0.0.1:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      // 前端开发时把 /api 请求代理到 FastAPI 后端
      '/api': {
        target: API_TARGET,
        changeOrigin: true,
      },
      // 打卡照片等静态文件
      '/uploads': {
        target: API_TARGET,
        changeOrigin: true,
      },
    },
  },
})
