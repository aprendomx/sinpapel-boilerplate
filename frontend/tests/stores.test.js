import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { http } from '@/api/http'
import { useSolicitudesStore } from '@/stores/solicitudes'

describe('useSolicitudesStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
  })

  it('carga la bandeja paginada', async () => {
    vi.spyOn(http, 'get').mockResolvedValueOnce({
      data: { count: 3, results: [{ id: 1, folio: 'SC-2026-000001' }] },
    })
    const store = useSolicitudesStore()

    await store.cargar()

    expect(store.solicitudes).toHaveLength(1)
    expect(store.total).toBe(3)
    expect(store.cargando).toBe(false)
    expect(store.error).toBeNull()
  })

  it('expone el error del backend en vez de propagarlo', async () => {
    vi.spyOn(http, 'get').mockRejectedValueOnce({
      response: { data: { detail: 'No autenticado.' } },
    })
    const store = useSolicitudesStore()

    await store.cargar()

    expect(store.error).toEqual({ detail: 'No autenticado.' })
    expect(store.solicitudes).toEqual([])
    expect(store.cargando).toBe(false)
  })

  it('devuelve null y guarda los errores por campo cuando el alta se rechaza', async () => {
    vi.spyOn(http, 'post').mockRejectedValueOnce({
      response: { data: { curp: ["El campo 'curp' es obligatorio."] } },
    })
    const store = useSolicitudesStore()

    const creada = await store.crear({ dependencia: 1, metadatos: {} })

    expect(creada).toBeNull()
    expect(store.error.curp).toBeTruthy()
  })

  it('no acepta una respuesta sin forma de página', async () => {
    // Es lo que devuelve el dev server cuando el proxy no cubre la ruta: el
    // index.html con un 200. Sin este chequeo la bandeja saldría vacía como si
    // no hubiera solicitudes.
    vi.spyOn(http, 'get').mockResolvedValueOnce({ data: '<!DOCTYPE html>' })
    const store = useSolicitudesStore()

    await store.cargar()

    expect(store.error.detail).toContain('respuesta inesperada')
    expect(store.solicitudes).toEqual([])
  })

  it('devuelve la solicitud creada', async () => {
    vi.spyOn(http, 'post').mockResolvedValueOnce({ data: { id: 7 } })
    const store = useSolicitudesStore()

    const creada = await store.crear({ dependencia: 1, metadatos: { curp: 'X' } })

    expect(creada.id).toBe(7)
    expect(store.error).toBeNull()
  })
})
