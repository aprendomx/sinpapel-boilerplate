import { expect, test } from '@playwright/test'

import {
  campoMetadato,
  comoSeVe,
  entrarComo,
  guardarMetadato,
  intentarTransicionar,
  llevarHastaRevision,
  panel,
  pestana,
  transicionar,
} from '../helpers.js'

/**
 * La otra salida del trámite: el rechazo.
 *
 * El camino feliz lo cubre `tramite-completo.spec.js`. Aquí importan tres cosas
 * que aquél no toca y que solo se ven de extremo a extremo:
 *
 * - que `EN_REVISION → RECHAZADA` funcione con el rol que le corresponde
 *   —revisor, no firmante—, y sin firma, porque esa arista no la exige;
 * - que el predicado json_logic bloquee de verdad el rechazo sin motivo, en vez
 *   de que la UI lo permita y el dato quede vacío;
 * - que quien presenta la solicitud no pueda resolverla.
 */

test('de EN_REVISION a RECHAZADA, con el motivo asentado', async ({ page }) => {
  const url = await llevarHastaRevision(page, 'CACC030303HDFXXX05')

  // Revisor, no firmante: son roles distintos y cada arista nombra el suyo.
  await entrarComo(page, 'carla')
  await page.goto(url)

  await guardarMetadato(page, 'Motivo del rechazo', 'La CURP no corresponde a la persona.')

  // Sin firma: `requiere_firma` es False en esta arista, a diferencia de
  // APROBADA. Si la UI la exigiera igualmente, el diálogo no se cerraría.
  await transicionar(page, 'RECHAZADA', { comentario: 'No procede.' })
  await expect(panel(page).locator('.sp-badge')).toHaveText(comoSeVe('RECHAZADA'))

  // El motivo quedó asentado en el expediente, no solo en el comentario del
  // seguimiento. Se comprueba el `value` del control y no el texto de la
  // página: el dato vive dentro del campo, y un `hasText` no ve los valores.
  await pestana(page, 'Metadatos')
  await expect(campoMetadato(page, 'Motivo del rechazo')).toHaveValue(
    /no corresponde a la persona/i,
  )
})

test('el predicado bloquea el rechazo sin motivo', async ({ page }) => {
  const url = await llevarHastaRevision(page, 'DADD040404MDFXXX03')

  await entrarComo(page, 'carla')
  await page.goto(url)

  // Sin pasar por Metadatos: el motivo sigue vacío.
  const respuesta = await intentarTransicionar(page, 'RECHAZADA', {
    comentario: 'Intento resolver sin asentar el motivo.',
  })

  // El motor traduce el predicado incumplido a 403: `puede_cambiar_estado`
  // lanza `PermissionError`, no `ValueError`. Esperar un 400 aquí es el error
  // que la documentación invita a cometer.
  expect(respuesta.status(), await respuesta.text()).toBe(403)

  // Y el estado no se movió: el bloqueo es real, no cosmético.
  await page.reload()
  await expect(panel(page).locator('.sp-badge')).toHaveText(comoSeVe('EN_REVISION'))
})

test('quien presenta la solicitud no puede resolverla', async ({ page }) => {
  const url = await llevarHastaRevision(page, 'EAEE050505HDFXXX01')

  await entrarComo(page, 'ana')
  await page.goto(url)

  // El panel SÍ le ofrece APROBADA y RECHAZADA, y no es un fallo: el endpoint
  // de transiciones disponibles devuelve las salidas del estado actual sin
  // filtrar por rol —el docstring del motor lo dice: «No filtra por user
  // permissions, eso lo hace can_transition_to»—. La autoridad está en la
  // ejecución, no en el menú, y es ahí donde hay que comprobarla.
  // Con firma, aunque no le corresponda: `useTransition.validate()` bloquea el
  // envío en el cliente cuando la arista exige firma y no se eligió backend, y
  // entonces la petición no llega a salir. Sin esto el test comprobaría la
  // validación del formulario, no el permiso del rol, que es lo que interesa.
  const respuesta = await intentarTransicionar(page, 'APROBADA', {
    firma: 'fake',
    comentario: 'Intento aprobar mi propia solicitud.',
  })

  expect(respuesta.status(), await respuesta.text()).toBe(403)

  // Y no se movió: el rechazo del motor es real, no un mensaje en la UI.
  await page.reload()
  await expect(panel(page).locator('.sp-badge')).toHaveText(comoSeVe('EN_REVISION'))
})
