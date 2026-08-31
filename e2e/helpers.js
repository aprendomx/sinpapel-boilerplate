/**
 * Utilidades compartidas por los e2e.
 *
 * Vivían dentro de `tramite-completo.spec.js`, que era el único e2e. Se
 * extraen sin cambiarlas: cada comentario documenta una trampa que costó una
 * sesión de depuración, y perderlos al copiar sería el peor resultado posible.
 *
 * Va fuera de `tests/` a propósito: Playwright toma como prueba todo lo que
 * empareje `*.spec.js` dentro de `testDir`, y un módulo de apoyo ahí dentro
 * confunde más de lo que ordena.
 */

import { expect } from '@playwright/test'

export const CONTRASENA = 'demo12345'

export async function entrarComo(page, usuario) {
  // Se limpian las cookies en vez de visitar el logout: desde Django 5 exige
  // POST, así que un GET no cierra nada y el login siguiente redirigiría con la
  // sesión anterior todavía viva.
  await page.context().clearCookies()

  // Por el login de la aplicación, no por el del admin: éste solo deja entrar a
  // cuentas `is_staff`, y de los cuatro roles que recorren estas pruebas solo
  // uno lo es.
  await page.goto('/cuentas/login/?next=/')
  await page.locator('#id_username').fill(usuario)
  await page.locator('#id_password').fill(CONTRASENA)
  await page.locator('button[type=submit]').click()

  // Se comprueba que la sesión quedó abierta en vez de confiar en un
  // `networkidle`: con credenciales incorrectas Django devuelve otra vez el
  // formulario con un 200 y la prueba seguiría con una sesión anónima.
  await page.waitForURL((u) => !u.pathname.startsWith('/cuentas/login'))
}

export function panel(page) {
  return page.locator('.sp-panel')
}

/**
 * Texto visible dentro del panel.
 *
 * El panel deja TODAS las pestañas en el DOM y oculta las inactivas con
 * `display: none`, así que un `getByText` normal alcanza contenido de pestañas
 * que nadie está viendo — incluidas las `<option>` de los formularios de carga.
 */
export function textoVisible(page, texto) {
  return panel(page).locator('.sp-panel__body *:visible', { hasText: texto })
}

/** Un estado tal como lo PINTA la librería, que sustituye el guion bajo. */
export function comoSeVe(estado) {
  return new RegExp(estado.replace(/_/g, '[ _]'))
}

/**
 * Abre el diálogo de transición, lo llena, confirma y devuelve la respuesta.
 *
 * No asierta el resultado: hay casos —un predicado que debe bloquear— donde el
 * fallo ES lo que se prueba. `transicionar()` es la variante que exige éxito.
 */
export async function intentarTransicionar(
  page,
  destino,
  { firma = null, comentario = '' } = {},
) {
  await page.waitForLoadState('networkidle')

  // `.last()` porque el remontaje del panel puede dejar un diálogo anterior en
  // el DOM; el recién montado es el que se ve.
  const dialogo = page.locator('.sp-dialog').last()
  const estados = dialogo.locator('select').first()

  // Abrir el diálogo puede no prender a la primera si el panel se está
  // remontando: se reintenta en vez de fallar por un adelanto de milisegundos.
  await expect(async () => {
    if (!(await estados.isVisible())) {
      await panel(page).getByRole('button', { name: 'Cambiar estado' }).click()
    }
    await expect(estados).toBeVisible({ timeout: 2000 })
  }).toPass({ timeout: 20000 })

  // Por `value`, no por etiqueta: la librería humaniza los nombres para
  // mostrarlos (`EN_REVISION` se pinta como «EN REVISION»), así que buscar por
  // texto nunca encontraría un estado con guion bajo.
  await estados.selectOption({ value: destino })
  if (comentario) {
    await dialogo.locator('textarea').first().fill(comentario)
  }
  if (firma) {
    // Firma polimórfica. En pruebas el backend usa FakeBackend; esta misma UI
    // ofrece FIEL en producción.
    await dialogo.locator('select').last().selectOption({ value: firma })
  }

  const respuesta = page.waitForResponse(
    (r) => r.url().includes('/transition/') && r.request().method() === 'POST',
  )
  await dialogo.getByRole('button', { name: 'Confirmar' }).click()
  return await respuesta
}

/** Transiciona exigiendo que el motor la acepte. */
export async function transicionar(page, destino, opciones = {}) {
  const resultado = await intentarTransicionar(page, destino, opciones)
  expect(resultado.status(), await resultado.text()).toBe(201)
  await expect(page.locator('.sp-dialog').last()).toBeHidden()

  // Tras la transición la pantalla relee la solicitud y remonta el panel, que
  // vuelve a pedir sus datos. Esperar a que la red se calme evita pulsar una
  // pestaña sobre el panel a medio remontar, que la reiniciaría.
  await page.waitForLoadState('networkidle')
}

/**
 * Selecciona una pestaña del panel y espera a que cargue su contenido.
 *
 * Cada pestaña consulta su propio endpoint al activarse; sin esperarlo, la
 * aserción siguiente correría sobre el panel todavía vacío.
 */
const ENDPOINT_DE_PESTANA = {
  Historial: '/history/',
  Requisitos: '/requisitos/',
  Documentos: '/documentos/',
  Metadatos: '/metadatos/',
}

