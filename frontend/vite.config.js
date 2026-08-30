import { fileURLToPath, URL } from 'node:url'

import { quasar, transformAssetUrls } from '@quasar/vite-plugin'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [
    vue({ template: { transformAssetUrls } }),
    quasar({ sassVariables: fileURLToPath(new URL('./src/quasar-variables.sass', import.meta.url)) }),
  ],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    port: 5173,
    // El dev server proxea TODAS las rutas del backend para que el navegador
    // hable siempre con un mismo origen: así no hace falta CORS y la cookie de
    // sesión de Django viaja sin configuración extra.
    //
    // El target sale del entorno porque cambia según dónde corra Vite: en
    // Docker el backend es el servicio `backend`, fuera es localhost.
    proxy: Object.fromEntries(
      ['/sinpapel', '/salud', '/reports', '/admin', '/static'].map((ruta) => [
        ruta,
        { target: process.env.VITE_PROXY_TARGET || 'http://localhost:8000', changeOrigin: true },
      ]),
    ),
  },
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['tests/**/*.test.js'],
  },
})
