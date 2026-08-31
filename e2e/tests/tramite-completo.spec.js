import { expect, test } from '@playwright/test'

import {
  adjuntar,
  comoSeVe,
  crearSolicitud,
  entrarComo,
  panel,
  pestana,
  textoVisible,
  transicionar,
} from '../helpers.js'

/**
 * El trámite completo: de la captura a la resolución firmada.
 *
 * Recorre los tres roles que intervienen —solicitante, ventanilla y firmante—
 * porque el reparto de permisos es parte de lo que hay que probar: cada
 * transición la ejecuta quien tiene el rol, y el motor rechaza a los demás.
 *
 * Corre contra el stack real (`make up` + `make seed`), no contra mocks. Es la
 * única prueba del repositorio que ejercita a la vez el frontend, el proxy, la
 * sesión, el CSRF, la API de workflow, el motor, la firma y los side effects.
 * Varias de esas piezas solo fallan cuando se juntan.
 */

const CURP = 'BEBB020202MDFXXX07'

test('de BORRADOR a APROBADA, con expediente completo y firma', async ({ page }) => {
  // ─── Solicitante: captura y presenta ──────────────────────────────────────
  await entrarComo(page, 'ana')

  const { url, folio } = await crearSolicitud(page, CURP)
  expect(folio).toMatch(/^SC-\d{4}-\d{6}$/)

  await transicionar(page, 'RECIBIDA', { comentario: 'Presento mi solicitud.' })
  await expect(panel(page).locator('.sp-badge')).toHaveText(comoSeVe('RECIBIDA'))

  // El acuse en PDF lo emite un side effect al entrar a RECIBIDA: nadie lo sube.
  await pestana(page, 'Documentos')
  await expect(textoVisible(page, /Acuse de recepción/i).first()).toBeVisible()

  // ─── Ventanilla: coteja el expediente y envía a revisión ──────────────────
  await entrarComo(page, 'beto')
  await page.goto(url)

  // Los requisitos documentales de RECIBIDA bloquean el avance.
  await pestana(page, 'Requisitos')
  await expect(textoVisible(page, 'Identificación oficial').first()).toBeVisible()
  await expect(textoVisible(page, 'Comprobante de domicilio').first()).toBeVisible()

  await adjuntar(page, 'Identificación oficial')
  await adjuntar(page, 'Comprobante de domicilio')

  // El predicado json_logic exige además el cotejo explícito de ventanilla.
  await pestana(page, 'Metadatos')
  await panel(page).locator('input[type=checkbox]:visible').first().check()

  // Se espera al PATCH: sin confirmar que el cotejo persistió, la transición
  // saldría antes y el predicado la rechazaría.
  const guardado = page.waitForResponse(
    (r) => r.url().includes('/metadatos/') && r.request().method() === 'PATCH',
  )
  await panel(page).locator('button:visible').filter({ hasText: 'Guardar' }).first().click()
  const respuestaGuardado = await guardado
  expect(respuestaGuardado.status(), await respuestaGuardado.text()).toBe(200)

  await transicionar(page, 'EN_REVISION', { comentario: 'Requisitos cotejados.' })
  await expect(panel(page).locator('.sp-badge')).toHaveText(comoSeVe('EN_REVISION'))

  // ─── Firmante: resuelve favorablemente, con firma ─────────────────────────
  await entrarComo(page, 'diana')
  await page.goto(url)

  // `requiere_firma=True` vive en la configuración de la transición, y el
  // preview lo anuncia para que la UI pida la firma por adelantado.
  await pestana(page, 'Previsualizar')
  await panel(page).locator('select:visible').first().selectOption({ value: 'APROBADA' })
  await expect(textoVisible(page, /firma/i).first()).toBeVisible()

  await transicionar(page, 'APROBADA', { firma: 'fake', comentario: 'Procede.' })
  await expect(panel(page).locator('.sp-badge')).toHaveText(comoSeVe('APROBADA'))

  // El oficio de resolución en DOCX lo emite el side effect de APROBADA.
  await pestana(page, 'Documentos')
  await expect(textoVisible(page, /Oficio de resolución/i).first()).toBeVisible()

  // La auditoría registró quién tocó el expediente.
  //
  // Esta pestaña muestra `HistoricalRecords` —cambios de fila— y no
  // `SeguimientoWorkflow`: el endpoint `history/` del framework expone lo
  // primero. Lo interesante aquí es que `history_user` viene poblado, que es
  // justo lo que se pierde si falta `HistoryRequestMiddleware`.
  await pestana(page, 'Historial')
  const historial = panel(page).locator('.sp-timeline')
  await expect(historial).toBeVisible()
  await expect(historial).toContainText('Creado')
  for (const actor of ['ana', 'beto', 'diana']) {
    await expect(historial).toContainText(actor)
  }
})