export async function pestana(page, nombre) {
  // El panel se remonta tras cada transición: pulsar mientras tanto reiniciaría
  // la pestaña activa.
  await page.waitForLoadState('networkidle')

  const boton = panel(page).getByRole('button', { name: nombre, exact: true })
  await expect(boton).toBeVisible()

  // Si la pestaña ya está activa no se dispara ninguna petición, así que
  // esperarla colgaría el test hasta el timeout.
  const yaActiva = (await boton.getAttribute('class'))?.includes('is-active')
  if (yaActiva) {
    return
  }

  // La espera se registra ANTES del clic: la petición sale al activarse la
  // pestaña, y `networkidle` ya se habría cumplido para entonces. Sin ella se
  // asertaría sobre un panel que todavía dice "Cargando…".
  //
  // Acotada, porque no todas las pestañas piden algo al activarse: alguna carga
  // sus datos al montar el panel. Es un acelerador, no un requisito — las
  // aserciones que siguen reintentan por su cuenta.
  const endpoint = ENDPOINT_DE_PESTANA[nombre]
  const respuesta = endpoint
    ? page
        .waitForResponse((r) => r.url().includes(endpoint), { timeout: 5000 })
        .catch(() => null)
    : Promise.resolve(null)
  await boton.click()
  await respuesta
}

/** Sube un documento del tipo indicado desde el panel de documentos. */
export async function adjuntar(page, tipo) {
  await pestana(page, 'Documentos')
  const documentos = page.locator('.sp-panel')

  await documentos.locator('select').first().selectOption({ label: tipo })
  await documentos.locator('input[type=file]').setInputFiles({
    name: `${tipo}.pdf`,
    mimeType: 'application/pdf',
    buffer: Buffer.from('%PDF-1.4\n% documento de prueba\n'),
  })

  const subida = page.waitForResponse(
    (r) => r.url().includes('/documentos/') && r.request().method() === 'POST',
  )
  await documentos.getByRole('button', { name: /Subir|Cargar/i }).click()
  const respuesta = await subida
  expect(respuesta.status(), await respuesta.text()).toBe(201)
}

/**
 * Captura una solicitud nueva y devuelve su URL y su folio.
 *
 * Asume que la sesión ya es la de una persona solicitante.
 */
export async function crearSolicitud(page, curp) {
  // El catálogo de dependencias llega por API: sin esperarlo, el select se
  // abriría vacío. La espera se registra ANTES de navegar, por lo mismo que en
  // `pestana()`: la petición la lanza el componente al montarse, y si la
  // respuesta llega antes de que `goto` resuelva, un `waitForResponse`
  // posterior no la ve y se queda colgado hasta el timeout. En local el orden
  // salía a favor y en CI no: el test pasaba aquí y fallaba allí.
  const dependencias = page.waitForResponse((r) => r.url().includes('/dependencias/'))
  await page.goto('/solicitudes/nueva')
  await dependencias

  // Quasar reenvía `data-test` al input nativo, no al contenedor. En un
  // `q-select` ese input es el combobox: al pulsarlo despliega las opciones en
  // un portal (`.q-menu`), fuera del árbol del campo.
  await page.locator('[data-test=campo-dependencia]').click()
  await page.locator('.q-menu .q-item').first().click()
  await page.locator('[data-test=campo-curp]').fill(curp)
  await page.locator('[data-test=enviar]').click()

  await page.waitForURL(/\/solicitudes\/\d+$/)
  const folio = (await page.locator('[data-test=folio]').textContent()).trim()
  return { url: page.url(), folio }
}

/**
 * El control de un campo de metadatos, por su etiqueta.
 *
 * La etiqueta NO envuelve al campo: el formulario la pinta como un `div`
 * hermano, así que un `label:hasText` no encuentra nada y el test se cuelga
 * hasta el timeout sin decir por qué. Se sube al contenedor desde el texto.
 */
export function campoMetadato(page, etiqueta) {
  return panel(page)
    .getByText(etiqueta, { exact: true })
    .locator('xpath=..')
    .locator('input:not([type=checkbox]), textarea')
    .first()
}

/**
 * Escribe un campo de texto de la pestaña Metadatos y espera a que persista.
 *
 * Sin confirmar el PATCH, una transición posterior saldría antes de que el
 * dato exista y el predicado la rechazaría por una razón equivocada.
 */
export async function guardarMetadato(page, etiqueta, valor) {
  await pestana(page, 'Metadatos')
  await campoMetadato(page, etiqueta).fill(valor)

  const guardado = page.waitForResponse(
    (r) => r.url().includes('/metadatos/') && r.request().method() === 'PATCH',
  )
  await panel(page).locator('button:visible').filter({ hasText: 'Guardar' }).first().click()
  const respuesta = await guardado
  expect(respuesta.status(), await respuesta.text()).toBe(200)
}

/** Deja una solicitud en EN_REVISION, que es el punto de partida de la resolución. */
export async function llevarHastaRevision(page, curp) {
  await entrarComo(page, 'ana')
  const { url } = await crearSolicitud(page, curp)
  await transicionar(page, 'RECIBIDA', { comentario: 'Presento mi solicitud.' })

  await entrarComo(page, 'beto')
  await page.goto(url)
  await adjuntar(page, 'Identificación oficial')
  await adjuntar(page, 'Comprobante de domicilio')

  // El predicado json_logic exige además el cotejo explícito de ventanilla.
  await pestana(page, 'Metadatos')
  await panel(page).locator('input[type=checkbox]:visible').first().check()
  const guardado = page.waitForResponse(
    (r) => r.url().includes('/metadatos/') && r.request().method() === 'PATCH',
  )
  await panel(page).locator('button:visible').filter({ hasText: 'Guardar' }).first().click()
  const respuesta = await guardado
  expect(respuesta.status(), await respuesta.text()).toBe(200)

  await transicionar(page, 'EN_REVISION', { comentario: 'Requisitos cotejados.' })
  return url
}
