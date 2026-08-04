import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        // 用 127.0.0.1 而非 localhost：Windows 上 localhost 可能优先解析到 IPv6(::1)，
        // 而后端 uvicorn 只监听 IPv4(0.0.0.0)，会导致代理请求 503/空响应
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    }
  }
});
