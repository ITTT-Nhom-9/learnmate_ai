import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Chart.js (~200 KB) chỉ dùng ở SCR-07 → tách chunk riêng để không ảnh hưởng bundle chính
          chartjs: ['chart.js'],
        },
      },
    },
  },
})

