import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: './', // Allows GitHub Pages to host in a subpath if needed
  build: {
    chunkSizeWarningLimit: 3000,
  }
})
