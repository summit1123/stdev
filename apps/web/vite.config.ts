import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    allowedHosts: ['diary-app.summit1123.co.kr', 'app.summit1123.co.kr'],
  },
  preview: {
    allowedHosts: ['diary-app.summit1123.co.kr', 'app.summit1123.co.kr'],
  },
})
