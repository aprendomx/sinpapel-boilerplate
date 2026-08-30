import * as quasar from 'quasar'
import { Quasar } from 'quasar'
import { config } from '@vue/test-utils'

// En el build real, @quasar/vite-plugin auto-importa cada componente q-* que
// aparece en un template. Ese transform no aplica al montar componentes desde
// un test, y un componente sin resolver no falla: Vue lo pinta como elemento
// desconocido y descarta sus slots con nombre. El síntoma es un wrapper vacío
// sin ningún error, así que se registran a mano.
const componentes = Object.fromEntries(
  Object.entries(quasar).filter(([nombre]) => /^Q[A-Z]/.test(nombre)),
)

config.global.plugins = [[Quasar, { components: componentes }]]

// jsdom no implementa estas dos y Quasar las usa al medir componentes.
global.ResizeObserver =
  global.ResizeObserver ||
  class {
    observe() {}
    unobserve() {}
    disconnect() {}
  }

if (!window.matchMedia) {
  window.matchMedia = (query) => ({
    matches: false,
    media: query,
    addEventListener() {},
    removeEventListener() {},
  })
}
