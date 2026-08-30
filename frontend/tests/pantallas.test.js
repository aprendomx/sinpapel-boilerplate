import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { http } from '@/api/http'
import BandejaPage from '@/pages/BandejaPage.vue'
import NuevaSolicitudPage from '@/pages/NuevaSolicitudPage.vue'
import SeguimientoPage from '@/pages/SeguimientoPage.vue'

const SOLICITUD = {
  id: 42,
  folio: 'SC-2026-000042',
  estado: { nombre: 'EN_REVISION', color: '#FFA500', icono: 'fact_check' },
  solicitante: 'Ana Pérez (ana)',
  dependencia: 1,
  dependencia_nombre: 'Dirección General de Atención',
  alerta_sla: false,
  puede_evaluar_sla: false,
  metadatos: { curp: 'AEAA010101HDFXXX09', tipo_constancia: 'ESTUDIOS' },
  creado: '2026-08-30T12:00:00Z',
  actualizado: '2026-08-30T12:00:00Z',
}

const rutasNavegadas = []
const routerFalso = { push: (destino) => rutasNavegadas.push(destino) }

/** Stubs de router: las pantallas usan RouterLink vía la prop `to` de q-btn. */
const global = {
  mocks: { $router: routerFalso },
  stubs: { RouterLink: true },
}

/**
 * Monta una pantalla dentro de un layout de Quasar.
 *
 * `q-page` exige un `QPageContainer` como ancestro: fuera de él Quasar no
 * renderiza nada y el wrapper sale vacío, sin error visible.
 */
function montarPagina(componente, props = {}) {
  const anfitrion = {
    components: { Pagina: componente },
    props: Object.keys(props),
    template: `
      <q-layout>
        <q-page-container>
          <Pagina v-bind="$props" />
        </q-page-container>
      </q-layout>
    `,
  }
  return mount(anfitrion, { props, global })
}

vi.mock('vue-router', () => ({
  useRouter: () => routerFalso,
  RouterView: { template: '<div />' },
}))

beforeEach(() => {
  setActivePinia(createPinia())
  vi.restoreAllMocks()
  rutasNavegadas.length = 0
})

describe('BandejaPage', () => {
  it('pinta las solicitudes que devuelve la API', async () => {
    vi.spyOn(http, 'get').mockResolvedValue({
      data: { count: 1, results: [SOLICITUD] },
    })

    const wrapper = montarPagina(BandejaPage)
    await flushPromises()

    const texto = wrapper.text()
    expect(texto).toContain('SC-2026-000042')
    expect(texto).toContain('EN REVISION')
    expect(texto).toContain('Dirección General de Atención')
  })

  it('avisa cuando no hay nada visible en vez de mostrar una tabla vacía', async () => {
    vi.spyOn(http, 'get').mockResolvedValue({ data: { count: 0, results: [] } })

    const wrapper = montarPagina(BandejaPage)
    await flushPromises()

    expect(wrapper.text()).toContain('Todavía no hay solicitudes visibles')
  })

  it('muestra el error del backend', async () => {
    vi.spyOn(http, 'get').mockRejectedValue({
      response: { data: { detail: 'No autenticado.' } },
    })

    const wrapper = montarPagina(BandejaPage)
    await flushPromises()

    expect(wrapper.text()).toContain('No autenticado.')
  })
})

