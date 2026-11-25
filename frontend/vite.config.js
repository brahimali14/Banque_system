import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Les appels /api sont redirigés vers FastAPI (pas de problème de CORS en développement).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/setupTests.js',
  },
})
