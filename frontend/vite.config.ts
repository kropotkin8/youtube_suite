import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/market':  { target: 'http://localhost:8000', changeOrigin: true },
      '/studio':  { target: 'http://localhost:8000', changeOrigin: true },
      '/jobs':    { target: 'http://localhost:8000', changeOrigin: true },
      '/insights':{ target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
