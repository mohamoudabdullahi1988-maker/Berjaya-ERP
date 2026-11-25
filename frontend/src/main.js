import { createApp } from 'vue'

import '@fontsource-variable/inter'
import '@fontsource-variable/space-grotesk'
import './style.css'

import App from './App.vue'
import router from './router'
import { boot } from './boot'
import { PRODUCT_NAME } from './brand'

document.title = PRODUCT_NAME
if (boot?.favicon) {
  const icon = document.createElement('link')
  icon.rel = 'icon'
  icon.href = boot.favicon
  document.head.appendChild(icon)
}

createApp(App).use(router).mount('#app')