describe('NuevaSolicitudPage', () => {
  it('envía el alta y navega al seguimiento de la solicitud creada', async () => {
    vi.spyOn(http, 'get').mockResolvedValue({
      data: { results: [{ id: 1, clave: 'DGA', nombre: 'Dirección General' }] },
    })
    const post = vi.spyOn(http, 'post').mockResolvedValue({ data: { id: 42 } })

    const wrapper = montarPagina(NuevaSolicitudPage)
    await flushPromises()

    await wrapper.findComponent({ name: 'QForm' }).trigger('submit')
    await flushPromises()

    expect(post).toHaveBeenCalledWith(
      '/api/tramite/solicitudes-constancia/',
      expect.objectContaining({ metadatos: expect.objectContaining({ tipo_constancia: 'ESTUDIOS' }) }),
    )
    expect(rutasNavegadas).toEqual([{ name: 'seguimiento', params: { id: 42 } }])
  })

  it('pinta el error por campo que devuelve el backend y no navega', async () => {
    vi.spyOn(http, 'get').mockResolvedValue({ data: { results: [] } })
    vi.spyOn(http, 'post').mockRejectedValue({
      response: { data: { curp: ["El campo 'curp' es obligatorio."] } },
    })

    const wrapper = montarPagina(NuevaSolicitudPage)
    await flushPromises()

    await wrapper.findComponent({ name: 'QForm' }).trigger('submit')
    await flushPromises()

    expect(wrapper.text()).toContain("El campo 'curp' es obligatorio.")
    expect(rutasNavegadas).toEqual([])
  })
})

/**
 * Responde según la URL.
 *
 * El SeguimientoPanel monta su propio store y consulta la API de workflow
 * (`/sinpapel/api/...`) por su cuenta, en paralelo a la de dominio. Devolverle
 * la solicitud a todo lo que pida rompe sus internos: espera listas.
 */
function respuestaPorRuta(url) {
  if (url.startsWith('/api/tramite/')) return { data: SOLICITUD }
  if (url.includes('available-transitions')) {
    return { data: [{ id: 4, nombre: 'APROBADA', color: '#00C853' }] }
  }
  if (url.includes('history')) return { data: { count: 0, results: [] } }
  if (url.includes('requisitos') || url.includes('documentos')) return { data: [] }
  if (url.includes('metadatos')) return { data: { schema: [], values: {} } }
  return { data: {} }
}

describe('SeguimientoPage', () => {
  it('monta el SeguimientoPanel con el recurso y el pk correctos', async () => {
    vi.spyOn(http, 'get').mockImplementation((url) =>
      Promise.resolve(respuestaPorRuta(url)),
    )

    const wrapper = montarPagina(SeguimientoPage, { id: '42' })
    await flushPromises()

    expect(wrapper.find('[data-test="folio"]').text()).toBe('SC-2026-000042')

    const panel = wrapper.findComponent({ name: 'SeguimientoPanel' })
    expect(panel.exists()).toBe(true)
    expect(panel.props('resource')).toBe('solicitudes-constancia')
    expect(panel.props('pk')).toBe(42)
    expect(panel.props('basePath')).toBe('/sinpapel/api')
    expect(panel.props('currentState')).toBe('EN_REVISION')
    // La pestaña de SLA solo se ofrece a administración: el endpoint que
    // consume exige IsAdminUser.
    expect(panel.props('canEvaluateSla')).toBe(false)
  })

  it('el panel consulta la API de workflow, no la de dominio', async () => {
    const get = vi
      .spyOn(http, 'get')
      .mockImplementation((url) => Promise.resolve(respuestaPorRuta(url)))

    montarPagina(SeguimientoPage, { id: '42' })
    await flushPromises()

    const urls = get.mock.calls.map(([url]) => url)
    expect(urls).toContain('/api/tramite/solicitudes-constancia/42/')
    expect(
      urls.some((u) => u.startsWith('/sinpapel/api/solicitudes-constancia/42/')),
    ).toBe(true)
  })

  it('no monta el panel si la solicitud no es accesible', async () => {
    vi.spyOn(http, 'get').mockRejectedValue({
      response: { data: { detail: 'No encontrado.' } },
    })

    const wrapper = montarPagina(SeguimientoPage, { id: '99' })
    await flushPromises()

    expect(wrapper.text()).toContain('No encontrado.')
    expect(wrapper.findComponent({ name: 'SeguimientoPanel' }).exists()).toBe(false)
  })
})
