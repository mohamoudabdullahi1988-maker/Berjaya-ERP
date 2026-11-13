import path from 'node:path'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import frappeui from 'frappe-ui/vite'

// Frappe's own pattern for a Vue app inside a Frappe app: the bundle is written to the app's
// public assets and the entry page to www/, where berjaya.py supplies the boot data.
// Paths are explicit so the build also runs outside a bench (clean checkout, CI lint job).
export default defineConfig({
  plugins: [
    frappeui({
      frontendRoute: '/berjaya',
      buildConfig: {
        outDir: '../sidra_realestate/public/berjaya',
        indexHtmlPath: '../sidra_realestate/www/berjaya.html',
        baseUrl: '/assets/sidra_realestate/berjaya/',
      },
    }),
    vue(),
  ],
  resolve: {
    alias: { '@': path.resolve(import.meta.dirname, 'src') },
  },
})
