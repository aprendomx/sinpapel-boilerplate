import { expect, test } from '@playwright/test'

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

const CONTRASENA = 'demo12345'
const CURP = 'BEBB020202MDFXXX07'

async function entrarComo(page, usuario) {
  // Se limpian las cookies en vez de visitar el logout: desde Django 5 exige
  // POST, así que un GET no cierra nada y el login siguiente redirigiría con la
  // sesión anterior todavía viva.
  await page.context().clearCookies()

  // Por el login de la aplicación, no por el del admin: éste solo deja entrar a
  // cuentas `is_staff`, y de los cuatro roles que recorre esta prueba solo uno
  // lo es.
  await page.goto('/cuentas/login/?next=/')
  await page.locator('#id_username').fill(usuario)
  await page.locator('#id_password').fill(CONTRASENA)
  await page.locator('button[type=submit]').click()

  // Se comprueba que la sesión quedó abierta en vez de confiar en un
  // `networkidle`: con credenciales incorrectas Django devuelve otra vez el
  // formulario con un 200 y la prueba seguiría con una sesión anónima.
  await page.waitForURL((u) => !u.pathname.startsWith('/cuentas/login'))
}

function panel(page) {
  return page.locator('.sp-panel')
}

/**
 * Texto visible dentro del panel.
 *
 * El panel deja TODAS las pestañas en el DOM y oculta las inactivas con
 * `display: none`, así que un `getByText` normal alcanza contenido de pestañas
 * que nadie está viendo — incluidas las `<option>` de los formularios de carga.
 */
function textoVisible(page, texto) {
  return panel(page).locator('.sp-panel__body *:visible', { hasText: texto })
}

/** Un estado tal como lo PINTA la librería, que sustituye el guion bajo. */
function comoSeVe(estado) {
  return new RegExp(estado.replace(/_/g, '[ _]'))
}

/** Abre el diálogo de transición, lo llena y confirma. */
async function transicionar(page, destino, { firma = null, comentario = '' } = {}) {
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
  const resultado = await respuesta
  expect(resultado.status(), await resultado.text()).toBe(201)
  await expect(dialogo).toBeHidden()

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

async function pestana(page, nombre) {
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

test('de BORRADOR a APROBADA, con expediente completo y firma', async ({ page }) => {
  // ─── Solicitante: captura y presenta ──────────────────────────────────────
  await entrarComo(page, 'ana')

  // El catálogo de dependencias llega por API: sin esperarlo, el select se
  // abriría vacío. La espera se registra ANTES de navegar, por lo mismo que en
  // `pestana()`: la petición la lanza el componente al montarse, y si la
  // respuesta llega antes de que `goto` resuelva, un `waitForResponse` posterior
  // no la ve y se queda colgado hasta el timeout. En local el orden salía a
  // favor y en CI no: el test pasaba aquí y fallaba allí.
  const dependencias = page.waitForResponse((r) => r.url().includes('/dependencias/'))
  await page.goto('/solicitudes/nueva')
  await dependencias

  // Quasar reenvía `data-test` al input nativo, no al contenedor. En un
  // `q-select` ese input es el combobox: al pulsarlo despliega las opciones en
  // un portal (`.q-menu`), fuera del árbol del campo.
  await page.locator('[data-test=campo-dependencia]').click()
  await page.locator('.q-menu .q-item').first().click()
  await page.locator('[data-test=campo-curp]').fill(CURP)
  await page.locator('[data-test=enviar]').click()

  await page.waitForURL(/\/solicitudes\/\d+$/)
  const url = page.url()
  const folio = (await page.locator('[data-test=folio]').textContent()).trim()
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

/** Sube un documento del tipo indicado desde el panel de documentos. */
async function adjuntar(page, tipo) {
  await pestana(page, 'Documentos')
  const documentos = page.locator('.sp-panel')

  await documentos.locator('select').first().selectOption({ label: tipo })
  await documentos
    .locator('input[type=file]')
    .setInputFiles({
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
