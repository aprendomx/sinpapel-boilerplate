import { Quasar } from 'quasar'
import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from '@/App.vue'
import { router } from '@/router'

import '@quasar/extras/material-icons/material-icons.css'
import 'quasar/src/css/index.sass'
// Sin este import los widgets de seguimiento se pintan sin estilos.
import '@aprendomx/sinpapel-vue/style.css'

createApp(App).use(createPinia()).use(router).use(Quasar).mount('#app')
