import { describe, expect, it } from 'vitest'

import { routes } from '@/router'

describe('router', () => {
  it('expone la ruta de inicio', () => {
    const inicio = routes.find((r) => r.name === 'inicio')

    expect(inicio).toBeDefined()
    expect(inicio.path).toBe('/')
  })

  it('no declara rutas duplicadas', () => {
    const paths = routes.map((r) => r.path)

    expect(new Set(paths).size).toBe(paths.length)
  })
})
