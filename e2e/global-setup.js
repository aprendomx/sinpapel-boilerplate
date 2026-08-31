/**
 * Comprobaciones previas al e2e.
 *
 * El e2e corre contra el stack real, así que puede fallar por tres motivos que
 * no tienen nada que ver con el código: el stack no está levantado, la base no
 * tiene cuentas, o el backend no responde. Sin este preflight, los tres se
 * manifiestan como un timeout esperando un selector — un síntoma que no dice
 * nada de la causa y que se depura mirando el sitio equivocado.
 */

const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost:5173'
const USUARIO = 'ana'
const CONTRASENA = 'demo12345'

function fallar(titulo, comoArreglarlo) {
  throw new Error(
    `\n\n✗ ${titulo}\n\n${comoArreglarlo}\n\n` +
      'El e2e necesita el stack levantado y sembrado; no monta el suyo.\n',
  )
}

async function pedir(ruta, opciones = {}) {
  try {
    return await fetch(`${BASE_URL}${ruta}`, { redirect: 'manual', ...opciones })
  } catch (causa) {
    fallar(
      `No hay nada escuchando en ${BASE_URL}`,
      'Levanta el stack:\n\n    make up\n    make seed\n\n' +
        `Detalle: ${causa.message}`,
    )
  }
}

export default async function globalSetup() {
  // 1. El frontend responde.
  const inicio = await pedir('/')
  if (!inicio.ok) {
    fallar(
      `El frontend respondió ${inicio.status} en ${BASE_URL}`,
      'Revisa los logs:\n\n    make logs',
    )
  }

  // 2. El backend responde a través del proxy. Que el frontend cargue no
  // implica que el backend esté detrás: el dev server sirve el index.html
  // igual, y el fallo aparecería mucho después.
  const salud = await pedir('/salud/')
  if (!salud.ok) {
    fallar(
      `El backend respondió ${salud.status} en ${BASE_URL}/salud/`,
      'Si el frontend carga pero esto falla, el proxy no cubre la ruta o el\n' +
        'backend no está sano:\n\n    make logs',
    )
  }

  // 3. Las cuentas de `make seed` existen. Es el fallo más frecuente y el peor
  // de diagnosticar: sin cuentas, el login devuelve el formulario otra vez con
  // un 200 y el test se cuelga esperando una pantalla que nunca llega.
  const formulario = await pedir('/cuentas/login/')
  const csrf = (formulario.headers.get('set-cookie') || '').match(/csrftoken=([^;]+)/)
  if (!csrf) {
    fallar(
      'El login no emitió cookie CSRF',
      'Es raro: revisa que /cuentas/ esté montado y proxeado.',
    )
  }

  const cuerpo = new URLSearchParams({
    username: USUARIO,
    password: CONTRASENA,
    csrfmiddlewaretoken: csrf[1],
    next: '/',
  })
  const entrada = await pedir('/cuentas/login/', {
    method: 'POST',
    headers: {
      'content-type': 'application/x-www-form-urlencoded',
      cookie: `csrftoken=${csrf[1]}`,
      referer: `${BASE_URL}/cuentas/login/`,
      origin: BASE_URL,
    },
    body: cuerpo,
  })

  // Un login correcto redirige; uno fallido devuelve el formulario con un 200.
  if (entrada.status !== 302) {
    fallar(
      `La cuenta '${USUARIO}' no puede iniciar sesión (HTTP ${entrada.status})`,
      'Falta sembrar las cuentas de demostración:\n\n    make seed\n\n' +
        'Crea una dependencia y una cuenta por rol. Solo corre con DEBUG=True.',
    )
  }
}
