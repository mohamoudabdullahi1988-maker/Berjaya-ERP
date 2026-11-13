// Validation output stays inside this workstream's frontend directory.
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import frappeui from 'frappe-ui/vite'
export default defineConfig({ plugins: [frappeui({ frontendRoute: '/berjaya', buildConfig: { outDir: '.verify/assets', indexHtmlPath: '.verify/berjaya.html', baseUrl: '/assets/sidra_realestate/berjaya/' } }), vue()] })
