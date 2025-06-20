import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from "@tailwindcss/vite";
// https://vite.dev/config/
export default defineConfig({
  plugins:
   [
    tailwindcss(),react()],
      server: {
    proxy: {
      // any request that starts with /api will be forwarded to localhost:5000
      '/api': {
        target: 'https://rag-chatbot-test-2.onrender.com',
        changeOrigin: true,
        secure: false,
      },
    },
  },
})
