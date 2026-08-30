import { describe, expect, it, vi } from 'vitest'

import { http } from '@/api/http'
import { consultarSalud } from '@/api/salud'

describe('consultarSalud', () => {
  it('devuelve el estado que reporta el backend', async () => {
    vi.spyOn(http, 'get').mockResolvedValueOnce({ data: { estado: 'ok' } })

    await expect(consultarSalud()).resolves.toBe('ok')
    expect(http.get).toHaveBeenCalledWith('/salud/')
  })

  it('reporta la falta de conexión en vez de propagar el error', async () => {
    vi.spyOn(http, 'get').mockRejectedValueOnce(new Error('ECONNREFUSED'))

    await expect(consultarSalud()).resolves.toBe('sin conexión')
  })
})
