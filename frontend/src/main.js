import * as quasar from 'quasar'
import { Quasar } from 'quasar'
import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from '@/App.vue'
import { router } from '@/router'

import '@quasar/extras/material-icons/material-icons.css'
import 'quasar/src/css/index.sass'
// Sin este import los widgets de seguimiento se pintan sin estilos.
import '@aprendomx/sinpapel-vue/style.css'

// @quasar/vite-plugin auto-importa los componentes q-* que aparecen en NUESTROS
// .vue, pero @aprendomx/sinpapel-vue se distribuye ya compilado: sus plantillas
// resuelven los componentes por nombre en tiempo de ejecución y necesitan que
// estén registrados globalmente.
//
// Sin esto, sus q-form / q-dialog se renderizan como elementos desconocidos.
// El panel se ve casi bien —los hijos sí se pintan— pero no hay un <form>
// real, así que el botón de confirmar no envía nada y las transiciones no
// ocurren. Falla en silencio: ni un error en consola.
const componentesQuasar = Object.fromEntries(
  Object.entries(quasar).filter(([nombre]) => /^Q[A-Z]/.test(nombre)),
)

createApp(App)
  .use(createPinia())
  .use(router)
  .use(Quasar, { components: componentesQuasar })
  .mount('#app')
