import { describe, expect, it } from 'vitest'

import { routes } from '@/router'

describe('router', () => {
  it('expone las tres pantallas del trámite', () => {
    const nombres = routes.map((r) => r.name)

    expect(nombres).toEqual(['bandeja', 'nueva-solicitud', 'seguimiento'])
  })

  it('la bandeja es la raíz', () => {
    const bandeja = routes.find((r) => r.name === 'bandeja')

    expect(bandeja.path).toBe('/')
  })

  it('el seguimiento recibe el id como prop', () => {
    const seguimiento = routes.find((r) => r.name === 'seguimiento')

    expect(seguimiento.path).toBe('/solicitudes/:id')
    // Sin `props: true` la pantalla tendría que leer el route por dentro y no
    // podría montarse en un test sin router.
    expect(seguimiento.props).toBe(true)
  })

  it('no declara rutas duplicadas', () => {
    const paths = routes.map((r) => r.path)

    expect(new Set(paths).size).toBe(paths.length)
  })
})
